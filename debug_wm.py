import urllib.request, json

u = 'http://api.wikimapia.org/?function=object&id=17671015&key=example&format=json'
d = json.loads(urllib.request.urlopen(u).read().decode('utf-8'))
print(json.dumps(d, indent=2, ensure_ascii=False)[:600])
