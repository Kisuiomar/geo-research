import urllib.request
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

url = 'http://api.wikimapia.org/?function=box&bbox=109.22,12.20,109.26,12.24&key=example&format=json&count=100'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
resp = urllib.request.urlopen(req)
data = json.loads(resp.read().decode('utf-8'))

print("Found", len(data.get('folder', [])), "places in Wikimapia:")
for p in data.get('folder', []):
    title = p.get('title', '')
    print(f"- {p['id']}: {title} @ {p['location']['lat']},{p['location']['lon']}")
