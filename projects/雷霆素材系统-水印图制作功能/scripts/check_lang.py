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

# 查看 Series=XY 的各语言版本 LanguageCode 格式
cursor.execute("""
    SELECT VideoId, LanguageCode, Language, VideoName 
    FROM VideoInfo 
    WHERE VideoCodeSeries = 'XY' AND IsDelete = 0
    ORDER BY LanguageCode
    LIMIT 30
""")
print('=== Series=XY 语言版本（前30条）===')
for r in cursor.fetchall():
    print(f'  VideoId={r[0]}, LangCode={r[1]}, Language={r[2]}, Name={r[3][:40]}')

# 查看所有不同的 LanguageCode
print()
cursor.execute("""
    SELECT LanguageCode, COUNT(*) as cnt 
    FROM VideoInfo 
    WHERE VideoCodeSeries = 'XY' AND IsDelete = 0
    GROUP BY LanguageCode 
    ORDER BY LanguageCode
""")
print('=== LanguageCode 分布 ===')
for r in cursor.fetchall():
    print(f'  {r[0]}: {r[1]} 条')

conn.close()
