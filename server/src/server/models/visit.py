import datetime
import typing

import sqlalchemy as sa
import sqlalchemy.orm as so

from server.extensions import db
from server.models.types import UTCDateTime
from server.utils.dates import set_end_of_day, to_eastern_datetime, utc_now

if typing.TYPE_CHECKING:
    from server.models.student import Student


class Visit(db.Model):
    __tablename__ = 'visits'
    # __table_args__ = (
    #     sa.Index(
    #         'uq_one_open_visit_per_student',
    #         'csu_id',
    #         unique=True,
    #         sqlite_where=sa.text('checkout_time IS NULL'),
    #     ),
    # )

    visit_id: so.Mapped[int] = so.mapped_column(primary_key=True)
    csu_id: so.Mapped[str] = so.mapped_column(
        sa.ForeignKey('students.csu_id'),
        index=True,
    )
    check_in_time: so.Mapped[datetime.datetime] = so.mapped_column(
        UTCDateTime, default=utc_now
    )
    checkout_time: so.Mapped[datetime.datetime] = so.mapped_column(
        UTCDateTime, nullable=True, default=None
    )

    student: so.Mapped['Student'] = so.relationship(back_populates='visit_records')

    @property
    def day_of_week(self):
        return to_eastern_datetime(self.check_in_time).strftime('%A')

    @property
    def week_number(self):
        return int(to_eastern_datetime(self.check_in_time).strftime('%W'))

    @property
    def month_str(self):
        return to_eastern_datetime(self.check_in_time).strftime('%Y-%m')

    @property
    def is_checked_out(self) -> bool:
        return self.checkout_time is not None

    # def set_checkout_time(self, *, to_eod=False):
    #     if to_eod:
    #         local_datetime = to_eastern_datetime(self.check_in_time)
    #         self.checkout_time = set_end_of_day(local_datetime.date())
    #     else:
    #         self.checkout_time = datetime.datetime.now(datetime.UTC)

    def __repr__(self) -> str:
        return f'<Attendance {self.visit_id}: Student {self.csu_id} at {self.check_in_time}> UTC'
