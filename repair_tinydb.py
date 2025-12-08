import json
import sys

def repair_tinydb(path, output_path=None):
    """
    Reads a TinyDB JSON file that may contain multiple JSON objects
    and merges them into a single valid JSON structure.
    """
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read().strip()

    # Try to parse as a single JSON first
    try:
        data = json.loads(raw)
        print("File is already valid JSON.")
        return data
    except json.JSONDecodeError:
        print("Malformed JSON detected, attempting repair...")

    # Split into individual JSON objects
    objects = []
    decoder = json.JSONDecoder()
    idx = 0
    while idx < len(raw):
        try:
            obj, end = decoder.raw_decode(raw, idx)
            objects.append(obj)
            idx = end
        except json.JSONDecodeError:
            idx += 1  # skip bad character

    # Merge objects into one dict
    merged = {}
    for obj in objects:
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key not in merged:
                    merged[key] = value
                else:
                    if isinstance(merged[key], dict) and isinstance(value, dict):
                        merged[key].update(value)
                    else:
                        if not isinstance(merged[key], list):
                            merged[key] = [merged[key]]
                        merged[key].append(value)

    # Save repaired file
    if output_path is None:
        output_path = path + ".repaired.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2)

    print(f"Repaired JSON written to {output_path}")
    return merged


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "DatabaseStorage/tinydb.json"
    repaired = repair_tinydb(path)
    print("Repair complete. Objects merged:", repaired.keys())