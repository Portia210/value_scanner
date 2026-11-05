"""Criterion definitions, results and the 0-1 strength measure (plans/v2-rebuild.md section 3).

A criterion is defined once; the report, the score and the dashboard all derive from it.
Missing data is `NA`, never `PASS`, and NA is left out of scores.
"""

from __future__ import annotations

import math
import operator
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

MARGIN = 0.2  # lesson 3: "a safety margin of about 20% on every item"


class Status(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    NA = "NA"


_COMPARE: dict[str, Callable[[float, float], bool]] = {
    ">": operator.gt,
    ">=": operator.ge,
    "<": operator.lt,
    "<=": operator.le,
}


@dataclass(frozen=True)
class Criterion:
    id: str
    guru: str  # screen | graham | fisher | piotroski
    lesson: int
    title: str
    formula: str  # human-readable, becomes docs/criteria/*.md (C10)
    direction: str  # one of > >= < <=
    threshold: float
    note: str = ""


@dataclass(frozen=True)
class Result:
    guru: str
    criterion_id: str
    status: Status
    value: float | None = None
    threshold: float | None = None
    strength: float | None = None
    note: str | None = None

    def as_row(self) -> dict:
        """The shape `Repository.save_results` expects."""
        return {
            "guru": self.guru,
            "criterion_id": self.criterion_id,
            "status": str(self.status),
            "value": self.value,
            "threshold": self.threshold,
            "strength": self.strength,
            "note": self.note,
        }


def is_missing(value: float | None) -> bool:
    return value is None or (isinstance(value, float) and math.isnan(value))


def strength(value: float, threshold: float, direction: str) -> float:
    """How comfortably a value passes (or how narrowly it fails), between 0 and 1.

    Passing with a margin of at least 20% of the threshold -> 1.0; passing by less -> 0.75;
    failing by less than 20% -> 0.25; failing by more -> 0. The margin is relative to
    |threshold|; for a threshold of 0 any pass counts as comfortable and any miss as 0.
    """
    passed = _COMPARE[direction](value, threshold)
    margin = MARGIN * abs(threshold)
    gap = value - threshold if direction in (">", ">=") else threshold - value  # >0 = better
    if passed:
        return 1.0 if gap >= margin else 0.75
    return 0.25 if -gap < margin else 0.0


def evaluate(criterion: Criterion, value: float | None, note: str | None = None) -> Result:
    """Apply a numeric criterion to a value. Missing/NaN -> NA."""
    if is_missing(value):
        return Result(
            criterion.guru,
            criterion.id,
            Status.NA,
            None,
            criterion.threshold,
            None,
            note or "no data",
        )
    value = round(value, 9)  # 1.3 / 1.0 - 1 is 0.30000000000000004: a value AT the threshold
    passed = _COMPARE[criterion.direction](value, criterion.threshold)
    return Result(
        criterion.guru,
        criterion.id,
        Status.PASS if passed else Status.FAIL,
        value,
        criterion.threshold,
        strength(value, criterion.threshold, criterion.direction),
        note,
    )


def compare(
    guru: str,
    criterion_id: str,
    now: float | None,
    before: float | None,
    *,
    lower_is_better: bool = False,
    note: str | None = None,
) -> Result:
    """A comparative criterion (Piotroski: this year better than last): strength is 1 or 0.
    `value` is this year's figure and `threshold` last year's. Equal is not an improvement."""
    if is_missing(now) or is_missing(before):
        return Result(guru, criterion_id, Status.NA, now, before, None, note or "no data")
    passed = now < before if lower_is_better else now > before
    return Result(
        guru,
        criterion_id,
        Status.PASS if passed else Status.FAIL,
        now,
        before,
        1.0 if passed else 0.0,
        note,
    )
