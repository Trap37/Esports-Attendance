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

from server.schemas.students import StudentDTO
from server.utils.dates import utc_now


class VisitDTO(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra='forbid',
        str_min_length=1,
        from_attributes=True,
    )

    visit_id: int
    csu_id: str = Field(max_length=8)
    check_in_time: datetime
    checkout_time: datetime | None
    student: StudentDTO

    @field_validator('check_in_time')
    def ensure_utc(cls, v: datetime | None):
        if v is None:
            return v

        if v.tzinfo is None:
            # Assume this was tz unaware from sql model
            return v.replace(tzinfo=UTC)
        return v.astimezone(UTC)


class VisitsListDTO(RootModel[list[VisitDTO]]): ...


class StudentScanDTO(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True, extra='forbid', from_attributes=True
    )

    scan_id: str = Field(min_length=1, max_length=8)

    @field_validator('scan_id')
    def validate_scan_id(cls, v: str):
        v = v.strip()
        if not v:
            raise ValueError('csu_id required')
        return v


class ScanResult(BaseModel):
    student_name: str | None
    status: Literal[
        'student_not_found',
        'checked_in',
        'gear_return_required',
        'checked_out',
    ]
    time: datetime = Field(default_factory=utc_now)


class ScanResponse(BaseModel):
    student_name: str | None
    time: Annotated[str, Field(description='Time in HH:MM:SS format')]
    registered: bool
    checkout: bool
    gear_checkout: bool

    @classmethod
    def from_result(cls, scan_result: 'ScanResult'):
        return cls.model_construct(
            student_name=scan_result.student_name,
            time=scan_result.time.strftime('%H:%M:%S'),
            registered=scan_result.student_name is not None,
            checkout=scan_result.status == 'checked_out',
            gear_checkout=scan_result.status == 'gear_return_required',
        )


class ActiveStudentDTO(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra='forbid',
        str_min_length=1,
        from_attributes=True,
    )

    scan_id: str
    full_name: str


class StudentsListResponse(BaseModel):
    students: list[ActiveStudentDTO]

    @computed_field
    @property
    def count(self) -> int:
        return len(self.students)
