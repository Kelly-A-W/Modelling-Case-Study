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
)
from .utils import gross_up, rank, riebesell

NOT_PRICED = "Not priced: value is missing or zero"


def price_hull(drone):
    """Drone hull premium (Model!L:O)."""
    drone.hull_base_rate = HULL_BASE_RATE
    drone.hull_weight_adjustment = WEIGHT_ADJUSTMENTS[drone.weight]
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
    return max((d.hull_final_rate for d in drones if d.has_detachable_camera), default=0)


def price_camera(camera, rate):
    """Camera hull premium (Model!H:I)."""
    camera.hull_rate = rate
    camera.hull_premium = camera.value * rate


def summarise(drones_hull, drones_tpl, cameras_hull, brokerage):
    """Net and gross premium summary (Model!F42:G45)."""
    net = [sum(drones_hull), sum(drones_tpl), sum(cameras_hull)]
    gross = [gross_up(p, brokerage) for p in net]
    return Premiums(*net, sum(net)), Premiums(*gross, sum(gross))


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


def _priced(items):
    """Return the items with a value, flagging the rest (the spreadsheet leaves them blank)."""
    for item in items:
        if not item.value:
            item.note = NOT_PRICED
    return [item for item in items if item.value]


def price_submission(submission, seed=None):
    """Price every drone and camera, then apply the extensions. Pass a seed for reproducible tie-breaks."""
    rng = random.Random(seed)
    drones = _priced(submission.drones)
    cameras = _priced(submission.detachable_cameras)

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

    n = submission.max_drones_in_air
    # A camera can only fly on a flying drone that takes a camera
    m = min(n, sum(d.has_detachable_camera for d in drones))
    apply_max_drones_in_air(drones, n, rng)
    apply_max_cameras_in_air(cameras, m, rng)

    submission.net_prem_after_extensions, submission.gross_prem_after_extensions = summarise(
        [d.final_hull_premium for d in drones],
        [d.final_tpl_premium for d in drones],
        [c.final_hull_premium for c in cameras],
        submission.brokerage,
    )
    return submission
