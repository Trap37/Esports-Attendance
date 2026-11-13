from datetime import UTC, date, datetime
from typing import Annotated, Literal

from pydantic import (
    AliasPath,
    BaseModel,
    ConfigDict,
    Field,
    RootModel,
    computed_field,
    field_serializer,
    field_validator,
)

import server.schemas.types as schema_types
from server.schemas.base import BaseDTO, BaseResponse
from server.schemas.students import StudentDTO
from server.utils.dates import eastern_now, format_timestamp, normalize_utc, utc_now


class VisitDTO(BaseDTO):
    visit_id: int
    csu_id: str = Field(max_length=8)
    check_in_time: schema_types.UTCDateTime
    checkout_time: schema_types.UTCDateTime | None = None

    student: StudentDTO

    day_of_week: str
    is_checked_out: bool


class VisitsListDTO(RootModel[list[VisitDTO]]): ...


class StudentScanDTO(BaseDTO):
    scan_id: str = Field(max_length=8)


class ScanEvent(BaseModel):
    student_name: schema_types.FULL_NAME | None
    status: schema_types.ScanStatus
    check_in_time: schema_types.EasternDateTime
    checkout_time: schema_types.EasternDateTime | None = None

    # @field_serializer('check_in_time', 'checkout_time')
    # def to_timestamp(self, value: schema_types.EasternDateTime | None):
    #     if value is None:
    #         return
    #     return format_timestamp(value, include_date=False)

    @classmethod
    def from_visit(cls, visit: VisitDTO):
        return cls(
            student_name=visit.student.full_name,
            status=schema_types.ScanStatus.CHECKING_OUT
            if visit.is_checked_out
            else schema_types.ScanStatus.CHECKING_IN,
            check_in_time=visit.check_in_time,
            checkout_time=visit.checkout_time,
        )


class ScanResult(ScanEvent):
    check_in_time: schema_types.EasternDateTime = Field(default_factory=eastern_now)


class ScanResponse(ScanEvent):
    @classmethod
    def from_scan_result(cls, result: ScanResult):
        return cls(
            student_name=result.student_name,
            status=result.status,
            check_in_time=result.check_in_time,
            checkout_time=result.checkout_time,
        )


class ActiveVisitDTO(BaseDTO):
    scan_id: schema_types.SCAN_ID = Field(
        validation_alias=AliasPath('student', 'scan_id'),
    )
    full_name: schema_types.FULL_NAME = Field(
        validation_alias=AliasPath('student', 'full_name'),
    )


class ActiveStudentsResponse(BaseResponse):
    students: list[ActiveVisitDTO]

    @computed_field
    @property
    def count(self) -> int:
        return len(self.students)


class AttendanceTodayResponse(BaseResponse):
    students: list[ScanEvent]

    @classmethod
    def from_visits(cls, visits: VisitsListDTO):
        return cls(students=[ScanEvent.from_visit(visit) for visit in visits.root])


class AttendanceHistoryResponseRow(BaseResponse):
    check_in_time: schema_types.EasternDateTime
    day_of_week: str

    scan_id: schema_types.SCAN_ID = Field(
        validation_alias=AliasPath('student', 'scan_id'),
    )
    csu_id: schema_types.CSU_ID = Field(
        validation_alias=AliasPath('student', 'csu_id'),
    )
    full_name: schema_types.FULL_NAME = Field(
        validation_alias=AliasPath('student', 'full_name'),
    )
    major: schema_types.MAJOR = Field(
        validation_alias=AliasPath('student', 'major'),
    )
    grade_level: schema_types.GradeLevel = Field(
        validation_alias=AliasPath('student', 'grade_level'),
    )

    @field_serializer('check_in_time')
    def to_timestamp(self, value: schema_types.EasternDateTime):
        return format_timestamp(value)


class AttendanceHistoryResponse(BaseResponse):
    start: date
    end: date
    rows: list[AttendanceHistoryResponseRow]

    @computed_field
    @property
    def count(self) -> int:
        return len(self.rows)

    @field_serializer('start', 'end')
    def to_iso_format(self, value: date):
        return value.isoformat()
