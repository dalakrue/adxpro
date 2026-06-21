# Run ADX Quant Pro

## Windows PowerShell
```powershell
cd "C:\path\to\ADX_Quant_Pro_EURUSD_H1_Quality_Mobile_Reconstructed_20260621"
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python scripts_migrate_history_quality_20260621.py
python -m pytest -q
streamlit run app.py
```

## macOS/Linux
```bash
cd /path/to/ADX_Quant_Pro_EURUSD_H1_Quality_Mobile_Reconstructed_20260621
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python scripts_migrate_history_quality_20260621.py
python -m pytest -q
streamlit run app.py
```

Use the existing Settings **Run Calculation** action. Opening Lunch fields, paging/searching history, copying, exporting, or opening the local AI Assistant reads the last committed generation and does not call the protected calculator.
