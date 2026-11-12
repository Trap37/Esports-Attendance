# TODO: Define DTOs for API inputs where validation is inconsistent.
# Use Pydantic.
# Start with student registration and gear checkout.
# Reuse existing Flask-WTF validation where appropriate;
# don't duplicate it just to follow a pattern.

import logging
import typing

from server.routes.attendance import bp as attendance_bp
from server.routes.students import bp as students_bp

if typing.TYPE_CHECKING:
    from flask import Flask


def register_blueprints(app: 'Flask'):
    app.register_blueprint(attendance_bp, url_prefix=f'/api/{attendance_bp.name}')
    app.register_blueprint(students_bp, url_prefix=f'/api/{students_bp.name}')
