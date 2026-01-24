from flask import Blueprint, request, jsonify
from app.utils import (
    calculate_experiment,
    build_therm_conductivity_steps,
    build_natural_convection_steps,
)
from app.models import Experiment, StudentRun
from app.extensions import db
import numpy as np
from datetime import datetime

bp = Blueprint('api', __name__, url_prefix='/api')

@bp.route('/calculate', methods=['POST'])
def calculate():
    # ... (existing calculate code) ...
    try:
        data = request.json or {}
        slug = data.get('slug')
        inputs = data.get('inputs')

        calc_data = calculate_experiment(slug, inputs)
        if "error" in calc_data:
            return jsonify({"success": False, "error": calc_data["error"]}), 404

        if slug == 'therm-conductivity-metal-rod':
            res = calc_data["results"]
            steps = build_therm_conductivity_steps(calc_data)
            trace_table = [
                {"label": "Vdot", "value": calc_data["normalized"]["vdot_m3s"], "unit": "m^3/s"},
                {"label": "m_dot", "value": calc_data["normalized"]["m_dot"], "unit": "kg/s"},
                {"label": "Qw", "value": calc_data["trace"]["qw"], "unit": "W"},
                {"label": "Area", "value": calc_data["trace"]["area"], "unit": "m^2"},
                {"label": "(dT/dx)_xx", "value": calc_data["trace"]["grads"][0], "unit": "K/m"},
                {"label": "(dT/dx)_yy", "value": calc_data["trace"]["grads"][1], "unit": "K/m"},
                {"label": "(dT/dx)_zz", "value": calc_data["trace"]["grads"][2], "unit": "K/m"},
                {"label": "ln(ro/ri)", "value": calc_data["trace"]["ln_ro_ri"], "unit": "-"},
                {"label": "Loss_xx", "value": calc_data["trace"]["loss_xx"], "unit": "W"},
                {"label": "Loss_yy", "value": calc_data["trace"]["loss_yy"], "unit": "W"},
                {"label": "Loss_zz", "value": calc_data["trace"]["loss_zz"], "unit": "W"},
                {"label": "Qxx", "value": calc_data["trace"]["qs"][0], "unit": "W"},
                {"label": "Qyy", "value": calc_data["trace"]["qs"][1], "unit": "W"},
                {"label": "Qzz", "value": calc_data["trace"]["qs"][2], "unit": "W"},
                {"label": "Kxx", "value": calc_data["trace"]["ks"][0], "unit": "W/mK"},
                {"label": "Kyy", "value": calc_data["trace"]["ks"][1], "unit": "W/mK"},
                {"label": "Kzz", "value": calc_data["trace"]["ks"][2], "unit": "W/mK"},
                {"label": "K_avg", "value": calc_data["trace"]["k_avg"], "unit": "W/mK"},
            ]

            return jsonify({
                "success": True,
                "slug": slug,
                "k_avg": round(res['k_avg'], 3),
                "steps": steps,
                "warnings": calc_data.get("warnings", []),
                "trace": calc_data.get("trace", {}),
                "normalized": calc_data.get("normalized", {}),
                "raw_inputs": calc_data.get("raw_inputs", {}),
                "trace_table": trace_table,
                "graphs": {
                    "type": "therm_conductivity",
                    "rod_temps": calc_data["normalized"]["t_rod"],
                }
            })

        if slug == "natural-convection-vertical-tube":
            res = calc_data["results"]
            steps_by_trial = build_natural_convection_steps(calc_data)
            trials = res.get("trials", [])
            trial_payload = []
            for item in trials:
                trial_payload.append({
                    "trial": item.get("trial", 1),
                    "q": item.get("q", 0.0),
                    "ts": item.get("ts", 0.0),
                    "ta": item.get("ta", 0.0),
                    "gr": item.get("gr", 0.0),
                    "ra": item.get("ra", 0.0),
                    "nu": item.get("nu_nusselt", 0.0),
                    "h_exp": item.get("h_exp", 0.0),
                    "h_theoretical": item.get("h_theoretical", 0.0),
                    "temps": item.get("temps", []),
                    "warnings": item.get("warnings", []),
                })

            trial_summary = [
                {
                    "trial": item.get("trial", 1),
                    "h_exp": item.get("h_exp"),
                    "h_theoretical": item.get("h_theoretical"),
                }
                for item in trials
            ]
            valid_exp = [item.get("h_exp") for item in trials if item.get("h_exp")]
            valid_theory = [item.get("h_theoretical") for item in trials if item.get("h_theoretical")]
            mean_h_exp = sum(valid_exp) / len(valid_exp) if valid_exp else None
            mean_h_theoretical = sum(valid_theory) / len(valid_theory) if valid_theory else None

            return jsonify({
                "success": True,
                "slug": slug,
                "steps": [],
                "steps_by_trial": steps_by_trial if isinstance(steps_by_trial, list) else [],
                "steps_html": steps_by_trial,
                "warnings": calc_data.get("warnings", []),
                "trace": calc_data.get("trace", {}),
                "normalized": calc_data.get("normalized", {}),
                "raw_inputs": calc_data.get("raw_inputs", {}),
                "trace_table": [],
                "trials": trial_payload,
                "trial_results": trial_payload,
                "final_results": {
                    "trial_summary": trial_summary,
                    "optional_overall": {
                        "mean_h_exp": mean_h_exp,
                        "mean_h_theoretical": mean_h_theoretical,
                    }
                },
                "explanation_blocks": calc_data.get("explanation_blocks", []),
                "final_explanation": calc_data.get("final_explanation", ""),
                "graphs": {
                    "type": "natural_convection",
                    "temp_labels": ["T1", "T2", "T3", "T4", "T5", "T6"],
                    "trials": [
                        {
                            "label": f"Trial {item.get('trial', idx + 1)}",
                            "temps": item.get("temps", []),
                            "h_exp": item.get("h_exp", 0.0),
                            "h_theoretical": item.get("h_theoretical", 0.0),
                        }
                        for idx, item in enumerate(trials)
                    ],
                }
            })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

    return jsonify({"success": False, "error": "Unknown slug"}), 404

