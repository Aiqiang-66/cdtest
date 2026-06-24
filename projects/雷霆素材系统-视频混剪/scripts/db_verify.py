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

print('=== TaskInfo - 最新视频混剪任务 ===')
cursor.execute("SELECT Id, TgtCode, Creator, CreateTime FROM TaskInfo WHERE TgtCode LIKE '%XY14%' ORDER BY CreateTime DESC LIMIT 5")
for r in cursor.fetchall():
    print(f'  ID={r[0]}, Code={r[1]}, Creator={r[2]}, Time={r[3]}')

print()
print('=== SubTaskInfo - 最新子任务 ===')
cursor.execute('SELECT Id, TaskId, CreateTime FROM SubTaskInfo ORDER BY CreateTime DESC LIMIT 5')
for r in cursor.fetchall():
    print(f'  ID={r[0]}, TaskId={r[1]}, Time={r[2]}')

print()
print('=== MaterialInfo - 最新素材 ===')
cursor.execute('SELECT Id, TgtCode, MaterialStatus, CreateTime FROM MaterialInfo WHERE MaterialStatus IN (9,10) ORDER BY CreateTime DESC LIMIT 5')
for r in cursor.fetchall():
    status_map = {9:'开始烧录', 10:'烧录完成待审核'}
    print(f'  ID={r[0]}, Code={r[1]}, Status={status_map.get(r[2],r[2])}, Time={r[3]}')

conn.close()
print()
print('DB校验完成')
