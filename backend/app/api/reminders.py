from fastapi import APIRouter

from app.mocks import reminders as mock_reminders
from app.models.reminders import Reminder

router = APIRouter(prefix="/reminders", tags=["reminders"])


@router.get("", response_model=list[Reminder])
def list_reminders() -> list[Reminder]:
    return mock_reminders.get_reminders()
