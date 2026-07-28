from datetime import date
from enum import Enum

from pydantic import BaseModel, Field


class PeriodUnit(str, Enum):
    days = "days"
    weeks = "weeks"
    months = "months"


class ScheduleRequest(BaseModel):
    equipment: str
    last_pm_date: date
    period_value: int = Field(gt=0)
    period_unit: PeriodUnit
    assigned_to: str | None = None
    notes: str | None = None


class CalendarEntry(BaseModel):
    id: str
    equipment: str
    last_pm_date: date
    period_value: int
    period_unit: PeriodUnit
    next_pm_date: date
    days_remaining: int
    assigned_to: str | None = None
    notes: str | None = None
