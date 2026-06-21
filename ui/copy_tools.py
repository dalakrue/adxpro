"""Copy/export UI helpers for future upgrades. Existing copy buttons remain unchanged."""
from __future__ import annotations
import streamlit as st

def copy_fallback_script(text: str, key: str = "copy_fallback") -> None:
    safe = str(text).replace("`", "\\`")
    st.markdown(f"""<script>
try {{ navigator.clipboard && navigator.clipboard.writeText(`{safe}`); }} catch(e) {{ console.log('copy fallback skipped', e); }}
</script>""", unsafe_allow_html=True)
