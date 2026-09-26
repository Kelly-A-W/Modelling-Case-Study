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
    return sorted(items, key=key, reverse=True)  # stable sort keeps the shuffled order within ties
