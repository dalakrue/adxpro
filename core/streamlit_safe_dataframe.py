"""Streamlit dataframe safety helpers.

Fixes PyArrow crashes caused by mixed object columns such as
Value = ["READY", 300, "BUY", 8.4]. Streamlit serializes dataframes with
PyArrow; PyArrow can reject object columns containing a mix of bytes/strings,
ints, dicts, lists, timestamps, etc. This module keeps numeric columns numeric
and converts only unsafe mixed/object columns into readable strings before the
UI sends them to the browser.
"""
from __future__ import annotations

import json
from typing import Any


def _cell_to_arrow_safe_text(value: Any) -> str:
    """Return a small, stable, UI-safe string for mixed/object dataframe cells."""
    try:
        import pandas as pd
        if value is None or pd.isna(value):
            return ""
    except Exception:
        if value is None:
            return ""
    try:
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="replace")
        if isinstance(value, (dict, list, tuple, set)):
            return json.dumps(value, ensure_ascii=False, default=str)
        return str(value)
    except Exception:
        return repr(value)


def make_arrow_safe_dataframe(df: Any):
    """Return a dataframe copy that Streamlit/PyArrow can always display."""
    try:
        import pandas as pd
        import numpy as np
        if not isinstance(df, pd.DataFrame):
            return df
        safe = df.copy()
        for col in safe.columns:
            s = safe[col]
            # Preserve real numeric/bool/datetime columns. Only object-like or
            # extension columns with mixed python objects need conversion.
            if pd.api.types.is_numeric_dtype(s) or pd.api.types.is_bool_dtype(s) or pd.api.types.is_datetime64_any_dtype(s):
                continue
            # Category/string/object can still contain mixed python objects after
            # concatenation. Convert to python string explicitly for Arrow.
            if pd.api.types.is_categorical_dtype(s):
                safe[col] = s.astype(str).replace({"nan": "", "None": ""})
            else:
                safe[col] = s.map(_cell_to_arrow_safe_text).astype("string")
        return safe
    except Exception:
        return df


def install_safe_dataframe_patch() -> None:
    """Patch st.dataframe once so every tab is protected from ArrowTypeError."""
    try:
        import streamlit as st
        if getattr(st, "_new7_arrow_safe_dataframe_installed", False):
            return
        original_dataframe = st.dataframe

        def safe_dataframe(data=None, *args, **kwargs):
            try:
                data = make_arrow_safe_dataframe(data)
                return original_dataframe(data, *args, **kwargs)
            except Exception as exc:
                message = str(exc)
                if "ArrowTypeError" in message or "pyarrow" in message or "Conversion failed for column" in message:
                    try:
                        data = make_arrow_safe_dataframe(data)
                        return original_dataframe(data.astype(str) if hasattr(data, "astype") else data, *args, **kwargs)
                    except Exception:
                        try:
                            st.warning("Table had mixed data types, so it was shown as text for phone safety.")
                            st.write(data.astype(str) if hasattr(data, "astype") else data)
                            return None
                        except Exception:
                            raise exc
                raise

        st.dataframe = safe_dataframe
        st._new7_arrow_safe_dataframe_installed = True
    except Exception:
        pass
