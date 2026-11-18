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
    model_validator,
)

import server.schemas.types as schema_types
from server.schemas.base import BaseDTO, BaseResponse, DateRange
from server.schemas.students import StudentDTO
from server.utils.dates import eastern_now, format_timestamp, normalize_utc, utc_now


class VisitDTO(BaseDTO):
    visit_id: int
    csu_id: str = Field(max_length=8)
    check_in_time: schema_types.UTCDateTime
    checkout_time: schema_types.UTCDateTime | None = None

    day_of_week: str
    week_number: int
    month_str: str

    is_checked_out: bool


class MappedVisitDTO(VisitDTO):
    student: StudentDTO


class ScanEvent(BaseDTO):
    student_name: schema_types.FULL_NAME | None
    check_in_time: schema_types.EasternDateTime
    checkout_time: schema_types.EasternDateTime | None = None
    status: schema_types.ScanStatus = Field(init=False)

    @model_validator(mode='after')
    def determine_status(self):
        self.status = (
            schema_types.ScanStatus.CHECKED_OUT
            if self.checkout_time is not None
            else schema_types.ScanStatus.CHECKED_IN
        )

        return self


class StudentScanRequest(BaseDTO):
    scan_id: schema_types.SCAN_ID


class ScanResult(ScanEvent):
    check_in_time: schema_types.EasternDateTime = Field(default_factory=eastern_now)


class CurrentAttendanceResult(BaseDTO):
    students: list[ScanEvent]


class AttendanceHistoryRequest(DateRange): ...


class AttendanceHistoryResultRow(BaseResponse):
    check_in_time: schema_types.EasternDateTime
    day_of_week: str

    scan_id: schema_types.SCAN_ID
    csu_id: schema_types.CSU_ID
    full_name: schema_types.FULL_NAME
    major: schema_types.MAJOR
    grade_level: schema_types.GradeLevel

    @field_serializer('check_in_time')
    def to_timestamp(self, value: schema_types.EasternDateTime):
        return format_timestamp(value)


class AttendanceHistoryResult(BaseDTO):
    start: date
    end: date
    rows: list[AttendanceHistoryResultRow]

    @computed_field
    @property
    def count(self) -> int:
        return len(self.rows)


# class ScanEvent(BaseModel):
#     student_name: schema_types.FULL_NAME | None
#     status: schema_types.ScanStatus
#     check_in_time: schema_types.EasternDateTime
#     checkout_time: schema_types.EasternDateTime | None = None

#     # @field_serializer('check_in_time', 'checkout_time')
#     # def to_timestamp(self, value: schema_types.EasternDateTime | None):
#     #     if value is None:
#     #         return
#     #     return format_timestamp(value, include_date=False)

#     @classmethod
#     def from_visit(cls, visit: VisitDTO):
#         return cls(
#             student_name=visit.student.full_name,
#             status=schema_types.ScanStatus.CHECKING_OUT
#             if visit.is_checked_out
#             else schema_types.ScanStatus.CHECKING_IN,
#             check_in_time=visit.check_in_time,
#             checkout_time=visit.checkout_time,
#         )


# class ScanResult(ScanEvent):
#     check_in_time: schema_types.EasternDateTime = Field(default_factory=eastern_now)


class ActiveStudentsResult(BaseDTO):
    scan_id: schema_types.SCAN_ID = Field(
        validation_alias=AliasPath('student', 'scan_id'),
    )
    full_name: schema_types.FULL_NAME = Field(
        validation_alias=AliasPath('student', 'full_name'),
    )
