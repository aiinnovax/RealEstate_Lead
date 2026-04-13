import streamlit as st
import pandas as pd
import json
from datetime import datetime
from apify_client import ApifyClient
from groq import Groq

# --- Page Config ---
st.set_page_config(page_title="99acres AI Lead Scout", page_icon="🏢", layout="wide")

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
    api_status = "🟢 Connected"
except Exception as e:
    api_status = "🔴 Missing API Keys"

# --- AI Scout Logic ---
def run_scout(city, property_type):
    with st.spinner(f"Requesting direct 99acres data for {city}..."):
        # Build the exact 99acres search URL structure
        formatted_city = city.lower().replace(" ", "-")
        target_url = f"https://www.99acres.com/search/property/buy/{formatted_city}"
        
        # TRIPLE-CHECK INPUT: We provide all possible variations to satisfy the Actor
        run_input = {
            "locations": [city],                # Version 1 (Most likely)
            "directSearchUrls": [target_url],   # Version 2 (CamelCase)
            "direct_search_urls": [target_url], # Version 3 (Snake_case)
            "startUrls": [{"url": target_url}], # Version 4 (Standard Apify)
            "maxItems": 10,
            "keyword": property_type
        }
        
        try:
            actor_id = "fatihtahta/99acres-scraper"
            # We use call() to wait for results
            run = apify_client.actor(actor_id).call(run_input=run_input)
            
            raw_data = []
            for item in apify_client.dataset(run["defaultDatasetId"]).iterate_items():
                raw_data.append(item)
            
            if not raw_data:
                # If data is empty, it's a 99acres block, not a code failure
                return "BLOCKED"
                
            # Convert JSON to text for the AI
            raw_content = json.dumps(raw_data)[:40000]
            
            # 2. Extract with AI
            system_prompt = "Identify GENUINE leads from 99acres. Reject brokers. Return JSON with 'leads' key."
            chat_completion = groq_client.chat.completions.create(
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": raw_content}],
                model="llama-3.1-8b-instant", 
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            return json.loads(chat_completion.choices[0].message.content).get("leads", [])
                
        except Exception as e:
            st.error(f"Apify Connection Error: {str(e)}")
            return []

# --- Main UI ---
st.title("🏢 Pure 99acres AI Scout")
st.caption(f"Status: {api_status} | Mode: Dedicated Scraper")

if "leads" not in st.session_state:
    st.session_state.leads = []

with st.sidebar:
    st.header("Search Parameters")
    city_input = st.text_input("City", value="Ahmedabad")
    p_type = st.text_input("Property Type", value="office space")
    
    col1, col2 = st.columns(2)
    with col1:
        run_btn = st.button("🚀 Find Leads", type="primary")
    with col2:
        if st.button("🗑️ Clear All"):
            st.session_state.leads = []
            st.rerun()

if run_btn:
    results = run_scout(city_input, p_type)
    if results == "BLOCKED":
        st.error("⚠️ 99acres detected the bot and blocked it. You MUST enable 'Residential Proxies' in your Apify Console for this Actor to work.")
    elif results:
        for r in results:
            r["Date_Found"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            st.session_state.leads.append(r)
        st.success(f"Found {len(results)} new 99acres leads!")
    else:
        st.warning("No unmasked leads found. Verify your Actor rental and proxy settings.")

# --- Results Table ---
if st.session_state.leads:
    df = pd.DataFrame(st.session_state.leads)
    st.dataframe(df, use_container_width=True)
