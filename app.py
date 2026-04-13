import streamlit as st
from crew import run_agents

st.set_page_config(page_title="AI Real Estate Lead Engine")

st.title("🏠 AI Real Estate Lead Engine")

if st.button("Run Lead Collection"):
    results = run_agents()
    st.write(results)
