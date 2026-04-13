import os
import json
from tavily import TavilyClient
from groq import Groq
from dotenv import load_dotenv

# Load environment variables (API keys)
load_dotenv()

def scout_leads(city, property_type):
    # Initialize our free clients
    tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
    groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    # 1. The Search Phase
    # We craft a highly specific query to find intent, not listings.
    search_query = f'"looking for {property_type}" OR "need to rent {property_type}" {city} (site:linkedin.com OR site:reddit.com OR site:twitter.com)'
    
    print(f"[*] Querying Tavily: {search_query}")
    search_results = tavily_client.search(query=search_query, search_depth="advanced", max_results=10)
    
    # Compile the text from the search results
    raw_content = ""
    for result in search_results.get('results', []):
        raw_content += f"URL: {result['url']}\nContent: {result['content']}\n\n"

    # 2. The AI Extraction Phase
    print("[*] Passing results to Groq (Llama-3) for filtering...")
    
    system_prompt = """
    You are an expert real estate lead scout. I will give you raw web search results. 
    Your job is to identify GENUINE individuals looking to buy, rent, or lease property. 
    Ignore broker listings, news articles, and spam.
    
    Extract the valid leads and return ONLY a valid JSON array of objects with these exact keys:
    "Intent" (Buy/Rent/Lease), "Property Type", "Location", "Budget" (or "Not Specified"), "Source Link", "Confidence Score" (e.g., "90%").
    If no valid leads are found, return an empty array: []
    """

    chat_completion = groq_client.chat.completions.create(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": raw_content}
        ],
        model="llama3-8b-8192", 
        temperature=0.1,
        response_format={"type": "json_object"}
    )

    # 3. Parse and Return
    try:
        # Groq returns a JSON string, we parse it into a Python dictionary
        response_text = chat_completion.choices[0].message.content
        # Sometimes LLMs wrap arrays in an object, so we handle both
        parsed_json = json.loads(response_text)
        
        if isinstance(parsed_json, dict) and len(parsed_json.keys()) == 1:
            key = list(parsed_json.keys())[0]
            return parsed_json[key]
        return parsed_json
        
    except Exception as e:
        print(f"[!] AI Parsing Error: {e}")
        return []

# --- Quick Test ---
if __name__ == "__main__":
    # Test the script locally
    leads = scout_leads("Ahmedabad", "office space")
    print("\n--- Verified Leads ---")
    print(json.dumps(leads, indent=2))
