# ATD Lab Project Context for ChatGPT

This file describes the current project structure, data model, routes, templates, and calculation logic so an LLM can generate prompts or add new experiments confidently.

---

## 1) Quick summary
A Flask web app that serves a "Thermodynamics Digital Lab Manual".
It currently supports TWO experiments:
1) Determination of Thermal Conductivity of a Metal Rod
2) Heat Transfer Through Free (Natural) Convection (Vertical Tube)

Experiments are stored in SQLite as JSON configs; the app renders them into tabs, collects inputs, performs calculations, and generates a PDF report. Natural convection supports **multiple trials** (default 2).

---

## 2) Tech stack
- Backend: Flask 3, Flask-SQLAlchemy
- DB: SQLite (instance/lab_manual.db)
- Math/Calc: NumPy
- PDF: WeasyPrint + xhtml2pdf fallback (Windows prefers xhtml2pdf)
- Frontend: Bootstrap 5, Chart.js, MathJax, custom JS/CSS

---

## 3) Entry points and runtime
- run.py: creates Flask app via create_app() and runs it
- start_lab.bat: convenience launcher; **now runs seed.py before run.py**
- seed.py: seeds Experiment 1 and Experiment 2 into the DB (idempotent)

Note: repo currently has .venv, but start_lab.bat looks for venv.

---

## 4) Folder structure (key files)
```
app/
  __init__.py                # create_app + config + blueprint registration + db init
  extensions.py              # SQLAlchemy instance
  models.py                  # Experiment, StudentRun models
  utils.py                   # normalization + calc engines + helpers
  blueprints/
    main.py                  # UI routes + PDF generation
    api.py                   # /api/calculate, /api/save_run, /api/simulate
    admin.py                 # admin dashboard + edit/new experiment
  templates/
    base.html                # layout + dynamic sidebar
    index.html               # homepage (dynamic experiment list)
    experiment.html          # main experiment UI (tabs)
    report.html              # PDF/print template
    admin/
      dashboard.html
      edit_experiment.html
  static/
    css/style.css
    js/experiment.js
    img/observation-diagram.png

instance/
  lab_manual.db              # SQLite DB

tests/
  test_units.py              # unit normalization test (exp1)
  test_natural_convection.py # trial-based tests (exp2)

requirements.txt
README.md
run.py
seed.py
start_lab.bat
```

---

## 5) Data model (SQLAlchemy)
Experiment
- id (int PK)
- slug (unique string)
- title (string)
- content (JSON) - full experiment config

StudentRun
- id
- experiment_id (FK to Experiment)
- student_name, usn, date
- inputs (JSON) - raw inputs (including trial list for exp2)
- results (JSON) - normalized + results + warnings

---

## 6) Experiment JSON content schema
Stored in Experiment.content and edited via Admin.

```json
{
  "aim": "string",
  "apparatus": "string",
  "description": "HTML string",
  "theory": "HTML/LaTeX string",
  "procedure": ["Step 1", "..."],
  "inputs": [
    { "name": "flow_rate_value", "label": "Water Flow Rate", "unit": "" }
  ],
  "constants": {
    "d_rod": { "value": 0.035, "unit": "m", "desc": "Diameter of Rod" }
  },
  "viva": [
    { "question": "Q?", "answer": "A." }
  ]
}
```

Notes:
- experiment.html renders inputs as form fields; special handling for flow_rate_value / vol_flow + unit selector.
- constants are shown in a table; for cpw, rho, d_rod, l1, l2, l3, ri, ro, dx a unit selector is shown.
- description and theory are rendered as HTML (| safe).

Natural Convection (exp2) uses a **custom multi-trial table** in experiment.html, not the generic inputs list.

---

## 7) Current experiments (seed.py)
### Experiment 1
Slug: therm-conductivity-metal-rod
Title: Determination of Thermal Conductivity of a Metal Rod

Inputs include:
- flow_rate_value
- t_wi, t_wo
- t1..t5 (rod temps)
- t6, t7, t8, t9, t12, t13 (insulation temps)

Constants include:
- d_rod, kins, l1, l2, l3, ri, ro, cpw, rho, dx

### Experiment 2
Slug: natural-convection-vertical-tube
Title: Heat Transfer Through Free (Natural) Convection (Vertical Tube)

