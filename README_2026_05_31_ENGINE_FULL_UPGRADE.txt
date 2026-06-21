ENGINE FULL UPGRADE - 2026-05-31

What changed:
1. Engine tab now has an Engine Command Center above the inner tabs.
2. Added Data Quality %, Regime, Dominant Direction, Trend Score, Exhaustion Score, DVE 30/120 candles.
3. Added Exit BUY Danger % and Exit SELL Danger % to help avoid closing the wrong hedge side too early.
4. Added Multi-Window Confirmation for 30, 60, 120, 300, and 600 candle windows.
5. Fixed the Similar Regime fallback: Engine no longer depends on missing tabs.backtest.
6. Built-in similarity scanner ranks older windows by similarity + directional efficiency + future move context.
7. Original Engine wrapper and original inner-tab structure are preserved.

Run:
streamlit run adx_dashpoard.py

Recommended workflow:
1. Start the app.
2. Connect from the global sidebar first.
3. Open Engine.
4. Check Data Quality first.
5. Use Engine Command Center + Multi-Window Confirmation before using Similar Regime.

Important:
This is analytical support only. It is not a guaranteed prediction and should not be used as the only reason to close a BUY or SELL basket.
