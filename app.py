import streamlit as st
import pandas as pd
import json
from datetime import datetime
from apify_client import ApifyClient
from groq import Groq

# --- Page Config ---
st.set_page_config(page_title="99acres Lead Scout", page_icon="🏢", layout="wide")

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

# --- AI Extraction Helper ---
def extract_leads_with_ai(raw_content, city):
    system_prompt = f"""
    You are a Real Estate Intelligence Expert. Parse the provided property listing data from 99acres.
    TASK: 
    1. Identify GENUINE property leads in {city}. 
    2. IGNORE all commercial ads or duplicate broker listings.
    3. Extract: Name, Phone, Intent (Buy/Rent), Requirement_Details, Budget, Source_Link.
    
    Return a JSON object with a 'leads' key containing an array of objects.
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
    with st.spinner(f"Initiating direct 99acres scan for {property_type}..."):
        # The actor fatihtahta/99acres-scraper uses 'startUrls' (array of objects) 
        # or 'locations' (array of strings).
        
        # We target the specific search URL for the city
        formatted_city = city.lower().replace(" ", "-")
        target_url = f"https://www.99acres.com/search/property/buy/{formatted_city}"
        
        # OFFICIAL INPUT SCHEMA for fatihtahta/99acres-scraper
        run_input = {
            "startUrls": [{"url": target_url}],
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
            
            if not raw_data:
                return []
                
            raw_content = json.dumps(raw_data)[:45000]
            return extract_leads_with_ai(raw_content, city)
                
        except Exception as e:
            st.error(f"Apify System Error: {str(e)}")
            return []

# --- Main UI ---
st.title("🏢 99acres AI Lead Scout")
st.caption(f"Status: {api_status} | Mode: Dedicated 99acres API")

with st.sidebar:
    st.header("Search Parameters")
    city_input = st.text_input("City", value="Ahmedabad")
    p_type = st.text_input("Property Type", value="office space")
    run_btn = st.button("🚀 Find Leads", type="primary")

if "leads" not in st.session_state:
    st.session_state.leads = []

if run_btn:
    # Clear session memory for a fresh search
    st.session_state.leads = []
    results = run_scout(city_input, p_type)
    if results:
        for r in results:
            r["Date"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            st.session_state.leads.append(r)
        st.success(f"Successfully processed {len(results)} potential records!")
    else:
        st.warning("No leads found. Check your Apify 'Runs' tab to ensure the Actor is active.")

# --- Results Table ---
if st.session_state.leads:
    st.divider()
    df = pd.DataFrame(st.session_state.leads)
    if "Source_Link" in df.columns:
        df = df.drop_duplicates(subset=['Source_Link'])
    
    st.dataframe(df, use_container_width=True)
    
    csv_data = df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download CSV", data=csv_data, file_name="99acres_leads.csv", mime="text/csv")
