import streamlit as st
import pandas as pd
import json
from datetime import datetime
from tavily import TavilyClient
from groq import Groq

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
    # 1. Search the web
    search_query = f'"looking for {property_type}" OR "need to rent {property_type}" {city} (site:linkedin.com OR site:reddit.com)'
    
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

    # 2. Extract with AI
    with st.spinner("AI filtering noise and extracting leads..."):
        system_prompt = """
        You are an expert real estate lead scout. I will give you raw web search results. 
        Your job is to identify GENUINE individuals looking to buy, rent, or lease property. 
        Ignore broker listings, news articles, and spam.
        
        Return ONLY a valid JSON array of objects with these keys:
        "Intent" (Buy/Rent/Lease), "Property Type", "Location", "Budget", "Source_Link", "Confidence_Score".
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
# 1. Search the web (UPDATED QUERY)
    search_query = f'("looking for {property_type}" OR "need {property_type}") {city} -broker -agent -realtor (site:reddit.com OR site:linkedin.com/posts/ OR site:linkedin.com/feed/update/)'
