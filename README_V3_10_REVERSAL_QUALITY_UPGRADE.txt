V3 10-REVERSAL QUALITY UPGRADE - 2026-06-03
================================================

What changed:
1. Kept the original 10-driver reversal engine intact.
2. Added V3 Quality Gate after the existing V2 strict noise gate.
3. Home and Finder now require stronger confirmation before showing 7/10+ reversal danger.
4. Raw 7/10 clusters are capped to 6/10 when they do not have:
   - enough before/after context,
   - old trend exhaustion,
   - pressure transfer to opposite side,
   - shock/fat-tail displacement,
   - flow/model confirmation.
5. Finder table now includes:
   - raw_active_10_count,
   - quality_score_v3,
   - quality_gate_v3.

Main behavior:
- 7/10 full reversal = high-quality confirmed reversal.
- 6/10 warning = transition / trend stop / preparation only.
- Noisy duplicated/sparse Finder windows are blocked from becoming danger alerts.

Run:
streamlit run main.py
