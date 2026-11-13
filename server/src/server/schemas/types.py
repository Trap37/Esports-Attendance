from datetime import date, datetime
from enum import StrEnum
from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field, field_validator, model_validator

from server.utils.dates import normalize_utc, to_eastern_datetime


class DateRange(BaseModel):
    start: date
    end: date

    @field_validator('start', 'end', mode='before')
    @classmethod
    def parse_date(cls, value: str | date):
        if isinstance(value, date):
            return value

        if isinstance(value, str):
            value = value.strip()

        return date.fromisoformat(value)

    @model_validator(mode='after')
    def validate_range(self):
        if self.start > self.end:
            raise ValueError('start must be on or before end date')

        return self


CSU_ID = Annotated[str, Field(max_length=8)]
SCAN_ID = Annotated[str, Field(max_length=8)]
FULL_NAME = Annotated[str, Field(max_length=128)]
MAJOR = Annotated[str, Field(max_length=64)]


class GradeLevel(StrEnum):
    FRESHMAN = 'Freshman'
    SOPHOMORE = 'Sophomore'
    JUNIOR = 'Junior'
    SENIOR = 'Senior'
    GRADUATE = 'Graduate'


class ScanStatus(StrEnum):
    STUDENT_NOT_FOUND = 'student_not_found'
    GEAR_RETURN_REQUIRED = 'gear_return_required'
    CHECKING_IN = 'checking_in'
    CHECKING_OUT = 'checking_out'


UTCDateTime = Annotated[datetime, AfterValidator(normalize_utc)]
EasternDateTime = Annotated[datetime, AfterValidator(to_eastern_datetime)]
