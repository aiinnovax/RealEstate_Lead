from transformers import pipeline

nlp = pipeline("ner", grouped_entities=True)

def extract_info(text):
    entities = nlp(text)

    return {
        "original": text,
        "entities": entities,
        "intent": "rent" if "rent" in text.lower() else "buy"
    }
