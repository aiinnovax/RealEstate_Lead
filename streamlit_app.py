# streamlit_app.py
import streamlit as st
from app import scrape_data, fetch_data_from_google, generate_leads

# Create a Streamlit application
st.title("Real Estate Lead Generation")
st.header("Input your search query")

query = st.text_input("Query")

if st.button("Search"):
    data = fetch_data_from_google(query)
    leads = generate_leads(data)
    st.write(leads)
