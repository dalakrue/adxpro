"""Main entry point for M1 ADX Quant Pro.

Run with:
    streamlit run adx_dashpoard.py

This file intentionally does not call st.set_page_config(); core.app_shell.run_app()
handles that once. Calling it twice can crash Streamlit on some versions.
"""

import warnings

import streamlit as st

try:
    from pandas.errors import SettingWithCopyWarning
    warnings.filterwarnings("ignore", category=SettingWithCopyWarning)
except Exception:
    pass
warnings.filterwarnings("ignore", message="y_pred contains classes not in y_true")


def main():
    try:
        from core.app_shell import run_app
        run_app()

    except ImportError as e:
        st.error("Import error. Check your project files and requirements.")
        st.code(str(e))

    except Exception as e:
        st.error("App crashed, but the entry file is working.")
        st.code(str(e))


if __name__ == "__main__":
    main()
