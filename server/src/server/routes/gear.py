from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from server.dependencies import get_gear_checkout_service
from server.schemas.gear import (
    ActiveCheckoutsCountResult,
    ActiveGearCheckoutsResult,
    CreateGearCheckoutRequest,
    GearCheckoutResult,
    GearCheckoutReturnRequest,
)
from server.schemas.responses import ErrorDetail, ErrorResponse, SuccessResponse
from server.utils.errors import (
    ActiveCheckoutExistsError,
    CheckoutNotFoundError,
    StudentNotFoundError,
)

bp = Blueprint('gear', __name__)


@bp.get('/stats')
def gear_stats():
    service = get_gear_checkout_service()

    result = service.get_gear_stats()

    response = SuccessResponse[ActiveCheckoutsCountResult](
        message='Gear checkout statistics retrieved successfully.',
        data=result,
    )

    return jsonify(response.model_dump(mode='json'))


@bp.get('/checkouts')
def gear_checkouts():
    service = get_gear_checkout_service()

    result = service.get_active_checkouts()

    response = SuccessResponse[ActiveGearCheckoutsResult](
        message='Active gear checkouts retrieved successfully.',
        data=result,
    )

    return jsonify(response.model_dump(mode='json'))


@bp.post('/checkout')
def gear_checkout():
    try:
        data = CreateGearCheckoutRequest.model_validate(
            request.get_json(silent=True) or {}
        )
    except ValidationError as e:
        return jsonify(
            ErrorResponse(
                message='Invalid checkout request.',
                error=ErrorDetail(code='INVALID_REQUEST'),
            )
            .include_error_details(e)
            .model_dump(mode='json')
        ), 400

    try:
        service = get_gear_checkout_service()

        result = service.checkout(data)
    except (StudentNotFoundError, ActiveCheckoutExistsError) as e:
        return jsonify(
            ErrorResponse(message=str(e), error=ErrorDetail(code=e.code)).model_dump(
                mode='json'
            ),
            e.status_code,
        )

    response = SuccessResponse[GearCheckoutResult](
        message='Gear checked out successfully.', data=result
    )

    return jsonify(response.model_dump(mode='json')), 201


@bp.post('/return/<int:checkout_id>')
def gear_return(checkout_id: int):
    try:
        data = request.get_json(silent=True) or {}
        data['checkout_id'] = checkout_id
        data = GearCheckoutReturnRequest.model_validate(data)
    except ValidationError as e:
        return jsonify(
            ErrorResponse(
                message='Invalid return request',
                error=ErrorDetail(code='INVALID_REQUEST'),
            )
            .include_error_details(e)
            .model_dump(mode='json')
        )

    try:
        service = get_gear_checkout_service()

        result = service.return_gear(data)
    except CheckoutNotFoundError as e:
        return jsonify(
            ErrorResponse(message=str(e), error=ErrorDetail(code=e.code)).model_dump(
                mode='json'
            ),
            e.status_code,
        )

    response = SuccessResponse[None](
        message='Gear returned successfully.',
    )

    return jsonify(response.model_dump(mode='json'))
