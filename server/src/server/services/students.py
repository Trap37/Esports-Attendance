import typing
from datetime import timedelta

from server.schemas.students import (
    GetStudentResult,
    ListStudentsResult,
    RegisterStudentRequest,
    RegisterStudentResult,
    StudentDTO,
    StudentUpdateRequest,
    StudentUpdateResponse,
)
from server.utils.dates import eastern_now, utc_now, utc_start_of_today
from server.utils.errors import (
    DuplicateScanIDError,
    StudentAlreadyExistsError,
    StudentNotFoundError,
)

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

    def register_student(self, request: RegisterStudentRequest):
        if self.students.exists_by_csu_id(request.csu_id):
            raise StudentAlreadyExistsError(request.csu_id)

        if self.students.exists_by_scan_id(request.scan_id):
            raise DuplicateScanIDError(request.scan_id)

        student = self.students.register(request)

        return RegisterStudentResult(student)

    def get_student(self, scan_id: str):
        student = self.students.get_by_scan_id(scan_id)
        if student is None:
            raise StudentNotFoundError(scan_id=scan_id)

        return GetStudentResult(student)

    def list_students(self, query=None):
        """Return all students; if query is given, filter by name, school_id, or scan_id (case-insensitive)."""
        students_list = self.students.list_students(query=query)
        return ListStudentsResult(students=students_list)

    def update_student(self, request: StudentUpdateRequest):
        """Update an existing student. Returns True if the student exists (even if no values changed)."""
        student = self.students.update(request)
        if student is None:
            raise StudentNotFoundError(request.scanner_code)

        return StudentUpdateResponse(student)
