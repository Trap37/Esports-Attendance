from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from server.dependencies import get_attendance_service
from server.schemas.attendance import (
    ActiveStudentsResult,
    AttendanceHistoryResult,
    CurrentAttendanceResult,
    DateRange,
    ScanResult,
    StudentScanRequest,
)
from server.schemas.responses import ErrorDetail, ErrorResponse, SuccessResponse

bp = Blueprint('attendance', __name__)


@bp.post('/scan')
def scan():
    try:
        data = StudentScanRequest.model_validate(request.get_json(silent=True) or {})
    except ValidationError as e:
        return jsonify(
            ErrorResponse(
                message='Invalid scan event request.',
                error=ErrorDetail(code='INVALID_REQUEST'),
            )
            .include_error_details(e)
            .model_dump(mode='json')
        ), 400

    service = get_attendance_service()

    result = service.process_scan(data)

    response = SuccessResponse[ScanResult](
        message='Student scan event successful.', data=result
    )

    return jsonify(response.model_dump(mode='json'))


@bp.get('/today')
def attendance_today():
    service = get_attendance_service()

    result = service.get_todays_attendance()

    response = SuccessResponse[CurrentAttendanceResult](
        message='Current attending students retrieval successful', data=result
    )

    return jsonify(response.model_dump(mode='json'))


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
        return jsonify(
            ErrorResponse(
                message='Invalid history request.',
                error=ErrorDetail(code='INVALID_REQUEST'),
            )
            .include_error_details(e)
            .model_dump(mode='json')
        ), 400

    service = get_attendance_service()

    result = service.get_attendance_in_range(date_range, include_mappings=True)

    response = SuccessResponse[AttendanceHistoryResult](
        message='Attendance history retrieval successful.', data=result
    )

    return jsonify(response.model_dump(mode='json'))


@bp.get('/active')
def active_attendees():
    service = get_attendance_service()

    result = service.get_active_attendance()

    response = SuccessResponse[list[ActiveStudentsResult]](
        message='Active visits retrieval successful.', data=result
    )

    return jsonify(response.model_dump(mode='json'))
