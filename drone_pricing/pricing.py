"""Pricing calculations. Each function fills in fields on the model in place."""

import random
from .data_structure import Premiums
from .parameters import (
    CAMERA_BASE_PREMIUM,
    DRONE_BASE_PREMIUM,
    HULL_BASE_RATE,
    RIEBESELL_BASE_LIMIT,
    RIEBESELL_Z,
    TPL_BASE_RATE,
    WEIGHT_ADJUSTMENTS,
    WEIGHT_BAND_LIMITS,
)
from .utils import gross_up, rank, riebesell

#--------------------------------------------------------
# Original Prcing Structure:
#--------------------------------------------------------
# I decided to structure my functions so that each match an equation in the excel model. 
# This helps makes the model easier to check against the spreadsheet, explain, maintain, 
# as well as displaying intermediate values. 

def weight_category(weight):
    """Weight band for a band label or an exact weight in kg."""
    if weight in WEIGHT_ADJUSTMENTS:
        return weight
    return next(band for band, limit in WEIGHT_BAND_LIMITS.items() if weight <= limit)


def hull_rate(weight):
    """Final hull rate for a weight: base rate x weight adjustment."""
    return HULL_BASE_RATE * WEIGHT_ADJUSTMENTS[weight_category(weight)]


def price_hull(drone):
    """Drone hull premium (Model!L:O)."""
    drone.weight_category = weight_category(drone.weight)
    drone.hull_base_rate = HULL_BASE_RATE
    drone.hull_weight_adjustment = WEIGHT_ADJUSTMENTS[drone.weight_category]
    drone.hull_final_rate = drone.hull_base_rate * drone.hull_weight_adjustment
    drone.hull_premium = drone.value * drone.hull_final_rate


def price_tpl(drone):
    """Drone TPL layer premium (Model!Q:T): base layer premium scaled by the Riebesell ILF."""
    drone.tpl_base_rate = TPL_BASE_RATE
    drone.tpl_base_layer_premium = drone.value * drone.tpl_base_rate
    top = riebesell(drone.tpl_limit + drone.tpl_excess, RIEBESELL_BASE_LIMIT, RIEBESELL_Z)
    bottom = riebesell(drone.tpl_excess, RIEBESELL_BASE_LIMIT, RIEBESELL_Z)
    drone.tpl_ilf = top - bottom
    drone.tpl_layer_premium = drone.tpl_base_layer_premium * drone.tpl_ilf


def camera_rate(drones):
    """Highest final hull rate among priced drones with a camera; 0 if none, as Excel's MAXIFS (Model!H33)."""
    return max((d.hull_final_rate for d in drones if d.has_detachable_camera is True), default=0)


def price_camera(camera, rate):
    """Camera hull premium (Model!H:I)."""
    camera.hull_rate = rate
    camera.hull_premium = camera.value * rate


def summarise(drones_hull, drones_tpl, cameras_hull, brokerage):
    """Net and gross premium summary (Model!F42:G45)."""
    net = [sum(drones_hull), sum(drones_tpl), sum(cameras_hull)]
    gross = [gross_up(p, brokerage) for p in net]
    return Premiums(*net, sum(net)), Premiums(*gross, sum(gross))

#--------------------------------------------------------
# Pricing Extensions:
#--------------------------------------------------------

def apply_max_drones_in_air(drones, n, rng):
    """Extension 1: full premium for the n most expensive drones, a fixed premium for the rest.

    The fixed premium is split between hull and TPL in the drone's full-premium proportions.
    """
    def full(d):
        return d.hull_premium + d.tpl_layer_premium

    for i, drone in enumerate(rank(drones, full, rng), start=1):
        drone.rank = i
        drone.charged_full_rate = i <= n
        scale = 1 if drone.charged_full_rate else DRONE_BASE_PREMIUM / full(drone)
        drone.final_hull_premium = drone.hull_premium * scale
        drone.final_tpl_premium = drone.tpl_layer_premium * scale