Observations UI:
- Two default trials in a table (Add/Remove buttons)
- Columns: V, I, T1..T6, T7 (Ta)

Air properties mode:
- Auto (from film temperature) or Manual input fields

Constants include:
- d_tube = 0.038 m, L_tube = 0.5 m, g = 9.81 m/s^2

---

## 8) Calculation engine (app/utils.py)
Key helpers:
- parse_numeric() supports plain numbers and 10^-6 formats
- normalize_inputs() handles Experiment 1 units and conversions

Experiment dispatch:
```
calculate_experiment(slug, inputs)
```

### Experiment 1
- calculate_therm_conductivity(slug, inputs)
- build_therm_conductivity_steps(calc_data)

### Experiment 2 (Natural Convection)
- calculate_natural_convection(slug, inputs)
  - accepts multi-trial observations via:
    - inputs.observations (JSON list)
    - OR trial_* form keys (trial_1_v, trial_1_t1, etc.)
  - computes per trial:
    Q, Ts, Ta, ΔT, Tf, β, Gr, Ra, Nu, h_exp, h_theoretical
  - supports manual or auto air properties
  - per-trial warnings (e.g., ΔT <= 0, missing temps)
  - returns results.trials[] with per-trial fields
- build_natural_convection_steps(calc_data)
  - returns steps per trial

Auto air properties
- AIR_PROPS_TABLE in utils.py (simple embedded lookup)
- get_air_properties_auto(temp_k) returns rho, cp, k_air, mu, nu, pr

---

## 9) Routes
Main UI (blueprints/main.py)
- GET / -> list experiments (index)
- GET /experiment/<slug> -> experiment view
- POST /experiment/<slug>/report -> PDF/HTML report

PDF:
- On Windows, tries xhtml2pdf by default.
- If WeasyPrint fails or USE_WEASYPRINT not set, falls back.
- For exp2, PDF expects `observations` JSON to be posted (provided by JS).

API (blueprints/api.py)
- POST /api/calculate
  - body: { slug, inputs }
  - exp1: returns steps, trace_table, graphs
  - exp2: returns trial_results, steps_by_trial, final_results, graphs

- POST /api/save_run
  - body: { slug, formData }
  - exp2 requires observations JSON (added in JS)

- POST /api/simulate
  - exp1: returns predicted rod temperature distribution
  - exp2: returns h vs power curve (simple model)

Admin (blueprints/admin.py)
- GET /admin -> dashboard
- GET/POST /admin/experiment/new -> create experiment (JSON textarea)
- GET/POST /admin/experiment/<id>/edit -> edit experiment

---

## 10) Frontend behavior
templates/experiment.html
- Tabs: Overview, Theory, Procedure, Observations, Calculations, Simulation, Viva
- exp1: shows observation diagram image
- exp2: uses multi-trial table (2 rows default) and air properties toggle

static/js/experiment.js
- calculateExperiment() -> calls /api/calculate
- saveRun() -> calls /api/save_run (adds observations for exp2)
- generatePDF() -> posts hidden form (adds observations for exp2)
- renderTrialResults() -> per-trial results table + final summary for exp2
- renderCharts() -> multi-trial line plot (T1..T6) + grouped bar chart (h_exp vs h_theoretical) for exp2
- updateSim() -> exp2 simple h vs power

Known quirks
- Some units in seed.py may show encoding artifacts (Â°C) from earlier data
- `.venv` vs `venv` naming in start_lab.bat

---

## 11) Tests
- tests/test_units.py (exp1 unit conversion sanity)
- tests/test_natural_convection.py (exp2 multi-trial sanity + h_theoretical numeric)

---

## 12) Adding a new experiment (high-level checklist)
1. Add new experiment JSON (Admin UI or seed script).
2. Create new calc function in app/utils.py.
3. Update calculate_experiment() dispatcher.
4. Update app/blueprints/api.py to handle new slug.
5. Update templates/JS if input layout differs.
6. Add tests for core calculations.

---

## 13) Key files to inspect when extending
- app/utils.py (calc engines + normalization + auto air props)
- app/blueprints/api.py (calc dispatch + JSON shape)
- app/templates/experiment.html (input rendering, trial table)
- app/static/js/experiment.js (client logic, charts, PDF/save)
- seed.py (experiment JSON)
- app/templates/report.html (PDF output per trial)
