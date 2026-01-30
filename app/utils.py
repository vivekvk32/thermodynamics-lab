import re
import json
import numpy as np
from app.models import Experiment


AIR_PROPS_TABLE = [
    {"T": 250.0, "rho": 1.394, "cp": 1006.0, "k": 0.0223, "mu": 1.70e-5, "pr": 0.71},
    {"T": 300.0, "rho": 1.177, "cp": 1007.0, "k": 0.02624, "mu": 1.846e-5, "pr": 0.707},
    {"T": 350.0, "rho": 1.007, "cp": 1009.0, "k": 0.0300, "mu": 2.08e-5, "pr": 0.70},
    {"T": 400.0, "rho": 0.882, "cp": 1012.0, "k": 0.0339, "mu": 2.29e-5, "pr": 0.69},
    {"T": 450.0, "rho": 0.784, "cp": 1015.0, "k": 0.0370, "mu": 2.50e-5, "pr": 0.69},
    {"T": 500.0, "rho": 0.707, "cp": 1017.0, "k": 0.0400, "mu": 2.70e-5, "pr": 0.69},
]


def interpolate_property(temp_k, key):
    if temp_k is None:
        return 0.0
    temps = [row["T"] for row in AIR_PROPS_TABLE]
    if temp_k <= temps[0]:
        return AIR_PROPS_TABLE[0][key]
    if temp_k >= temps[-1]:
        return AIR_PROPS_TABLE[-1][key]
    for idx in range(len(AIR_PROPS_TABLE) - 1):
        t0 = AIR_PROPS_TABLE[idx]["T"]
        t1 = AIR_PROPS_TABLE[idx + 1]["T"]
        if t0 <= temp_k <= t1:
            v0 = AIR_PROPS_TABLE[idx][key]
            v1 = AIR_PROPS_TABLE[idx + 1][key]
            if t1 == t0:
                return v0
            frac = (temp_k - t0) / (t1 - t0)
            return v0 + frac * (v1 - v0)
    return AIR_PROPS_TABLE[-1][key]


def get_air_properties_auto(temp_k):
    rho = interpolate_property(temp_k, "rho")
    cp = interpolate_property(temp_k, "cp")
    k_air = interpolate_property(temp_k, "k")
    mu = interpolate_property(temp_k, "mu")
    pr = interpolate_property(temp_k, "pr")
    nu = mu / rho if rho else 0.0
    return {
        "rho": rho,
        "cp": cp,
        "k_air": k_air,
        "mu": mu,
        "nu": nu,
        "pr": pr,
    }


def parse_numeric(value):
    if value is None:
        return 0.0
    if isinstance(value, (int, float, np.integer, np.floating)):
        return float(value)
    text = str(value).strip()
    if not text:
        return 0.0
    try:
        return float(text)
    except (ValueError, TypeError):
        pass

    compact = re.sub(r"\s+", "", text.lower())
    compact = compact.replace("**", "^").replace("×", "x").replace("−", "-").replace("–", "-")

    # Support "10^-6"
    match = re.match(r"^10\^?([+-]?\d+)$", compact)
    if match:
        return 10 ** int(match.group(1))

    # Support "1x10^-6" or "1*10^-6"
    match = re.match(r"^([+-]?\d*\.?\d+)(?:x|\*)10\^?([+-]?\d+)$", compact)
    if match:
        return float(match.group(1)) * (10 ** int(match.group(2)))

    return 0.0


