Train Data Full Upgrade - 2026-06-01

What changed:
1. Train Data now has four inner sections: Live Training, Model Validation, History Search, and Database Center.
2. Uses only the global sidebar connector. It reads st.session_state['last_df'] from Home/Engine/Doo Prime connection.
3. Adds stronger data-quality checks: missing columns, duplicate candles, time gaps, and invalid OHLC values.
4. Adds future-label preparation:
   - target_buy
   - target_sell
   - target_direction = BUY / SELL / WAIT
   - future_move_pct and future_move_atr
5. Adds model validation with walk-forward RandomForest when scikit-learn is installed.
6. Adds feature-importance chart and BUY/SELL probability metrics.
7. Adds saved training-cache reload.
8. Adds manual Save Now and Download latest training CSV.
9. Keeps Database Center inside Train Data.
10. Does not remove or change original Home, Engine, Pre Original, Profile routing.

Run:
streamlit run adx_dashpoard.py --server.address 0.0.0.0 --server.port 8501

If port 8501 is busy, use another integer port, for example:
streamlit run adx_dashpoard.py --server.address 0.0.0.0 --server.port 8502
