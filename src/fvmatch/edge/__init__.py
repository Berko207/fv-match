"""Edge module: de-vigging and Kelly staking."""

from .devig import devig, multiplicative, power, shin
from .kelly import Leg, fractional_kelly, joint_match_stakes, kelly_fraction

__all__ = [
    "devig",
    "multiplicative",
    "power",
    "shin",
    "kelly_fraction",
    "fractional_kelly",
    "joint_match_stakes",
    "Leg",
]
