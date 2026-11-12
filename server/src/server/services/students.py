import typing
from datetime import timedelta

from server.schemas.students import (
    StudentDTO,
    StudentRegistrationError,
    StudentRetrievalError,
    StudentUpdate,
    StudentUpdateError,
)
from server.utils.dates import eastern_now, utc_now, utc_start_of_today

if typing.TYPE_CHECKING:
    from server.repositories.attendance import AttendanceRepository
    from server.repositories.gear import GearCheckoutRepository
    from server.repositories.students import StudentRepository


class StudentsService:
    def __init__(
        self,
        student_repository: 'StudentRepository',
        # attendance_repository: 'AttendanceRepository',
        # gear_checkout_repository: 'GearCheckoutRepository',
    ):
        self.students = student_repository
        # self.attendance = attendance_repository
        # self.gear_checkouts = gear_checkout_repository

    def register_student(self, student: StudentDTO):
        if self.students.register(
            student.scan_id,
            student.csu_id,
            student.full_name,
            student.major,
            student.grade_level,
        ):
            return {'success': True}
        else:
            return StudentRegistrationError.model_construct()

    def get_student(self, scan_id: str):
        student = self.students.get_by_scan_id(scan_id)
        if student:
            return student
        return StudentRetrievalError.model_construct()

    def list_students(self, query=None):
        """Return all students; if query is given, filter by name, school_id, or scan_id (case-insensitive)."""
        return self.students.list_students(query)

    def update_student(self, student: StudentUpdate):
        """Update an existing student. Returns True if the student exists (even if no values changed)."""
        if self.students.update(
            student.scanner_code,
            student.scan_id,
            student.full_name,
            student.major,
            student.grade_level,
        ):
            return {'success': True}
        else:
            return StudentUpdateError.model_construct()
