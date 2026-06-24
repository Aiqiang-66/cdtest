"""
水印图制作 - 接口自动化批量下发任务
从数据库查询各语言代号对应的剧ID，批量调用 BatchAdd 接口下发水印图制作任务
"""
import pymysql
import requests
import json
import os
import time
from datetime import datetime

# ============ 配置 ============
DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_PORT = int(os.environ.get('DB_PORT', '4000'))
DB_USER = os.environ.get('DB_USER', 'root')
DB_PASSWORD = os.environ.get('DB_PASSWORD', '')
DB_GLOBAL = os.environ.get('DB_GLOBAL', 'sharpengine_ads_global')

API_URL = 'https://adassetserver-cn-new-test1.changdu.ltd/api/BurnResourceTask/BatchAdd'

# 从环境变量获取 Token
TOKEN = os.environ.get('API_TOKEN', '')

# 需要检索的语言代号列表（数据库中是大小写混合格式）
# 数据库实际 LanguageCode: AR, CN, DE, EN, FR, FT, HI, ID, IT, JP, KR, PL, PT, RU, SP, TH, TL, TR, VI
LANG_CODES = ['FT', 'EN', 'SP', 'PT', 'FR', 'RU', 'JP', 'ID', 'TH', 'VI',
              'KR', 'TL', 'DE', 'IT', 'AR', 'HI', 'PL', 'TR']

# 下发任务的尺寸
RATIOS = [916, 45, 11, 169]

# Core 类型
CORES = [1, 4, 5, 18]

# 基准剧ID（用于查找同系列各语言版本）
BASE_VIDEO_ID = '14583322'

# ============ 步骤1：查询数据库获取各语言剧ID ============
print('=' * 60)
print('步骤1：查询数据库获取各语言代号对应的剧ID')
print('=' * 60)

conn = pymysql.connect(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, database=DB_GLOBAL, charset='utf8mb4')
cursor = conn.cursor()

# 先查基准剧的 Series 信息
cursor.execute("SELECT VideoId, LanguageCode, VideoCode, VideoCodeSeries, AllEpis FROM VideoInfo WHERE VideoId = %s", (BASE_VIDEO_ID,))
base = cursor.fetchone()
if base:
    print(f'基准剧: VideoId={base[0]}, Lang={base[1]}, Code={base[2]}, Series={base[3]}, Epis={base[4]}')
    series_code = base[3]  # VideoCodeSeries 用于关联同系列
else:
    print(f'未找到基准剧 VideoId={BASE_VIDEO_ID}')
    conn.close()
    exit(1)

# 通过 VideoCodeSeries 查找同系列各语言版本
print(f'\n通过 Series={series_code} 查找各语言版本...')
cursor.execute("""
    SELECT VideoId, LanguageCode, VideoName, AllEpis 
    FROM VideoInfo 
    WHERE VideoCodeSeries = %s AND IsDelete = 0
    ORDER BY LanguageCode
""", (series_code,))

all_videos = cursor.fetchall()
print(f'找到 {len(all_videos)} 个语言版本')

# 按语言代号分组
lang_video_map = {}
for v in all_videos:
    vid, lang, name, epis = v
    lang_video_map[lang] = {'video_id': vid, 'name': name, 'epis': epis}

print('\n各语言版本:')
for lang in LANG_CODES:
    if lang in lang_video_map:
        v = lang_video_map[lang]
        print(f'  [{lang}] VideoId={v["video_id"]}, Name={v["name"][:40]}, Epis={v["epis"]}')
    else:
        print(f'  [{lang}] 未找到')

conn.close()

# ============ 步骤2：构建下发任务列表 ============
print('\n' + '=' * 60)
print('步骤2：构建下发任务列表')
print('=' * 60)

# 收集所有需要下发的 tgtIds
tgt_ids = []
for lang in LANG_CODES:
    if lang in lang_video_map:
        tgt_ids.append(lang_video_map[lang]['video_id'])

print(f'共 {len(tgt_ids)} 个剧ID待下发: {tgt_ids}')

# ============ 步骤3：批量调用API下发任务（每个语言单独下发） ============
print('\n' + '=' * 60)
print('步骤3：批量调用API下发任务（每个语言单独下发）')
print('=' * 60)

headers = {
    'Authorization': f'Bearer {TOKEN}',
    'Content-Type': 'application/json',
    'Referer': 'https://sc-test.changdu.ltd/',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

results = []
total_success = 0
total_fail = 0
total_skip = 0

for core in CORES:
    print(f'\n--- Core{core} ---')
    
    for tgt_id in tgt_ids:
        # 找到对应的语言代号
        lang = None
        for lc in LANG_CODES:
            if lc in lang_video_map and lang_video_map[lc]['video_id'] == tgt_id:
                lang = lc
                break
        
        payload = {
            "resourceType": 1,
            "tgtType": 2,
            "ratios": RATIOS,
            "core": core,
            "tgtIds": [tgt_id]
        }
        
        try:
            response = requests.post(API_URL, json=payload, headers=headers, timeout=30)
            data = response.json()
            
            is_success = data.get('isSuccess', False)
            message = data.get('message', '')
            items = data.get('data', [])
            
            for item in items:
                item_ok = item.get('success')
                item_msg = item.get('message', '')
                ratio = item.get('ratio')
                if item_ok:
                    total_success += 1
                    print(f'  ✅ [{lang}] {tgt_id} ratio={ratio} Core{core} -> 创建成功 taskId={item.get("taskId")}')
                elif '已存在' in item_msg or '制作中' in item_msg:
                    total_skip += 1
                    # print(f'  ⏭ [{lang}] {tgt_id} ratio={ratio} Core{core} -> {item_msg}')
                else:
                    total_fail += 1
                    print(f'  ❌ [{lang}] {tgt_id} ratio={ratio} Core{core} -> {item_msg}')
            
        except Exception as e:
            total_fail += 1
            print(f'  ❌ [{lang}] {tgt_id} Core{core} 请求异常: {e}')
        
        time.sleep(0.1)  # 避免请求过快
    
    time.sleep(0.5)

# ============ 步骤4：汇总报告 ============
print('\n' + '=' * 60)
print('步骤4：汇总报告')
print('=' * 60)
print(f'时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
print(f'Core类型: {CORES}')
print(f'尺寸: {RATIOS}')
print(f'语言数: {len(tgt_ids)}')
print(f'总请求数: {len(CORES) * len(tgt_ids)}')
print(f'成功: {total_success}, 跳过(已存在): {total_skip}, 失败: {total_fail}')

print('\n自动化下发任务完成!')
