from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, RootModel, field_validator

from server.schemas.base import BaseDTO
from server.schemas.types import GradeLevel
from server.utils.dates import utc_now


class StudentDTO(BaseDTO):
    csu_id: str = Field(max_length=8)
    scan_id: str = Field(max_length=8)
    full_name: str = Field(max_length=128)
    major: str = Field(max_length=64)
    grade_level: GradeLevel


class ListStudentsResult(RootModel[list[StudentDTO]]): ...


class ListStudentsResponse(BaseModel):
    students: list[StudentDTO]


class StudentRegistrationError(BaseModel):
    error: str = 'A student with that Scan ID already exists'


class StudentRetrievalError(BaseModel):
    error: str = 'Student not found'


class StudentUpdate(BaseDTO):
    scanner_code: str = Field(max_length=8)
    scan_id: str = Field(max_length=8)
    full_name: str = Field(max_length=128)
    major: str = Field(max_length=64)
    grade_level: GradeLevel


class StudentUpdateError(BaseModel):
    error: str = 'Student not found'
