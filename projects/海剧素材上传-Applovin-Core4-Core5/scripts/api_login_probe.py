import requests
import os

base = 'https://adassetserver-cn-new-test1.changdu.ltd'
user = os.environ.get('TEST_USER', '240017')
pwd = os.environ.get('TEST_PASS', '')

print(f'=== API Login Probe ===')
print(f'User: {user}')
print(f'API: {base}')

paths = ['/api/Authorize/Login', '/api/login', '/api/token', '/api/Account/Login', '/connect/token']
for p in paths:
    try:
        r = requests.post(base + p, json={'username': user, 'password': pwd}, timeout=8)
        code = r.status_code
        body = r.text[:150] if r.text else '(empty)'
        print(f'POST {p}: {code} ({len(r.content)}b) {body}')
    except Exception as e:
        print(f'POST {p}: ERROR - {e}')
