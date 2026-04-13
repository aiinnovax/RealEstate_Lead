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
        # We construct a generic 99acres search URL based on your city
        target_url = f"https://www.99acres.com/search/property/buy/{city.lower()}"
        
        # 1. APIFY INPUT: Hard-capped to 10 to protect your free credits
        run_input = {
            "startUrls": [{"url": target_url}],
            "maxItems": 10,  # Strict Daily/Run Limit
            "keyword": property_type
        }
        
        try:
            # ---> IMPORTANT: REPLACE THIS STRING WITH THE EXACT APIFY ACTOR ID <---
            # Example: "developer-name/99acres-scraper"
            actor_id = "fatihtahta/99acres-scraper" 
            
            run = apify_client.actor(actor_id).call(run_input=run_input)
            
            raw_content = ""
            for item in apify_client.dataset(run["defaultDatasetId"]).iterate_items():
                raw_content += json.dumps(item) + "\n\n"
                
        except Exception as e:
            st.error(f"Apify Scraping Error. Did you insert the correct Actor ID? Details: {e}")
            return []

    if not raw_content.strip():
        return []
    raw_content = raw_content[:40000]

    # 2. Extract with Groq AI
    with st.spinner("Groq AI processing 99acres JSON data..."):
        system_prompt = """
        You are an elite real estate lead data extractor. I will give you raw JSON output directly from a 99acres web scraper.
        Your ONLY mission is to parse this data, find GENUINE individuals looking to buy/rent/lease, and extract their details.
        
        CRITICAL RULES:
        1. REJECT BROKERS: If the 'poster type' or description indicates a broker/agent, ignore it entirely.
        2. EXTRACT CONTACTS: Look carefully for unmasked phone numbers, +91 formats, or emails in descriptions or contact fields.
        3. EXTRACT REQUIREMENTS: Summarize exactly what they want based on the property description.
        
        Return ONLY a valid JSON array of objects with these exact keys:
        "Name" (or "Unknown"),
        "Phone" (Extract if available, otherwise "Hidden by 99acres"),
        "Email" (Extract if available, otherwise "Not Found"),
        "Intent" (Buy/Rent/Lease), 
        "Requirement_Details", 
        "Location", 
        "Budget", 
        "Source_Link"
        
        If no valid leads are found, return an empty array: []
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
st.markdown("Automated 99acres web scouting and intent verification for real estate brokers.")
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
    elif "YOUR_ACTOR_ID_HERE" in open(__file__).read():
         st.error("Wait! You need to update the Apify Actor ID in the app.py code on GitHub before running.")
    else:
        st.info(f"Initiating search for {property_type} in {target_city} (Max 10 results)...")
        
        new_leads = run_scout(target_city, property_type)
        
        if new_leads and len(new_leads) > 0:
            st.success(f"Successfully pulled {len(new_leads)} records from 99acres!")
            
            for lead in new_leads:
                lead["Date_Found"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                st.session_state.lead_database.append(lead)
        else:
            st.warning("No unmasked leads found. Try adjusting your search parameters.")

# --- Display the Database ---
if len(st.session_state.lead_database) > 0:
    st.divider()
    st.subheader(f"📂 Lead Database ({len(st.session_state.lead_database)} Total)")
    
    df = pd.DataFrame(st.session_state.lead_database)
    
    if "Source_Link" in df.columns:
        df = df.drop_duplicates(subset=['Source_Link'])
    
    cols = ['Date_Found'] + [col for col in df.columns if col != 'Date_Found']
    df = df[cols]
    
    st.dataframe(
        df, 
        use_container_width=True,
        column_config={
            "Source_Link": st.column_config.LinkColumn("View Source")
        }
    )
    
    csv_data = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Leads as CSV",
        data=csv_data,
        file_name=f"99acres_Leads_{target_city}_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        type="primary"
    )

    # --- AI Outreach Assistant ---
    st.divider()
    st.subheader("💬 AI Outreach Assistant")
    st.markdown("Select a lead below to instantly generate a personalized, high-converting outreach message.")

    lead_options = [f"{lead.get('Intent', 'Lead')} - {lead.get('Requirement_Details', 'Property')} in {lead.get('Location', 'Unknown')} (Phone: {lead.get('Phone', 'N/A')})" for lead in st.session_state.lead_database]
    
    selected_lead_idx = st.selectbox("Select a Lead to Pitch:", range(len(lead_options)), format_func=lambda x: lead_options[x])

    if st.button("✨ Draft Personalized Pitch"):
        target_lead = st.session_state.lead_database[selected_lead_idx]

        with st.spinner("Writing the perfect message..."):
            draft_prompt = f"""
            You are a highly successful, approachable real estate broker making first contact.
            Write a short, casual, and highly converting direct message for a prospect.
            
            Prospect details:
            - Name: {target_lead.get('Name', 'Unknown')}
            - Looking to: {target_lead.get('Intent', 'Unknown')}
            - Requirement: {target_lead.get('Requirement_Details', 'Unknown')}
            - Location: {target_lead.get('Location', 'Unknown')}
            - Budget: {target_lead.get('Budget', 'Unknown')}
            
            CRITICAL RULES:
            1. Keep it under 4 sentences. Short and punchy.
            2. Do not sound like a corporate robot. Sound human, local to {target_city}, and helpful.
            3. Include a clear call to action.
            4. Leave placeholders like [Your Name].
            """

            try:
                pitch_completion = groq_client.chat.completions.create(
                    messages=[{"role": "user", "content": draft_prompt}],
                    model="llama-3.1-8b-instant",
                    temperature=0.7, 
                )
                pitch_text = pitch_completion.choices[0].message.content
                
                st.success("Draft ready! Copy and send.")
                st.text_area("Your Custom Message:", value=pitch_text, height=200)
            except Exception as e:
                st.error(f"Failed to draft message: {e}")
