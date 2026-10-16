import sys
sys.path.insert(0, ".")
from web.server import search_nominatim, search_photon

queries = [
    "Международный финансовый центр Астана",
    "astana international financial centre",
    "МФЦА Астана",
    "Мангилик Ел 55 Астана",
    "Мәңгілік Ел 55"
]

for q in queries:
    hit = search_nominatim(q, prefer_kazakhstan=True)
    print(f"Query: {q} -> Hit: {hit}")
