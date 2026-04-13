def score_leads(data):
    for d in data:
        score = 0

        if "urgent" in d["original"].lower():
            score += 10
        if d["budget"] != "unknown":
            score += 10
        if d["intent"] != "unknown":
            score += 5

        if score >= 20:
            d["rating"] = "HOT"
        elif score >= 10:
            d["rating"] = "WARM"
        else:
            d["rating"] = "COLD"

    return data
