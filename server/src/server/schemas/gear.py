from pydantic import model_validator

import server.schemas.types as schema_types
from server.schemas.base import BaseDTO, BaseResponse
from server.schemas.students import StudentDTO


class GearCheckoutDTO(BaseDTO):
    checkout_id: int
    csu_id: schema_types.CSU_ID

    keyboard: bool
    mouse: bool
    mousepad: bool
    headset: bool

    checkout_time: schema_types.UTCDateTime
    returned_time: schema_types.UTCDateTime | None


class MappedGearCheckoutDTO(GearCheckoutDTO):
    student: StudentDTO


class ActiveCheckoutsCountResult(BaseDTO):
    total: int
    keyboards: int
    mice: int
    other: int


class GearCheckoutItemDTO(BaseDTO):
    keyboard: bool
    mouse: bool
    mousepad: bool
    headset: bool

    @model_validator(mode='after')
    def validate_selection(self):
        if not any((self.keyboard, self.mouse, self.mousepad, self.headset)):
            raise ValueError('Select at least one gear item')

        return self


class ActiveGearCheckoutDTO(BaseDTO):
    checkout_id: str
    scan_id: schema_types.SCAN_ID
    full_name: schema_types.FULL_NAME
    items: list[GearCheckoutItemDTO]
    checkout_time: schema_types.EasternDateTime


class ActiveGearCheckoutsResult(BaseDTO):
    checkouts: list[ActiveGearCheckoutDTO]


class CreateGearCheckoutRequest(BaseDTO):
    scan_id: schema_types.SCAN_ID
    items: GearCheckoutItemDTO


class GearCheckoutResult(BaseDTO):
    checkout_id: str
