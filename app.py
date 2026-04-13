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

# --- AI Scout Logic ---
def run_scout(city, property_type):
    with st.spinner(f"Force-scanning 99acres listings in {city}..."):
        # We are changing the URL to a standard search result page
        # This page is more likely to give the scraper raw data
        formatted_city = city.lower().replace(" ", "-")
        target_url = f"https://www.99acres.com/{property_type.replace(' ', '-')}-in-{formatted_city}-ffid"
        
        run_input = {
            "direct_search_urls": [target_url],
            "directSearchUrls": [target_url],
            "maxItems": 10
        }
        
        try:
            actor_id = "fatihtahta/99acres-scraper"
            run = apify_client.actor(actor_id).call(run_input=run_input)
            
            raw_data = []
            for item in apify_client.dataset(run["defaultDatasetId"]).iterate_items():
                raw_data.append(item)
            
            if not raw_data:
                # DEBUG: If no data, let's see why
                st.write("🔍 Apify ran, but 99acres returned 0 results for this URL.")
                return []
                
            return extract_leads_with_ai(json.dumps(raw_data)[:50000], city)
                
        except Exception as e:
            st.error(f"Apify System Error: {str(e)}")
            return []
            
            # Convert the deep data to string for the AI to analyze
            raw_content = json.dumps(raw_data)[:50000]
                
        except Exception as e:
            st.error(f"Apify System Error: {str(e)}")
            return []

    # 2. Extract with Groq AI (The Brain)
    with st.spinner("AI Brain extracting high-quality leads..."):
        system_prompt = f"""
        You are a Real Estate Analyst. Analyze the 99acres JSON data.
        1. Identify GENUINE buyer/renter requirements.
        2. Filter out all Company/Broker listings.
        3. Extract: Name, Phone (if present), Requirement (e.g. 2BHK/Office), Budget, and Source_Link.
        Return ONLY a JSON object with a 'leads' key.
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

# --- Main UI ---
st.title("🏢 99acres AI Lead Scout")
st.caption(f"Status: {api_status} | Target: Pure 99acres Data")

with st.sidebar:
    st.header("Search Parameters")
    city_input = st.text_input("Target City", value="Ahmedabad")
    p_type = st.text_input("Property Type", value="office space")
    run_btn = st.button("🚀 Scrape 99acres", type="primary")

if "leads" not in st.session_state:
    st.session_state.leads = []

if run_btn:
    results = run_scout(city_input, p_type)
    if results:
        for r in results:
            r["Date_Found"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            st.session_state.leads.append(r)
        st.success(f"Verified {len(results)} leads from 99acres!")
    else:
        st.warning("No unmasked leads found. Verify your Apify Actor rental is active.")

# --- Results Table ---
if st.session_state.leads:
    df = pd.DataFrame(st.session_state.leads)
    if "Source_Link" in df.columns:
        df = df.drop_duplicates(subset=['Source_Link'])
    st.dataframe(df, use_container_width=True)
    
    csv_data = df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download CSV", data=csv_data, file_name="99acres_leads.csv", mime="text/csv")
