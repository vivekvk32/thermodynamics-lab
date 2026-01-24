import unittest

from app import create_app
from app.extensions import db
from app.models import Experiment
from app.utils import calculate_natural_convection, get_air_properties_auto


class TestNaturalConvection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.ctx = cls.app.app_context()
        cls.ctx.push()
        db.create_all()

        exp = Experiment.query.filter_by(slug='natural-convection-vertical-tube').first()
        if not exp:
            exp = Experiment(
                slug='natural-convection-vertical-tube',
                title='Heat Transfer Through Free (Natural) Convection (Vertical Tube)',
                content={
                    "constants": {
                        "d_tube": {"value": 0.038, "unit": "m", "desc": "Tube Diameter"},
                        "L_tube": {"value": 0.5, "unit": "m", "desc": "Tube Length"},
                        "g": {"value": 9.81, "unit": "m/s^2", "desc": "Acceleration due to gravity"},
                    }
                }
            )
            db.session.add(exp)
            db.session.commit()

    @classmethod
    def tearDownClass(cls):
        cls.ctx.pop()

    def test_auto_properties(self):
        props = get_air_properties_auto(300.0)
        self.assertGreater(props["rho"], 1.0)
        self.assertGreater(props["k_air"], 0.02)
        self.assertGreater(props["mu"], 1e-5)
        self.assertGreater(props["pr"], 0.6)

    def test_natural_convection_calc(self):
        inputs = {
            "air_props_mode": "auto",
            "observations": [
                {
                    "trial": 1,
                    "v": 80,
                    "i": 1.5,
                    "t1": 70,
                    "t2": 68,
                    "t3": 66,
                    "t4": 64,
                    "t5": 62,
                    "t6": 60,
                    "t7": 30,
                },
                {
                    "trial": 2,
                    "v": 75,
                    "i": 1.4,
                    "t1": 65,
                    "t2": 63,
                    "t3": 61,
                    "t4": 60,
                    "t5": 58,
                    "t6": 57,
                    "t7": 30,
                }
            ]
        }
        calc = calculate_natural_convection("natural-convection-vertical-tube", inputs)
        res = calc["results"]
        trials = res["trials"]

        self.assertEqual(len(trials), 2)
        self.assertGreater(trials[0]["q"], 0)
        self.assertIsNotNone(trials[0]["h_exp"])
        self.assertIsNotNone(trials[0]["h_theoretical"])
        self.assertGreater(trials[0]["h_theoretical"], 0)
        self.assertAlmostEqual(trials[0]["ra"], trials[0]["gr"] * trials[0]["pr"], delta=abs(trials[0]["ra"]) * 0.01 + 1e-6)


if __name__ == '__main__':
    unittest.main()
