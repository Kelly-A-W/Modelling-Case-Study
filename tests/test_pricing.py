import unittest

from drone_pricing.example_data import get_example_data
from drone_pricing.data_structure import Submission
from drone_pricing.pricing import NOT_PRICED, price_submission


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


class TestMissingValues(unittest.TestCase):
    def test_zero_or_missing_value_is_flagged_not_priced(self):
        data = get_example_data()
        data["drones"][0]["value"] = 0
        data["detachable_cameras"][0]["value"] = None
        result = price(data)
        drone, camera = result.drones[0], result.detachable_cameras[0]
        self.assertEqual(drone.note, NOT_PRICED)
        self.assertIsNone(drone.hull_premium)
        self.assertEqual(camera.note, NOT_PRICED)
        self.assertAlmostEqual(result.net_prem.drones_hull, 1152 + 1080)

    def test_no_camera_drones_gives_zero_camera_rate(self):
        data = get_example_data()
        for drone in data["drones"]:
            drone["has_detachable_camera"] = False
        self.assertEqual(price(data).detachable_cameras[0].hull_rate, 0)


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
