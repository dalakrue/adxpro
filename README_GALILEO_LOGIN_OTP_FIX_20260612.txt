Galileo Login + OTP Fix 2026-06-12

What changed:
- Login page redesigned with lightweight Galileo-style purple/blue glass theme.
- Home/Data Visualization get a matching CSS-only mobile theme.
- No heavy JS animation, no canvas, no GPU effects, no background calculation loops.
- Guest button remains available.
- Account database remains outside code folder by default: ~/.new7_quant_app/auth.sqlite3
- OTP create account flow now has two modes:
  1) Local test OTP: always works for testing and does not use Gmail SMTP.
  2) Real Gmail SMTP: requires a 16-character Google App Password.

Important Gmail note:
- Gmail will reject your normal Gmail password with SMTP error 534 / 5.7.9.
- Use Google 2-Step Verification, then create a Google App Password.
- Paste the 16-character app password into the app, not your normal Gmail password.
- The app now catches this before crashing and falls back to local OTP for testing.
