from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from server.dependencies import get_attendance_service
from server.schemas.attendance import (
    ActiveStudentsResponse,
    AttendanceHistoryResponse,
    AttendanceTodayResponse,
    ScanResponse,
    StudentScanDTO,
)
from server.schemas.responses import SuccessResponse
from server.schemas.types import DateRange
from server.utils.errors import depricated_format_pydantic_validation_errors

bp = Blueprint('attendance', __name__)


@bp.post('/scan')
def scan():
    try:
        student_scan = StudentScanDTO.model_validate(
            request.get_json(silent=True) or {}
        )
    except ValidationError as e:
        errors = depricated_format_pydantic_validation_errors(e)
        return jsonify({'errors': errors}), 400

    service = get_attendance_service()
    result = service.process_scan(student_scan.scan_id)
    return jsonify(ScanResponse.from_scan_result(result).model_dump(mode='json'))


@bp.get('/today')
def attendance_today():
    service = get_attendance_service()
    result = service.get_todays_attendance()
    # print(result.root)
    # print(AttendanceTodayResponse.from_visits(result).model_dump_json())
    return jsonify(AttendanceTodayResponse.from_visits(result).model_dump(mode='json'))


@bp.get('/history')
def attendance_history():
    try:
        date_range = DateRange.model_validate(
            {
                'start': (request.args.get('start', '')),
                'end': (request.args.get('end', '')),
            }
        )
    except ValidationError as e:
        errors = depricated_format_pydantic_validation_errors(e)
        return jsonify({'errors': errors}), 400

    service = get_attendance_service()
    result = service.get_attendance_in_range(date_range, include_mappings=True)

    return jsonify(
        AttendanceHistoryResponse.model_validate(
            {
                'start': date_range.start,
                'end': date_range.end,
                'rows': result,
            },
            from_attributes=True,
        ).model_dump(mode='json')
    )
    # return jsonify(
    #     {
    #         'start': date_range.start.isoformat(),
    #         'end': date_range.end.isoformat(),
    #         'count': len(rows),
    #         'rows': rows,
    #     }
    # )


@bp.get('/active')
def active_attendees():
    service = get_attendance_service()
    result = service.get_active_attendance()

    return jsonify(
        ActiveStudentsResponse.model_validate(
            {
                'students': result,
            }
        ).model_dump(mode='json')
    )
