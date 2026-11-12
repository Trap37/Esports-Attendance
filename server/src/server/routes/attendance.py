from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from server.dependencies import get_attendance_service
from server.schemas.attendance import (
    ActiveStudentDTO,
    ScanResponse,
    StudentScanDTO,
    StudentsListResponse,
)
from server.utils.errors import format_pydantic_validation_errors

bp = Blueprint('attendance', __name__)


@bp.post('/scan')
def scan():
    try:
        student_scan = StudentScanDTO.model_validate(
            request.get_json(silent=True) or {}
        )
    except ValidationError as e:
        errors = format_pydantic_validation_errors(e)
        # return jsonify({'error': 'csu_id required'}), 400
        return jsonify({'errors': errors}), 400

    service = get_attendance_service()
    result = service.process_scan(student_scan.scan_id)
    # FIXME: Javascript needs updated to comply with new pydantic schema
    return jsonify(ScanResponse.from_result(result).model_dump(mode='json'))


@bp.get('/today')
def attendance_today():
    service = get_attendance_service()
    result = service.get_todays_attendance()
    response = StudentsListResponse.model_construct(
        students=[
            ActiveStudentDTO.model_validate(visit.student) for visit in result.root
        ]
    )
    return jsonify(response.model_dump(mode='json'))
