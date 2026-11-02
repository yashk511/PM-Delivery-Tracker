"""Likelihood x impact scoring (both on a 1-5 scale)."""


def score(likelihood: int, impact: int) -> int:
    for name, v in (("likelihood", likelihood), ("impact", impact)):
        if not 1 <= int(v) <= 5:
            raise ValueError(f"{name} must be between 1 and 5, got {v}")
    return int(likelihood) * int(impact)


def band(s: int) -> str:
    if s >= 20:
        return "Critical"
    if s >= 12:
        return "High"
    if s >= 6:
        return "Medium"
    return "Low"