def normalize_inputs(raw_inputs, consts):
    raw_inputs = raw_inputs or {}
    consts = consts or {}

    warnings = []
    suspects = set()

    def normalize_unit(unit, mapping, default):
        if not unit:
            return default
        key = str(unit).strip().lower()
        return mapping.get(key, unit)

    def get_num(key, default=0.0):
        return parse_numeric(raw_inputs.get(key, default))

    def get_const_num(key, default=0.0):
        item = consts.get(key, {})
        return parse_numeric(item.get("value", default))

    def get_const_unit(key, default=""):
        item = consts.get(key, {})
        return item.get("unit", default)

    length_unit_map = {
        "m": "m",
        "meter": "m",
        "meters": "m",
        "metre": "m",
        "metres": "m",
        "mm": "mm",
        "millimeter": "mm",
        "millimeters": "mm",
        "millimetre": "mm",
        "millimetres": "mm",
    }

    flow_unit_map = {
        "l/min": "L/min",
        "liter/min": "L/min",
        "liters/min": "L/min",
        "litre/min": "L/min",
        "litres/min": "L/min",
        "ml/min": "mL/min",
        "milliliter/min": "mL/min",
        "milliliters/min": "mL/min",
        "millilitre/min": "mL/min",
        "millilitres/min": "mL/min",
        "cc/min": "cc/min",
        "kg/s": "kg/s",
        "kg/sec": "kg/s",
        "kg/min": "kg/min",
    }

    # Flow rate inputs
    flow_value = get_num("flow_rate_value", raw_inputs.get("vol_flow", raw_inputs.get("flow", 0.0)))
    flow_unit = raw_inputs.get("flow_rate_unit")
    if not flow_unit:
        if "vol_flow" in raw_inputs:
            flow_unit = "cc/min"
        else:
            flow_unit = "L/min"
    flow_unit = normalize_unit(flow_unit, flow_unit_map, "L/min")

    # Fluid properties
    rho = get_num("rho", get_const_num("rho", 1000.0))
    rho_unit = normalize_unit(raw_inputs.get("rho_unit", get_const_unit("rho", "kg/m^3")), {
        "kg/m3": "kg/m^3",
        "kg/m^3": "kg/m^3",
    }, "kg/m^3")

    cpw = get_num("cpw", get_const_num("cpw", 4180.0))
    cpw_unit = normalize_unit(raw_inputs.get("cpw_unit", get_const_unit("cpw", "J/kgK")), {
        "j/kgk": "J/kgK",
        "j/kg-k": "J/kgK",
        "kj/kgk": "kJ/kgK",
        "kj/kg-k": "kJ/kgK",
    }, "J/kgK")
    if cpw_unit == "kJ/kgK":
        cpw *= 1000.0
    if cpw and cpw < 1000:
        warnings.append("Cp value is very low; check if kJ/kgK was entered without unit conversion.")
        suspects.add("cpw")

    kins = get_num("kins", get_const_num("kins", 0.0))

    def get_length(name, default_val=0.0, unit_key=None):
        val = get_num(name, get_const_num(name, default_val))
        unit = raw_inputs.get(unit_key or f"{name}_unit", get_const_unit(name, "m"))
        unit = normalize_unit(unit, length_unit_map, "m")
        return val, unit

    d_rod_val, d_rod_unit = get_length("d_rod", get_const_num("d_rod", 0.0), "rod_diameter_unit")
    l1_val, l1_unit = get_length("l1", get_const_num("l1", 0.0), "l1_unit")
    l2_val, l2_unit = get_length("l2", get_const_num("l2", 0.0), "l2_unit")
    l3_val, l3_unit = get_length("l3", get_const_num("l3", 0.0), "l3_unit")
    ri_val, ri_unit = get_length("ri", get_const_num("ri", 0.0), "ri_unit")
    ro_val, ro_unit = get_length("ro", get_const_num("ro", 0.0), "ro_unit")
    dx_val, dx_unit = get_length("dx", get_const_num("dx", 0.06), "dx_unit")

    def to_m(val, unit):
        return val / 1000.0 if unit == "mm" else val

    d_rod = to_m(d_rod_val, d_rod_unit)
    l1 = to_m(l1_val, l1_unit)
    l2 = to_m(l2_val, l2_unit)
    l3 = to_m(l3_val, l3_unit)
    ri = to_m(ri_val, ri_unit)
    ro = to_m(ro_val, ro_unit)
    dx = to_m(dx_val, dx_unit)

    # Temperature inputs (C, deltaT is K-equivalent)
    t_wi = get_num("t_wi", 0.0)
    t_wo = get_num("t_wo", 0.0)
    t_rod = [get_num(f"t{i}", 0.0) for i in range(1, 6)]
    t_ins = {i: get_num(f"t{i}", 0.0) for i in [6, 7, 8, 9, 12, 13]}

    # Flow conversion
    vdot_m3s = 0.0
    m_dot = 0.0
    flow_lmin = 0.0
    if flow_unit in ["L/min", "mL/min", "cc/min"]:
        factor = 1e-3 if flow_unit == "L/min" else 1e-6
        vdot_m3s = (flow_value * factor) / 60.0
        m_dot = rho * vdot_m3s
        flow_lmin = flow_value if flow_unit == "L/min" else flow_value / 1000.0
    elif flow_unit in ["kg/s", "kg/min"]:
        m_dot = flow_value if flow_unit == "kg/s" else flow_value / 60.0
        vdot_m3s = (m_dot / rho) if rho else 0.0
        flow_lmin = (vdot_m3s * 60.0) / 1e-3 if rho else 0.0
    else:
        warnings.append(f"Unknown flow unit '{flow_unit}'. Assuming L/min.")
        vdot_m3s = (flow_value * 1e-3) / 60.0
        m_dot = rho * vdot_m3s
        flow_lmin = flow_value

    # Geometry sanity checks
    geom_checks = {
        "d_rod": d_rod,
        "l1": l1,
        "l2": l2,
        "l3": l3,
        "dx": dx,
        "ri": ri,
        "ro": ro,
    }
    for name, val in geom_checks.items():
        if val == 0:
            continue
        if val > 5 or val < 1e-6:
            warnings.append(f"{name} normalized to {fmt_num(val)} m. Likely unit mismatch.")
            suspects.add(f"{name}_unit")

    raw = {
        "flow_rate_value": flow_value,
        "flow_rate_unit": flow_unit,
        "rho": rho,
        "rho_unit": rho_unit,
        "cpw": cpw,
        "cpw_unit": cpw_unit,
        "kins": kins,
        "d_rod": d_rod_val,
        "rod_diameter_unit": d_rod_unit,
        "l1": l1_val,
        "l1_unit": l1_unit,
        "l2": l2_val,
        "l2_unit": l2_unit,
        "l3": l3_val,
        "l3_unit": l3_unit,
        "ri": ri_val,
        "ri_unit": ri_unit,
        "ro": ro_val,
        "ro_unit": ro_unit,
        "dx": dx_val,
        "dx_unit": dx_unit,
        "t_wi": t_wi,
        "t_wo": t_wo,
        "t_rod": t_rod,
        "t_ins": t_ins,
    }

    normalized = {
        "flow_rate_value": flow_value,
        "flow_rate_unit": flow_unit,
        "rho": rho,
        "cpw": cpw,
        "kins": kins,
        "d_rod": d_rod,
        "l1": l1,
        "l2": l2,
        "l3": l3,
        "ri": ri,
        "ro": ro,
        "dx": dx,
        "t_wi": t_wi,
        "t_wo": t_wo,
        "t_rod": t_rod,
        "t_ins": t_ins,
        "vdot_m3s": vdot_m3s,
        "m_dot": m_dot,
        "flow_lmin": flow_lmin,
    }

    return {
        "raw_inputs": raw,
        "normalized": normalized,
        "warnings": warnings,
        "suspects": suspects,
    }


