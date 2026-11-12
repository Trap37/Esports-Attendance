from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from server.utils.dates import utc_now


class StudentDTO(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra='forbid',
        str_min_length=1,
        from_attributes=True,
    )

    csu_id: str = Field(max_length=8)
    scan_id: str = Field(max_length=8)
    full_name: str = Field(max_length=128)
    major: str = Field(max_length=64)
    grade_level: Literal[
        'Freshman',
        'Sophomore',
        'Junior',
        'Senior',
        'Graduate',
    ] = Field(max_length=16)


class StudentRegistrationError(BaseModel):
    error: str = 'A student with that Scan ID already exists'


class StudentRetrievalResult(BaseModel):
    students: list['StudentDTO']


class StudentRetrievalError(BaseModel):
    error: str = 'Student not found'


class StudentUpdate(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra='forbid',
        str_min_length=1,
        from_attributes=True,
    )

    scanner_code: str = Field(max_length=8)
    scan_id: str = Field(max_length=8)
    full_name: str = Field(max_length=128)
    major: str = Field(max_length=64)
    grade_level: Literal[
        'Freshman',
        'Sophomore',
        'Junior',
        'Senior',
        'Graduate',
    ] = Field(max_length=16)


class StudentUpdateError(BaseModel):
    error: str = 'Student not found'
