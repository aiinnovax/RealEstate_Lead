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
    api_status = "🟢 System Connected"
except Exception as e:
    api_status = "🔴 Missing API Keys"

# --- AI Extraction Helper ---
def extract_leads_with_ai(raw_content, city):
    system_prompt = f"""
    You are a Real Estate Intelligence Expert. 
    Analyze the 99acres JSON data for {city}.
    1. Extract leads who want to buy or rent.
    2. REJECT all listings from 'Brokers' or 'Agents' if possible.
    3. Output JSON with a 'leads' key. Columns: Name, Phone, Intent, Requirement, Budget, Source_Link.
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
    with st.spinner(f"Requesting direct 99acres data for {city}..."):
        # BUILD THE URL: Simplified format to ensure the scraper accepts it
        formatted_city = city.lower().replace(" ", "-")
        target_url = f"https://www.99acres.com/search/property/buy/{formatted_city}"
        
        # VERIFIED SCHEMA: fatihtahta/99acres-scraper
        # 'startUrls' must be a list of strings for the Python client.
        run_input = {
            "startUrls": [target_url],
            "locations": [city],
            "propertyType": "buy",
            "maxItems": 10
        }
        
        try:
            actor_id = "fatihtahta/99acres-scraper"
            run = apify_client.actor(actor_id).call(run_input=run_input)
            
            raw_data = []
            for item in apify_client.dataset(run["defaultDatasetId"]).iterate_items():
                raw_data.append(item)
            
            # CRITICAL DEBUG: Check if data actually came back
            if not raw_data:
                st.error("⚠️ The 99acres Scraper returned 0 results. Check your Apify 'Runs' log for a '403 Forbidden' or 'Blocked' error.")
                return []
                
            return extract_leads_with_ai(json.dumps(raw_data)[:40000], city)
                
        except Exception as e:
            st.error(f"Apify Connection Error: {str(e)}")
            return []

# --- Main UI ---
st.title("🏢 99acres AI Lead Scout")
st.caption(f"Status: {api_status} | Target: Dedicated 99acres Scraper")

with st.sidebar:
    st.header("Search Parameters")
    city_input = st.text_input("Target City", value="Ahmedabad")
    p_type = st.text_input("Property Type", value="office space")
    run_btn = st.button("🚀 Scrape 99acres", type="primary")

if "leads" not in st.session_state:
    st.session_state.leads = []

if run_btn:
    st.session_state.leads = [] # Clear memory
    results = run_scout(city_input, p_type)
    if results:
        for r in results:
            r["Date_Found"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            st.session_state.leads.append(r)
        st.success(f"Found {len(results)} potential leads!")
    else:
        st.info("Scan completed with 0 leads. Check Apify for bot-detection blocks.")

# --- Results Table ---
if st.session_state.leads:
    df = pd.DataFrame(st.session_state.leads)
    st.dataframe(df, use_container_width=True)
    csv_data = df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download CSV", data=csv_data, file_name="99acres_leads.csv", mime="text/csv")
