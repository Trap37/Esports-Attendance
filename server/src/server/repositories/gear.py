import typing
from datetime import datetime

import sqlalchemy as sa

from server.models.gear import GearCheckout
from server.utils.dates import set_end_of_day, to_eastern_datetime, utc_now

if typing.TYPE_CHECKING:
    from flask_sqlalchemy import SQLAlchemy


class GearCheckoutRepository:
    def __init__(self, db: 'SQLAlchemy'):
        self._db = db

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
