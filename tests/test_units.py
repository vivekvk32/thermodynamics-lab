import math
import unittest

from app.utils import normalize_inputs


class TestUnitNormalization(unittest.TestCase):
    def test_flow_lmin_to_mdot(self):
        consts = {
            "rho": {"value": 1000, "unit": "kg/m^3"},
            "cpw": {"value": 4180, "unit": "J/kgK"},
            "d_rod": {"value": 35, "unit": "mm"},
        }
        inputs = {
            "flow_rate_value": 0.15,
            "flow_rate_unit": "L/min",
            "t_wi": 20,
            "t_wo": 21,
        }
        data = normalize_inputs(inputs, consts)
        norm = data["normalized"]
        self.assertAlmostEqual(norm["m_dot"], 2.5e-3, delta=1e-6)

        qw = norm["m_dot"] * norm["cpw"] * (norm["t_wo"] - norm["t_wi"])
        self.assertAlmostEqual(qw, 10.45, delta=0.2)

        self.assertAlmostEqual(norm["d_rod"], 0.035, delta=1e-6)
        area = math.pi * norm["d_rod"] ** 2 / 4
        self.assertAlmostEqual(area, 9.62e-4, delta=1e-6)


if __name__ == '__main__':
    unittest.main()
