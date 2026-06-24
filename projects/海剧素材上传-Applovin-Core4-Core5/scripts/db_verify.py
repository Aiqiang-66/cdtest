import pymysql
import os
import json

# DB connection from env vars (required for this script)
conn = pymysql.connect(
    host=os.environ.get('DB_HOST', ''),
    port=int(os.environ.get('DB_PORT', '4000')),
    user=os.environ.get('DB_USER', ''),
    password=os.environ.get('DB_PASSWORD', ''),
    database='sharpengine_ads_asset_prod',
    charset='utf8mb4'
)

cursor = conn.cursor()

print("=" * 60)
print("TC-AL-018: MaterialUploadLog Core字段验证")
print("=" * 60)

# 1. 检查 Applovin (SourceChlType=6) 且 Core=4/5 的最新上传记录
print("\n1. Applovin Core4/Core5 最新上传记录:")
cursor.execute("""
    SELECT Id, MaterialId, CODE, Core, UploadStatus, AssetGuid, CreateTime, CosPath
    FROM MaterialUploadLog
    WHERE SourceChlType = 6 AND Core IN (4, 5)
    ORDER BY Id DESC
    LIMIT 10
""")
rows = cursor.fetchall()
if rows:
    for r in rows:
        status_map = {0:'待上传', 1:'上传中', 2:'失败', 3:'部分成功', 4:'成功'}
        print(f"  ID={r[0]}, MatId={r[1]}, Code={r[2]}, Core={r[3]}, Status={status_map.get(r[4],r[4])}, AssetGuid={r[5][:20] if r[5] else 'NULL'}, Time={r[6]}")
else:
    print("  无 Core=4/5 的 Applovin 上传记录")

# 2. 对比 Core1 的上传统计
print("\n2. Applovin 各Core上传数量:")
cursor.execute("""
    SELECT Core, COUNT(*) as cnt, MAX(CreateTime) as latest
    FROM MaterialUploadLog
    WHERE SourceChlType = 6
    GROUP BY Core
    ORDER BY Core
""")
for r in cursor.fetchall():
    print(f"  Core{r[0]}: {r[1]} 条, 最新={r[2]}")

# 3. 检查是否有 Core4/Core5 的素材关联到 MaterialInfo
print("\n3. Core4/Core5 素材关联 MaterialInfo:")
cursor.execute("""
    SELECT mi.Id, mi.TgtCode, mi.Core, mi.MaterialStatus, mi.CreateTime
    FROM MaterialInfo mi
    JOIN MaterialUploadLog mul ON mi.Id = mul.MaterialId
    WHERE mul.SourceChlType = 6 AND mul.Core IN (4, 5)
    ORDER BY mi.Id DESC
    LIMIT 10
""")
rows = cursor.fetchall()
if rows:
    status_map = {0:'待处理', 1:'处理中', 2:'成功', 3:'失败', 9:'开始烧录', 10:'烧录完成待审核'}
    for r in rows:
        print(f"  MatInfoId={r[0]}, Code={r[1]}, Core={r[2]}, Status={status_map.get(r[3],r[3])}, Time={r[4]}")
else:
    print("  无关联的 MaterialInfo 记录")

# 4. 检查 MaterialConvertCoreTask 转Core链
print("\n4. MaterialConvertCoreTask 转Core(C4/C5)任务链:")
cursor.execute("""
    SELECT Id, ConvertType, CovertId, Status, CreateTime
    FROM MaterialConvertCoreTask
    WHERE ConvertType IN (4, 5)
    ORDER BY Id DESC
    LIMIT 10
""")
rows = cursor.fetchall()
if rows:
    for r in rows:
        print(f"  ID={r[0]}, ConvertType={r[1]}, CovertId={r[2]}, Status={r[3]}, Time={r[4]}")
else:
    print("  无 ConvertType=4/5 的任务")

# 5. 检查 GeneratePicture 相关表
print("\n5. GeneratePictureMaterial 表是否存在:")
cursor.execute("SHOW TABLES LIKE '%GeneratePicture%'")
tables = cursor.fetchall()
print(f"  相关表: {[t[0] for t in tables]}")

if tables:
    print("\n6. GeneratePictureMaterial 最新记录:")
    for table in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
            cnt = cursor.fetchone()[0]
            print(f"  {table[0]}: {cnt} 条")
        except Exception as e:
            print(f"  {table[0]}: 查询失败 - {e}")

conn.close()
print("\n" + "=" * 60)
print("DB验证完成")
print("=" * 60)
