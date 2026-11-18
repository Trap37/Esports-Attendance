import typing
from collections import abc
from datetime import UTC, datetime, timedelta

import sqlalchemy as sa
import sqlalchemy.orm as so
from sqlalchemy.exc import IntegrityError

from server.models.student import Student
from server.models.visit import Visit
from server.schemas.attendance import MappedVisitDTO, ScanEvent, VisitDTO
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

    def create(self, csu_id: str):
        try:
            visit = Visit(csu_id=csu_id)

            self._db.session.add(visit)
            self._db.session.commit()

            return visit
        except IntegrityError:
            self._db.session.rollback()

    def get_by_csu_id(self, csu_id: str):
        statement = sa.select(Visit).where(
            Visit.csu_id == csu_id,
            Visit.checkout_time.is_(None),
        )

        visit = self._db.session.scalar(statement)

        return VisitDTO.model_validate(visit)

    @typing.overload
    def get_active_visits_before(
        self,
        time: datetime,
        *,
        raw: typing.Literal[False] = False,
        csu_id: str | None = None,
    ) -> list[VisitDTO]: ...
    @typing.overload
    def get_active_visits_before(
        self,
        time: datetime,
        *,
        raw: typing.Literal[True],
        csu_id: str | None = None,
    ) -> abc.Sequence[Visit]: ...
    def get_active_visits_before(
        self, time: datetime, *, raw: bool = False, csu_id: str | None = None
    ):
        statement = sa.select(Visit).where(
            Visit.checkout_time.is_(None),
            Visit.check_in_time < time,
        )

        if csu_id:
            statement.where(Visit.csu_id == csu_id)
        # .options(so.joinedload(Visit.student))

        visits = self._db.session.scalars(statement).all()

        if raw:
            return visits
        else:
            return [VisitDTO.model_validate(visit) for visit in visits]

    def get_visits_in_range(
        self,
        start_time: datetime,
        end_time: datetime,
        *,
        only_active: bool = False,
        order_by_time: bool = False,
        include_mappings: bool = False,
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
        statement = sa.select(Visit).where(
            Visit.check_in_time >= start_time,
            Visit.check_in_time < end_time,
        )

        if only_active:
            statement = statement.where(Visit.checkout_time.is_(None))
        if order_by_time:
            statement = statement.order_by(Visit.check_in_time.desc())
        if include_mappings:
            statement.options(so.joinedload(Visit.student))

        visits = self._db.session.scalars(statement).all()

        dto = MappedVisitDTO if include_mappings else VisitDTO

        return [dto.model_validate(visit) for visit in visits]

    # def get_todays_active_visits(self):
    #     start_time = utc_start_of_today()
    #     end_time = start_time + timedelta(days=1)

    #     return self.get_active_visits_in_range(start_time, end_time)

    def check_out(self, visit_id: str | int, *, to_eod=False):
        visit = self._db.session.scalar(
            sa.select(Visit).where(
                Visit.visit_id == visit_id,
                Visit.checkout_time.is_(None),
            )
        )
        if visit is None:
            return None

        self._check_out(visit, to_eod=to_eod)

        self._db.session.commit()

        return VisitDTO.model_validate(visit)

    def _check_out(self, visit: Visit, *, to_eod: bool = False):
        if to_eod:
            local_datetime = to_eastern_datetime(visit.check_in_time)
            visit.checkout_time = set_end_of_day(local_datetime.date())
        else:
            visit.checkout_time = utc_now()

    def close_previous_day_visits(self, *, csu_id: str | None = None):
        visits = self.get_active_visits_before(
            utc_start_of_today(), csu_id=csu_id, raw=True
        )

        for visit in visits:
            self._check_out(visit, to_eod=True)

        self._db.session.commit()
