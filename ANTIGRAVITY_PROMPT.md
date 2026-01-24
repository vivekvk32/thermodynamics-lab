Heres a copy-paste prompt for Google Antigravity (agentic codegen) to add your second Thermodynamics lab experiment into the same existing "Thermodynamics Digital Lab Manual" Flask web app (same DB/JSON experiment system, same UI tabs, same PDF + graphs + simulation pattern). Its written to match your current project architecture and extend it cleanly.

---

## Prompt to paste into Google Antigravity (Agents)

You are a team of coding agents building on an existing local project: a Flask + SQLite "Thermodynamics Digital Lab Manual" web app. The app already supports Experiment 1: Thermal Conductivity of a Metal Rod, with experiments stored as JSON configs in SQLite, rendered into Bootstrap tab UI, with Chart.js graphs, MathJax formulas, /api/calculate, /api/simulate, save run, and PDF report generation. Follow the existing structure, patterns, and naming conventions described in PROJECT_CONTEXT.md.

### Goal

Add Experiment 2 (the next experiment in the same Thermodynamics/Heat Transfer lab manual):

EXPERIMENT NO-4: Heat Transfer through Free (Natural) Convection  Vertical Brass Tube in a Duct

Aim: determine the natural convection heat transfer coefficient for a vertical tube exposed to atmospheric air.

Use the experiment details and formulas from exp4.pdf.

---

# A) Agents and Responsibilities (must use multiple agents)

Create and run agents with explicit tasks:

1. Architect Agent

- Read PROJECT_CONTEXT.md and map current routes, JSON schema, calc dispatch, templates, JS flow.
- Decide minimal-change approach consistent with existing Experiment 1.

2. Backend Agent

- Implement new calculation function(s) in app/utils.py.
- Extend API dispatch in app/blueprints/api.py so /api/calculate supports the new slug.
- Extend /api/simulate to support simulation for this experiment.
- Add unit normalization + warnings similar to Experiment 1.

3. Frontend/UI Agent

- Ensure the existing tabbed UI works with the new experiment JSON:
  Overview, Theory, Procedure, Observations, Calculations, Simulation, Viva.
- Add any experiment-specific charts and results panels in the existing template and JS rendering.
- Keep UI visually appealing: Bootstrap cards, clear typography, sticky calculate bar, clean results table, alerts for warnings.

4. Data/Seed Agent

- Add a seed script or extend existing seed.py to insert the new experiment JSON into SQLite.
- Ensure the experiment appears in the homepage list and sidebar list (currently hard-coded quirks exist - fix to dynamic if feasible without breaking existing).

5. Testing Agent

- Add unit tests in tests/ for key computations and unit conversions.
- Provide at least sanity tests for h values and dimensionless numbers.

---

# B) New Experiment Definition (JSON in DB)

Create a new Experiment record in SQLite with:

- slug: natural-convection-vertical-tube
- title: Heat Transfer Through Free (Natural) Convection (Vertical Tube)
- aim, apparatus, description, theory (HTML + MathJax), procedure, inputs, constants, viva.

Use content from exp4.pdf:

- Apparatus: brass tube, rectangular duct, ammeter, voltmeter, thermocouples etc.
- Setup description: brass tube in vertical rectangular duct, heater inside, tube surface temp measured by 7 thermocouples, heat loss by natural convection.
- Procedure steps (turn heater on, steady state, read thermocouples and wattmeter, repeat).
- Specifications constants: tube material brass; diameter d=0.038 m; length L=0.5 m; heater 300 W; thermocouples 7; duct size 250x250x900 mm.
- Viva questions list from pdf.

### Inputs (Observations tab)

Create inputs to match observation table:

- Voltage V (volts)
- Current I (amps)
- Thermocouple temps: T1..T6 (surface temps along tube, C)
- Ambient Ta from T7 (C) (treat input as T7 but label "Ambient temp (T7 = Ta)" as in manual)

### Constants (Constants table)

Include:

- d_tube = 0.038 m
- L_tube = 0.5 m
- g = 9.81 m/s^2
- pi (optional)
- Optional emissivity/area loss toggle: keep simple by default.

### Air Properties at Film Temperature

Manual says: compute film temperature and take air properties from handbook at Tf:

- film temperature: Tf = [(Ts + Ta)/2] + 273 (Kelvin)
- volumetric coefficient: beta = 1/Tf
- properties needed: density rho, Cp, thermal conductivity k_air, dynamic viscosity mu, kinematic viscosity nu, Prandtl Pr.

Implement BOTH modes (user selectable):

1. Auto properties (recommended): approximate air properties as functions of Tf using standard engineering correlations / piecewise interpolation embedded in code (no internet calls). Keep it transparent and show values used.
2. Manual properties: allow user to type rho, Cp, k, mu (or nu), Pr if they want to match handbook tables exactly.

UI: Add a toggle "Air properties mode: Auto / Manual". If Manual, show the property input fields.

---

# C) Calculations (must match lab manual)

