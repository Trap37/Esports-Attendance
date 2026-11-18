from datetime import datetime
from typing import TYPE_CHECKING, Literal

import sqlalchemy as sa
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from server.models.student import Student
from server.schemas.students import (
    ListStudentsResult,
    RegisterStudentRequest,
    StudentDTO,
    StudentUpdateRequest,
)

if TYPE_CHECKING:
    from flask_sqlalchemy import SQLAlchemy


class StudentRepository:
    def __init__(self, db: 'SQLAlchemy'):
        self._db = db

    def register(self, request: RegisterStudentRequest):
        try:
            student = Student(
                csu_id=request.csu_id,
                scan_id=request.scan_id,
                full_name=request.full_name,
                major=request.major,
                grade_level=request.grade_level,
            )
            self._db.session.add(student)
            self._db.session.commit()
            return StudentDTO.model_validate(student)
        except IntegrityError:
            self._db.session.rollback()
            # XXX: Translate known database constraint violations to meaningful exceptions

    def exists_by_csu_id(self, csu_id: str):
        return bool(
            self._db.session.scalar(sa.select(Student).where(Student.csu_id == csu_id))
        )

    def exists_by_scan_id(self, scan_id: str):
        return bool(
            self._db.session.scalar(
                sa.select(Student).where(Student.scan_id == scan_id)
            )
        )

    def get_by_scan_id(self, scan_id: str):
        student = self._get_by_scan_id(scan_id)
        if student is None:
            return None

        return StudentDTO.model_validate(student)

    def _get_by_scan_id(self, scan_id: str):
        return self._db.session.scalar(
            sa.select(Student).where(Student.scan_id == scan_id)
        )

    def list_students(self, *, query: str | None = None):
        statement = sa.select(Student).order_by(sa.func.lower(Student.full_name))
        if query is not None:
            pattern = f'%{query}%'
            statement = statement.where(
                sa.or_(
                    Student.full_name.ilike(pattern),
                    Student.csu_id.ilike(pattern),
                    Student.scan_id.ilike(pattern),
                )
            )

        students = self._db.session.scalars(statement).all()

        return [StudentDTO.model_validate(student) for student in students]
        # return StudentListResult(
        #     students=[
        #         StudentDTO.model_validate(student)
        #         for student in self._db.session.scalars(statement).all()
        #     ]
        # )

    def update(self, request: StudentUpdateRequest):
        student = self._get_by_scan_id(request.scanner_code)
        if student is None:
            return None

        try:
            student.scan_id = request.scan_id
            student.full_name = request.full_name
            student.major = request.major
            student.grade_level = request.grade_level

            self._db.session.commit()

            return StudentDTO.model_validate(student)
        except IntegrityError:
            self._db.session.rollback()
