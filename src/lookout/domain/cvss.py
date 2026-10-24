"""CVSS v3 base score from a vector, so severity can be a computed fact and not a model's opinion."""

import math

from lookout.domain.severity import Severity

_AV = {"N": 0.85, "A": 0.62, "L": 0.55, "P": 0.2}
_AC = {"L": 0.77, "H": 0.44}
_UI = {"N": 0.85, "R": 0.62}
_CIA = {"H": 0.56, "L": 0.22, "N": 0.0}
_PR_UNCHANGED = {"N": 0.85, "L": 0.62, "H": 0.27}
_PR_CHANGED = {"N": 0.85, "L": 0.68, "H": 0.5}


def _roundup(value: float) -> float:
    """The CVSS 3.1 round-up to one decimal, immune to floating point noise."""
    scaled = round(value * 100000)
    if scaled % 10000 == 0:
        return scaled / 100000.0
    return (math.floor(scaled / 10000) + 1) / 10.0


def base_score(vector: str) -> float | None:
    """The base score of a ``CVSS:3.x/...`` vector, or ``None`` for anything else (v2, v4, malformed)."""
    parts = vector.strip().split("/")
    if not parts[0].startswith("CVSS:3."):
        return None
    metrics = dict(part.split(":", 1) for part in parts[1:] if ":" in part)
    try:
        changed = metrics["S"] == "C"
        privileges = (_PR_CHANGED if changed else _PR_UNCHANGED)[metrics["PR"]]
        exploitability = 8.22 * _AV[metrics["AV"]] * _AC[metrics["AC"]] * privileges * _UI[metrics["UI"]]
        iss = 1 - (1 - _CIA[metrics["C"]]) * (1 - _CIA[metrics["I"]]) * (1 - _CIA[metrics["A"]])
        if metrics["S"] not in ("U", "C"):
            return None
    except KeyError:
        return None
    impact = 7.52 * (iss - 0.029) - 3.25 * (iss - 0.02) ** 15 if changed else 6.42 * iss
    if impact <= 0:
        return 0.0
    return _roundup(min((impact + exploitability) * (1.08 if changed else 1.0), 10.0))


def severity_of(vector: str) -> Severity | None:
    """The severity word for a vector's base score; ``None`` when it cannot be scored or scores zero."""
    score = base_score(vector)
    if score is None or score == 0:
        return None
    if score < 4.0:
        return Severity.LOW
    if score < 7.0:
        return Severity.MODERATE
    if score < 9.0:
        return Severity.HIGH
    return Severity.CRITICAL
