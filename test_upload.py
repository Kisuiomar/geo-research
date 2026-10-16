import urllib.request
import json
import uuid

boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"
body = []
body.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"title\"\r\n\r\nТестовая загрузка".encode('utf-8'))
body.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"dummy.jpg\"\r\nContent-Type: image/jpeg\r\n".encode('utf-8'))
with open('dummy.jpg', 'rb') as f:
    body.append(f.read())
body.append(f"--{boundary}--\r\n".encode('utf-8'))

payload = b"\r\n".join(body)

req = urllib.request.Request(
    'http://127.0.0.1:8765/api/upload',
    data=payload,
    headers={'Content-Type': f'multipart/form-data; boundary={boundary}'}
)
resp = urllib.request.urlopen(req)
data = json.loads(resp.read().decode('utf-8'))
print("Upload status:", data["status"], "Case:", data["case"]["id"], "Title:", data["case"]["title"])
