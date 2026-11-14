from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from server.dependencies import get_students_service
from server.schemas.students import (
    ListStudentsResponse,
    StudentDTO,
    StudentRegistrationError,
    StudentRetrievalError,
    StudentUpdate,
    StudentUpdateError,
)
from server.utils.errors import depricated_format_pydantic_validation_errors

bp = Blueprint('students', __name__)


@bp.get('/')
def students_list():
    q = (request.args.get('q') or '').strip() or None

    service = get_students_service()
    result = service.list_students(q)
    return jsonify(
        ListStudentsResponse.model_validate({'students': result.root}).model_dump(
            mode='json'
        )
    )


@bp.get('/<scan_id>')
def students_get(scan_id: str):
    service = get_students_service()
    result = service.get_student(scan_id)
    if isinstance(result, StudentRetrievalError):
        return jsonify(result.model_dump(mode='json')), 404
    return jsonify(result.model_dump(mode='json'))


@bp.post('/register')
def register():
    try:
        data = StudentDTO.model_validate(request.get_json(silent=True) or {})
    except ValidationError as e:
        errors = depricated_format_pydantic_validation_errors(e)
        return jsonify(
            {
                'error': 'Invalid registration details',
                'details': errors,
            }
        ), 400

    service = get_students_service()
    result = service.register_student(data)
    if isinstance(result, StudentRegistrationError):
        return jsonify(result.model_dump(mode='json')), 409
    return jsonify(result), 201


@bp.put('/<scanner_code>')
def students_update(scanner_code: str):
    try:
        r = request.get_json(silent=True) or {}
        r['scanner_code'] = scanner_code
        data = StudentUpdate.model_validate(r)
    except ValidationError as e:
        errors = depricated_format_pydantic_validation_errors(e)
        return jsonify(
            {
                'error': 'Invalid registration details',
                'details': errors,
            }
        )

    service = get_students_service()
    result = service.update_student(data)
    if isinstance(result, StudentUpdateError):
        return jsonify(result.model_dump(mode='json')), 404
    return jsonify(result)
