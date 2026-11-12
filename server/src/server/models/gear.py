import datetime
import typing

import sqlalchemy as sa
import sqlalchemy.orm as so

from server.extensions import db
from server.utils.dates import set_end_of_day, to_eastern_datetime

if typing.TYPE_CHECKING:
    from server.models.visit import Student


class GearCheckout(db.Model):
    __tablename__ = 'gear_checkouts'

    checkout_id: so.Mapped[int] = so.mapped_column(primary_key=True)
    csu_id: so.Mapped[str] = so.mapped_column(
        sa.ForeignKey('students.csu_id'),
        index=True,
    )
    keyboard: so.Mapped[bool] = so.mapped_column(default=False)
    mouse: so.Mapped[bool] = so.mapped_column(default=False)
    mousepad: so.Mapped[bool] = so.mapped_column(default=False)
    headset: so.Mapped[bool] = so.mapped_column(default=False)
    checkout_time: so.Mapped[datetime.datetime] = so.mapped_column(
        default=lambda: datetime.datetime.now(datetime.UTC), index=True
    )
    returned_time: so.Mapped[datetime.datetime | None] = so.mapped_column(
        nullable=True, index=True
    )

    student: so.Mapped['Student'] = so.relationship(
        back_populates='gear_checkout_records'
    )

    @property
    def is_returned(self) -> bool:
        return self.returned_time is not None

    # def set_return_time(self, *, to_eod=False):
    #     if to_eod:
    #         local_date = to_eastern_datetime(self.checkout_time)
    #         self.returned_time = set_end_of_day(local_date.date())
    #     else:
    #         self.returned_time = datetime.datetime.now(datetime.UTC)

    def __repr__(self) -> str:
        return f'<GearCheckout {self.checkout_id}: Student {self.csu_id} at {self.checkout_time} UTC>'
