import pymysql
import os

conn = pymysql.connect(
    host=os.environ.get('DB_HOST', 'localhost'),
    port=int(os.environ.get('DB_PORT', 4000)),
    user=os.environ.get('DB_USER', 'root'),
    password=os.environ.get('DB_PASSWORD', ''),
    database='sharpengine_ads_global',
    charset='utf8mb4'
)
cursor = conn.cursor()

# 查看 VideoInfo 表结构
cursor.execute('DESC VideoInfo')
print('=== VideoInfo 表结构 ===')
for r in cursor.fetchall():
    print(f'  {r[0]}: {r[1]}')

print()
# 查看 14583322 对应的各语言版本
cursor.execute("SELECT VideoId, LanguageCode, AllEpis FROM VideoInfo WHERE VideoId = 14583322 OR SeriesId = 14583322 LIMIT 5")
print('=== VideoId=14583322 ===')
for r in cursor.fetchall():
    print(f'  VideoId={r[0]}, Lang={r[1]}, Epis={r[2]}')

# 查看 Series 字段
print()
cursor.execute("SELECT VideoId, LanguageCode, SeriesId, AllEpis FROM VideoInfo WHERE VideoId = 14583322 LIMIT 1")
for r in cursor.fetchall():
    print(f'  VideoId={r[0]}, Lang={r[1]}, SeriesId={r[2]}, Epis={r[3]}')

conn.close()
