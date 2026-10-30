import datetime

import sqlalchemy as sa
import sqlalchemy.orm as so

from app import db
from config import EASTERN


def _to_eastern_datetime(value: datetime.datetime):
    if value.tzinfo is None:
        value = value.replace(tzinfo=datetime.UTC)

    return value.astimezone(EASTERN)


def _set_end_of_day(timestamp: datetime.date):
    """Return 5 PM Eastern on the timestamp's local date, in UTC."""
    return datetime.datetime.combine(
        timestamp,
        datetime.time(17, 0),
        tzinfo=EASTERN,
    ).astimezone(datetime.UTC)


def _to_eastern_strftime(value: datetime.datetime):
    """Returns datetime in EST formatted as YYYY-MM-DD HH MM SS AM/PM"""
    return _to_eastern_datetime(value).strftime('%Y-%m-%d %I:%M %p')


# IDEA: Can create Mixin class that adds csu_id column as foreignkey
class Student(db.Model):
    __tablename__ = 'students'

    csu_id: so.Mapped[str] = so.mapped_column(sa.String(8), primary_key=True)
    scan_id: so.Mapped[str] = so.mapped_column(
        sa.String(8),
        index=True,
        unique=True,
    )
    full_name: so.Mapped[str] = so.mapped_column(sa.String(128), index=True)
    # FEATURE: Make a Majors and Minors model and connect with many to many relationship
    major: so.Mapped[str] = so.mapped_column(
        sa.String(64),
    )
    grade_level: so.Mapped[str] = so.mapped_column(sa.String(16))

    visit_records: so.WriteOnlyMapped['Visit'] = so.relationship(
        back_populates='student', cascade='all, delete-orphan'
    )
    gear_checkout_records: so.WriteOnlyMapped['GearCheckout'] = so.relationship(
        back_populates='student', cascade='all, delete-orphan'
    )

    @so.validates('full_name')
    def validate_full_name(self, key: str, value: str):
        return value.title()

    def __repr__(self) -> str:
        return f'<Student {self.csu_id}: {self.full_name}>'


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
        sa.ForeignKey(Student.csu_id),
        index=True,
    )
    check_in_time: so.Mapped[datetime.datetime] = so.mapped_column(
        default=lambda: datetime.datetime.now(datetime.UTC)
    )
    checkout_time: so.Mapped[datetime.datetime] = so.mapped_column(
        nullable=True, default=None
    )

    student: so.Mapped[Student] = so.relationship(back_populates='visit_records')

    @property
    def day_of_week(self):
        return _to_eastern_datetime(self.check_in_time).strftime('%A')

    @property
    def week_number(self):
        return int(_to_eastern_datetime(self.check_in_time).strftime('%W'))

    @property
    def month_str(self):
        return _to_eastern_datetime(self.check_in_time).strftime('%Y-%m')

    @property
    def is_checked_out(self) -> bool:
        return self.checkout_time is not None

    def set_checkout_time(self, *, to_eod=False):
        if to_eod:
            local_datetime = _to_eastern_datetime(self.check_in_time)
            self.checkout_time = _set_end_of_day(local_datetime.date())
        else:
            self.checkout_time = datetime.datetime.now(datetime.UTC)

    def __repr__(self) -> str:
        return f'<Attendance {self.visit_id}: Student {self.csu_id} at {self.check_in_time}> UTC'


class GearCheckout(db.Model):
    __tablename__ = 'gear_checkouts'

    checkout_id: so.Mapped[int] = so.mapped_column(primary_key=True)
    csu_id: so.Mapped[str] = so.mapped_column(
        sa.ForeignKey(Student.csu_id),
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

    student: so.Mapped[Student] = so.relationship(
        back_populates='gear_checkout_records'
    )

    @property
    def is_returned(self) -> bool:
        return self.returned_time is not None

    def set_return_time(self, *, to_eod=False):
        if to_eod:
            local_date = _to_eastern_datetime(self.checkout_time)
            self.returned_time = _set_end_of_day(local_date.date())
        else:
            self.returned_time = datetime.datetime.now(datetime.UTC)

    def __repr__(self) -> str:
        return f'<GearCheckout {self.checkout_id}: Student {self.csu_id} at {self.checkout_time} UTC>'