def fmt_num(value, digits=3):
    try:
        val = float(value)
    except (TypeError, ValueError):
        return "0"
    if val == 0:
        return "0"
    if abs(val) < 1e-3 or abs(val) >= 1e4:
        return f"{val:.{digits}e}"
    return f"{val:.{digits}f}"


def build_therm_conductivity_steps(calc_data):
    normalized = calc_data["normalized"]
    trace = calc_data["trace"]

    t_rod = normalized["t_rod"]
    t_ins = normalized["t_ins"]

    steps = [
        "1. Flow conversion: "
        f"$$\\dot{{V}} = {fmt_num(normalized['flow_rate_value'])}\\ \\text{{{normalized['flow_rate_unit']}}} \\rightarrow "
        f"\\dot{{V}} = {fmt_num(normalized['vdot_m3s'])}\\ \\text{{m}}^3/\\text{{s}},\\ "
        f"\\dot{{m}} = \\rho \\dot{{V}} = {fmt_num(normalized['rho'])} \\times {fmt_num(normalized['vdot_m3s'])} = {fmt_num(normalized['m_dot'])}\\ \\text{{kg/s}}$$",
        "2. Heat carried by water: "
        f"$$Q_w = \\dot{{m}} C_p (T_{{wo}} - T_{{wi}}) = {fmt_num(normalized['m_dot'])} \\times {fmt_num(normalized['cpw'], 0)} "
        f"\\times ({fmt_num(normalized['t_wo'])} - {fmt_num(normalized['t_wi'])}) = {fmt_num(trace['qw'])}\\ \\text{{W}}$$",
        "3. Area of rod: "
        f"$$A = \\frac{{\\pi d^2}}{{4}} = \\frac{{\\pi ({fmt_num(normalized['d_rod'])})^2}}{{4}} = {fmt_num(trace['area'])}\\ \\text{{m}}^2$$",
        "4. Temperature gradients: "
        f"$$\\begin{{aligned}}"
        f"\\left(\\frac{{dT}}{{dx}}\\right)_{{xx}} &= \\frac{{{fmt_num(t_rod[0])} - {fmt_num(t_rod[2])}}}{{2\\,{fmt_num(normalized['dx'])}}} = {fmt_num(trace['grads'][0])}\\ \\text{{K/m}} \\\\"
        f"\\left(\\frac{{dT}}{{dx}}\\right)_{{yy}} &= \\frac{{{fmt_num(t_rod[1])} - {fmt_num(t_rod[3])}}}{{2\\,{fmt_num(normalized['dx'])}}} = {fmt_num(trace['grads'][1])}\\ \\text{{K/m}} \\\\"
        f"\\left(\\frac{{dT}}{{dx}}\\right)_{{zz}} &= \\frac{{{fmt_num(t_rod[2])} - {fmt_num(t_rod[4])}}}{{2\\,{fmt_num(normalized['dx'])}}} = {fmt_num(trace['grads'][2])}\\ \\text{{K/m}}"
        f"\\end{{aligned}}$$",
        "5. Heat through XX: "
        f"$$Q_{{xx}} = Q_w + \\frac{{2\\pi L_1 k_{{ins}}(T_{{12}}-T_{{13}})}}{{\\ln(r_o/r_i)}} "
        f"= {fmt_num(trace['qw'])} + {fmt_num(trace['loss_xx'])} = {fmt_num(trace['qs'][0])}\\ \\text{{W}}$$"
        f"$$K_{{xx}} = \\frac{{Q_{{xx}}}}{{A\\left(\\frac{{dT}}{{dx}}\\right)_{{xx}}}} "
        f"= \\frac{{{fmt_num(trace['qs'][0])}}}{{{fmt_num(trace['area'])} \\times {fmt_num(trace['grads'][0])}}} = {fmt_num(trace['ks'][0])}\\ \\text{{W/mK}}$$",
        "6. Heat through YY: "
        f"$$Q_{{yy}} = Q_{{xx}} + \\frac{{2\\pi L_2 k_{{ins}}(T_{{8}}-T_{{9}})}}{{\\ln(r_o/r_i)}} "
        f"= {fmt_num(trace['qs'][0])} + {fmt_num(trace['loss_yy'])} = {fmt_num(trace['qs'][1])}\\ \\text{{W}}$$"
        f"$$K_{{yy}} = \\frac{{Q_{{yy}}}}{{A\\left(\\frac{{dT}}{{dx}}\\right)_{{yy}}}} "
        f"= \\frac{{{fmt_num(trace['qs'][1])}}}{{{fmt_num(trace['area'])} \\times {fmt_num(trace['grads'][1])}}} = {fmt_num(trace['ks'][1])}\\ \\text{{W/mK}}$$",
        "7. Heat through ZZ: "
        f"$$Q_{{zz}} = Q_{{yy}} + \\frac{{2\\pi L_3 k_{{ins}}(T_{{6}}-T_{{7}})}}{{\\ln(r_o/r_i)}} "
        f"= {fmt_num(trace['qs'][1])} + {fmt_num(trace['loss_zz'])} = {fmt_num(trace['qs'][2])}\\ \\text{{W}}$$"
        f"$$K_{{zz}} = \\frac{{Q_{{zz}}}}{{A\\left(\\frac{{dT}}{{dx}}\\right)_{{zz}}}} "
        f"= \\frac{{{fmt_num(trace['qs'][2])}}}{{{fmt_num(trace['area'])} \\times {fmt_num(trace['grads'][2])}}} = {fmt_num(trace['ks'][2])}\\ \\text{{W/mK}}$$",
        "8. Average conductivity: "
        f"$$K_{{avg}} = \\frac{{K_{{xx}} + K_{{yy}} + K_{{zz}}}}{{3}} = {fmt_num(trace['k_avg'])}\\ \\text{{W/mK}}$$",
    ]

    return steps


