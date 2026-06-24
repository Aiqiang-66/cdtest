import pymysql
import os

conn = pymysql.connect(
    host=os.environ.get('DB_HOST', 'localhost'),
    port=int(os.environ.get('DB_PORT', '4000')),
    user=os.environ.get('DB_USER', 'root'),
    password=os.environ.get('DB_PASSWORD', ''),
    database=os.environ.get('DB_DATABASE', 'sharpengine_ads_global'),
    charset='utf8mb4'
)

cursor = conn.cursor()

print("=== 查询X2035相关数据 ===")
cursor.execute("SELECT VideoId, LanguageCode, VideoName FROM VideoInfo WHERE VideoId LIKE '%2035%' LIMIT 10")
for row in cursor.fetchall():
    print(f"VideoId={row[0]}, Language={row[1]}, Name={row[2]}")

print("\n=== 查询最近的扩语种任务详情 ===")
cursor.execute("""
    SELECT Id, SubTaskType, FissionLanguages, CreateTime, Creator 
    FROM sharpengine_ads_asset_prod.AIMixedClipTask 
    WHERE SubTaskType = 4 
    ORDER BY CreateTime DESC 
    LIMIT 5
""")
for row in cursor.fetchall():
    print(f"ID={row[0]}, Type={row[1]}, Languages={row[2]}, Time={row[3]}, Creator={row[4]}")

conn.close()
