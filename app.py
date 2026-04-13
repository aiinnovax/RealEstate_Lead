import streamlit as st
from config import SEARCH_ENGINE_CODE, API_ENDPOINT, API_KEY, SEARCH_ENGINE_ID

# Create a Streamlit app
st.title("Ahmedabad Real Estate Search")
st.write("Search for properties in Ahmedabad")

# Render the search engine code
st.components.v1.html(SEARCH_ENGINE_CODE, height=600, width=800)

# Add a button to get the search results
if st.button("Get Search Results"):
    # Use the custom search engine API to get the search results
    import requests
    query = "ahmedabad real estate"
    params = {
        "key": API_KEY,
        "cx": SEARCH_ENGINE_ID,
        "q": query
    }
    response = requests.get(API_ENDPOINT, params=params)
    results = response.json()["items"]
    st.write("Search Results:")
    for result in results:
        st.write(result["title"])
        st.write(result["link"])
