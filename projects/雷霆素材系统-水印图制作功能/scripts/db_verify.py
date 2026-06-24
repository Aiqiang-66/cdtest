import pymysql
import os

# Connect to TiDB
conn = pymysql.connect(
    host=os.environ.get('DB_HOST', 'localhost'),
    port=int(os.environ.get('DB_PORT', 4000)),
    user=os.environ.get('DB_USER', 'root'),
    password=os.environ.get('DB_PASSWORD', ''),
    database=os.environ.get('DB_DATABASE', 'sharpengine_ads_asset_prod'),
    charset='utf8mb4'
)

cursor = conn.cursor()

print("=== DB Check 1: BurnResource - latest watermark records ===")
cursor.execute("""
    SELECT Id, Title, ResourceType, Core, Ratio, TgtType, TgtCode, TgtId, TgtName, 
           Language, IsEnabled, CreateTime, Creator
    FROM BurnResource 
    WHERE ResourceType = 1 AND TgtType = 2 AND Ratio IN (916, 45)
    ORDER BY CreateTime DESC 
    LIMIT 10
""")
rows = cursor.fetchall()
print(f"Found {len(rows)} records")
for row in rows:
    print(f"  Row: {row}")

print("\n=== DB Check 2: BurnResourceTask - latest tasks ===")
try:
    cursor.execute("""
        SELECT Id, ResourceType, TgtType, Core, Status, CreateTime, Creator
        FROM BurnResourceTask 
        ORDER BY CreateTime DESC 
        LIMIT 10
    """)
    rows2 = cursor.fetchall()
    print(f"Found {len(rows2)} records")
    for row in rows2:
        print(f"  ID={row[0]}, ResourceType={row[1]}, TgtType={row[2]}, Core={row[3]}, Status={row[4]}, Time={row[5]}, Creator={row[6]}")
except Exception as e:
    print(f"BurnResourceTask query failed: {e}")
    # Try to find the table
    cursor.execute("SHOW TABLES LIKE '%Burn%'")
    tables = cursor.fetchall()
    print(f"Tables with 'Burn': {[t[0] for t in tables]}")

print("\n=== DB Check 3: Count by TgtCode for recent watermark ===")
cursor.execute("""
    SELECT TgtCode, Ratio, COUNT(*) as cnt, MAX(CreateTime) as latest
    FROM BurnResource 
    WHERE ResourceType = 1 AND TgtType = 2
    GROUP BY TgtCode, Ratio
    ORDER BY latest DESC
    LIMIT 10
""")
rows3 = cursor.fetchall()
for row in rows3:
    print(f"  TgtCode={row[0]}, Ratio={row[1]}, Count={row[2]}, Latest={row[3]}")

conn.close()
print("\nDB verification complete!")
