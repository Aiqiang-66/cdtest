import pymysql
import os

# 连接数据库
conn = pymysql.connect(
    host=os.environ.get('DB_HOST', 'localhost'),
    port=int(os.environ.get('DB_PORT', '4000')),
    user=os.environ.get('DB_USER', 'root'),
    password=os.environ.get('DB_PASSWORD', ''),
    database=os.environ.get('DB_DATABASE', 'sharpengine_ads_asset_prod'),
    charset='utf8mb4'
)

cursor = conn.cursor()

print("=== 数据库校验：自动化扩语种 ===\n")

# 1. 检查AIMixedClipTask表
print("1. AIMixedClipTask 表结构：")
cursor.execute("DESC AIMixedClipTask")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]}")

# 2. 检查最近的任务
print("\n2. 最近的任务：")
cursor.execute("""
    SELECT Id, CreateTime 
    FROM AIMixedClipTask 
    ORDER BY CreateTime DESC 
    LIMIT 5
""")
for row in cursor.fetchall():
    print(f"  ID={row[0]}, Time={row[1]}")

# 3. 检查AIMixedClipSubTask表
print("\n3. AIMixedClipSubTask 表结构：")
cursor.execute("DESC AIMixedClipSubTask")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]}")

# 4. 检查最近的子任务
print("\n4. 最近的子任务：")
cursor.execute("""
    SELECT Id, TaskId, CreateTime 
    FROM AIMixedClipSubTask 
    ORDER BY CreateTime DESC 
    LIMIT 5
""")
for row in cursor.fetchall():
    print(f"  ID={row[0]}, TaskId={row[1]}, Time={row[2]}")

# 5. 检查语言相关数据
print("\n5. 语言相关数据（VideoInfo表）：")
cursor.execute("""
    SELECT VideoId, LanguageCode, VideoName 
    FROM sharpengine_ads_global.VideoInfo 
    WHERE VideoId = 'X2035' 
    LIMIT 10
""")
for row in cursor.fetchall():
    print(f"  VideoId={row[0]}, Language={row[1]}, Name={row[2]}")

# 6. 检查扩语种任务
print("\n6. 扩语种任务（SubTaskType=4）：")
cursor.execute("""
    SELECT Id, SubTaskType, FissionLanguages, CreateTime, Creator 
    FROM AIMixedClipTask 
    WHERE SubTaskType = 4 
    ORDER BY CreateTime DESC 
    LIMIT 5
""")
for row in cursor.fetchall():
    print(f"  ID={row[0]}, Type={row[1]}, Languages={row[2]}, Time={row[3]}, Creator={row[4]}")

conn.close()
print("\n=== 数据库校验完成 ===")
