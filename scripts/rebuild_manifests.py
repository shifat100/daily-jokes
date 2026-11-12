import os
import json
from datetime import datetime

DATA_ROOT = "data"

def main():
    os.makedirs(DATA_ROOT, exist_ok=True)

    languages = []

    # Scan every sub-folder inside data/
    for entry in sorted(os.listdir(DATA_ROOT)):
        folder = os.path.join(DATA_ROOT, entry)

        # Skip files, hidden folders, and files (only process folders)
        if not os.path.isdir(folder) or entry.startswith("."):
            continue

        # Collect every .txt file in this language folder
        txt_files = sorted(
            [f for f in os.listdir(folder) if f.lower().endswith(".txt")],
            reverse=True
        )

        # Rebuild this language's manifest
        manifest = {
            "language": entry,
            "count": len(txt_files),
            "files": txt_files,
            "updated": datetime.now().isoformat()
        }
        with open(os.path.join(folder, "manifest.json"), "w", encoding="utf-8") as fp:
            json.dump(manifest, fp, ensure_ascii=False, indent=2)

        languages.append({"code": entry, "count": len(txt_files)})
        print(f"✅ {entry}: {len(txt_files)} jokes indexed")

    # Rebuild root languages.json (list of ALL language folders)
    with open(os.path.join(DATA_ROOT, "languages.json"), "w", encoding="utf-8") as fp:
        json.dump(
            {"languages": languages, "updated": datetime.now().isoformat()},
            fp, ensure_ascii=False, indent=2
        )

    print(f"\n🌍 Total languages: {len(languages)}")


if __name__ == "__main__":
    main()
