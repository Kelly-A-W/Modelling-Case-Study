import unittest

from drone_pricing.example_data import get_example_data
from drone_pricing.data_structure import Submission, ValidationError


def with_drone(**changes):
    data = get_example_data()
    data["drones"][0].update(changes)
    return data


class TestValidation(unittest.TestCase):
    def test_example_is_valid(self):
        Submission.from_dict(get_example_data())

    def test_rejects_bad_inputs(self):
        for changes in [
            {"weight": "heavy"},
            {"value": -1},
            {"value": "10000"},
            {"tpl_limit": 0},
            {"tpl_excess": -1},
            {"has_detachable_camera": 1},
        ]:
            with self.subTest(changes), self.assertRaises(ValidationError):
                Submission.from_dict(with_drone(**changes))

    def test_rejects_missing_field(self):
        data = get_example_data()
        del data["drones"][0]["weight"]
        with self.assertRaises(ValidationError):
            Submission.from_dict(data)

    def test_rejects_bad_submission_fields(self):
        for key, value in [("brokerage", 1), ("max_drones_in_air", -1), ("max_drones_in_air", 1.5)]:
            data = get_example_data()
            data[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValidationError):
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
