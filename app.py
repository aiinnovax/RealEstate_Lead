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
    """Returns `True` if the user has the correct password."""
    def password_entered():
        if st.session_state["password"] == st.secrets["APP_PASSWORD"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # don't store password in memory
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.markdown("## 🔒 Private Access Only")
        st.text_input("Enter App Password", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.markdown("## 🔒 Private Access Only")
        st.text_input("Enter App Password", type="password", on_change=password_entered, key="password")
        st.error("😕 Incorrect Password. Try again.")
        return False
    else:
        return True

if not check_password():
    st.stop()

# --- Initialize API Clients Securely ---
try:
    apify_client = ApifyClient(st.secrets["APIFY_API_TOKEN"])
    groq_client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    api_status = "🟢 Apify & Groq Connected"
except Exception as e:
    api_status = "🔴 Missing API Keys"

# --- AI Scout Logic ---
def run_scout(city, property_type):
    with st.spinner("Apify Cloud Browser attacking 99acres... (Please wait)..."):
        # Construct search URL
        target_url = f"https://www.99acres.com/search/property/buy/{city.lower()}"
        
        # 1. APIFY INPUT: Hard-capped to 10 for safety
        run_input = {
            "startUrls": [{"url": target_url}],
            "maxItems": 10,
            "keyword": property_type
        }
        
        try:
            # CORRECT ACTOR ID
            actor_id = "fatihtahta/99acres-scraper" 
            # 1. APIFY INPUT: Corrected for fatihtahta's scraper requirements
        run_input = {
            "search_url": f"https://www.99acres.com/search/property/buy/{city.lower()}",
            "max_items": 10,
            "keyword": property_type
        }
            run = apify_client.actor(actor_id).call(run_input=run_input)
            
            raw_content = ""
            for item in apify_client.dataset(run["defaultDatasetId"]).iterate_items():
                raw_content += json.dumps(item) + "\n\n"
                
        except Exception as e:
            st.error(f"Apify Scraping Error: {e}")
            return []

    if not raw_content.strip():
        return []
    raw_content = raw_content[:40000]

    # 2. Extract with Groq AI
    with st.spinner("Groq AI processing 99acres data..."):
        system_prompt = """
        You are an elite real estate lead extractor. Parse the JSON from 99acres.
        REJECT BROKERS. Extract GENUINE individuals only.
        Look for unmasked phone numbers, +91 formats, or emails.
        Return ONLY a JSON array with: Name, Phone, Email, Intent, Requirement_Details, Location, Budget, Source_Link.
        """

        try:
            chat_completion = groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": raw_content}
                ],
                model="llama-3.1-8b-instant", 
                temperature=0.1,
                response_format={"type": "json_object"}
            )

            response_text = chat_completion.choices[0].message.content
            parsed_json = json.loads(response_text)
            
            if isinstance(parsed_json, dict) and len(parsed_json.keys()) == 1:
                key = list(parsed_json.keys())[0]
                return parsed_json[key]
            return parsed_json
            
        except Exception as e:
            st.error(f"AI Extraction Error: {e}")
            return []

# --- Main UI ---
st.title("🏢 AI Real Estate Lead Scout")
st.markdown("Automated 99acres scouting for real estate brokers.")
st.caption(f"System Status: {api_status} | Limit: 10 Leads/Run")

# --- Sidebar Controls ---
with st.sidebar:
    st.header("Scout Settings")
    target_city = st.text_input("Target City", value="Ahmedabad")
    property_type = st.text_input("Focus Area", value="office space")
    start_scout = st.button("🚀 Run AI Scout", type="primary")

# --- Dashboard Logic ---
if "lead_database" not in st.session_state:
    st.session_state.lead_database = []

if start_scout:
    if api_status == "🔴 Missing API Keys":
        st.error("Please add your API keys to Streamlit Secrets first!")
    else:
        st.info(f"Initiating search for {property_type} in {target_city}...")
        new_leads = run_scout(target_city, property_type)
        
        if new_leads and len(new_leads) > 0:
            st.success(f"Successfully pulled {len(new_leads)} records!")
            for lead in new_leads:
                lead["Date_Found"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                st.session_state.lead_database.append(lead)
        else:
            st.warning("No unmasked leads found at this moment.")

# --- Display Database ---
if len(st.session_state.lead_database) > 0:
    st.divider()
    df = pd.DataFrame(st.session_state.lead_database)
    if "Source_Link" in df.columns:
        df = df.drop_duplicates(subset=['Source_Link'])
    
    st.dataframe(df, use_container_width=True)
    
    csv_data = df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download CSV", data=csv_data, file_name="leads.csv", mime="text/csv")

    # --- Outreach Assistant ---
    st.divider()
    st.subheader("💬 AI Outreach Assistant")
    lead_options = [f"{l.get('Intent')} - {l.get('Requirement_Details')} ({l.get('Phone')})" for l in st.session_state.lead_database]
    selected_idx = st.selectbox("Select a Lead:", range(len(lead_options)), format_func=lambda x: lead_options[x])

    if st.button("✨ Draft Pitch"):
        target = st.session_state.lead_database[selected_idx]
        with st.spinner("Drafting..."):
            prompt = f"Write a short WhatsApp message for a broker to contact this lead: {target}"
            pitch = groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.1-8b-instant",
                temperature=0.7
            ).choices[0].message.content
            st.text_area("Message:", value=pitch, height=150)
