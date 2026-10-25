from datetime import UTC, datetime, time

import sqlalchemy as sa
import sqlalchemy.orm as so

from app import db
from config import EASTERN


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
    # FIXME: This should ideally be a list of majors
    major: so.Mapped[str] = so.mapped_column(
        sa.String(64),
    )
    # XXX: Student grade level is no longer optional
    grade_level: so.Mapped[str] = so.mapped_column(sa.String(16))

    visit_records: so.WriteOnlyMapped['Visit'] = so.relationship(
        back_populates='student', cascade='all, delete-orphan'
    )
    gear_checkout_records: so.WriteOnlyMapped['GearCheckout'] = so.relationship(
        back_populates='student', cascade='all, delete-orphan'
    )

    # def __repr__(self) -> str:
    #     return f'<Student {self.csu_id}: {self.full_name}>'


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
    check_in_time: so.Mapped[datetime] = so.mapped_column(
        default=lambda: datetime.now(UTC)
    )
    checkout_time: so.Mapped[datetime] = so.mapped_column(nullable=True, default=None)

    student: so.Mapped[Student] = so.relationship(back_populates='visit_records')

    @property
    def day_of_week(self):
        return self.check_in_time.strftime('%A')

    @property
    def week_number(self):
        return int(self.check_in_time.strftime('%W'))

    @property
    def month_str(self):
        return self.check_in_time.strftime('%Y-%m')

    @property
    def is_checked_out(self) -> bool:
        return self.checkout_time is not None

    def set_checkout_time(self, *, to_eod=False):
        if to_eod:
            check_in = self.check_in_time

            # SQLite may return a naive datetime; treat it as UTC.
            if check_in.tzinfo is None:
                check_in = check_in.replace(tzinfo=UTC)

            local_date = check_in.astimezone(EASTERN).date()

            self.checkout_time = datetime.combine(
                local_date,
                time(17, 0),
                tzinfo=EASTERN,
            ).astimezone(UTC)
        else:
            self.checkout_time = datetime.now(UTC)

    # def __repr__(self) -> str:
    #     return f'<Attendance {self.id}: Student {self.csu_id} at {self.check_in_time}>'


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
    checkout_time: so.Mapped[datetime] = so.mapped_column(
        default=lambda: datetime.now(UTC), index=True
    )
    returned_time: so.Mapped[datetime | None] = so.mapped_column(
        nullable=True, index=True
    )

    student: so.Mapped[Student] = so.relationship(
        back_populates='gear_checkout_records'
    )

    @property
    def is_returned(self) -> bool:
        return self.returned_time is not None

    def set_return_time(self):
        self.returned_time = datetime.now(UTC)
