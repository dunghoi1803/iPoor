from sqlalchemy import Integer, cast, func
from sqlalchemy.orm import Session

from .. import models

HOUSEHOLD_CODE_PREFIX = "HH-"
HOUSEHOLD_CODE_PAD = 4


def generate_household_code(db: Session) -> str:
    max_suffix = (
        db.query(
            func.max(
                cast(
                    func.substr(models.Household.household_code, len(HOUSEHOLD_CODE_PREFIX) + 1),
                    Integer,
                )
            )
        )
        .filter(models.Household.household_code.like(f"{HOUSEHOLD_CODE_PREFIX}%"))
        .scalar()
    )
    next_code = (max_suffix or 0) + 1
    return f"{HOUSEHOLD_CODE_PREFIX}{str(next_code).zfill(HOUSEHOLD_CODE_PAD)}"