def format_theory_html(text):
    if not text:
        return ""
    s = str(text)

    # Basic LaTeX -> readable HTML conversions for print
    s = s.replace("\\_", "_")
    s = s.replace("\\pi", "&pi;")
    s = s.replace("\\ln", "ln")
    s = s.replace("\\cdot", "&times;")

    def frac(match):
        return f"({match.group(1)}/{match.group(2)})"

    s = re.sub(r"\\frac\{([^{}]+)\}\{([^{}]+)\}", frac, s)

    # Subscripts/superscripts in common patterns
    s = re.sub(r"([A-Za-z])_\{([^{}]+)\}", r"\1<sub>\2</sub>", s)
    s = re.sub(r"([A-Za-z0-9])\^\{([^{}]+)\}", r"\1<sup>\2</sup>", s)
    s = re.sub(r"([A-Za-z])_([A-Za-z0-9]+)", r"\1<sub>\2</sub>", s)
    s = re.sub(r"([A-Za-z0-9])\^([A-Za-z0-9]+)", r"\1<sup>\2</sup>", s)

    # Remove remaining backslashes from LaTeX commands
    s = s.replace("\\", "")

    # Convert block and inline math to styled containers
    s = re.sub(r"\$\$(.+?)\$\$", lambda m: f'<div class="math-block">{m.group(1).strip()}</div>', s, flags=re.S)
    s = re.sub(r"\$(.+?)\$", lambda m: f'<span class="math">{m.group(1).strip()}</span>', s, flags=re.S)

    return s


def calculate_therm_conductivity(slug, inputs):
    # Fetch Constants
    exp = Experiment.query.filter_by(slug=slug).first()
    if not exp:
        return {"error": "Experiment not found"}

    consts = exp.content.get("constants", {})

    norm_pack = normalize_inputs(inputs, consts)
    normalized = norm_pack["normalized"]
    warnings = list(norm_pack["warnings"])
    suspects = set(norm_pack["suspects"])

    d_rod = normalized["d_rod"]
    kins = normalized["kins"]
    l1 = normalized["l1"]
    l2 = normalized["l2"]
    l3 = normalized["l3"]
    ri = normalized["ri"]
    ro = normalized["ro"]
    cpw = normalized["cpw"]
    mw = normalized["m_dot"]
    dx = normalized["dx"]

    t_wi = normalized["t_wi"]
    t_wo = normalized["t_wo"]
    t_rod = normalized["t_rod"]
    t_ins = normalized["t_ins"]

    delta_t_water = t_wo - t_wi
    qw = mw * cpw * delta_t_water

    area = (np.pi * (d_rod ** 2)) / 4.0 if d_rod else 0.0

    if dx:
        grad_xx = (t_rod[0] - t_rod[2]) / (2 * dx)
        grad_yy = (t_rod[1] - t_rod[3]) / (2 * dx)
        grad_zz = (t_rod[2] - t_rod[4]) / (2 * dx)
    else:
        grad_xx = grad_yy = grad_zz = 0.0
        warnings.append("dx is zero; gradients are set to 0.")
        suspects.add("dx_unit")

    ln_ro_ri = np.log(ro / ri) if ro and ri and ro > 0 and ri > 0 else 0.0
    rad_factor = (2 * np.pi * kins) / ln_ro_ri if ln_ro_ri else 0.0

    loss_xx_term = rad_factor * l1 * (t_ins[12] - t_ins[13])
    loss_yy_term = rad_factor * l2 * (t_ins[8] - t_ins[9])
    loss_zz_term = rad_factor * l3 * (t_ins[6] - t_ins[7])

    q_xx = qw + loss_xx_term
    q_yy = q_xx + loss_yy_term
    q_zz = q_yy + loss_zz_term

    k_xx = q_xx / (area * grad_xx) if area and grad_xx else 0.0
    k_yy = q_yy / (area * grad_yy) if area and grad_yy else 0.0
    k_zz = q_zz / (area * grad_zz) if area and grad_zz else 0.0

    k_avg = (k_xx + k_yy + k_zz) / 3.0 if (k_xx or k_yy or k_zz) else 0.0

    # Guardrails
    if delta_t_water >= 0.5 and normalized["flow_lmin"] >= 0.05 and qw < 0.1:
        warnings.append("Qw is very low for the given flow and deltaT. Check flow units and conversion.")
        suspects.add("flow_rate_unit")

    if k_avg and (k_avg > 2000 or k_avg < 1):
        if not suspects:
            suspects.update(["flow_rate_unit", "rod_diameter_unit", "l1_unit", "l2_unit", "l3_unit", "ri_unit", "ro_unit"])
        suspect_list = ", ".join(sorted(suspects))
        warnings.append(f"Likely unit error: K_avg = {fmt_num(k_avg)} W/mK. Check {suspect_list}.")

    trace = {
        "qw": qw,
        "area": area,
        "grads": [grad_xx, grad_yy, grad_zz],
        "qs": [q_xx, q_yy, q_zz],
        "ks": [k_xx, k_yy, k_zz],
        "k_avg": k_avg,
        "ln_ro_ri": ln_ro_ri,
        "rad_factor": rad_factor,
        "loss_xx": loss_xx_term,
        "loss_yy": loss_yy_term,
        "loss_zz": loss_zz_term,
        "delta_t_water": delta_t_water,
    }

    return {
        "raw_inputs": norm_pack["raw_inputs"],
        "normalized": normalized,
        "results": {
            "qw": qw,
            "area": area,
            "grads": [grad_xx, grad_yy, grad_zz],
            "qs": [q_xx, q_yy, q_zz],
            "ks": [k_xx, k_yy, k_zz],
            "k_avg": k_avg,
        },
        "trace": trace,
        "warnings": warnings,
        "constants": consts,
    }


