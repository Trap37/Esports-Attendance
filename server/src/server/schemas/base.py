from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict

from server.utils.dates import normalize_utc


class BaseDTO(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra='forbid',
        str_min_length=1,
        from_attributes=True,
    )


class GradeLevel(StrEnum):
    FRESHMAN = 'Freshman'
    SOPHOMORE = 'Sophomore'
    JUNIOR = 'Junior'
    SENIOR = 'Senior'
    GRADUATE = 'Graduate'


UTCDateTime = Annotated[datetime, AfterValidator(normalize_utc)]
