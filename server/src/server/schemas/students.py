from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, RootModel, field_validator

import server.schemas.types as schema_types
from server.schemas.base import BaseDTO
from server.utils.dates import utc_now


class StudentDTO(BaseDTO):
    csu_id: schema_types.CSU_ID
    scan_id: schema_types.SCAN_ID
    full_name: schema_types.FULL_NAME
    major: schema_types.MAJOR
    grade_level: schema_types.GradeLevel


class RegisterStudentRequest(BaseDTO):
    csu_id: schema_types.CSU_ID
    scan_id: schema_types.SCAN_ID
    full_name: schema_types.FULL_NAME
    major: schema_types.MAJOR
    grade_level: schema_types.GradeLevel


class RegisterStudentResult(RootModel[StudentDTO]): ...


class ListStudentsRequest(BaseDTO):
    query: str = Field(serialization_alias='q')


class ListStudentsResult(BaseDTO):
    students: list[StudentDTO]


class GetStudentResult(RootModel[StudentDTO]): ...


class StudentUpdateRequest(BaseDTO):
    scanner_code: schema_types.SCAN_ID
    scan_id: schema_types.SCAN_ID
    full_name: schema_types.FULL_NAME
    major: schema_types.MAJOR
    grade_level: schema_types.GradeLevel


class StudentUpdateResponse(RootModel[StudentDTO]): ...
