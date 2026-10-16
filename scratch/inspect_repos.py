import os
import json

base_dir = r"c:\Users\user\.gemini\antigravity-ide\scratch\geo-research\cloned_repos"
repos = os.listdir(base_dir)

summary = {}

for r in repos:
    r_path = os.path.join(base_dir, r)
    if not os.path.isdir(r_path):
        continue
    files = []
    readme_snippet = ""
    for root, dirs, fnames in os.walk(r_path):
        # ignore .git
        if ".git" in dirs:
            dirs.remove(".git")
        for f in fnames:
            rel = os.path.relpath(os.path.join(root, f), r_path)
            files.append(rel)
            if f.lower().startswith("readme") and not readme_snippet:
                try:
                    with open(os.path.join(root, f), "r", encoding="utf-8", errors="ignore") as rf:
                        readme_snippet = rf.read()[:1500]
                except Exception as e:
                    readme_snippet = str(e)
    summary[r] = {
        "file_count": len(files),
        "files_sample": files[:25],
        "readme_snippet": readme_snippet
    }

with open(r"c:\Users\user\.gemini\antigravity-ide\scratch\geo-research\scratch\repos_summary.json", "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2, ensure_ascii=False)

print("Repos summarized. Found repos:", list(summary.keys()))
