2026-06-12 Research/Data Analysis/Data Mining/NLP upgrade

Added:
- Top-level Research tab with inner tabs: Data Analysis, Data Mining, NLP.
- Run-gated Research Calculation. No data mining or NLP API/RSS call runs on page load.
- Library alignment/status table for JavaScript helper, Polars, DuckDB, Numba, PyArrow, Plotly Resampler, Streamlit Copy Button, CacheTools, Scikit-learn, LightGBM, CatBoost, Statsmodels, HMMLearn, NLTK, and VADER.
- Optional Random Forest data mining using scikit-learn with n_jobs=1 and bounded rows for iPhone/laptop safety.
- KNN similar-history priority display, ascending Priority Rank.
- NLP EURUSD news confirmation using Finnhub/FMP/RSS only after the Run button.
- Regime prediction history + NLP overlay for hours 1 to 14 with at least top-ranked entry-opportunity rows when data supports it.
- Data Visualization research accuracy block under PowerBI: Random Forest + Regime/NLP History.
- Copy Full now includes final merged intelligence, DV research accuracy, and Research tab export.
- Home login now includes Guest mode without account/password.

Important:
- One Unified PowerBI regime remains the master. Research/RF/NLP only confirms, conflicts, or lowers priority.
- BEAR = SELL, BULL = BUY, RANGE = WAIT.
- Heavy libraries are imported defensively; if a package is missing, the app shows OPTIONAL / NOT INSTALLED instead of crashing.
- Some research libraries may not have wheels for Python 3.13. requirements.txt uses environment markers for the most risky ones; requirements_research_optional.txt contains the full optional stack if your Python version supports it.
