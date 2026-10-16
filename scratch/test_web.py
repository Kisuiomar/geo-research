import urllib.request

with urllib.request.urlopen("http://127.0.0.1:8765/") as r:
    content = r.read().decode("utf-8")
    print("HTTP status:", r.status)
    print("Content length:", len(content))
    checks = [
        ("tabRadar", "tabRadar" in content),
        ("tabKnowledge", "tabKnowledge" in content),
        ("radarView", "radarView" in content),
        ("knowledgeView", "knowledgeView" in content),
        ("ubinamLadderCard", "ubinamLadderCard" in content),
        ("findmyphotoCard", "findmyphotoCard" in content),
        ("kzSignboardCard", "kzSignboardCard" in content),
    ]
    for name, found in checks:
        print(f"Check {name}: {'[PASS]' if found else '[FAIL]'}")
