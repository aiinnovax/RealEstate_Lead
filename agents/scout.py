import requests

API_KEY = "YOUR_GOOGLE_API_KEY"
CX = "YOUR_SEARCH_ENGINE_ID"

def get_leads():
    query = "looking for flat rent Ahmedabad OR want to buy property Ahmedabad"
    
    url = "https://www.googleapis.com/customsearch/v1"
    
    params = {
        "key": API_KEY,
        "cx": CX,
        "q": query
    }

    response = requests.get(url, params=params)
    data = response.json()

    leads = []

    if "items" in data:
        for item in data["items"]:
            leads.append(item["title"] + " " + item["snippet"])

    return leads
