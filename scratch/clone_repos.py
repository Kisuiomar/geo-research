import os
import subprocess

repos = [
    "https://github.com/M-Enzinger/findmyphoto.git",
    "https://github.com/Oldcircle/geo-sleuth.git",
    "https://github.com/msxfury/geo-lens.git",
    "https://github.com/Franky100-pig/Geo-Guesser.git",
    "https://github.com/skriptkiddy98x/spybrain.git",
    "https://github.com/xiaoyangtx996/Searching-skill.git",
    "https://github.com/WJSGZZ/Ubinam.git"
]

target_dir = r"c:\Users\user\.gemini\antigravity-ide\scratch\geo-research\cloned_repos"
os.makedirs(target_dir, exist_ok=True)

for repo in repos:
    name = repo.split("/")[-1].replace(".git", "")
    dest = os.path.join(target_dir, name)
    print(f"Processing {name}...")
    if os.path.exists(dest):
        print(f"Directory {dest} exists. Fetching/pulling...")
        try:
            subprocess.run(["git", "-C", dest, "pull"], check=False)
        except Exception as e:
            print(f"Error pulling {name}: {e}")
    else:
        print(f"Cloning {repo} to {dest}...")
        try:
            subprocess.run(["git", "clone", "--depth", "1", repo, dest], check=False)
        except Exception as e:
            print(f"Error cloning {name}: {e}")

print("Clone step complete.")
