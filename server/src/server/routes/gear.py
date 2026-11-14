from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from server.dependencies import get_gear_checkout_service
from server.schemas.gear import (
    ActiveCheckoutsCountResult,
    ActiveGearCheckoutsResult,
    CreateGearCheckoutRequest,
    GearCheckoutResult,
)
from server.schemas.responses import ErrorDetail, ErrorResponse, SuccessResponse
from server.utils.errors import ActiveCheckoutExistsError, StudentNotFoundError

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
            ).include_error_details(e)
        ), 400

    try:
        service = get_gear_checkout_service()

        result = service.checkout(data)
    except StudentNotFoundError as e:
        return jsonify(
            ErrorResponse(message=str(e), error=ErrorDetail(code=e.code)),
            e.status_code,
        )
    except ActiveCheckoutExistsError as e:
        return jsonify(
            ErrorResponse(message=str(e), error=ErrorDetail(code=e.code)),
            e.status_code,
        )

    response = SuccessResponse[GearCheckoutResult](
        message='Gear checked out successfully.', data=result
    )

    return jsonify(response.model_dump(mode='json')), 201


@bp.post('/return/<int:checkout_id>')
def gear_return(checkout_id: int):
    response = ...

    return jsonify(SuccessResponse[None])
