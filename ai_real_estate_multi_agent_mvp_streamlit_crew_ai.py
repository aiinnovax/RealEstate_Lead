# =========================
# FILE: requirements.txt
# =========================
streamlit
crewai
langchain
openai
transformers
pandas

# =========================
# FILE: app.py
# =========================
import streamlit as st
from crew import run_agents

st.set_page_config(page_title="AI Real Estate Lead Engine")

st.title("🏠 AI Real Estate Lead Engine")

if st.button("Run Lead Collection"):
    results = run_agents()
    st.write(results)

# =========================
# FILE: crew.py
# =========================
from crewai import Agent, Task, Crew
from agents.scout import get_leads
from agents.extractor import extract_info
from agents.cleaner import clean_data
from agents.scorer import score_leads


def run_agents():
    raw = get_leads()
    extracted = [extract_info(x) for x in raw]
    cleaned = clean_data(extracted)
    scored = score_leads(cleaned)
    return scored

# =========================
# FILE: agents/scout.py
# =========================
def get_leads():
    return [
        "Looking for 2BHK in Ahmedabad under 25k urgent",
        "Want to sell my flat in SG Highway Ahmedabad",
        "Need office space for lease in Prahladnagar",
        "Broker here posting fake ad"
    ]

# =========================
# FILE: agents/extractor.py
# =========================
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

# =========================
# FILE: agents/cleaner.py
# =========================
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

# =========================
# FILE: agents/scorer.py
# =========================
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

# =========================
# FILE: README.md
# =========================
# AI Real Estate Multi-Agent System

## Run locally or on Streamlit Cloud

### Install
pip install -r requirements.txt

### Run
streamlit run app.py

## Features
- Multi-agent pipeline
- Lead extraction
- Cleaning
- Scoring

## Next Steps
- Add real scraping (Playwright)
- Connect Google Sheets
- Add HuggingFace models
