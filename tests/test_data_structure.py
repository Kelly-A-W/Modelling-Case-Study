import unittest

from drone_pricing.example_data import get_example_data
from drone_pricing.data_structure import Submission


class TestValidation(unittest.TestCase):
    def test_example_has_no_problems(self):
        submission = Submission.from_dict(get_example_data())
        self.assertEqual([d.problems() for d in submission.drones], [[], [], []])

    def test_missing_input_is_loaded_as_none(self):
        data = get_example_data()
        del data["drones"][0]["weight"]
        drone = Submission.from_dict(data).drones[0]
        self.assertIsNone(drone.weight)
        self.assertEqual(drone.problems(), ["weight is missing"])

    def test_problems(self):
        for changes, expected in [
            ({"weight": "heavy"}, "weight 'heavy' is invalid"),
            ({"value": -1}, "value -1 is invalid"),
            ({"value": "10000"}, "value '10000' is invalid"),
            ({"tpl_limit": 0}, "tpl_limit 0 is invalid"),
            ({"tpl_excess": None}, "tpl_excess is missing"),
        ]:
            data = get_example_data()
            data["drones"][0].update(changes)
            with self.subTest(changes):
                self.assertEqual(Submission.from_dict(data).drones[0].problems(), [expected])

    def test_camera_flag_problem(self):
        for flag, expected in [(True, None), (False, None), (None, "has_detachable_camera is missing"),
                               (1, "has_detachable_camera 1 is invalid")]:
            data = get_example_data()
            data["drones"][0]["has_detachable_camera"] = flag
            with self.subTest(flag=flag):
                self.assertEqual(Submission.from_dict(data).drones[0].camera_flag_problem(), expected)

    def test_rejects_bad_submission_fields(self):
        for key, value in [("brokerage", 1), ("max_drones_in_air", -1), ("max_drones_in_air", 1.5)]:
            data = get_example_data()
            data[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                Submission.from_dict(data)

    def test_to_dict_keeps_original_layout(self):
        data = get_example_data()
        out = Submission.from_dict(data).to_dict()
        self.assertLessEqual(data.keys(), out.keys())
        self.assertLessEqual(data["drones"][0].keys(), out["drones"][0].keys())
        self.assertIn("gross_prem", out)
        self.assertIn("net_prem", out)


if __name__ == "__main__":
    unittest.main()
