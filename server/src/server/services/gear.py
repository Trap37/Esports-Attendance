import typing

from server.dependencies import get_attendance_service
from server.schemas.gear import (
    ActiveCheckoutsCountResult,
    ActiveGearCheckoutDTO,
    ActiveGearCheckoutsResult,
    CreateGearCheckoutRequest,
    GearCheckoutResult,
    MappedGearCheckoutDTO,
)
from server.services.attendance import AttendanceService
from server.utils.dates import utc_time_is_before_today
from server.utils.errors import ActiveCheckoutExistsError, StudentNotFoundError

if typing.TYPE_CHECKING:
    from server.repositories.attendance import AttendanceRepository
    from server.repositories.gear import GearCheckoutRepository
    from server.repositories.students import StudentRepository


class GearCheckoutService:
    def __init__(
        self,
        student_repository: 'StudentRepository',
        attendance_repository: 'AttendanceRepository',
        gear_checkout_repository: 'GearCheckoutRepository',
    ) -> None:
        self.students = student_repository
        self.attendance = attendance_repository
        self.gear_checkouts = gear_checkout_repository

    def checkout(self, request: CreateGearCheckoutRequest):
        student = self.students.get_by_scan_id(request.scan_id)
        if student is None:
            raise StudentNotFoundError(request.scan_id)

        active = self.gear_checkouts.get_active_checkout(student.csu_id)
        if active is not None:
            raise ActiveCheckoutExistsError(student.csu_id)

        visit = self.attendance.get_active_visit(student.csu_id)
        if visit is None:
            self.attendance.create(student.csu_id)
        elif utc_time_is_before_today(visit.check_in_time):
            attendance_service = get_attendance_service()
            attendance_service._close_previous_day_visits(student.csu_id)
            attendance_service._close_previous_day_checkouts(student.csu_id)

            self.attendance.create(student.csu_id)

        checkout = self.gear_checkouts.create(student.csu_id, request.items)
        return GearCheckoutResult(checkout_id=str(checkout.checkout_id))

    def get_gear_stats(self):
        # TICKET:: Mousepad and headset can just be separate why combined?
        # FEATURE: Can have a csv or json file that holds data about every piece of equipment
        # FEATURE: Can add add total number of equipment items here
        checkouts = self.gear_checkouts.get_all_active_checkouts()
        return ActiveCheckoutsCountResult(
            total=len(checkouts),
            keyboards=sum(r.keyboard for r in checkouts),
            mice=sum(r.mouse for r in checkouts),
            other=sum(bool(r.mousepad) + bool(r.headset) for r in checkouts),
        )

    def get_active_checkouts(self):
        checkouts = self.gear_checkouts.get_all_active_checkouts(
            order_by_time=True, include_mappings=True
        )
        return ActiveGearCheckoutsResult(
            checkouts=[
                ActiveGearCheckoutDTO.model_validate(model) for model in checkouts
            ]
        )