def calculate_natural_convection(slug, inputs):
    inputs = inputs or {}
    exp = Experiment.query.filter_by(slug=slug).first()
    if not exp:
        return {"error": "Experiment not found"}

    consts = exp.content.get("constants", {})
    warnings = []

    def get_const_num(key, default=0.0):
        item = consts.get(key, {})
        return parse_numeric(item.get("value", default))

    d_tube = get_const_num("d_tube", 0.038)
    l_tube = get_const_num("L_tube", 0.5)
    g = get_const_num("g", 9.81)

    area_s = np.pi * d_tube * l_tube if d_tube and l_tube else 0.0

    mode = str(inputs.get("air_props_mode", "auto")).strip().lower()
    manual_mode = mode.startswith("man")
    props_source = "manual" if manual_mode else "auto"
    rho = cp = k_air = mu = nu = pr = 0.0
    manual_missing = False

    if manual_mode:
        rho = parse_numeric(inputs.get("rho_air", 0.0))
        cp = parse_numeric(inputs.get("cp_air", 0.0))
        k_air = parse_numeric(inputs.get("k_air", 0.0))
        mu = parse_numeric(inputs.get("mu_air", 0.0))
        nu = parse_numeric(inputs.get("nu_air", 0.0))
        pr = parse_numeric(inputs.get("pr_air", 0.0))

        if not mu and nu and rho:
            mu = nu * rho
        if not nu and mu and rho:
            nu = mu / rho
        if not pr and cp and mu and k_air:
            pr = (cp * mu) / k_air

        if not rho or not k_air:
            manual_missing = True
            warnings.append("Manual properties are incomplete; rho and k are required for accurate results.")
        if not mu and not nu:
            manual_missing = True
            warnings.append("Manual properties missing viscosity; provide mu or nu.")
        if not pr and not (cp and mu and k_air):
            manual_missing = True
            warnings.append("Manual properties missing Prandtl number; using computed value if possible.")

        if manual_missing:
            warnings.append("Manual properties are incomplete; auto values will be used for missing fields.")

    def resolve_air_properties(tf):
        auto_props = get_air_properties_auto(tf)
        if not manual_mode:
            return {
                "rho": auto_props["rho"],
                "cp": auto_props["cp"],
                "k_air": auto_props["k_air"],
                "mu": auto_props["mu"],
                "nu": auto_props["nu"],
                "pr": auto_props["pr"],
                "used_auto": True,
            }

        rho_use = rho
        cp_use = cp
        k_use = k_air
        mu_use = mu
        nu_use = nu
        used_auto = False

        if not rho_use and mu_use and nu_use:
            rho_use = mu_use / nu_use
        if not rho_use:
            rho_use = auto_props["rho"]
            used_auto = True
        if not cp_use:
            cp_use = auto_props["cp"]
            used_auto = True
        if not k_use:
            k_use = auto_props["k_air"]
            used_auto = True

        if not mu_use and nu_use and rho_use:
            mu_use = nu_use * rho_use
        if not nu_use and mu_use and rho_use:
            nu_use = mu_use / rho_use
        if not mu_use and not nu_use:
            mu_use = auto_props["mu"]
            nu_use = auto_props["nu"]
            used_auto = True

        pr_use = pr
        if not pr_use and cp_use and mu_use and k_use:
            pr_use = (cp_use * mu_use) / k_use
        if not pr_use:
            pr_use = auto_props["pr"]
            used_auto = True

        return {
            "rho": rho_use,
            "cp": cp_use,
            "k_air": k_use,
            "mu": mu_use,
            "nu": nu_use,
            "pr": pr_use,
            "used_auto": used_auto,
        }
    def parse_observations(payload):
        if isinstance(payload, dict) and "observations" in payload:
            obs = payload.get("observations")
            if isinstance(obs, str):
                try:
                    obs = json.loads(obs)
                except Exception:
                    obs = []
            if isinstance(obs, list):
                normalized = []
                for item in obs:
                    if not isinstance(item, dict):
                        continue
                    lower = {str(k).lower(): v for k, v in item.items()}
                    normalized.append({
                        "trial": lower.get("trial", item.get("trial", 1)),
                        "v": lower.get("v", item.get("v", item.get("voltage"))),
                        "i": lower.get("i", item.get("i", item.get("current"))),
                        "t1": lower.get("t1", item.get("t1")),
                        "t2": lower.get("t2", item.get("t2")),
                        "t3": lower.get("t3", item.get("t3")),
                        "t4": lower.get("t4", item.get("t4")),
                        "t5": lower.get("t5", item.get("t5")),
                        "t6": lower.get("t6", item.get("t6")),
                        "t7": lower.get("t7", item.get("t7", lower.get("ta", item.get("ta")))),
                    })
                return normalized

        trial_re = re.compile(r"^trial_(\\d+)_(v|i|t[1-7])$", re.IGNORECASE)
        trials = {}
        if isinstance(payload, dict):
            for key, val in payload.items():
                match = trial_re.match(str(key))
                if not match:
                    continue
                idx = int(match.group(1))
                field = match.group(2).lower()
                trials.setdefault(idx, {})[field] = parse_numeric(val)
        if trials:
            return [
                {"trial": idx, **data}
                for idx, data in sorted(trials.items())
            ]

        if any(k in payload for k in ["v", "i", "t1", "t2", "t3", "t4", "t5", "t6", "t7"]):
            return [{
                "trial": 1,
                "v": parse_numeric(payload.get("v", payload.get("voltage", payload.get("V", 0.0)))),
                "i": parse_numeric(payload.get("i", payload.get("current", payload.get("I", 0.0)))),
                "t1": parse_numeric(payload.get("t1", 0.0)),
                "t2": parse_numeric(payload.get("t2", 0.0)),
                "t3": parse_numeric(payload.get("t3", 0.0)),
                "t4": parse_numeric(payload.get("t4", 0.0)),
                "t5": parse_numeric(payload.get("t5", 0.0)),
                "t6": parse_numeric(payload.get("t6", 0.0)),
                "t7": parse_numeric(payload.get("t7", payload.get("ta", payload.get("Ta", 0.0)))),
            }]
        return []

    def compute_trial(trial):
        trial_warnings = []
        raw_v = trial.get("v")
        raw_i = trial.get("i")
        raw_temps = [trial.get(f"t{idx}") for idx in range(1, 7)]
        raw_ta = trial.get("t7", trial.get("ta"))

        def is_missing(val):
            return val is None or (isinstance(val, str) and val.strip() == "")

        v = parse_numeric(raw_v)
        i = parse_numeric(raw_i)
        temps = [parse_numeric(val) for val in raw_temps]
        ta = parse_numeric(raw_ta)

        if any(is_missing(val) for val in raw_temps) or is_missing(raw_ta):
            trial_warnings.append("Missing temperature inputs for this trial.")
            return {
                "trial": int(trial.get("trial", 1)),
                "v": v,
                "i": i,
                "temps": [None] * 6,
                "ta": ta,
                "ts": None,
                "delta_t": None,
                "tf": None,
                "beta": None,
                "q": v * i,
                "rho": rho,
                "cp": cp,
                "k_air": k_air,
                "mu": mu,
                "nu_kin": nu,
                "pr": pr,
                "gr": None,
                "ra": None,
                "nu_nusselt": None,
                "h_exp": None,
                "h_theoretical": None,
                "area_s": area_s,
                "corr_c": None,
                "corr_n": None,
                "corr_range": None,
                "props_source": props_source,
            }, trial_warnings

        ts = sum(temps) / 6.0 if temps else 0.0
        delta_t = ts - ta

        if v <= 0 or i <= 0:
            trial_warnings.append("Voltage or current is non-positive. Check readings.")
        if delta_t <= 0:
            trial_warnings.append("Surface temperature is not above ambient; deltaT is non-positive.")

        q = v * i
        tf = ((ts + ta) / 2.0) + 273.15
        beta = 1.0 / tf if tf else 0.0

        props = resolve_air_properties(tf)
        rho_use = props["rho"]
        cp_use = props["cp"]
        k_use = props["k_air"]
        mu_use = props["mu"]
        nu_use = props["nu"]
        pr_use = props["pr"]

        if props.get("used_auto") and (tf < AIR_PROPS_TABLE[0]["T"] or tf > AIR_PROPS_TABLE[-1]["T"]):
            trial_warnings.append("Film temperature is outside auto-property table range; values were clamped.")
        if manual_mode and props.get("used_auto"):
            trial_warnings.append("Manual air properties were incomplete; auto values were used for missing entries.")

        if delta_t <= 0:
            return {
                "trial": int(trial.get("trial", 1)),
                "v": v,
                "i": i,
                "temps": temps,
                "ta": ta,
                "ts": ts,
                "delta_t": delta_t,
                "tf": tf,
                "beta": beta,
                "q": q,
                "rho": rho_use,
                "cp": cp_use,
                "k_air": k_use,
                "mu": mu_use,
                "nu_kin": nu_use,
                "pr": pr_use,
                "gr": None,
                "ra": None,
                "nu_nusselt": None,
                "h_exp": None,
                "h_theoretical": None,
                "area_s": area_s,
                "corr_c": None,
                "corr_n": None,
                "corr_range": None,
                "props_source": props_source,
            }, trial_warnings

        gr = (l_tube ** 3) * beta * g * delta_t * (rho_use ** 2) / (mu_use ** 2) if mu_use else 0.0
        ra = gr * pr_use

        corr_c = 0.56
        corr_n = 0.25
        corr_range = "1e4-1e8"
        if ra >= 1e8:
            corr_c = 0.13
            corr_n = 1.0 / 3.0
            corr_range = "1e8-1e12"

        if ra < 1e4 or ra > 1e12:
            trial_warnings.append("Rayleigh number is outside correlation ranges; using nearest correlation.")

        nu_corr = corr_c * (ra ** corr_n) if ra > 0 else 0.0
        h_correlation = (nu_corr * k_use) / l_tube if l_tube else 0.0
        h_from_power = q / (area_s * delta_t) if area_s and delta_t else 0.0

        result = {
            "trial": int(trial.get("trial", 1)),
            "v": v,
            "i": i,
            "temps": temps,
            "ta": ta,
            "ts": ts,
            "delta_t": delta_t,
            "tf": tf,
            "beta": beta,
            "q": q,
            "rho": rho_use,
            "cp": cp_use,
            "k_air": k_use,
            "mu": mu_use,
            "nu_kin": nu_use,
            "pr": pr_use,
            "gr": gr,
            "ra": ra,
            "nu_nusselt": nu_corr,
            "h_exp": h_from_power if h_from_power else None,
            "h_theoretical": h_correlation if h_correlation else None,
            "area_s": area_s,
            "corr_c": corr_c,
            "corr_n": corr_n,
            "corr_range": corr_range,
            "props_source": props_source,
        }

        return result, trial_warnings

    observations = parse_observations(inputs)
    if not observations:
        return {"error": "No observation trials provided."}

    trials = []
    all_warnings = list(warnings)
    for trial in observations:
        result, trial_warnings = compute_trial(trial)
        if trial_warnings:
            for w in trial_warnings:
                all_warnings.append(f"Trial {result['trial']}: {w}")
        trials.append({
            "trial": result["trial"],
            "inputs": {
                "v": result["v"],
                "i": result["i"],
                "t1": result["temps"][0] if len(result["temps"]) > 0 else 0.0,
                "t2": result["temps"][1] if len(result["temps"]) > 1 else 0.0,
                "t3": result["temps"][2] if len(result["temps"]) > 2 else 0.0,
                "t4": result["temps"][3] if len(result["temps"]) > 3 else 0.0,
                "t5": result["temps"][4] if len(result["temps"]) > 4 else 0.0,
                "t6": result["temps"][5] if len(result["temps"]) > 5 else 0.0,
                "t7": result["ta"],
            },
            "results": result,
            "warnings": trial_warnings,
        })

    raw_inputs = {
        "observations": [{**trial["inputs"], "trial": trial["trial"]} for trial in trials],
        "air_props_mode": props_source,
        "rho_air": rho,
        "cp_air": cp,
        "k_air": k_air,
        "mu_air": mu,
        "nu_air": nu,
        "pr_air": pr,
    }

    results = {
        "trials": [trial["results"] for trial in trials],
        "props_source": props_source,
        "area_s": area_s,
    }

    explanation_blocks, final_explanation = build_natural_convection_explanations({
        "results": results
    })

    return {
        "raw_inputs": raw_inputs,
        "normalized": results,
        "results": results,
        "trace": results,
        "warnings": all_warnings,
        "constants": consts,
        "explanation_blocks": explanation_blocks,
        "final_explanation": final_explanation,
    }


