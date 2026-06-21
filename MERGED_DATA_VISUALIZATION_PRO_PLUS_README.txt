MERGED UPGRADE

This ZIP has the Data Visualization Pro++ candle upgrade merged directly into the source code.

Main patched file:
- tabs/home.py

Also patched mirrored home files when present so old split/package copies stay consistent.

Added features:
- Actual candlestick chart
- BLUE predicted future candlestick chart
- Prediction vs Actual history table
- Smooth major-regime detector with less noise
- Days in regime and estimated days left
- Original code kept; upgrade is appended and overrides the Data Visualization renderer only.
