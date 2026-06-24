import pymysql
import os

conn = pymysql.connect(
    host=os.environ.get('DB_HOST', 'localhost'),
    port=int(os.environ.get('DB_PORT', 4000)),
    user=os.environ.get('DB_USER', 'root'),
    password=os.environ.get('DB_PASSWORD', ''),
    database='sharpengine_ads_asset_prod',
    charset='utf8mb4'
)
cursor = conn.cursor()

print('=== BurnResource - 按Core统计今日新增(17:30后) ===')
cursor.execute("SELECT Core, COUNT(*) as cnt FROM BurnResource WHERE ResourceType=1 AND TgtType=2 AND CreateTime >= '2026-05-26 17:30:00' GROUP BY Core ORDER BY Core")
for r in cursor.fetchall():
    print(f'  Core{r[0]}: {r[1]} 条')

print()
print('=== Core4 最新5条 ===')
cursor.execute("SELECT Title, Core, Ratio, TgtCode, CreateTime FROM BurnResource WHERE ResourceType=1 AND Core=4 AND CreateTime >= '2026-05-26 17:30:00' ORDER BY CreateTime DESC LIMIT 5")
for r in cursor.fetchall():
    print(f'  {r[0][:50]}, Core={r[1]}, Ratio={r[2]}, Code={r[3]}, Time={r[4]}')

print()
print('=== Core5 最新5条 ===')
cursor.execute("SELECT Title, Core, Ratio, TgtCode, CreateTime FROM BurnResource WHERE ResourceType=1 AND Core=5 AND CreateTime >= '2026-05-26 17:30:00' ORDER BY CreateTime DESC LIMIT 5")
for r in cursor.fetchall():
    print(f'  {r[0][:50]}, Core={r[1]}, Ratio={r[2]}, Code={r[3]}, Time={r[4]}')

print()
print('=== Core18 最新5条 ===')
cursor.execute("SELECT Title, Core, Ratio, TgtCode, CreateTime FROM BurnResource WHERE ResourceType=1 AND Core=18 AND CreateTime >= '2026-05-26 17:30:00' ORDER BY CreateTime DESC LIMIT 5")
for r in cursor.fetchall():
    print(f'  {r[0][:50]}, Core={r[1]}, Ratio={r[2]}, Code={r[3]}, Time={r[4]}')

conn.close()
print('\nDB校验完成')
