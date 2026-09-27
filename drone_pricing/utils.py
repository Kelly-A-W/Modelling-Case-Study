import math


def riebesell(x, base_limit, z):
    """Riebesell ILF curve R(x) = (x / B) ^ log2(1 + z), as the workbook's VBA Riebesell()."""
    return (x / base_limit) ** math.log2(1 + z)


def gross_up(net, brokerage):
    """Gross a net premium up for brokerage."""
    return net / (1 - brokerage)


def rank(items, key, rng):
    """Sort items by key, highest first, breaking ties at random."""
    items = list(items)
    rng.shuffle(items)
    return sorted(items, key=key, reverse=True)


def round_for_display(obj, is_premium=False):
    """Copy of the output with premiums rounded to 2 dp; rates and factors are left unrounded.

    Only used for printing: calculations and stored values are never rounded.
    """
    if isinstance(obj, dict):
        return {k: round_for_display(v, is_premium or "prem" in k) for k, v in obj.items()}
    if isinstance(obj, list):
        return [round_for_display(v, is_premium) for v in obj]
    if is_premium and isinstance(obj, float):
        return round(obj, 2)
    return obj
