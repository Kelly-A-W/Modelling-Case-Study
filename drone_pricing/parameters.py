"""Rating parameters, mirroring the spreadsheet's Parameters sheet."""

HULL_BASE_RATE = 0.06
TPL_BASE_RATE = 0.02

RIEBESELL_BASE_LIMIT = 1_000_000
RIEBESELL_Z = 0.2

# Maximum take-off weight adjustments for hull
WEIGHT_ADJUSTMENTS = {
    "0 - 5kg": 1.0,
    "5 - 10kg": 1.2,
    "10 - 20kg": 1.6,
    "> 20kg": 2.5,
}

# Upper limit (kg, inclusive) of each weight band, for mapping exact weights to bands
WEIGHT_BAND_LIMITS = {
    "0 - 5kg": 5,
    "5 - 10kg": 10,
    "10 - 20kg": 20,
    "> 20kg": float("inf"),
}

# Extensions: fixed premiums for drones and cameras that are not charged the full rate
DRONE_BASE_PREMIUM = 150
CAMERA_BASE_PREMIUM = 50
