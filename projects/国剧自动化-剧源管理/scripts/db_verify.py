import pymysql
import os

conn = pymysql.connect(
    host=os.environ.get('DB_HOST', 'localhost'),
    port=int(os.environ.get('DB_PORT', 4000)),
    user=os.environ.get('DB_USER', 'root'),
    password=os.environ.get('DB_PASSWORD', ''),
    database=os.environ.get('DB_DATABASE', 'sharpengine_ads_asset_prod'),
    charset='utf8mb4'
)

cursor = conn.cursor()

print("=== 数据库校验：国剧AI复刻 ===\n")

# 1. 检查AsyncJobInfo表结构
print("1. AsyncJobInfo 表结构：")
cursor.execute("DESC AsyncJobInfo")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]}")

# 2. 检查JobType=8（剧源向量处理）的记录
print("\n2. JobType=8（剧源向量处理）最新记录：")
cursor.execute("""
    SELECT Id, JobType, DataId, Status, CreateTime, CreatorUid 
    FROM AsyncJobInfo 
    WHERE JobType = 8 
    ORDER BY CreateTime DESC 
    LIMIT 5
""")
for row in cursor.fetchall():
    status_map = {0:'已创建', 1:'执行中', 2:'成功', 3:'失败', 999:'异常'}
    print(f"  ID={row[0]}, Type={row[1]}, DataId={row[2]}, Status={status_map.get(row[3],row[3])}, Time={row[4]}, Creator={row[5]}")

# 3. 检查JobType=9（AI复刻）的记录
print("\n3. JobType=9（AI复刻）最新记录：")
cursor.execute("""
    SELECT Id, JobType, DataId, Status, CreateTime, CreatorUid 
    FROM AsyncJobInfo 
    WHERE JobType = 9 
    ORDER BY CreateTime DESC 
    LIMIT 5
""")
for row in cursor.fetchall():
    status_map = {0:'已创建', 1:'执行中', 2:'成功', 3:'失败', 999:'异常'}
    print(f"  ID={row[0]}, Type={row[1]}, DataId={row[2]}, Status={status_map.get(row[3],row[3])}, Time={row[4]}, Creator={row[5]}")

# 4. 统计各JobType数量
print("\n4. 各JobType统计：")
cursor.execute("""
    SELECT JobType, COUNT(*) as cnt 
    FROM AsyncJobInfo 
    GROUP BY JobType 
    ORDER BY JobType
""")
for row in cursor.fetchall():
    print(f"  JobType={row[0]}: {row[1]} 条")

conn.close()
print("\n=== 数据库校验完成 ===")