def build_natural_convection_steps(calc_data):
    def build_steps_for_trial(res):
        return [
            f"1. Energy input: $$Q = V \\times I = {fmt_num(res['q'])}\\ \\text{{W}}$$",
            f"2. Average surface temperature: $$T_s = \\frac{{T_1+\\cdots+T_6}}{{6}} = {fmt_num(res['ts'])}^\\circ\\text{{C}}$$",
            f"3. Temperature difference: $$\\Delta T = T_s - T_a = {fmt_num(res['delta_t'])}\\ \\text{{K}}$$",
            f"4. Film temperature: $$T_f = \\frac{{T_s+T_a}}{{2}} + 273.15 = {fmt_num(res['tf'])}\\ \\text{{K}}$$",
            f"5. Volumetric coefficient: $$\\beta = \\frac{{1}}{{T_f}} = {fmt_num(res['beta'])}\\ \\text{{K}}^{{-1}}$$",
            f"6. Grashof number: $$Gr = L^3 \\beta g \\Delta T \\left(\\frac{{\\rho^2}}{{\\mu^2}}\\right) = {fmt_num(res['gr'])}$$",
            f"7. Rayleigh number: $$Ra = Gr \\times Pr = {fmt_num(res['ra'])}$$",
            f"8. Correlation: $$Nu = C(Ra)^n = {fmt_num(res['nu_nusselt'])}$$ "
            f"$\\text{{(}}C={res['corr_c']},\\ n={fmt_num(res['corr_n'])},\\ \\text{{range}}\\ {res['corr_range']}\\text{{)}}$",
            f"9. h from correlation: $$h = \\frac{{Nu\\,k}}{{L}} = {fmt_num(res['h_theoretical'])}\\ \\text{{W/m}}^2\\text{{K}}$$",
            f"10. h from power balance: $$h = \\frac{{Q}}{{A_s \\Delta T}} = {fmt_num(res['h_exp'])}\\ \\text{{W/m}}^2\\text{{K}}$$",
        ]

    results = calc_data.get("results", {})
    trials = results.get("trials", [])
    if not trials and isinstance(results, dict) and "q" in results:
        return build_steps_for_trial(results)
    return [{"trial": res.get("trial", idx + 1), "steps": build_steps_for_trial(res)} for idx, res in enumerate(trials)]


