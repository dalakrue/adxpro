
try:
    import streamlit as st
    st.markdown("""
    <style>
    [data-testid="stSidebar"] {display:none !important;}
    [data-testid="collapsedControl"] {display:none !important;}
    </style>
    """, unsafe_allow_html=True)
except Exception:
    pass

"""Alternative Streamlit entry point.
Run with:
    streamlit run main.py
"""
from adx_dashpoard import main

if __name__ == "__main__":
    main()
