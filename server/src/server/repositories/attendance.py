import typing
from datetime import UTC, datetime, timedelta

import sqlalchemy as sa
import sqlalchemy.orm as so

from server.models.student import Student
from server.models.visit import Visit
from server.schemas.attendance import ActiveVisitDTO, VisitsListDTO
from server.utils.dates import (
    set_end_of_day,
    to_eastern_datetime,
    utc_now,
    utc_start_of_today,
)

if typing.TYPE_CHECKING:
    from flask_sqlalchemy import SQLAlchemy


class AttendanceRepository:
    def __init__(self, db: 'SQLAlchemy'):
        self._db = db

    # FIXME: use active=True param instead of assuming user wants active only
    def get_active_visit(self, csu_id: str):
        return self._db.session.scalar(
            sa.select(Visit).where(
                Visit.csu_id == csu_id,
                Visit.checkout_time.is_(None),
            )
        )

    def get_active_visits_before(self, csu_id: str, start_of_today: datetime):
        return self._db.session.scalars(
            sa.select(Visit)
            .where(
                Visit.csu_id == csu_id,
                Visit.check_in_time < start_of_today,
                Visit.checkout_time.is_(None),
            )
            .options(so.joinedload(Visit.student))
        ).all()

    def get_visits_in_range(
        self, start_time: datetime, end_time: datetime, *, only_active: bool = False
    ):
        # rows = self._db.session.execute(
        #     sa.select(
        #         Student.csu_id,
        #         Student.scan_id,
        #         Student.full_name,
        #     )
        #     .join(Student, Visit.csu_id == Student.csu_id)
        #     .where(
        #         Visit.check_in_time >= start_time,
        #         Visit.check_in_time <= end_time,
        #         Visit.checkout_time.is_(None),
        #     )
        #     .group_by(
        #         Student.csu_id,
        #         Student.scan_id,
        #         Student.full_name,
        #     )
        #     .order_by(sa.func.min(Visit.check_in_time))
        # ).all()

        # return [ActiveStudentDTO.model_validate(row) for row in rows]
        # TODO: Make this a decorator to check all date params for being utc
        if (
            start_time.tzinfo is None
            or start_time.utcoffset() != timedelta(0)
            or end_time.tzinfo is None
            or end_time.utcoffset() != timedelta(0)
        ):
            raise ValueError('Datetime must be UTC-aware')

        statement = (
            sa.select(Visit)
            .where(
                Visit.check_in_time >= start_time,
                Visit.check_in_time < end_time,
            )
            .options(so.joinedload(Visit.student))
            .order_by(Visit.check_in_time.desc())
        )

        if only_active is True:
            statement = statement.where(Visit.checkout_time.is_(None))

        return VisitsListDTO.model_validate(self._db.session.scalars(statement).all())

    # def get_todays_active_visits(self):
    #     start_time = utc_start_of_today()
    #     end_time = start_time + timedelta(days=1)

    #     return self.get_active_visits_in_range(start_time, end_time)

    def create(self, csu_id: str):
        self._db.session.add(Visit(csu_id=csu_id))
        self._db.session.commit()

    def check_out(self, visit: Visit, *, to_eod=False):
        # visit.set_checkout_time(to_eod=True)
        if to_eod:
            local_datetime = to_eastern_datetime(visit.check_in_time)
            visit.checkout_time = set_end_of_day(local_datetime.date())
        else:
            visit.checkout_time = utc_now()

        self._db.session.commit()
