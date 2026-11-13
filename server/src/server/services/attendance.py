# NOTE: Have services return ordinary Python objects or clearly defined results, not Flask Response objects or jsonify() results

import typing
from datetime import timedelta

from server.schemas.attendance import ScanResult
from server.schemas.types import DateRange, ScanStatus
from server.utils.dates import (
    eastern_date_range_to_utc,
    eastern_now,
    utc_now,
    utc_start_of_today,
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

    def process_scan(self, scan_id: str):
        student = self.students.get_by_scan_id(scan_id)

        if student is None:
            return ScanResult(
                student_name=None,
                status=ScanStatus.STUDENT_NOT_FOUND,
            )

        visit = self.attendance.get_active_visit(student.csu_id)
        if visit is None:
            # Student has no active check-ins or outs.
            self.attendance.create(student.csu_id)
            return ScanResult(
                student_name=student.full_name,
                status=ScanStatus.CHECKING_IN,
            )

        elif visit.check_in_time < utc_start_of_today():
            self._close_previous_day_visits(student.csu_id)
            self._close_previous_day_checkouts(student.csu_id)

            self.attendance.create(student.csu_id)
            return ScanResult(
                student_name=student.full_name,
                status=ScanStatus.CHECKING_IN,
            )

        gear_checkout = self.gear_checkouts.get_active_checkout(student.csu_id)
        if gear_checkout is not None:
            # Student has an unclosed gear checkout
            return ScanResult(
                student_name=student.full_name,
                status=ScanStatus.GEAR_RETURN_REQUIRED,
            )

        self.attendance.check_out(visit)

        return ScanResult(
            student_name=student.full_name,
            status=ScanStatus.CHECKING_OUT,
            checkout_time=eastern_now(),
        )

    def _close_previous_day_visits(self, csu_id: str):
        visits = self.attendance.get_active_visits_before(
            csu_id,
            utc_start_of_today(),
        )

        for visit in visits:
            self.attendance.check_out(visit, to_eod=True)

    def _close_previous_day_checkouts(self, csu_id: str):
        checkouts = self.gear_checkouts.get_active_checkouts_before(
            csu_id,
            utc_start_of_today(),
        )

        for checkout in checkouts:
            self.gear_checkouts.return_checkout(checkout, to_eod=True)

    def get_todays_attendance(self):
        """Return a list of student names who are scanned in right now."""
        # return self.attendance.get_todays_active_visits()
        start_time = utc_start_of_today()
        end_time = start_time + timedelta(days=1)

        return self.attendance.get_visits_in_range(start_time, end_time)

    def get_active_attendance(self):
        start_time = utc_start_of_today()
        end_time = start_time + timedelta(days=1)

        return self.attendance.get_visits_in_range(
            start_time, end_time, only_active=True
        )

    def get_attendance_in_range(self, date_range: DateRange):
        start, end = eastern_date_range_to_utc(
            date_range.start,
            date_range.end,
        )

        return self.attendance.get_visits_in_range(start, end)
