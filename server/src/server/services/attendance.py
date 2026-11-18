# NOTE: Have services return ordinary Python objects or clearly defined results, not Flask Response objects or jsonify() results

import typing
from datetime import timedelta

from server.schemas.attendance import (
    ActiveStudentsResult,
    AttendanceHistoryResult,
    AttendanceHistoryResultRow,
    CurrentAttendanceResult,
    DateRange,
    MappedVisitDTO,
    ScanResult,
    StudentScanRequest,
)
from server.schemas.types import ScanStatus
from server.utils.dates import (
    eastern_date_range_to_utc,
    eastern_now,
    to_eastern_datetime,
    utc_now,
    utc_start_of_today,
    utc_time_is_before_today,
)

if typing.TYPE_CHECKING:
    from server.repositories.attendance import AttendanceRepository
    from server.repositories.gear import GearCheckoutRepository
    from server.repositories.students import StudentRepository


class AttendanceService:
    def __init__(
        self,
        student_repository: 'StudentRepository',
        attendance_repository: 'AttendanceRepository',
        gear_checkout_repository: 'GearCheckoutRepository',
    ):
        self.students = student_repository
        self.attendance = attendance_repository
        self.gear_checkouts = gear_checkout_repository

    def process_scan(self, request: StudentScanRequest):
        student = self.students.get_by_scan_id(request.scan_id)
        if student is None:
            return ScanResult(
                student_name=None,
                status=ScanStatus.STUDENT_NOT_FOUND,
            )

        visit = self.attendance.get_by_csu_id(student.csu_id)
        if visit is None:
            # Student has no active check-ins or outs.
            self.attendance.create(student.csu_id)
            return ScanResult(
                student_name=student.full_name,
                status=ScanStatus.CHECKING_IN,
            )

        elif utc_time_is_before_today(visit.check_in_time):
            self.attendance.close_previous_day_visits(csu_id=student.csu_id)
            self.gear_checkouts.close_previous_day_checkouts(csu_id=student.csu_id)

            self.attendance.create(student.csu_id)
            return ScanResult(
                student_name=student.full_name,
                status=ScanStatus.CHECKING_IN,
            )

        gear_checkout = self.gear_checkouts.get_by_csu_id(student.csu_id)
        if gear_checkout is not None:
            # Student has an unclosed gear checkout
            return ScanResult(
                student_name=student.full_name,
                status=ScanStatus.GEAR_RETURN_REQUIRED,
            )

        visit = self.attendance.check_out(visit.visit_id)
        return ScanResult(
            student_name=student.full_name,
            status=ScanStatus.CHECKING_OUT,
            checkout_time=visit.checkout_time,
        )

    def get_todays_attendance(self):
        """Return a list of student names who are scanned in right now."""
        start_time = utc_start_of_today()
        end_time = start_time + timedelta(days=1)

        visits = self.attendance.get_visits_in_range(
            start_time,
            end_time,
            only_active=True,
            order_by_time=True,
            include_mappings=True,
        )

        return CurrentAttendanceResult(
            students=[
                ActiveVisitDto(
                    student_name=visit.student.full_name,
                    check_in_time=visit.check_in_time,
                    checkout_time=visit.checkout_time,
                )
                for visit in visits
            ]
        )

    def get_active_attendance(self):
        start_time = utc_start_of_today()
        end_time = start_time + timedelta(days=1)

        visits = self.attendance.get_visits_in_range(
            start_time, end_time, only_active=True, include_mappings=True
        )

        return [
            ActiveStudentsResult(
                scan_id=visit.student.scan_id, full_name=visit.student.full_name
            )
            for visit in visits
        ]

    def get_attendance_in_range(
        self, date_range: DateRange, *, include_mappings: bool = False
    ):
        start, end = eastern_date_range_to_utc(
            date_range.start,
            date_range.end,
        )

        attendance = self.attendance.get_visits_in_range(
            start, end, include_mappings=include_mappings
        )

        return AttendanceHistoryResult(
            start=start.date(),
            end=end.date(),
            rows=[
                AttendanceHistoryResultRow(
                    check_in_time=visit.check_in_time,
                    day_of_week=visit.day_of_week,
                    scan_id=visit.student.scan_id,
                    csu_id=visit.student.csu_id,
                    full_name=visit.student.full_name,
                    major=visit.student.major,
                    grade_level=visit.student.grade_level,
                )
                for visit in attendance
            ],
        )
