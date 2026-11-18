from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from server.dependencies import get_students_service
from server.schemas.responses import ErrorDetail, ErrorResponse, SuccessResponse
from server.schemas.students import (
    GetStudentResult,
    ListStudentsRequest,
    ListStudentsResult,
    RegisterStudentRequest,
    RegisterStudentResult,
    StudentDTO,
    StudentUpdateRequest,
)
from server.utils.errors import (
    DuplicateScanIDError,
    StudentAlreadyExistsError,
    StudentNotFoundError,
)

bp = Blueprint('students', __name__)


@bp.get('/')
def students_list():
    try:
        data = ListStudentsRequest.model_validate(request.get_json(silent=True) or {})
    except ValidationError as e:
        return jsonify(
            ErrorResponse(
                message='Invalid checkout request.',
                error=ErrorDetail(code='INVALID_REQUEST'),
            )
            .include_error_details(e)
            .model_dump(mode='json')
        ), 400

    service = get_students_service()

    result = service.list_students(data.query)

    response = SuccessResponse[ListStudentsResult](
        message='Active students retrieved successfully.', data=result
    )

    return jsonify(response.model_dump(mode='json'))


@bp.get('/<scan_id>')
def students_get(scan_id: str):
    try:
        service = get_students_service()

        result = service.get_student(scan_id)
    except StudentNotFoundError as e:
        return jsonify(
            ErrorResponse(message=str(e), error=ErrorDetail(code=e.code)).model_dump(
                mode='json'
            ),
            e.status_code,
        )

    response = SuccessResponse[GetStudentResult](
        message='Student retrieved successfully.', data=result
    )

    return jsonify(response.model_dump(mode='json'))


@bp.post('/register')
def register():
    try:
        data = RegisterStudentRequest.model_validate(
            request.get_json(silent=True) or {}
        )
    except ValidationError as e:
        return jsonify(
            ErrorResponse(
                message='Invalid registration details.',
                error=ErrorDetail(code='INVALID_REQUEST'),
            )
            .include_error_details(e)
            .model_dump(mode='json')
        ), 400

    try:
        service = get_students_service()

        result = service.register_student(data)
    except (StudentAlreadyExistsError, DuplicateScanIDError) as e:
        return jsonify(
            ErrorResponse(message=str(e), error=ErrorDetail(code=e.code)).model_dump(
                mode='json'
            ),
            e.status_code,
        )

    response = SuccessResponse[RegisterStudentResult](
        message='Student registered successfully.', data=result
    )

    return jsonify(response.model_dump(mode='json')), 201


@bp.put('/<scanner_code>')
def students_update(scanner_code: str):
    try:
        r = request.get_json(silent=True) or {}
        r['scanner_code'] = scanner_code
        data = StudentUpdateRequest.model_validate(r)
    except ValidationError as e:
        return jsonify(
            ErrorResponse(
                message='Invalid update request.',
                error=ErrorDetail(code='INVALID_REQUEST'),
            )
            .include_error_details(e)
            .model_dump(mode='json')
        ), 400

    try:
        service = get_students_service()

        result = service.update_student(data)
    except StudentNotFoundError as e:
        return jsonify(
            ErrorResponse(message=str(e), error=ErrorDetail(code=e.code)).model_dump(
                mode='json'
            ),
            e.status_code,
        )

    return jsonify(result.model_dump(mode='json'))
