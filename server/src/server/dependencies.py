from server.extensions import db
from server.services.attendance import AttendanceService
from server.services.students import StudentsService


def get_attendance_service() -> AttendanceService:
    from server.repositories.attendance import AttendanceRepository
    from server.repositories.gear import GearCheckoutRepository
    from server.repositories.students import StudentRepository

    student_repository = StudentRepository(db)
    attendance_repository = AttendanceRepository(db)
    gear_checkout_repository = GearCheckoutRepository(db)

    return AttendanceService(
        student_repository, attendance_repository, gear_checkout_repository
    )


def get_students_service() -> StudentsService:
    from server.repositories.students import StudentRepository

    student_repository = StudentRepository(db)
    return StudentsService(student_repository)
