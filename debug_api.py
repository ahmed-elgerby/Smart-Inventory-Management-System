import json
import urllib.request

BASE = 'http://localhost'

print('Logging in...')
req = urllib.request.Request(
    BASE + '/api/auth/login',
    data=json.dumps({'username': 'admin', 'password': 'admin123'}).encode('utf-8'),
    headers={'Content-Type': 'application/json'},
)
with urllib.request.urlopen(req) as r:
    login = json.load(r)
    print('login response:', login)

token = login.get('token')
if not token:
    raise SystemExit('No token in login response')

print('Token length', len(token))

print('Sending update request...')
req = urllib.request.Request(
    BASE + '/api/items/1',
    data=json.dumps({'quantity': 5}).encode('utf-8'),
    method='PUT',
    headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token},
)
try:
    with urllib.request.urlopen(req, timeout=10) as r:
        print('update status', r.getcode())
        print('update response', json.load(r))
except Exception as e:
    print('update error', type(e), e)
