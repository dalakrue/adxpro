AI Assistant Lite upgrade 2026-06-12

Added inside Home/Lunch as a new inner tab:
- AI Assistant Lite

Files added:
- tabs/ai_assistant_lite.py
- tabs/ai_assistant_lite_home_patch_20260612.py

Functions added:
- build_ai_context_from_existing_data
- local_ai_detect_intent
- similar_setup_finder
- historical_tp_reach_rate
- weakest_factor_analysis
- regime_based_mining
- similar_hour_analysis
- prediction_error_mining
- data_quality_score
- answer_confidence_score
- local_ai_generate_answer
- render_ai_assistant_lite_tab

What it does:
- Uses st.chat_input, st.chat_message, and st.session_state message history.
- No OpenAI API, no external AI API, no paid API, no internet API.
- Uses local regex/keyword/phrase parsing to detect intent, target price, hours, and direction.
- Uses existing Home/Lunch/Data Visualization metrics and history data only.
- Explains current signal, BUY/SELL safety, TP probability, exit risk, TP quality, regime/prediction conflict, KNN/Greedy priority, similar past setups, historical TP reach proxy, data quality, and answer confidence.

Limitations:
- It does not replace trading decisions.
- It does not guarantee price movement.
- If the current metrics/history have not been calculated yet, it asks you to click Run Calculation first.
