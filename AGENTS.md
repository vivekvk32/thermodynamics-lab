# Agent Notes (ATD Lab)

This file captures implementation notes and pitfalls for future agent work,
especially when adding new experiments.

## Recent Fixes
- Fixed a runtime alert: `Error: name 'exp' is not defined` by escaping LaTeX
  braces inside a Python f-string in `app/utils.py`.
  - Example safe pattern: `f"$h_{{exp}} = {value}\\ \\text{{W/m}}^2\\text{{K}}$"`
  - Root cause: `{exp}` inside `$...$` was interpreted as a Python f-string
    placeholder instead of LaTeX.

## LaTeX + f-strings Pitfall
- Any `{...}` inside an f-string is treated as Python. For LaTeX, you must
  double braces: `{{` and `}}`.
- Common safe forms:
  - `\\dot{{m}}`, `\\text{{W}}`, `h_{{theoretical}}`, `K_{{avg}}`
- Quick sanity check (manual):
  - Search for f-strings that include `$` and single `{` near LaTeX.
  - If you see `_{exp}` or `\\text{W}` in an f-string, change to `{{...}}`.

## Adding a New Experiment (Checklist)
1) **Seed data**
   - Add content in `seed.py` (`aim`, `theory`, `inputs`, `constants`, `viva`).
   - Include LaTeX with double braces if used in Python f-strings.
2) **Calculation engine**
   - Implement in `app/utils.py`:
     - `calculate_<experiment>()`
     - `build_<experiment>_steps()` if step-by-step output is needed.
   - Wire it into `calculate_experiment()` dispatch.
3) **API wiring**
   - Update `app/blueprints/api.py` `/api/calculate` response shape.
   - Keep response keys consistent with front-end render logic.
4) **Front-end rendering**
   - Update `app/templates/experiment.html` for inputs/observations layout.
   - Update `app/static/js/experiment.js` for:
     - result tables
     - step rendering
     - graphs (Chart.js config)
5) **Report PDF**
   - Update `app/templates/report.html` for observation tables and result text.
   - Ensure LaTeX formatting matches MathJax / latex2mathml expectations.
6) **Tests (if applicable)**
   - Add or update tests in `tests/`.

## Files of Interest
- Core math: `app/utils.py`
- API endpoints: `app/blueprints/api.py`
- Report generation: `app/blueprints/main.py`, `app/templates/report.html`
- Front-end logic: `app/static/js/experiment.js`