def apply_max_cameras_in_air(cameras, m, rng):
    """Extension 2: full premium for the m most valuable cameras, a fixed premium for the rest."""
    for i, camera in enumerate(rank(cameras, lambda c: c.value, rng), start=1):
        camera.rank = i
        camera.charged_full_rate = i <= m
        camera.final_hull_premium = camera.hull_premium if camera.charged_full_rate else CAMERA_BASE_PREMIUM

#--------------------------------------------------------
# Flag missing prices:
#--------------------------------------------------------

def _can_price(submission, kind, item, problems):
    """Record a warning for an item that can't be priced."""
    if problems:
        submission.warnings.append(
            f"Fleet has been priced with {kind} {item.serial_number} removed because: {', '.join(problems)}"
        )
    return not problems


def _camera_flag_ok(submission, drone, camera_drones, n):
    """Keep a drone with a missing or invalid camera flag only if the flag can't change camera pricing.

    It can't change the camera rate if the drone's hull rate is not above it, and it can't change
    m = min(n, number of camera drones) if at least n drones are already known to take a camera.
    """
    problem = drone.camera_flag_problem()
    if not problem:
        return True
    rate, max_rate = hull_rate(drone.weight), max(hull_rate(d.weight) for d in camera_drones)
    if rate > max_rate:
        reason = f"its hull rate ({rate:g}) is above the camera rate ({max_rate:g})"
    elif len(camera_drones) < n:
        reason = (f"fewer than {n} drones are known to take a camera, "
                  "so it could change how many cameras are charged the full rate")
    else:
        submission.warnings.append(
            f"Drone {drone.serial_number}: {problem}, but this did not affect pricing because its hull rate "
            f"({rate:g}) is not above the camera rate ({max_rate:g}) and at least {n} drones are known to take a camera"
        )
        return True
    return _can_price(submission, "drone", drone, [f"{problem} and {reason}"])

#--------------------------------------------------------
# Final Pricing Ouput:
#--------------------------------------------------------

def price_submission(submission, seed=None):
    """Price every drone and camera that has the inputs it needs, then apply the extensions.

    Items with missing or invalid inputs are left unpriced and listed in `submission.warnings`.
    Pass a seed for reproducible tie-breaks.
    """
    rng = random.Random(seed)
    submission.warnings = []
    n = submission.max_drones_in_air
    cameras = [c for c in submission.detachable_cameras if _can_price(submission, "camera", c, c.problems())]
    drones = [d for d in submission.drones if _can_price(submission, "drone", d, d.problems())]

    # Cameras need a priceable drone to be mounted on - without one, only the drones are priced
    camera_drones = [d for d in drones if d.has_detachable_camera is True]
    if cameras and not camera_drones:
        submission.warnings.append(
            "Fleet has been priced with all cameras removed because: every drone either has no "
            "detachable camera or its has_detachable_camera is missing"
        )
        cameras = []
    if cameras:
        drones = [d for d in drones if _camera_flag_ok(submission, d, camera_drones, n)]

    for drone in drones:
        price_hull(drone)
        price_tpl(drone)
    rate = camera_rate(drones)
    for camera in cameras:
        price_camera(camera, rate)

    submission.net_prem, submission.gross_prem = summarise(
        [d.hull_premium for d in drones],
        [d.tpl_layer_premium for d in drones],
        [c.hull_premium for c in cameras],
        submission.brokerage,
    )

    # A camera can only fly on a flying drone that takes a camera
    m = min(n, len(camera_drones))
    apply_max_drones_in_air(drones, n, rng)
    apply_max_cameras_in_air(cameras, m, rng)

    submission.net_prem_after_extensions, submission.gross_prem_after_extensions = summarise(
        [d.final_hull_premium for d in drones],
        [d.final_tpl_premium for d in drones],
        [c.final_hull_premium for c in cameras],
        submission.brokerage,
    )
    return submission
