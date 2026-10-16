import urllib.request
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

def query_overpass(query):
    url = 'https://overpass-api.de/api/interpreter'
    req = urllib.request.Request(url, data=query.encode('utf-8'), headers={'User-Agent': 'geo-sleuth/1.0'})
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read().decode('utf-8'))

print("--- VINPEARL HARBOUR & HILL ---")
q = """
[out:json][timeout:25];
(
  node(12.208, 109.233, 12.218, 109.245);
  way(12.208, 109.233, 12.218, 109.245);
);
out center tags;
"""
data = query_overpass(q)
for el in data.get('elements', []):
    tags = el.get('tags', {})
    lat = el.get('lat') or el.get('center', {}).get('lat')
    lon = el.get('lon') or el.get('center', {}).get('lon')
    if tags:
        print(f"{el.get('type')}/{el.get('id')}: {lat:.6f}, {lon:.6f} -> {tags.get('name', '')} {tags}")
