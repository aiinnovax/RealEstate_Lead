import streamlit as st
import pandas as pd
import json
from datetime import datetime
from tavily import TavilyClient
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
    tavily_client = TavilyClient(api_key=st.secrets["TAVILY_API_KEY"])
    groq_client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    api_status = "🟢 Connected"
except Exception as e:
    api_status = "🔴 Missing API Keys"

# ... [The rest of your run_scout function and dashboard code stays exactly the same below here] ...

# --- Page Config ---
st.set_page_config(page_title="AI Real Estate Scout", page_icon="🏢", layout="wide")

# --- Initialize API Clients Securely ---
# We use st.secrets instead of local .env files
try:
    tavily_client = TavilyClient(api_key=st.secrets["TAVILY_API_KEY"])
    groq_client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    api_status = "🟢 Connected"
except Exception as e:
    api_status = "🔴 Missing API Keys"

# --- AI Scout Logic ---
def run_scout(city, property_type):
    # 1. Search the web (UPDATED QUERY: Strict filtering to avoid broker profiles)
    search_query = f'("looking for {property_type}" OR "need {property_type}") {city} ("+91" OR "whatsapp" OR "contact me" OR "call me") (site:facebook.com OR site:sulekha.com OR site:locanto.net OR site:quikr.com) -broker -agent'
    
    with st.spinner("Scouting the web..."):
        # Reduced max_results to 5 to keep the data cleaner and faster
        search_results = tavily_client.search(query=search_query, search_depth="advanced", max_results=5)
    
    raw_content = ""
    for result in search_results.get('results', []):
        raw_content += f"URL: {result['url']}\nContent: {result['content']}\n\n"

    # DEFENSIVE CHECK: Make sure we actually found something
    if not raw_content.strip():
        return []

    # DEFENSIVE TRUNCATION: Hard cap the text at ~40,000 characters just to be safe
    raw_content = raw_content[:40000]

    # 2. Extract with AI (UPDATED PROMPT: The "Iron Wall" against broker spam)
    with st.spinner("AI filtering noise and extracting leads..."):
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
                # UPGRADED MODEL: Llama 3.1 has a 128,000 token limit!
                model="llama-3.1-8b-instant", 
                temperature=0.1,
                response_format={"type": "json_object"}
            )

            response_text = chat_completion.choices[0].message.content
            parsed_json = json.loads(response_text)
            
            # Groq sometimes wraps arrays in a single dictionary key
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

    # Create a clean list of options for the dropdown
    lead_options = [f"{lead['Intent']} - {lead['Property Type']} in {lead['Location']} (Budget: {lead['Budget']})" for lead in st.session_state.lead_database]
    
    # Dropdown to select a specific lead
    selected_lead_idx = st.selectbox("Select a Lead to Pitch:", range(len(lead_options)), format_func=lambda x: lead_options[x])

    if st.button("✨ Draft Personalized Pitch"):
        target_lead = st.session_state.lead_database[selected_lead_idx]

        with st.spinner("Writing the perfect message..."):
            draft_prompt = f"""
            You are a highly successful, approachable real estate broker making first contact on LinkedIn or Reddit.
            Write a short, casual, and highly converting direct message (DM) for a prospect.
            
            Prospect details:
            - Looking to: {target_lead['Intent']}
            - Property: {target_lead['Property Type']}
            - Location: {target_lead['Location']}
            - Budget: {target_lead['Budget']}
            
            CRITICAL RULES:
            1. Keep it under 4 sentences. Short and punchy.
            2. Do not sound like a corporate robot or a desperate salesperson. Sound human, local, and helpful.
            3. Include a clear, low-pressure call to action (e.g., asking if they want you to send over a few off-market options that fit their criteria).
            4. Leave placeholders like [Your Name] and [Prospect Name].
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
