"""Preferred Streamlit entry point.

Streamlit Cloud main file path:
    app.py

Local run:
    streamlit run app.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# Make absolute project imports reliable even when Streamlit starts from a
# parent working directory or a cloud runner changes the current directory.
_PROJECT_ROOT = Path(__file__).resolve().parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from adx_dashpoard import main


if __name__ == "__main__":
    main()
