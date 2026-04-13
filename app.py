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

# Stop the app from running the rest of the code if the password is wrong
if not check_password():
    st.stop()

# --- Initialize API Clients Securely ---
try:
    # Notice we are now using Apify instead of Tavily
    apify_client = ApifyClient(st.secrets["APIFY_API_TOKEN"])
    groq_client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    api_status = "🟢 Apify & Groq Connected"
except Exception as e:
    api_status = "🔴 Missing API Keys"

# --- AI Scout Logic ---
def run_scout(city, property_type):
    # 1. The Bloodhound Query (Hunting for +91 and contact words on open platforms)
    search_query = f'("looking for {property_type}" OR "need {property_type}") {city} ("+91" OR "whatsapp" OR "contact me" OR "call me") (site:facebook.com OR site:sulekha.com OR site:locanto.net OR site:quikr.com) -broker -agent'
    
    with st.spinner("Apify Cloud Browser spinning up... (This takes 15-30 seconds)..."):
        run_input = {
            "queries": search_query,
            "resultsPerPage": 15,
            "maxPagesPerQuery": 1,
            "languageCode": "en",
            "countryCode": "in" # Target India specifically
        }
        
        try:
            # Calling the FREE Apify Google Search Scraper
            run = apify_client.actor("apify/google-search-scraper").call(run_input=run_input)
            
            raw_content = ""
            for item in apify_client.dataset(run["defaultDatasetId"]).iterate_items():
                organic_results = item.get("organicResults", [])
                for result in organic_results:
                    raw_content += f"URL: {result.get('url', '')}\nText: {result.get('title', '')} {result.get('description', '')}\n\n"
        except Exception as e:
            st.error(f"Apify Scraping Error: {e}")
            return []

    # DEFENSIVE CHECK
    if not raw_content.strip():
        return []
    raw_content = raw_content[:40000]

    # 2. Extract with Groq AI
    with st.spinner("Groq AI extracting contact info..."):
        system_prompt = """
        You are an elite real estate lead data extractor. I will give you raw web search results. 
        Your ONLY mission is to find GENUINE individuals looking to buy, rent, or lease property and extract their contact details.
        
        CRITICAL RULES:
        1. REJECT BROKERS: If the text sounds like an agent offering a property, ignore it completely.
        2. EXTRACT CONTACTS: You must aggressively scan for phone numbers (especially Indian +91 formats), WhatsApp numbers, or emails.
        3. EXTRACT REQUIREMENTS: Summarize exactly what they want (e.g., "3BHK, unfurnished, family").
        
        Return ONLY a valid JSON array of objects with these exact keys:
        "Name" (or "Unknown"),
        "Phone" (Extract the exact number if found, otherwise "Not Found"),
        "Email" (Extract if found, otherwise "Not Found"),
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
st.markdown("Automated web scouting and intent verification for real estate brokers.")
st.caption(f"System Status: {api_status}")

# --- Sidebar Controls ---
with st.sidebar:
    st.header("Scout Settings")
    target_city = st.text_input("Target City", value="Ahmedabad")
    property_type = st.text_input("Focus Area", value="office space")
    
    start_scout = st.button("🚀 Run AI Scout", type="primary")

# --- Dashboard Logic ---

# 1. Initialize Memory (Session State)
if "lead_database" not in st.session_state:
    st.session_state.lead_database = []

if start_scout:
    if api_status == "🔴 Missing API Keys":
        st.error("Please add your API keys to Streamlit Secrets first!")
    else:
        st.info(f"Initiating search for {property_type} in {target_city}...")
        
        # Run our backend function
        new_leads = run_scout(target_city, property_type)
        
        if new_leads and len(new_leads) > 0:
            st.success(f"Successfully verified {len(new_leads)} high-intent leads!")
            
            # Add timestamps and append to our session memory
            for lead in new_leads:
                lead["Date_Found"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                st.session_state.lead_database.append(lead)
        else:
            st.warning("No new high-intent leads found right now. Try adjusting your search parameters.")

# 2. Display the Database
if len(st.session_state.lead_database) > 0:
    st.divider()
    st.subheader(f"📂 Lead Database ({len(st.session_state.lead_database)} Total)")
    
    # Convert memory to a DataFrame
    df = pd.DataFrame(st.session_state.lead_database)
    
    # Clean up: Remove duplicates if the AI scraped the same link twice
    if "Source_Link" in df.columns:
        df = df.drop_duplicates(subset=['Source_Link'])
    
    # Reorder columns to put Date first
    cols = ['Date_Found'] + [col for col in df.columns if col != 'Date_Found']
    df = df[cols]
    
    st.dataframe(
        df, 
        use_container_width=True,
        column_config={
            "Source_Link": st.column_config.LinkColumn("View Source")
        }
    )
    
    # 3. The Export Button
    csv_data = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Leads as CSV",
        data=csv_data,
        file_name=f"Real_Estate_Leads_{target_city}_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        type="primary"
    )

    # --- 4. AI Outreach Assistant ---
    st.divider()
    st.subheader("💬 AI Outreach Assistant")
    st.markdown("Select a lead below to instantly generate a personalized, high-converting outreach message.")

    # Create a clean list of options for the dropdown using the NEW data keys
    lead_options = [f"{lead.get('Intent', 'Lead')} - {lead.get('Requirement_Details', 'Property')} in {lead.get('Location', 'Unknown')} (Phone: {lead.get('Phone', 'N/A')})" for lead in st.session_state.lead_database]
    
    # Dropdown to select a specific lead
    selected_lead_idx = st.selectbox("Select a Lead to Pitch:", range(len(lead_options)), format_func=lambda x: lead_options[x])

    if st.button("✨ Draft Personalized Pitch"):
        target_lead = st.session_state.lead_database[selected_lead_idx]

        with st.spinner("Writing the perfect message..."):
            draft_prompt = f"""
            You are a highly successful, approachable real estate broker making first contact on WhatsApp, LinkedIn, or Email.
            Write a short, casual, and highly converting direct message for a prospect.
            
            Prospect details:
            - Name: {target_lead.get('Name', 'Unknown')}
            - Looking to: {target_lead.get('Intent', 'Unknown')}
            - Requirement: {target_lead.get('Requirement_Details', 'Unknown')}
            - Location: {target_lead.get('Location', 'Unknown')}
            - Budget: {target_lead.get('Budget', 'Unknown')}
            
            CRITICAL RULES:
            1. Keep it under 4 sentences. Short and punchy.
            2. Do not sound like a corporate robot or a desperate salesperson. Sound human, local to {target_city}, and helpful.
            3. Include a clear, low-pressure call to action (e.g., asking if they want you to send over a few off-market options that fit their criteria).
            4. Leave placeholders like [Your Name]. If the prospect name is 'Unknown', start with a friendly generic greeting.
            """

            try:
                # We use a slightly higher temperature (0.7) here so the AI is more creative and conversational
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
