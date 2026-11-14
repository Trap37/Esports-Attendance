from datetime import datetime
from typing import TYPE_CHECKING, Literal

import sqlalchemy as sa
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from server.models.student import Student
from server.schemas.students import ListStudentsResult, StudentDTO

if TYPE_CHECKING:
    from flask_sqlalchemy import SQLAlchemy


class StudentRepository:
    def __init__(self, db: 'SQLAlchemy'):
        self._db = db

    def get_by_scan_id(self, scan_id: str):
        student = self._db.session.scalar(
            sa.select(Student).where(Student.scan_id == scan_id)
        )

        if student is None:
            return None
        return StudentDTO.model_validate(student)

    def register(
        self,
        scan_id: str,
        csu_id: str,
        full_name: str,
        major: str,
        grade_level: Literal[
            'Freshman',
            'Sophomore',
            'Junior',
            'Senior',
            'Graduate',
        ],
    ):
        try:
            student = Student(
                csu_id=csu_id,
                scan_id=scan_id,
                full_name=full_name,
                major=major,
                grade_level=grade_level,
            )
            self._db.session.add(student)
            self._db.session.commit()
            return student
        except IntegrityError:
            self._db.session.rollback()
            return None

    def list_students(self, query=None):
        statement = sa.select(Student).order_by(sa.func.lower(Student.full_name))
        if query:
            pattern = f'%{query}%'
            statement = statement.where(
                sa.or_(
                    Student.full_name.ilike(pattern),
                    Student.csu_id.ilike(pattern),
                    Student.scan_id.ilike(pattern),
                )
            )

        return ListStudentsResult.model_validate(
            self._db.session.scalars(statement).all()
        )
        # return StudentListResult(
        #     students=[
        #         StudentDTO.model_validate(student)
        #         for student in self._db.session.scalars(statement).all()
        #     ]
        # )

    def update(self, scanner_code, scan_id, full_name, major, grade_level):
        student = self._db.session.scalar(
            sa.select(Student).where(Student.scan_id == scanner_code)
        )
        if student is None:
            return False
        else:
            student.scan_id = scan_id
            student.full_name = full_name
            student.major = major
            student.grade_level = grade_level
            self._db.session.commit()
            return True
