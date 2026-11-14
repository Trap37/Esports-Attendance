import typing
from datetime import datetime

import sqlalchemy as sa
import sqlalchemy.orm as so

from server.models.gear import GearCheckout
from server.schemas.gear import (
    GearCheckoutDTO,
    GearCheckoutItemDTO,
    GearCheckoutResult,
    MappedGearCheckoutDTO,
)
from server.utils.dates import set_end_of_day, to_eastern_datetime, utc_now

if typing.TYPE_CHECKING:
    from flask_sqlalchemy import SQLAlchemy


class GearCheckoutRepository:
    def __init__(self, db: 'SQLAlchemy'):
        self._db = db

    def create(self, csu_id: str, items: GearCheckoutItemDTO):
        checkout = GearCheckout(
            csu_id=csu_id,
            keyboard=items.keyboard,
            mouse=items.mouse,
            mousepad=items.mousepad,
            headset=items.headset,
        )
        self._db.session.add(checkout)
        self._db.session.commit()
        return GearCheckoutDTO.model_validate(checkout)

    def get_active_checkout(self, csu_id: str):
        return self._db.session.scalar(
            sa.select(GearCheckout).where(
                GearCheckout.csu_id == csu_id,
                GearCheckout.returned_time.is_(None),
            )
        )

    def get_active_checkouts_before(self, csu_id: str, start_of_today: datetime):
        return self._db.session.scalars(
            sa.select(GearCheckout).where(
                GearCheckout.csu_id == csu_id,
                GearCheckout.returned_time < start_of_today,
                # GearCheckout.returned_time.is_(None),
            )
        ).all()

    def return_checkout(self, checkout: GearCheckout, *, to_eod=False):
        if to_eod:
            local_datetime = to_eastern_datetime(checkout.checkout_time)
            checkout.checkout_time = set_end_of_day(local_datetime.date())
        else:
            checkout.checkout_time = utc_now()

    @typing.overload
    def get_all_active_checkouts(
        self,
        *,
        order_by_time: bool = False,
        include_mappings: typing.Literal[False] = False,
    ) -> list[GearCheckoutDTO]: ...

    @typing.overload
    def get_all_active_checkouts(
        self,
        *,
        order_by_time: bool = False,
        include_mappings: typing.Literal[True],
    ) -> list[MappedGearCheckoutDTO]: ...

    def get_all_active_checkouts(
        self,
        *,
        order_by_time: bool = False,
        include_mappings: bool = False,
    ) -> list[GearCheckoutDTO] | list[MappedGearCheckoutDTO]:
        statement = sa.select(GearCheckout).where(GearCheckout.returned_time.is_(None))

        if order_by_time:
            statement = statement.order_by(GearCheckout.checkout_time)
        if include_mappings:
            statement = statement.options(so.joinedload(GearCheckout.student))

        rows = self._db.session.scalars(statement).all()

        dto = MappedGearCheckoutDTO if include_mappings else GearCheckoutDTO

        return [dto.model_validate(model) for model in rows]
