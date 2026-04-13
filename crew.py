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
