def extract_info(text):
    text_lower = text.lower()

    intent = "unknown"
    if "looking" in text_lower or "need" in text_lower:
        intent = "rent"
    elif "sell" in text_lower:
        intent = "sell"
    elif "lease" in text_lower:
        intent = "lease"

    return {
        "original": text,
        "intent": intent,
        "location": "Ahmedabad" if "ahmedabad" in text_lower else "unknown",
        "budget": "25k" if "25k" in text_lower else "unknown"
    }
