import requests

def get_leads():
    query = "looking for flat Ahmedabad rent"
    url = f"https://www.googleapis.com/customsearch/v1?q={query}"

    # TEMP: mock fallback (since API key needed)
    return [
        "Looking for 2BHK in Ahmedabad under 20k urgent",
        "Need flat on rent in Satellite Ahmedabad",
        "Want to buy property in Ahmedabad budget 50 lakh"
    ]
