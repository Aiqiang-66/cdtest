import requests
import sys

base = 'https://adassetserver-cn-new-test1.changdu.ltd'

paths = [
    '/swagger/index.html',
    '/api/Authorize/Login',
    '/api/Common/GetPlatformDropList',
    '/api/Task/GetBatchUploadInfo',
    '/api/Task/BatchAddVideo',
    '/api/VideoCn/GetCompositeImageLocalPath',
]

for p in paths:
    try:
        r = requests.get(f'{base}{p}', timeout=8, allow_redirects=False)
        print(f'{p}: {r.status_code} ({len(r.content)}b)')
        if r.status_code == 401:
            print('  -> Auth required (endpoint EXISTS)')
        if r.status_code in [301,302,307,308]:
            loc = r.headers.get('Location', '?')
            print(f'  -> Redirect to: {loc}')
    except Exception as e:
        print(f'{p}: ERROR - {e}')
