import typing

import sqlalchemy as sa
import sqlalchemy.orm as so

from server.extensions import db

if typing.TYPE_CHECKING:
    from server.models.gear import GearCheckout
    from server.models.visit import Visit


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
