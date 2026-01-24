from app import create_app, db
from app.models import Experiment
import json

app = create_app()

def seed():
    with app.app_context():
        # Experiment 1 Content
        content = {
            "aim": "To determine the thermal conductivity of the metal rod.",
            "apparatus": "Metal bar (Copper), Electric Heater, Water Jacket, Insulating Powder (Chalk), Thermocouples (T1-T13), Measuring Jar, Stopwatch, Dimmerstat.",
            "description": """
            <p>The experimental setup consists of a metal rod, one end of which is heated by an electric heater while the other end projects into a cooling water jacket. The middle portion of the rod is thermally insulated using chalk powder.</p>
            <p>Heat flows axially from the hot end to the cold end. Ideally, the heat input should equal heat output, but practically there are radial losses. We measure temperatures at various points along the rod (T1-T5) and in the insulation (radial points) to account for these losses.</p>
            <p><strong>Cooling Arrangement:</strong> Water is circulated through the jacket. The temperature rise of the water reflects the heat carried away: $Q_w = m_w C_{pw} (T_{out} - T_{in})$.</p>
            """,
            "theory": """
            <h4>Fourier's Law</h4>
            <p>The rate of heat transfer is proportional to the area and the temperature gradient.</p>
            $$ Q = -k A \\frac{dT}{dx} $$
            <p>Where $k$ is the thermal conductivity (W/mK).</p>
            
            <h4>Heat Balance</h4>
            <p>Ideally $Q_{input} = Q_{rod} = Q_{water}$. Due to radial losses through insulation:</p>
            $$ Q_{rod} = Q_{water} + Q_{radial\_loss} $$
            
            <p>The radial loss through a cylindrical shell of insulation:</p>
            $$ Q_{loss} = \\frac{2 \\pi K_{ins} L (T_{inner} - T_{outer})}{\\ln(r_o / r_i)} $$
            <p>However, for this specific setup, we utilize the given formula for discrete sections:</p>
            $$ Q_{radial} = \\frac{K_{ins} (T_{inner} - T_{outer})}{\\frac{\\ln(r_o / r_i)}{2\\pi L}} \\text{ (approx per section)} $$
            <p>(Implementation note: We will use the exact formula structure provided in the lab manual specs logic).</p>
            """,
            "procedure": [
                "1. Connect the water supply to the inlet of the cooling jacket.",
                "2. Adjust water flow to 0.1 - 0.2 Liters/min using the measuring jar.",
                "3. Switch on the heater supply and adjust dimmerstat to a suitable voltage (e.g., 80V-100V).",
                "4. Wait for steady state (temperatures stop changing substantially).",
                "5. Note down T1 to T5 (Rod), T6-T9, T12-T13 (Insulation), and T10 (Win), T11 (Wout).",
                "6. Measure water flow rate again."
            ],
            "inputs": [
                {"name": "flow_rate_value", "label": "Water Flow Rate", "unit": ""},
                {"name": "t_wi", "label": "Water Inlet T10", "unit": "°C"},
                {"name": "t_wo", "label": "Water Outlet T11", "unit": "°C"},
                {"name": "t1", "label": "Rod Temp T1", "unit": "°C"},
                {"name": "t2", "label": "Rod Temp T2", "unit": "°C"},
                {"name": "t3", "label": "Rod Temp T3", "unit": "°C"},
                {"name": "t4", "label": "Rod Temp T4", "unit": "°C"},
                {"name": "t5", "label": "Rod Temp T5", "unit": "°C"},
                {"name": "t6", "label": "Insulation T6", "unit": "°C"},
                {"name": "t7", "label": "Insulation T7", "unit": "°C"},
                {"name": "t8", "label": "Insulation T8", "unit": "°C"},
                {"name": "t9", "label": "Insulation T9", "unit": "°C"},
                {"name": "t12", "label": "Insulation T12", "unit": "°C"},
                {"name": "t13", "label": "Insulation T13", "unit": "°C"}
            ],
            "constants": {
                "d_rod": {"value": 0.035, "unit": "m", "desc": "Diameter of Rod"},
                "d_jack": {"value": 0.100, "unit": "m", "desc": "Diameter of Jacket"},
                "kins": {"value": 0.3005, "unit": "W/mK", "desc": "K of Insulation"},
                "l1": {"value": 0.025, "unit": "m", "desc": "Length Section 1 (XX)"},
                "l2": {"value": 0.12, "unit": "m", "desc": "Length Section 2 (YY)"},
                "l3": {"value": 0.12, "unit": "m", "desc": "Length Section 3 (ZZ)"},
                "ri": {"value": 0.0425, "unit": "m", "desc": "Inner Radius Insulation"},
                "ro": {"value": 0.055, "unit": "m", "desc": "Outer Radius Insulation"},
                "cpw": {"value": 4178, "unit": "J/kgK", "desc": "Sp. Heat Water"},
                "rho": {"value": 1000, "unit": "kg/m^3", "desc": "Density of Water"},
                "dx": {"value": 0.06, "unit": "m", "desc": "Thermocouple Spacing (dx)"}
            },
            "viva": [
                {"question": "What is Fourier's Law?", "answer": "Rate of heat flow is prop. to area and temp gradient."},
                {"question": "What is steady state?", "answer": "When temperature at any point does not change with time."},
                {"question": "Why is copper used?", "answer": "High thermal conductivity."}
            ]
        }
        exp1 = Experiment.query.filter_by(slug='therm-conductivity-metal-rod').first()
        if not exp1:
            exp1 = Experiment(
                slug='therm-conductivity-metal-rod',
                title='Determination of Thermal Conductivity of a Metal Rod',
                content=content
            )
            db.session.add(exp1)
            print("Experiment 1 Seeded Successfully.")

        # Experiment 2 Content (Natural Convection)
        content2 = {
            "aim": "To determine the natural convection heat transfer coefficient for the vertical tube exposed to atmospheric air.",
            "apparatus": "Brass tube, rectangular duct, electric heater, dimmerstat, ammeter, voltmeter, wattmeter, thermocouples, selector switch.",
            "description": """
            <p>The setup consists of a brass tube fitted vertically inside a rectangular duct open at top and bottom. An electric heater is placed at the center to heat the tube surface.</p>
            <p>Heat is lost from the tube surface to surrounding air by natural convection. Seven thermocouples measure surface and ambient temperatures along the tube.</p>
            """,
            "theory": """
            <h4>Energy Input</h4>
            <p>Electrical heat input is given by:</p>
            $$ Q = V I $$
            <h4>Temperature Definitions</h4>
            <p>Average surface temperature:</p>
            $$ T_s = \\frac{T_1+T_2+T_3+T_4+T_5+T_6}{6} $$
            <p>Film temperature:</p>
            $$ T_f = \\frac{T_s + T_a}{2} + 273 $$
            <p>Volumetric coefficient:</p>
            $$ \\beta = \\frac{1}{T_f} $$
            <h4>Dimensionless Numbers</h4>
            $$ Gr = \\frac{L^3 \\beta g \\Delta T \\rho^2}{\\mu^2} $$
            $$ Ra = Gr \\times Pr $$
            <h4>Nusselt Correlation</h4>
            <p>For vertical tube in natural convection:</p>
            $$ Nu = \\frac{h L}{k} = C (Gr Pr)^n $$
            <p>where:</p>
            <ul>
              <li>C = 0.56, n = 0.25 for 10^4 &lt; Ra &lt; 10^8</li>
              <li>C = 0.13, n = 1/3 for 10^8 &lt; Ra &lt; 10^12</li>
            </ul>
            <p>Heat transfer coefficients:</p>
            $$ h_{corr} = \\frac{Nu k}{L} $$
            $$ h_{power} = \\frac{Q}{A_s (T_s - T_a)} $$
            """,
            "procedure": [
                "1. Switch on the heater and adjust input using dimmerstat.",
                "2. Wait until steady state is reached.",
                "3. Record thermocouple temperatures using selector switch.",
                "4. Note voltage, current, and wattmeter readings.",
                "5. Repeat for different heater settings."
            ],
            "inputs": [
                {"name": "v", "label": "Voltage (V)", "unit": "V"},
                {"name": "i", "label": "Current (I)", "unit": "A"},
                {"name": "t1", "label": "Surface Temp T1", "unit": "C"},
                {"name": "t2", "label": "Surface Temp T2", "unit": "C"},
                {"name": "t3", "label": "Surface Temp T3", "unit": "C"},
                {"name": "t4", "label": "Surface Temp T4", "unit": "C"},
                {"name": "t5", "label": "Surface Temp T5", "unit": "C"},
                {"name": "t6", "label": "Surface Temp T6", "unit": "C"},
                {"name": "t7", "label": "Ambient Temp (T7 = Ta)", "unit": "C"},
                {
                    "name": "air_props_mode",
                    "label": "Air Properties Mode",
                    "type": "select",
                    "options": [
                        {"value": "auto", "label": "Auto (from film temperature)", "selected": True},
                        {"value": "manual", "label": "Manual (enter properties)"}
                    ],
                    "required": False
                },
                {"name": "rho_air", "label": "Air Density (rho)", "unit": "kg/m^3", "group": "air_props_manual", "required": False},
                {"name": "cp_air", "label": "Specific Heat (Cp)", "unit": "J/kgK", "group": "air_props_manual", "required": False},
                {"name": "k_air", "label": "Thermal Conductivity (k)", "unit": "W/mK", "group": "air_props_manual", "required": False},
                {"name": "mu_air", "label": "Dynamic Viscosity (mu)", "unit": "Pa.s", "group": "air_props_manual", "required": False},
                {"name": "nu_air", "label": "Kinematic Viscosity (nu)", "unit": "m^2/s", "group": "air_props_manual", "required": False},
                {"name": "pr_air", "label": "Prandtl Number (Pr)", "unit": "-", "group": "air_props_manual", "required": False}
            ],
            "constants": {
                "d_tube": {"value": 0.038, "unit": "m", "desc": "Tube Diameter"},
                "L_tube": {"value": 0.5, "unit": "m", "desc": "Tube Length"},
                "g": {"value": 9.81, "unit": "m/s^2", "desc": "Acceleration due to gravity"}
            },
            "viva": [
                {"question": "What is meant by critical Reynolds number?", "answer": "It is the Reynolds number at which flow transitions from laminar to turbulent."},
                {"question": "Define Grashof number.", "answer": "Ratio of buoyancy to viscous forces in natural convection."},
                {"question": "Sketch temperature and velocity profiles in free convection on a vertical wall.", "answer": "Temperature and velocity increase from wall to a peak and then decay to ambient."},
                {"question": "What is meant by dimensional analysis?", "answer": "A method to reduce variables using fundamental dimensions."},
                {"question": "What are the uses of dimensional analysis?", "answer": "To develop correlations and scale experimental data."}
            ]
        }

        exp2 = Experiment.query.filter_by(slug='natural-convection-vertical-tube').first()
        if not exp2:
            exp2 = Experiment(
                slug='natural-convection-vertical-tube',
                title='Heat Transfer Through Free (Natural) Convection (Vertical Tube)',
                content=content2
            )
            db.session.add(exp2)
            print("Experiment 2 Seeded Successfully.")

        db.session.commit()

if __name__ == '__main__':
    seed()
