import streamlit as st
import pandas as pd
import json
from datetime import datetime
from apify_client import ApifyClient
from groq import Groq

# --- Page Config ---
st.set_page_config(page_title="AI Real Estate Scout", page_icon="🏢", layout="wide")

# --- Security Gate ---
def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets["APP_PASSWORD"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False
    if "password_correct" not in st.session_state:
        st.markdown("## 🔒 Private Access Only")
        st.text_input("Enter App Password", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.markdown("## 🔒 Private Access Only")
        st.text_input("Enter App Password", type="password", on_change=password_entered, key="password")
        st.error("😕 Incorrect Password.")
        return False
    else:
        return True

if not check_password():
    st.stop()

# --- Initialize API Clients ---
try:
    apify_client = ApifyClient(st.secrets["APIFY_API_TOKEN"])
    groq_client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    api_status = "🟢 System Ready"
except Exception as e:
    api_status = "🔴 Missing API Keys"

# --- AI Extraction Helper ---
def extract_leads_with_ai(raw_content, city):
    system_prompt = f"""
    You are a Real Estate Data Expert. I will provide snippets from Google search results.
    TASK: Identify individuals in {city} who want to buy or rent property.
    RULES: 
    1. EXCLUDE Brokers. 
    2. Extract: Name, Phone, Requirement_Details, Budget, Source_Link.
    Return JSON with a 'leads' key containing an array.
    """
    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": raw_content}],
            model="llama-3.1-8b-instant", 
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        return json.loads(chat_completion.choices[0].message.content).get("leads", [])
    except:
        return []

# --- AI Scout Logic ---
def run_scout(city, property_type):
    with st.spinner("Apify Cloud Agent scouting Google for leads..."):
        # This query targets 99acres and social media for public requirements
        search_query = f'site:99acres.com OR site:facebook.com "looking for {property_type}" {city} "+91"'
        
        run_input = {
            "queries": search_query,
            "maxPagesPerQuery": 1,
            "resultsPerPage": 15,
            "countryCode": "in",
            "languageCode": "en"
        }
        
        try:
            # Using the OFFICIAL FREE GOOGLE SCRAPER - No rental needed
            run = apify_client.actor("apify/google-search-scraper").call(run_input=run_input)
            
            raw_text = ""
            for item in apify_client.dataset(run["defaultDatasetId"]).iterate_items():
                for result in item.get("organicResults", []):
                    raw_text += f"Title: {result.get('title')}\nDesc: {result.get('description')}\nURL: {result.get('url')}\n\n"
            
            if not raw_text:
                return []
            
            return extract_leads_with_ai(raw_text, city)
                
        except Exception as e:
            st.error(f"Apify Error: {str(e)}")
            return []

# --- Main UI ---
st.title("🏢 AI Real Estate Lead Scout")
st.caption(f"Status: {api_status} | Mode: Multi-Source Cloud Scout")

with st.sidebar:
    st.header("Search Parameters")
    city_input = st.text_input("City", value="Ahmedabad")
    p_type = st.text_input("Property Type", value="office space")
    run_btn = st.button("🚀 Find Leads", type="primary")

if "leads" not in st.session_state:
    st.session_state.leads = []

if run_btn:
    results = run_scout(city_input, p_type)
    if results:
        for r in results:
            r["Date"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            st.session_state.leads.append(r)
        st.success(f"Found {len(results)} potential leads!")
    else:
        st.warning("No new leads found. Try a different property type.")

# --- Results Table ---
if st.session_state.leads:
    df = pd.DataFrame(st.session_state.leads)
    st.dataframe(df, use_container_width=True)
    
    # --- Outreach Assistant ---
    st.divider()
    st.subheader("💬 Smart Outreach")
    lead_options = [f"{l.get('Name', 'Lead')} - {l.get('Phone', 'No Phone')}" for l in st.session_state.leads]
    selected_idx = st.selectbox("Select lead:", range(len(lead_options)), format_func=lambda x: lead_options[x])
    
    if st.button("✨ Write WhatsApp Message"):
        lead = st.session_state.leads[selected_idx]
        msg_prompt = f"Write a professional WhatsApp message for a broker to a lead looking for {lead.get('Requirement_Details')} in {city_input}."
        pitch = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": msg_prompt}],
            model="llama-3.1-8b-instant"
        ).choices[0].message.content
        st.text_area("Message:", value=pitch, height=150)
