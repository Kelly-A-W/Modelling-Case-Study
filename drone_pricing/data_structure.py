# Data frame for a submission: 
# holds the inputs plus every calculated value.

from dataclasses import asdict, dataclass, field, fields
from .parameters import WEIGHT_ADJUSTMENTS

#--------------------------------------------------------
# Helper Functions:
#--------------------------------------------------------

# ensure calculated fields are not required inputs, and set the starting value:
def _output():
    return field(default=None, init=False)

# create custom errors:
def _require(condition, message):
    if not condition:
        raise ValueError(message)

# check numerical inputs are numerical:
def _is_number(x):
    return type(x) in (int, float)

# reason an input can't be used for pricing, or None if it is fine:
def _problem(name, x, is_valid):
    if x is None:
        return f"{name} is missing"
    if not is_valid(x):
        return f"{name} {x!r} is invalid"

# build a class from a dict of inputs; missing inputs are set to None:
def _from_dict(cls, data):
    return cls(**{f.name: data.get(f.name) for f in fields(cls) if f.init})

#--------------------------------------------------------
# Classes:
#--------------------------------------------------------

@dataclass
class Drone:
    serial_number: str
    value: float
    weight: str | float  # band label, e.g. "0 - 5kg", or exact weight in kg
    has_detachable_camera: bool
    tpl_limit: float
    tpl_excess: float
    # Spreadsheet calculations
    weight_category: str = _output()
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

    # reasons this drone can't be priced (empty if it can):
    def problems(self):
        found = [
            _problem("value", self.value, lambda x: _is_number(x) and x > 0),
            _problem("weight", self.weight, lambda x: x in WEIGHT_ADJUSTMENTS or (_is_number(x) and x > 0)),
            _problem("tpl_limit", self.tpl_limit, lambda x: _is_number(x) and x > 0),
            _problem("tpl_excess", self.tpl_excess, lambda x: _is_number(x) and x >= 0),
        ]
        return [p for p in found if p]

    # the camera flag is checked separately, as it only matters if it could change camera pricing:
    def camera_flag_problem(self):
        return _problem("has_detachable_camera", self.has_detachable_camera, lambda x: type(x) is bool)


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

    # reasons this camera can't be priced (empty if it can):
    def problems(self):
        found = _problem("value", self.value, lambda x: _is_number(x) and x > 0)
        return [found] if found else []


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
    # Drones and cameras removed from pricing, and why
    warnings: list = field(default_factory=list, init=False)

    def __post_init__(self):
        _require(_is_number(self.brokerage) and 0 <= self.brokerage < 1, "brokerage must be in [0, 1)")
        _require(type(self.max_drones_in_air) is int and self.max_drones_in_air >= 0, "max_drones_in_air must be an integer >= 0")

    @classmethod
    def from_dict(cls, data):
        data = {
            **data,
            "drones": [_from_dict(Drone, d) for d in data.get("drones", [])],
            "detachable_cameras": [_from_dict(Camera, c) for c in data.get("detachable_cameras", [])],
        }
        return _from_dict(cls, data)

    def to_dict(self):
        return asdict(self)
