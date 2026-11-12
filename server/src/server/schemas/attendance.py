from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    RootModel,
    computed_field,
    field_validator,
)

from server.schemas.base import BaseDTO, UTCDateTime
from server.schemas.students import StudentDTO
from server.utils.dates import normalize_utc, utc_now


class VisitDTO(BaseDTO):
    visit_id: int
    csu_id: str = Field(max_length=8)
    check_in_time: UTCDateTime
    checkout_time: UTCDateTime | None
    student: StudentDTO

    @field_validator('check_in_time', 'checkout_time')
    def ensure_utc(cls, v: datetime | None):
        if v is None:
            return v
        return normalize_utc(v)


class VisitsListDTO(RootModel[list[VisitDTO]]): ...


class StudentScanDTO(BaseDTO):
    scan_id: str = Field(max_length=8)


class ScanResult(BaseModel):
    student_name: str | None
    status: Literal[
        'student_not_found',
        'checked_in',
        'gear_return_required',
        'checked_out',
    ]
    time: UTCDateTime = Field(default_factory=utc_now)


class ScanResponse(BaseModel):
    student_name: str | None
    time: Annotated[str, Field(description='Time in HH:MM:SS format')]
    registered: bool
    checkout: bool
    gear_checkout: bool

    @classmethod
    def from_result(cls, scan_result: 'ScanResult'):
        return cls(
            student_name=scan_result.student_name,
            time=scan_result.time.strftime('%H:%M:%S'),
            # FIXME: This probably doesn't need to exist anymore. Lean into enum from /api/scan
            registered=scan_result.student_name is not None,
            checkout=scan_result.status == 'checked_out',
            gear_checkout=scan_result.status == 'gear_return_required',
        )


class ActiveStudentDTO(BaseDTO):
    scan_id: str
    full_name: str


class StudentsListResponse(BaseModel):
    students: list[ActiveStudentDTO]

    @computed_field
    @property
    def count(self) -> int:
        return len(self.students)
