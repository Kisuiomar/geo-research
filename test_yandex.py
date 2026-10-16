import urllib.request
import json
import uuid
import re

def search_yandex_by_image(image_path):
    boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"
    with open(image_path, "rb") as f:
        img_data = f.read()

    body = (
        f"--{boundary}\r\n"
        f"Content-Disposition: form-data; name=\"upfile\"; filename=\"photo.jpg\"\r\n"
        f"Content-Type: image/jpeg\r\n\r\n"
    ).encode("utf-8") + img_data + f"\r\n--{boundary}--\r\n".encode("utf-8")

    req = urllib.request.Request(
        "https://yandex.com/images-apphost/image-download?cname=image-search",
        data=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        }
    )
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        raw = resp.read().decode("utf-8")
        data = json.loads(raw)
        cbir_id = data.get("image_id") or data.get("cbir_id")
        return cbir_id
    except Exception as e:
        print("Upload failed:", e)
        return None

cid = search_yandex_by_image("photo_2.jpg")
print("CBIR ID:", cid)
if cid:
    res_url = f"https://yandex.com/images/search?rpt=imageview&cbir_id={cid}"
    print("Result URL:", res_url)
    req2 = urllib.request.Request(res_url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7"
    })
    try:
        html = urllib.request.urlopen(req2, timeout=15).read().decode("utf-8")
        # Find tags or titles
        tags = re.findall(r'class="Tags-ItemText[^>]*>([^<]+)<', html)
        print("Found Tags:", tags[:10])
        titles = re.findall(r'<div class="CbirItem-Title"[^>]*>([^<]+)<', html)
        print("Found Titles:", titles[:5])
    except Exception as e2:
        print("Fetch result failed:", e2)
