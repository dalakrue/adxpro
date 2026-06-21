Final sync fix 2026-06-12

What changed:
- Research is moved into Lunch/Home as an inner tab.
- Data Visualization now uses one final synced intelligence section instead of duplicate sections.
- One Unified PowerBI Price Projection has a synced accuracy-adjusted overlay based on regime, error history, KNN/Greedy priority, NLP cached status, Quant Structure, and Research Random Forest support.
- Actual vs Error projection is restored inside the projection open/close field.
- Copy Necessary 100 Lines and Copy Full Home H1 include the final synced data.
- Login screen appears before the app opens, with Login, Create Account + OTP, and Guest mode.
- Accounts are stored in ~/.new7_quant_app/auth.sqlite3 by default so they survive code updates.

OTP note:
- Real Gmail OTP requires SMTP sender Gmail + Gmail App Password or NEW7_SMTP_* environment variables.
- Without SMTP setup, the app shows a local OTP for testing instead of crashing.

Libraries:
- requirements.txt includes the requested research libraries.
- CatBoost and HMMLearn may not have Python 3.13 wheels; use Python 3.12 for the full optional stack.
