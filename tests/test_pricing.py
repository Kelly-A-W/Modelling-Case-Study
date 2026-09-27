import unittest

from drone_pricing.example_data import get_example_data
from drone_pricing.data_structure import Submission
from drone_pricing.pricing import price_submission, weight_category


def price(data, seed=0):
    return price_submission(Submission.from_dict(data), seed=seed)


class TestSpreadsheetParity(unittest.TestCase):
    """Expected values are taken from the xlsm."""

    def setUp(self):
        self.result = price(get_example_data())

    def assertValues(self, items, field, expected):
        for item, value in zip(items, expected):
            with self.subTest(item=item.serial_number, field=field):
                self.assertAlmostEqual(getattr(item, field), value, places=6)

    def test_drones(self):
        drones = self.result.drones
        self.assertValues(drones, "hull_weight_adjustment", [1.0, 1.6, 1.2])
        self.assertValues(drones, "hull_final_rate", [0.06, 0.096, 0.072])
        self.assertValues(drones, "hull_premium", [600, 1152, 1080])
        self.assertValues(drones, "tpl_base_layer_premium", [200, 240, 300])
        self.assertValues(drones, "tpl_ilf", [1.0, 0.527049657, 0.305409931])
        self.assertValues(drones, "tpl_layer_premium", [200, 126.491917679, 91.622979420])

    def test_cameras(self):
        cameras = self.result.detachable_cameras
        self.assertValues(cameras, "hull_rate", [0.072] * 4)
        self.assertValues(cameras, "hull_premium", [360, 180, 108, 144])

    def test_summary(self):
        net, gross = self.result.net_prem, self.result.gross_prem
        self.assertAlmostEqual(net.drones_hull, 2832)
        self.assertAlmostEqual(net.drones_tpl, 418.114897099, places=6)
        self.assertAlmostEqual(net.cameras_hull, 792)
        self.assertAlmostEqual(net.total, 4042.114897099, places=6)
        self.assertAlmostEqual(gross.drones_hull, 4045.714285714, places=6)
        self.assertAlmostEqual(gross.total, 5774.449852998, places=6)


class TestWeightCategory(unittest.TestCase):
    def test_exact_weights_map_to_bands(self):
        for weight, band in [(0.5, "0 - 5kg"), (5, "0 - 5kg"), (5.1, "5 - 10kg"), (20, "10 - 20kg"), (25, "> 20kg")]:
            with self.subTest(weight=weight):
                self.assertEqual(weight_category(weight), band)

    def test_band_labels_pass_through(self):
        self.assertEqual(weight_category("5 - 10kg"), "5 - 10kg")

    def test_exact_weights_give_spreadsheet_prices(self):
        data = get_example_data()
        for drone, kg in zip(data["drones"], [3, 15, 7.5]):
            drone["weight"] = kg
        self.assertAlmostEqual(price(data).net_prem.total, 4042.114897099, places=6)


