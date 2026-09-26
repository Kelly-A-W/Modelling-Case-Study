"""Data model for a submission: holds the inputs plus every calculated value.

Calculated fields are `init=False`, so they cannot be passed in and start as None.
`to_dict()` returns the same nested layout as the original example data.
"""
from dataclasses import asdict, dataclass, field, fields

from .parameters import WEIGHT_ADJUSTMENTS


class ValidationError(ValueError):
    pass


def _output():
    return field(default=None, init=False)


def _require(condition, message):
    if not condition:
        raise ValidationError(message)


def _is_number(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _is_value(x):
    """Values may be missing (None) or zero; such items are flagged as not priced."""
    return x is None or (_is_number(x) and x >= 0)


def _from_dict(cls, data):
    try:
        return cls(**{f.name: data[f.name] for f in fields(cls) if f.init})
    except KeyError as e:
        raise ValidationError(f"{cls.__name__} is missing {e}") from None


@dataclass
class Drone:
    serial_number: str
    value: float
    weight: str
    has_detachable_camera: bool
    tpl_limit: float
    tpl_excess: float
    # Spreadsheet calculations
    hull_base_rate: float = _output()
    hull_weight_adjustment: float = _output()
    hull_final_rate: float = _output()
    hull_premium: float = _output()
    tpl_base_rate: float = _output()
    tpl_base_layer_premium: float = _output()
    tpl_ilf: float = _output()
    tpl_layer_premium: float = _output()
    # Extension: max drones in air
    rank: int = _output()
    charged_full_rate: bool = _output()
    final_hull_premium: float = _output()
    final_tpl_premium: float = _output()
    note: str = _output()

    def __post_init__(self):
        name = f"Drone {self.serial_number}"
        _require(_is_value(self.value), f"{name}: value must be a number >= 0 or None")
        _require(self.weight in WEIGHT_ADJUSTMENTS, f"{name}: unknown weight {self.weight!r}")
        _require(isinstance(self.has_detachable_camera, bool), f"{name}: has_detachable_camera must be True/False")
        _require(_is_number(self.tpl_limit) and self.tpl_limit > 0, f"{name}: tpl_limit must be > 0")
        _require(_is_number(self.tpl_excess) and self.tpl_excess >= 0, f"{name}: tpl_excess must be >= 0")

    @classmethod
    def from_dict(cls, data):
        return _from_dict(cls, data)


@dataclass
class Camera:
    serial_number: str
    value: float
    # Spreadsheet calculations
    hull_rate: float = _output()
    hull_premium: float = _output()
    # Extension: max cameras in air
    rank: int = _output()
    charged_full_rate: bool = _output()
    final_hull_premium: float = _output()
    note: str = _output()

    def __post_init__(self):
        _require(_is_value(self.value), f"Camera {self.serial_number}: value must be a number >= 0 or None")

    @classmethod
    def from_dict(cls, data):
        return _from_dict(cls, data)


@dataclass
class Premiums:
    drones_hull: float = None
    drones_tpl: float = None
    cameras_hull: float = None
    total: float = None


@dataclass
class Submission:
    insured: str
    underwriter: str
    broker: str
    brokerage: float
    max_drones_in_air: int
    drones: list
    detachable_cameras: list
    # Spreadsheet premium summary
    gross_prem: Premiums = field(default_factory=Premiums, init=False)
    net_prem: Premiums = field(default_factory=Premiums, init=False)
    # Premium summary after the extensions
    gross_prem_after_extensions: Premiums = field(default_factory=Premiums, init=False)
    net_prem_after_extensions: Premiums = field(default_factory=Premiums, init=False)

    def __post_init__(self):
        _require(_is_number(self.brokerage) and 0 <= self.brokerage < 1, "brokerage must be in [0, 1)")
        _require(
            isinstance(self.max_drones_in_air, int) and not isinstance(self.max_drones_in_air, bool)
            and self.max_drones_in_air >= 0,
            "max_drones_in_air must be an integer >= 0",
        )

    @classmethod
    def from_dict(cls, data):
        data = {
            **data,
            "drones": [Drone.from_dict(d) for d in data.get("drones", [])],
            "detachable_cameras": [Camera.from_dict(c) for c in data.get("detachable_cameras", [])],
        }
        return _from_dict(cls, data)

    def to_dict(self):
        return asdict(self)
