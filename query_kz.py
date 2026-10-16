import urllib.request
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

q = """
[out:json][timeout:25];
(
  node['name'~'Жумбактас|Жұмбақтас|Zhumbaktas|Окжетпес|Оқжетпес',i](53.0, 70.1, 53.2, 70.4);
  way['name'~'Жумбактас|Жұмбақтас|Zhumbaktas|Окжетпес|Оқжетпес',i](53.0, 70.1, 53.2, 70.4);
);
out center tags;
"""
req = urllib.request.Request('https://overpass-api.de/api/interpreter', data=q.encode('utf-8'), headers={'User-Agent': 'geo-sleuth/1.0'})
data = json.loads(urllib.request.urlopen(req).read().decode('utf-8'))
for el in data.get('elements', []):
    tags = el.get('tags', {})
    lat = el.get('lat') or el.get('center', {}).get('lat')
    lon = el.get('lon') or el.get('center', {}).get('lon')
    print(f"{el.get('type')}/{el.get('id')}: {lat:.6f}, {lon:.6f} -> {tags.get('name')} | {tags}")