class TestMissingInputs(unittest.TestCase):
    def test_items_missing_inputs_are_removed_with_warning(self):
        data = get_example_data()
        del data["drones"][0]["weight"]
        data["detachable_cameras"][0]["value"] = None
        result = price(data)
        self.assertIsNone(result.drones[0].hull_premium)
        self.assertIsNone(result.detachable_cameras[0].hull_premium)
        self.assertAlmostEqual(result.net_prem.drones_hull, 1152 + 1080)
        self.assertEqual(result.warnings, [
            "Fleet has been priced with camera ZZZ-999 removed because: value is missing",
            "Fleet has been priced with drone AAA-111 removed because: weight is missing",
        ])

    def test_missing_camera_flag_is_fine_without_cameras(self):
        data = get_example_data()
        data["detachable_cameras"] = []
        for drone in data["drones"]:
            del drone["has_detachable_camera"]
        result = price(data)
        self.assertEqual(result.warnings, [])
        self.assertAlmostEqual(result.net_prem.drones_hull, 2832)

    def test_missing_camera_flag_kept_when_it_cannot_affect_pricing(self):
        data = get_example_data()
        data["max_drones_in_air"] = 1  # CCC-333 alone covers n, and AAA-111's rate 0.06 < 0.072
        del data["drones"][0]["has_detachable_camera"]
        result = price(data)
        self.assertEqual(result.warnings, [
            "Drone AAA-111: has_detachable_camera is missing, but this did not affect pricing because its hull rate "
            "(0.06) is not above the camera rate (0.072) and at least 1 drones are known to take a camera",
        ])
        self.assertAlmostEqual(result.net_prem.total, 4042.114897099, places=6)

    def test_missing_camera_flag_removes_drone_with_higher_rate(self):
        data = get_example_data()
        del data["drones"][1]["has_detachable_camera"]  # BBB-222: rate 0.096 > 0.072
        self.assertEqual(price(data).warnings, [
            "Fleet has been priced with drone BBB-222 removed because: has_detachable_camera is missing "
            "and its hull rate (0.096) is above the camera rate (0.072)",
        ])

    def test_missing_camera_flag_removes_drone_that_could_change_m(self):
        data = get_example_data()
        del data["drones"][0]["has_detachable_camera"]  # only CCC-333 known, but n = 2
        self.assertEqual(price(data).warnings, [
            "Fleet has been priced with drone AAA-111 removed because: has_detachable_camera is missing "
            "and fewer than 2 drones are known to take a camera, so it could change how many cameras are "
            "charged the full rate",
        ])

    def test_cameras_removed_when_no_drone_takes_one(self):
        data = get_example_data()
        data["drones"][0]["has_detachable_camera"] = False
        del data["drones"][2]["has_detachable_camera"]  # BBB-222 is already False
        result = price(data)
        self.assertEqual(result.warnings, [
            "Fleet has been priced with all cameras removed because: every drone either has no "
            "detachable camera or its has_detachable_camera is missing",
        ])
        self.assertIsNone(result.detachable_cameras[0].hull_premium)
        self.assertEqual(result.net_prem.cameras_hull, 0)
        self.assertAlmostEqual(result.net_prem.drones_hull, 2832)


class TestExtensions(unittest.TestCase):
    def test_max_drones_in_air(self):
        drones = {d.serial_number: d for d in price(get_example_data()).drones}
        cheapest = drones["AAA-111"]  # full premium 800, lowest of the three
        self.assertFalse(cheapest.charged_full_rate)
        self.assertAlmostEqual(cheapest.final_hull_premium, 112.5)
        self.assertAlmostEqual(cheapest.final_tpl_premium, 37.5)
        self.assertEqual(drones["BBB-222"].final_hull_premium, drones["BBB-222"].hull_premium)

    def test_max_cameras_in_air(self):
        cameras = {c.serial_number: c.final_hull_premium for c in price(get_example_data()).detachable_cameras}
        self.assertEqual(cameras, {"ZZZ-999": 360, "YYY-888": 180, "XXX-777": 50, "WWW-666": 50})

    def test_summary_after_extensions(self):
        net = price(get_example_data()).net_prem_after_extensions
        self.assertAlmostEqual(net.drones_hull, 112.5 + 1152 + 1080)
        self.assertAlmostEqual(net.cameras_hull, 360 + 180 + 50 + 50)

    def test_drones_unchanged_when_all_can_fly(self):
        data = get_example_data()
        data["max_drones_in_air"] = 10
        before, after = price(data).net_prem, price(data).net_prem_after_extensions
        self.assertEqual((after.drones_hull, after.drones_tpl), (before.drones_hull, before.drones_tpl))
        # Cameras are still capped: only 2 drones take a camera, so m = min(10, 2) = 2
        self.assertEqual(after.cameras_hull, 360 + 180 + 50 + 50)


class TestTieBreaks(unittest.TestCase):
    def tied_data(self):
        data = get_example_data()
        data["max_drones_in_air"] = 1
        data["drones"][1] = {**data["drones"][0], "serial_number": "TIE-000"}
        del data["drones"][2]
        return data

    def winner(self, seed):
        return next(d.serial_number for d in price(self.tied_data(), seed).drones if d.charged_full_rate)

    def test_same_seed_same_result(self):
        self.assertEqual(self.winner(1), self.winner(1))

    def test_either_tied_drone_can_win(self):
        self.assertEqual({self.winner(seed) for seed in range(20)}, {"AAA-111", "TIE-000"})


if __name__ == "__main__":
    unittest.main()
