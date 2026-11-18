from datetime import date
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class BaseDTO(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        str_min_length=1,
        from_attributes=True,
    )


class BaseResponse(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra='forbid',
        str_min_length=1,
    )


class DateRange(BaseDTO):
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
