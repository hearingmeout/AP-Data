#!/usr/bin/env python3
"""
Deduplicate Physics C E&M topic lookup against *all* other TopicLookup JSONs.

- Looks in TOPIC_DIR for *TopicLookup.json files
- Treats this file as the "base" to dedupe:

    Physics_C_Electricity_and_Magnetism_TopicLookup.json

- Builds a set of (unitCd, topicCd, skillCd) from ALL OTHER files.
- Removes any Physics entries whose (unitCd, topicCd, skillCd) appears in that set.
- Drops empty topics/units.
- Writes NEW_Physics_C_Electricity_and_Magnetism_TopicLookup.json in the same folder.
"""

import json
from pathlib import Path

# ===== CONFIG =====
TOPIC_DIR = Path("topicLookups")  # adjust if your folder is named differently
PHYSICS_FILENAME = "Physics_C_Electricity_and_Magnetism_TopicLookup.json"
OUTPUT_FILENAME = "NEW_Physics_C_Electricity_and_Magnetism_TopicLookup.json"


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def main():
    physics_path = TOPIC_DIR / PHYSICS_FILENAME
    if not physics_path.exists():
        print(f"[error] Physics file not found: {physics_path.resolve()}")
        return

    # 1. Find ALL TopicLookup JSONs in the directory
    all_files = sorted(TOPIC_DIR.glob("*TopicLookup.json"))
    if not all_files:
        print(f"[error] No *TopicLookup.json files found in {TOPIC_DIR.resolve()}")
        return

    print(f"[info] Found {len(all_files)} TopicLookup files in {TOPIC_DIR.resolve()}")

    # 2. Build set of signatures from *other* subjects
    other_files = [p for p in all_files if p.name != PHYSICS_FILENAME and not p.name.startswith("NEW_")]

    print(f"[info] Using {len(other_files)} non-Physics files for deduping:")
    for p in other_files:
        print(f"       - {p.name}")

    seen_signatures = set()
    other_entry_count = 0

    for path in other_files:
        try:
            data = load_json(path)
        except Exception as e:
            print(f"[warn] Skipping {path.name}: failed to parse JSON ({e})")
            continue

        units = data.get("lookupData", {}).get("units", [])
        for unit in units:
            u_cd = unit.get("unitCd")
            topics = unit.get("topics", [])
            for topic in topics:
                t_cd = topic.get("topicCd")
                skills = topic.get("skills", [])
                for skill in skills:
                    s_cd = skill.get("skillCd")
                    if u_cd and t_cd and s_cd:
                        seen_signatures.add((u_cd, t_cd, s_cd))
                        other_entry_count += 1

    print(f"[info] Collected {other_entry_count} (unitCd, topicCd, skillCd) entries "
          f"from other subjects ({len(seen_signatures)} unique signatures).")

    # 3. Load the Physics C E&M topic lookup
    physics_data = load_json(physics_path)
    physics_units = physics_data.get("lookupData", {}).get("units", [])

    original_units_count = len(physics_units)
    original_topics_count = 0
    original_skills_count = 0

    new_units = []
    removed_skills = 0

    # 4. Filter physics entries
    for unit in physics_units:
        u_cd = unit.get("unitCd")
        new_topics = []
        topics = unit.get("topics", [])
        original_topics_count += len(topics)

        for topic in topics:
            t_cd = topic.get("topicCd")
            skills = topic.get("skills", [])
            original_skills_count += len(skills)

            new_skills = []
            for skill in skills:
                s_cd = skill.get("skillCd")
                sig = (u_cd, t_cd, s_cd)
                if sig in seen_signatures:
                    # Duplicate – remove
                    removed_skills += 1
                else:
                    new_skills.append(skill)

            # Only keep topic if it still has skills
            if new_skills:
                topic_copy = dict(topic)
                topic_copy["skills"] = new_skills
                new_topics.append(topic_copy)

        # Only keep unit if it still has topics
        if new_topics:
            unit_copy = dict(unit)
            unit_copy["topics"] = new_topics
            new_units.append(unit_copy)

    # 5. Build new physics data structure
    new_data = {
        "lookupData": {
            "units": new_units
        }
    }

    # 6. Write output
    output_path = TOPIC_DIR / OUTPUT_FILENAME
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(new_data, f, ensure_ascii=False, indent=2)

    # 7. Stats
    new_topics_count = sum(len(u.get("topics", [])) for u in new_units)
    new_skills_count = sum(
        len(t.get("skills", []))
        for u in new_units
        for t in u.get("topics", [])
    )

    print("\n===== SUMMARY =====")
    print(f"Physics units:   {original_units_count} → {len(new_units)}")
    print(f"Physics topics:  {original_topics_count} → {new_topics_count}")
    print(f"Physics skills:  {original_skills_count} → {new_skills_count}")
    print(f"Removed skills (dupes vs other subjects): {removed_skills}")
    print(f"Output written to: {output_path.resolve()}")
    print("===================")


if __name__ == "__main__":
    main()
