import random
import unittest

from drone_pricing.utils import gross_up, rank, riebesell

B, Z = 1_000_000, 0.2


class TestRiebesell(unittest.TestCase):
    def test_base_limit_is_one(self):
        self.assertAlmostEqual(riebesell(B, B, Z), 1)

    def test_doubling_rule(self):
        self.assertAlmostEqual(riebesell(6e6, B, Z), (1 + Z) * riebesell(3e6, B, Z))

    def test_zero(self):
        self.assertEqual(riebesell(0, B, Z), 0)


class TestUtils(unittest.TestCase):
    def test_gross_up(self):
        self.assertAlmostEqual(gross_up(70, 0.3), 100)

    def test_rank_highest_first(self):
        self.assertEqual(rank([1, 3, 2], lambda x: x, random.Random()), [3, 2, 1])


if __name__ == "__main__":
    unittest.main()
