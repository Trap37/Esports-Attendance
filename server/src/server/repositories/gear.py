import typing
from collections import abc
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
from server.utils.dates import (
    set_end_of_day,
    to_eastern_datetime,
    utc_now,
    utc_start_of_today,
)

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

    def get_by_checkout_id(self, checkout_id: int | str, *, raw: bool = False):
        checkout = self._db.session.scalar(
            sa.select(GearCheckout).where(
                GearCheckout.checkout_id == checkout_id,
            )
        )
        if checkout is None:
            return None

        if raw:
            return checkout
        else:
            return GearCheckoutDTO.model_validate(checkout)

    @typing.overload
    def get_active_checkouts_before(
        self,
        time: datetime,
        *,
        raw: typing.Literal[False] = False,
        csu_id: str | None = None,
    ) -> list[GearCheckoutDTO]: ...
    @typing.overload
    def get_active_checkouts_before(
        self, time: datetime, *, raw: typing.Literal[True], csu_id: str | None = None
    ) -> abc.Sequence[GearCheckout]: ...
    def get_active_checkouts_before(
        self,
        time: datetime,
        *,
        raw: bool = False,
        csu_id: str | None = None,
    ):
        statement = sa.select(GearCheckout).where(
            GearCheckout.returned_time.is_(None),
            GearCheckout.checkout_time < time,
        )

        if csu_id is not None:
            statement = statement.where(GearCheckout.csu_id == csu_id)

        checkouts = self._db.session.scalars(statement).all()
        if raw:
            return checkouts
        else:
            return [GearCheckoutDTO.model_validate(checkout) for checkout in checkouts]

    @typing.overload
    def get_all_active_checkouts(
        self, *, include_mappings: typing.Literal[False], order_by_time: bool = False
    ) -> list[GearCheckoutDTO]: ...

    @typing.overload
    def get_all_active_checkouts(
        self,
        *,
        include_mappings: typing.Literal[True],
        order_by_time: bool = False,
    ) -> list[MappedGearCheckoutDTO]: ...

    def get_all_active_checkouts(
        self,
        *,
        include_mappings: bool = False,
        order_by_time: bool = False,
    ) -> list[GearCheckoutDTO] | list[MappedGearCheckoutDTO]:
        statement = sa.select(GearCheckout).where(GearCheckout.returned_time.is_(None))

        if order_by_time:
            statement = statement.order_by(GearCheckout.checkout_time)
        if include_mappings:
            statement = statement.options(so.joinedload(GearCheckout.student))

        checkouts = self._db.session.scalars(statement).all()

        dto = MappedGearCheckoutDTO if include_mappings else GearCheckoutDTO

        return [dto.model_validate(checkout) for checkout in checkouts]

    def return_checkout(self, checkout_id: int | str, *, to_eod=False):
        checkout = self.get_by_checkout_id(checkout_id, raw=True)
        if checkout is None:
            return None

        self._return_checkout(checkout, to_eod=to_eod)
        self._db.session.commit()

        return GearCheckoutDTO.model_validate(checkout)

    def _return_checkout(
        self,
        checkout: GearCheckout,
        *,
        to_eod: bool = False,
    ):
        if to_eod:
            local_datetime = to_eastern_datetime(checkout.checkout_time)
            checkout.returned_time = set_end_of_day(local_datetime.date())
        else:
            checkout.returned_time = utc_now()

    def close_previous_day_checkouts(self, *, csu_id: str | None = None):
        checkouts = self.get_active_checkouts_before(
            utc_start_of_today(), csu_id=csu_id, raw=True
        )

        for checkout in checkouts:
            self._return_checkout(checkout, to_eod=True)
        self._db.session.commit()