@bp.route('/save_run', methods=['POST'])
def save_run():
    try:
        data = request.json
        slug = data.get('slug')
        form_data = data.get('formData')
        
        # 1. Get Experiment
        exp = Experiment.query.filter_by(slug=slug).first()
        if not exp:
            return jsonify({"success": False, "error": "Experiment not found"}), 404
            
        # 2. Extract specific student info
        student_name = form_data.get('student_name', 'Unknown')
        usn = form_data.get('usn', 'N/A')
        date_str = form_data.get('date')
        
        run_date = datetime.utcnow()
        if date_str:
            try:
                run_date = datetime.strptime(date_str, '%Y-%m-%d')
            except:
                pass

        # 3. Calculate Results to store them
        # Convert form data to inputs format expected by calc engine
        inputs = {k: v for k, v in form_data.items() if k not in ['student_name', 'usn', 'date', 'instructor', 'slug']}
        
        # Re-map t1..t13 keys if needed (the calc engine expects 't1', 't2'...) which matches form names
        # Just passing filtered dict is fine
        
        calc_res = calculate_experiment(slug, inputs)
        if "error" in calc_res:
            return jsonify({"success": False, "error": calc_res["error"]}), 400
        
        # 4. Save to DB
        run = StudentRun(
            experiment_id=exp.id,
            student_name=student_name,
            usn=usn,
            date=run_date,
            inputs=calc_res.get('raw_inputs', inputs),
            results={
                "results": calc_res.get("results", {}),
                "normalized": calc_res.get("normalized", {}),
                "warnings": calc_res.get("warnings", []),
                "trace": calc_res.get("trace", {}),
            }
        )
        
        db.session.add(run)
        db.session.commit()
        
        return jsonify({"success": True, "id": run.id})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@bp.route('/simulate', methods=['POST'])
def simulate():
    # ... (existing simulate code) ...
    data = request.json or {}
    slug = data.get("slug", "therm-conductivity-metal-rod")

    if slug == "natural-convection-vertical-tube":
        q = float(data.get("q", 100))
        delta_t = float(data.get("delta_t", 30))
        d_tube = float(data.get("d_tube", 0.038))
        l_tube = float(data.get("l_tube", 0.5))
        area_s = np.pi * d_tube * l_tube if d_tube and l_tube else 0.0

        q_min = max(10.0, q * 0.4)
        q_max = max(q_min + 10.0, q * 1.6)
        qs = np.linspace(q_min, q_max, 10)
        hs = [val / (area_s * delta_t) if area_s and delta_t else 0.0 for val in qs]
        return jsonify({
            "q": qs.tolist(),
            "h": hs,
            "delta_t": delta_t,
        })

    flow = float(data.get('flow', 0.15))
    watts = float(data.get('watts', 40))

    k_copper = 385
    d = 0.035
    area = np.pi * d**2 / 4
    length = 0.3

    q_eff = watts * 0.9
    gradient = q_eff / (k_copper * area) if area else 0.0
    t_cold = 25 + (watts / (flow * 4180 / 60 * 10)) if flow else 25
    t_hot = t_cold + gradient * length

    x = np.linspace(0, length, 10)
    temps = t_hot - gradient * x

    return jsonify({
        "x": x.tolist(),
        "temps": temps.tolist()
    })
