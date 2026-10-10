# ResQMap AI — PS-53 Starter

A beginner-friendly Flask dashboard starter for the Disaster Damage Prioritization System.

## 1. Requirements
- Python 3.11 or 3.12 recommended
- VS Code
- Internet connection for Leaflet map tiles and CDN assets

## 2. Windows setup (PowerShell)

Open this folder in VS Code, then open Terminal > New Terminal.

Create a virtual environment:

```powershell
py -3.12 -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, use Command Prompt terminal instead:

```bat
.venv\Scripts\activate.bat
```

Install dependencies:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Run the application:

```powershell
python app.py
```

Open http://127.0.0.1:5000 in your browser.

Health check: http://127.0.0.1:5000/health

## 3. What works in this starter
- Responsive dashboard
- Sample incident summary cards
- Leaflet map with sample incident markers
- Ranked inspection queue
- CSV export
- Flask JSON API at `/api/incidents`

## 4. Important note
All current incident locations, damage labels and scores are illustrative demo data. They are not real disaster assessments and are not produced by an AI model yet. Next development steps are image upload, OpenCV image comparison, model integration if feasible, and calculated priority scores.

## 5. Project structure

```text
resqmap_ai_starter/
├── app.py
├── requirements.txt
├── README.md
├── templates/
│   └── index.html
└── static/
    ├── style.css
    └── app.js
```
