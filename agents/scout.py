import requests

API_KEY = "AIzaSyD7buH7nFOwwq2kcQF68Ucm7jRIbNKBpYk"
CX = "<script async src="https://cse.google.com/cse.js?cx=06d962c38ed374c29">
</script>
<div class="gcse-search"></div> "

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
