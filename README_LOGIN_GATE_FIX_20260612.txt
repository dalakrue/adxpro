Login gate fix 2026-06-12

Fixed:
- NameError: _login_success is not defined.
- Guest button now logs in without crashing.
- Login page rebuilt in lightweight Galileo-style layout.
- Login/Create Account/Guest are real tab-style controls, not radio choices.
- Login form appears in the white glass card area.
- Local/Desktop account creation no longer shows OTP by default.
- Streamlit Cloud Gmail OTP can be enabled by setting NEW7_REQUIRE_OTP=1.
- Gmail SMTP requires a 16-character Google App Password; normal Gmail passwords are rejected by Google.
- Account database remains persistent at ~/.new7_quant_app/auth.sqlite3 unless NEW7_AUTH_DB is set.

Low RAM/CPU:
- CSS-only visual design.
- No canvas, no animation loop, no heavy JavaScript.
