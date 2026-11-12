import os
import json
from datetime import datetime

DATA_ROOT = "data"


def main():
    os.makedirs(DATA_ROOT, exist_ok=True)
    languages = []

    for entry in sorted(os.listdir(DATA_ROOT)):
        folder = os.path.join(DATA_ROOT, entry)

        # Only process real folders, skip hidden files/folders
        if not os.path.isdir(folder) or entry.startswith("."):
            continue

        # All .txt files in this language folder
        txt_files = sorted(
            [
                f for f in os.listdir(folder)
                if f.lower().endswith(".txt") and not f.startswith(".")
            ],
            reverse=True,
        )

        manifest = {
            "language": entry,          # e.g. "bn-BD"
            "count": len(txt_files),
            "files": txt_files,
            "updated": datetime.now().isoformat(),
        }
        manifest_path = os.path.join(folder, "manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as fp:
            json.dump(manifest, fp, ensure_ascii=False, indent=2)

        languages.append({"code": entry, "count": len(txt_files)})
        print(f"✅ {entry}: {len(txt_files)} file(s) indexed")

    # Root index of all languages
    root_index = os.path.join(DATA_ROOT, "languages.json")
    with open(root_index, "w", encoding="utf-8") as fp:
        json.dump(
            {"languages": languages, "updated": datetime.now().isoformat()},
            fp, ensure_ascii=False, indent=2,
        )

    print(f"\n🌍 {len(languages)} language folder(s) processed → {root_index}")


if __name__ == "__main__":
    main()
