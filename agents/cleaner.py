def clean_data(data):
    cleaned = []
    seen = set()

    for d in data:
        if "broker" in d["original"].lower():
            continue
        if d["original"] in seen:
            continue
        seen.add(d["original"])
        cleaned.append(d)

    return cleaned
