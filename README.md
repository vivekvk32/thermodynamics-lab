# Thermodynamics Digital Lab Manual

A complete web-based digital lab manual and simulator for marine engineering thermodynamics experiments.

## Features
- **Interactive Experiments**: Theory, Procedure, Observations, and Calculations tabs.
- **Automatic Calculations**: Step-by-step working shown for every result.
- **Graphs**: Dynamic visualization of temperature distributions using Chart.js.
- **Simulation Mode**: "What-if" analysis with interactive sliders (Flow rate, Heater power).
- **PDF Reporting**: Generate professional lab records with one click (LaTeX formulas included).
- **Admin Panel**: Add or edit experiments, constants, and questions via a web interface.
- **Student Data**: Save and track student run data.

## Installation

### Prerequisites
- Python 3.8+
- [GTK3 Runtime](https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases) (Required for WeasyPrint PDF generation on Windows)

### Setup
1. **Clone the repository** (or download source)
   ```bash
   cd "ATD lab"
   ```

2. **Create a virtual environment** (Recommended)
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # Linux/Mac
   source venv/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize Database**
   Run the seed script to create the database and load Experiment 1.
   ```bash
   python seed.py
   ```

5. **Run the Application**
   ```bash
   python run.py
   ```
   Access the app at `http://127.0.0.1:5000`

## Admin Panel
Access the admin dashboard at `http://127.0.0.1:5000/admin`.
(No password set by default for this local version).

## Usage
1. Click **Start Experiment 1** on the home page.
2. Read the **Overview** and **Theory**.
3. Go to **Observations** tab:
   - Enter values (e.g., Water Flow: 200, temps T1-T13).
   - Click **Compute Results**.
4. View **Calculations** tab for step-by-step logic and graphs.
5. Click **Generate Report PDF** to download the lab record.
6. Use **Simulation** tab to visualize theoretical trends.

## Tech Stack
- **Backend**: Flask, SQLAlchemy, SQLite, NumPy
- **Frontend**: Bootstrap 5, Chart.js, MathJax
- **PDF**: WeasyPrint, latex2mathml

## Developer Notes (Maintenance)
- **LaTeX in f-strings**: When embedding LaTeX in Python f-strings, escape braces with double braces (e.g., `h_{{exp}}`, `\\text{{W/m}}`). Unescaped `{exp}` inside `$...$` will raise `NameError: name 'exp' is not defined` at runtime.
- **Where calculations live**: Core math is in `app/utils.py`; request handlers in `app/blueprints/api.py` and `app/blueprints/main.py`; front-end rendering in `app/static/js/experiment.js`; report layout in `app/templates/report.html`.
- **Adding experiments**: See `AGENTS.md` for a checklist and pitfalls.