def build_natural_convection_explanations(calc_data):
    results = calc_data.get("results", {})
    trials = results.get("trials", [])
    explanation_blocks = []

    def classify_ra(ra):
        if ra is None:
            return "Rayleigh number not available."
        if ra < 1e4:
            return "very weak natural convection (correlation may not apply)"
        if ra < 1e8:
            return "laminar natural convection on a vertical surface (using C=0.56, n=0.25)"
        if ra < 1e12:
            return "turbulent natural convection (using C=0.13, n=1/3)"
        return "outside standard range; result is an extrapolation"

    def fmt_or_dash(val):
        return fmt_num(val) if val is not None else "-"

    def deviation_info(h_exp, h_theoretical):
        if h_exp is None or h_theoretical in (None, 0):
            return None, "Deviation not available (theoretical value missing or zero)."
        dev = abs(h_exp - h_theoretical) / h_theoretical * 100.0
        if dev <= 20:
            label = "good agreement"
        elif dev <= 50:
            label = "moderate mismatch (common in teaching labs)"
        else:
            label = "large mismatch; likely heat losses or measurement/property errors"
        return dev, label

    for trial in trials:
        trial_id = trial.get("trial", 1)
        q = trial.get("q")
        ts = trial.get("ts")
        ta = trial.get("ta")
        delta_t = trial.get("delta_t")
        ra = trial.get("ra")
        h_exp = trial.get("h_exp")
        h_theoretical = trial.get("h_theoretical")
        corr_c = trial.get("corr_c")
        corr_n = trial.get("corr_n")

        dev, dev_label = deviation_info(h_exp, h_theoretical)
        ra_class = classify_ra(ra)

        if ts is None or ta is None or delta_t is None:
            explanation_blocks.append(
                f"<b>Trial {trial_id}</b><br>"
                "Some required temperatures are missing, so calculations could not be completed for this trial.<br>"
            )
            continue

        block = [
            f"<b>Trial {trial_id}</b><br>",
            f"$Q = V \\times I = {fmt_or_dash(q)}\\ \\text{{W}}$. This is the electrical power supplied to the heater; higher $Q$ generally raises tube surface temperature.<br>",
            f"$T_s = {fmt_or_dash(ts)}^\\circ\\text{{C}},\\ T_a = {fmt_or_dash(ta)}^\\circ\\text{{C}},\\ \\Delta T = {fmt_or_dash(delta_t)}\\ \\text{{K}}$. "
            "The temperature difference $\\Delta T$ is the driving force for natural convection; larger $\\Delta T$ usually increases convection strength.<br>",
            f"$Ra = {fmt_or_dash(ra)}$. This indicates the strength of natural convection (buoyancy vs viscosity/thermal diffusion). Regime: {ra_class}.<br>",
            f"Correlation used: $C = {fmt_or_dash(corr_c)},\\ n = {fmt_or_dash(corr_n)}$.<br>",
            f"$h_{{exp}} = {fmt_or_dash(h_exp)}\\ \\text{{W/m}}^2\\text{{K}}$ (from power balance), "
            f"$h_{{theoretical}} = {fmt_or_dash(h_theoretical)}\\ \\text{{W/m}}^2\\text{{K}}$ (from correlation).<br>",
        ]

        if dev is None:
            block.append(f"{dev_label}<br>")
        else:
            block.append(f"Deviation = {fmt_num(dev)}%. Interpretation: {dev_label}.<br>")
            if dev > 50:
                block.append("<ul>")
                block.append("<li>Steady state reached?</li>")
                block.append("<li>T7 truly ambient?</li>")
                block.append("<li>Radiation losses ignored</li>")
                block.append("<li>Air properties ($k$, $\mu$, $Pr$) at film temperature</li>")
                block.append("<li>Instrument calibration</li>")
                block.append("</ul>")

        explanation_blocks.append("".join(block))

    # Final explanation
    valid_trials = [t for t in trials if t.get("h_exp") is not None and t.get("h_theoretical") not in (None, 0)]
    mean_h_exp = sum(t["h_exp"] for t in valid_trials) / len(valid_trials) if valid_trials else None
    mean_h_theoretical = sum(t["h_theoretical"] for t in valid_trials) / len(valid_trials) if valid_trials else None
    mean_dev = None
    if valid_trials:
        devs = [abs(t["h_exp"] - t["h_theoretical"]) / t["h_theoretical"] * 100.0 for t in valid_trials]
        mean_dev = sum(devs) / len(devs)

    higher_trial = None
    if valid_trials:
        higher_trial = max(valid_trials, key=lambda t: t.get("h_exp", 0))

    final_lines = [
        "<b>Overall interpretation</b><br>",
        "Natural convection depends on temperature difference and fluid properties; $Ra$ and $Nu$ connect theory to the heat transfer coefficient $h$.<br>",
        "We compute $h_{theoretical}$ from correlations as a benchmark; experiments often differ due to real-world losses and measurement uncertainty.<br>",
        "<br><b>Glossary:</b> $T_s$ = average surface temperature, $T_a$ = ambient temperature, $\\Delta T = T_s - T_a$, $Ra = Gr\\times Pr$, $Nu = (hL/k)$.<br>",
    ]

    if higher_trial:
        final_lines.append(
            f"Trial {higher_trial['trial']} shows a higher experimental $h$ ("
            f"${fmt_num(higher_trial.get('h_exp'))}\\ \\text{{W/m}}^2\\text{{K}}$), which is consistent with its larger $\\Delta T$ or higher $Q$.<br>"
        )

    if mean_h_exp is not None and mean_h_theoretical is not None:
        final_lines.append(
            f"Mean $h_{{exp}} = {fmt_num(mean_h_exp)}\\ \\text{{W/m}}^2\\text{{K}}$, "
            f"mean $h_{{theoretical}} = {fmt_num(mean_h_theoretical)}\\ \\text{{W/m}}^2\\text{{K}}$, "
            f"mean deviation = {fmt_num(mean_dev)}%.<br>"
        )

    if trials:
        final_lines.append("<br><b>Lab record conclusion (template):</b><br>")
        for trial in trials:
            h_exp = trial.get("h_exp")
            h_theoretical = trial.get("h_theoretical")
            if h_exp is not None and h_theoretical not in (None, 0):
                dev_pct = abs(h_exp - h_theoretical) / h_theoretical * 100.0
                dev_text = fmt_num(dev_pct)
            else:
                dev_text = "N/A"
            final_lines.append(
                f"The experimental heat transfer coefficient was $h_{{exp}} = {fmt_or_dash(h_exp)}\\ \\text{{W/m}}^2\\text{{K}}$ and the theoretical value predicted by correlation was $h_{{theoretical}} = {fmt_or_dash(h_theoretical)}\\ \\text{{W/m}}^2\\text{{K}}$ for Trial {trial.get('trial', 1)}. "
                f"The deviation was {dev_text}%, mainly due to steady-state errors, property mismatch, or heat losses.<br>"
            )

    return explanation_blocks, "".join(final_lines)


def calculate_experiment(slug, inputs):
    if slug == "therm-conductivity-metal-rod":
        return calculate_therm_conductivity(slug, inputs)
    if slug == "natural-convection-vertical-tube":
        return calculate_natural_convection(slug, inputs)
    return {"error": "Unknown slug"}
