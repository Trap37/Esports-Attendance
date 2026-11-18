# TODO: Register a Flask error handler
# @app.errorhandler(AppError)
# def handle_app_error(error: AppError):
#     return jsonify(
#         ErrorResponse(
#             message=str(error),
#             error=ErrorDetail(code=error.code),
#         ).model_dump()
#     ), error.status_code


class AppError(Exception):
    """Base exception for all app operations."""

    code: str
    status_code: int


class StudentError(AppError):
    """Base exception for student operations"""


class StudentNotFoundError(StudentError):
    code = 'STUDENT_NOT_FOUND'
    status_code = 404

    def __init__(self, scan_id: str):
        self.scan_id = scan_id
        super().__init__(f'No student found with scan ID: {scan_id}')


class StudentAlreadyExistsError(StudentError):
    code = 'STUDENT_ALREADY_EXISTS'
    status_code = 409

    def __init__(self, csu_id: str) -> None:
        super().__init__(f'A student with csu_id "{csu_id}" already exists')


class DuplicateScanIDError(StudentError):
    code = 'DUPLICATE_SCAN_ID'
    status_code = 409

    def __init__(self, scan_id: str) -> None:
        super().__init__(f'Scan ID "{scan_id}" is already in use')


class GearCheckoutError(AppError):
    """Base exception for gear checkout operations."""


class CheckoutNotFoundError(GearCheckoutError):
    code = 'CHECKOUT_NOT_FOUND'
    status_code = 404

    def __init__(self, checkout_id: str) -> None:
        super().__init__(f'No Checkout found with ID: {checkout_id}')


class ActiveCheckoutExistsError(GearCheckoutError):
    code = 'ACTIVE_CHECKOUT_EXISTS'
    status_code = 409

    def __init__(self, csu_id: str):
        self.csu_id = csu_id
        super().__init__(f'Student {csu_id} already has an active checkout.')