Implement calculations and show step-by-step in Calculations tab (like Experiment 1 steps HTML).

1. Energy input:

- Q = V * I (watts)

2. Average surface temperature:

- Ts = (T1+T2+T3+T4+T5+T6) / 6

3. Temperature difference:

- deltaT = Ts - Ta

4. Film temperature:

- Tf(K) = [(Ts + Ta)/2] + 273

5. Compute dimensionless groups:

- Grashof number:
  Gr = (L^3 * beta * g * deltaT * rho^2) / mu^2 (as shown in manual)
- Rayleigh number:
  Ra = Gr * Pr

6. Correlation constants:
   Use:

- C = 0.56, n = 0.25 for 10^4 < Ra < 10^8
- C = 0.13, n = 1/3 for 10^8 < Ra < 10^12

7. Nusselt number:

- Nu = (h * L) / k = C * (Gr*Pr)^n

8. Heat transfer coefficients:
   Interpret and implement BOTH, but label clearly to avoid confusion:

- h_correlation (from Nu correlation):
  h_correlation = (Nu * k_air) / L
- h_from_power (from electrical power balance):
  h_from_power = Q / [A_s * (Ts - Ta)]
  Where surface area A_s = pi * d * L (tube external area). (This is implied by the manuals As (Ts-Ta) term.)

Return both h values to UI and PDF:

- h_from_power (W/m^2K)
- h_correlation (W/m^2K)
  Also return Q, Ts, Ta, Tf, beta, rho, mu, nu, k_air, Pr, Gr, Ra, Nu, A_s.

Add warnings:

- if deltaT <= 0, warn user.
- if Ra outside correlation ranges, warn and still compute with nearest range or stop with friendly error (choose consistent approach).
- if units look wrong (e.g., temps too high, V or I non-positive), warn.

---

# D) Graphs (Calculations tab)

Use Chart.js like existing app. Generate:

1. Temperature profile plot: T1..T6 along position index (or normalized length). Simple x-axis = [1..6] with labels "T1T6".
2. Bar chart: compare h_from_power vs h_correlation.
3. Optional: Nu vs Ra point (single point) on log axes if feasible; otherwise show as KPI cards.

Return graphs payload from /api/calculate consistent with existing front-end pattern.

---

# E) Simulation Tab (interactive)

Create a simple simulation for this experiment:
Inputs:

- voltage (V) and current (I) OR directly watts Q (allow both with toggle)
- ambient Ta
- optionally a "target Ts" or "estimated deltaT"

Outputs:

- predicted h_from_power curve as watts increases
- optionally predicted Ts given h and Q using Ts = Ta + Q/(A_s*h)
  This is a lightweight educational simulation (not CFD). Must be clearly labeled "simple model".

Wire it through /api/simulate with slug support, similar to existing sim endpoint.

---

# F) PDF Report

Extend report generation so the new experiment prints cleanly:

- Student details (name/usn/date)
- Aim/apparatus/procedure
- Observation table (V, I, T1..T7)
- Constants table (d, L, etc.)
- Step-by-step calculations (same HTML steps)
- Final results: h_from_power and h_correlation
- Graph images (embed chart screenshots or regenerate server-side; follow existing approach used in Experiment 1)

---

# G) Acceptance Criteria (must be met)

1. Experiment appears on home page and sidebar, opens at /experiment/natural-convection-vertical-tube.
2. Observations form accepts V, I, T1..T7 and property mode inputs.
3. Calculate button calls /api/calculate and returns:

   - steps HTML
   - warnings
   - results + trace table
   - chart data rendered correctly
4. Simulation tab works with new slug.
5. Save Run stores inputs/results in StudentRun.
6. PDF report generates without crashing (Windows fallback supported as per project).
7. Unit tests pass.

---

# H) Implementation Notes (dont break existing experiment)

- Do not refactor everything. Minimal safe changes.
- Add a dispatcher in utils: calculate_experiment(slug, inputs) that routes to existing thermal conductivity calc and new natural convection calc.
- Keep normalization helpers consistent.
- Keep templates generic; only add experiment-specific UI where necessary.
- Update hard-coded "Experiments Available: 1" and sidebar list if easy; otherwise add new item without breaking.

---

# I) Files you MUST touch (expected)

- app/utils.py (new calc + property helper + steps builder)
- app/blueprints/api.py (slug dispatch)
- app/static/js/experiment.js (render graphs/results for new experiment without breaking existing)
- seed.py (insert experiment JSON)
- templates/ only if needed (prefer reuse)
- tests/ add tests

---

# J) Source Material Available Locally

- PROJECT_CONTEXT.md at /mnt/data/PROJECT_CONTEXT.md describes existing app structure and patterns.
- exp4.pdf at /mnt/data/exp4.pdf contains experiment write-up, formulas, constants, and viva.

Build it now, run locally, and ensure everything works end-to-end.

---

If you want, I can also produce the exact experiment JSON blob (ready to paste into your Admin "new experiment" textarea) in the same schema your app uses - so Antigravity can just seed it and move on.
