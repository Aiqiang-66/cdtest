import pymysql
from datetime import datetime, timedelta

conn = pymysql.connect(host='tidb-in.changdu.ltd',port=4000,user='root',password='987654321**',database='sharpengine_ads_asset_prod',charset='utf8mb4')
cursor = conn.cursor()

# SC XY14素材
cursor.execute("SELECT Id, MaterialName, Code, SourceChlType, SyncMaterialUploadLogId, TgtType, TgtId, SyncCore, AssetGuid FROM MaterialUploadLog WHERE Code LIKE %s AND SourceChlType=7 LIMIT 10", ('%XY14%',))
rows = cursor.fetchall()
print('=== SC素材 Code=XY14 SourceChlType=7 ===')
for r in rows:
    print(f'  Id={r[0]}, Name={str(r[1])[:60]}, Code={r[2]}, ChlType={r[3]}, SyncId={r[4]}, Tgt={r[5]}, Core={r[7]}, Guid={str(r[8])[:30]}')

# 各数量统计
cursor.execute('SELECT SourceChlType, COUNT(*) as cnt FROM MaterialUploadLog WHERE Code LIKE %s GROUP BY SourceChlType', ('%XY14%',))
print('\n=== XY14按SourceChlType分布 ===')
type_map = {1:'Facebook', 2:'TikTok', 3:'Google', 4:'分销', 5:'Moloco', 6:'Applovin', 7:'Snapchat', 8:'Mintegral'}
for r in cursor.fetchall():
    print(f'  {type_map.get(r[0], r[0])}: {r[1]}')

cursor.execute('SELECT COUNT(*) FROM MaterialUploadLog WHERE SourceChlType=7')
print(f'\nSC素材总数: {cursor.fetchone()[0]}')

cursor.execute('SELECT COUNT(*) FROM MaterialUploadLog WHERE Code LIKE %s AND SourceChlType=7', ('%XY14%',))
print(f'SC XY14素材数: {cursor.fetchone()[0]}')

# 最新SC同步任务
since = (datetime.now() - timedelta(hours=48)).strftime('%Y-%m-%d %H:%M:%S')
cursor.execute("""
    SELECT t.Id, t.SourceUploadLogId, t.Status, t.TgtType, t.TgtCode, t.CreateTime, ul.Code, ul.SourceChlType 
    FROM MaterialSyncTask t 
    JOIN MaterialUploadLog ul ON t.SourceUploadLogId = ul.Id
    WHERE t.CreateTime >= %s AND (ul.SourceChlType=7 OR t.TgtType=7) 
    ORDER BY t.CreateTime DESC LIMIT 10
""", (since,))
rows = cursor.fetchall()
print(f'\n=== 最近48h SC相关同步任务 ===')
for r in rows:
    tgt_type_map = {1:'FB', 2:'TT', 3:'UAC', 7:'SC'}
    chl_map = {1:'FB', 2:'TT', 7:'SC'}
    status_map = {1:'待处理', 2:'完成', 3:'失败'}
    print(f'  Id={r[0]}, Status={status_map.get(r[2], r[2])}, Src={chl_map.get(r[7], r[7])}, Tgt={tgt_type_map.get(r[3], r[3])}({r[4]}), Time={r[5]}, Code={r[6]}')

# 表数据量
print('\n=== 表行数 ===')
tables = ['MaterialSyncTask','MaterialSyncSubTask','MaterialUploadLog','MaterialInfo']
for t in tables:
    cursor.execute(f'SELECT COUNT(*) FROM {t}')
    print(f'  {t}: {cursor.fetchone()[0]}')

conn.close()
