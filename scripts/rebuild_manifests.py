import os
import json
import re
from datetime import datetime

DATA_ROOT = "data"


def natural_sort_key(s):
    """1.txt, 2.txt, 10.txt যাতে উল্টাপাল্টা না হয়ে সঠিক ক্রমানুসারে সর্ট হয়"""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]


def main():
    if not os.path.isdir(DATA_ROOT):
        print(f"⚠️ '{DATA_ROOT}' ফোল্ডারটি পাওয়া যায়নি। নতুন তৈরি করা হচ্ছে...")
        os.makedirs(DATA_ROOT, exist_ok=True)
        return

    languages = []
    total_jokes = 0

    for entry in sorted(os.listdir(DATA_ROOT)):
        folder = os.path.join(DATA_ROOT, entry)

        # কেবল আসল ফোল্ডারগুলো চেক করবে (.git বা languages.json বাদ দেবে)
        if not os.path.isdir(folder) or entry.startswith("."):
            continue

        # .txt ফাইলগুলো নেওয়া
        txt_files = [
            f for f in os.listdir(folder)
            if f.lower().endswith(".txt") and not f.startswith(".")
        ]

        # 🛑 পরিবর্তন ১: খালি ফোল্ডার থাকলে তা ওয়েবসাইটে ইনডেক্স হবে না
        if not txt_files:
            print(f"⏩ {entry}: কোনো .txt ফাইল নেই, স্কিপ করা হলো।")
            continue

        # নতুন ফাইল সবার উপরে রাখতে রিভার্স ন্যাচারাল সর্ট
        txt_files.sort(key=natural_sort_key, reverse=True)

        manifest = {
            "language": entry,
            "count": len(txt_files),
            "files": txt_files,
            "updated": datetime.now().isoformat(),
        }

        # manifest.json তৈরি (যাতে ফ্রন্টএন্ড দ্রুত ফাইল লিস্ট পায়)
        manifest_path = os.path.join(folder, "manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as fp:
            json.dump(manifest, fp, ensure_ascii=False, indent=2)

        languages.append({"code": entry, "count": len(txt_files)})
        total_jokes += len(txt_files)
        print(f"✅ {entry}: {len(txt_files)} file(s) indexed")

    # সব ভাষার রুট ইনডেক্স তৈরি
    root_index = os.path.join(DATA_ROOT, "languages.json")
    with open(root_index, "w", encoding="utf-8") as fp:
        json.dump(
            {
                "languages": languages,
                "total_jokes": total_jokes,
                "updated": datetime.now().isoformat()
            },
            fp,
            ensure_ascii=False,
            indent=2,
        )

    print(f"\n🌍 সম্পন্ন! মোট ভাষা: {len(languages)}, মোট জোকস: {total_jokes} → {root_index}")


if __name__ == "__main__":
    main()
