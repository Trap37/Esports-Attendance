from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from pydantic_core import ErrorDetails

from server.schemas.base import BaseDTO, BaseResponse


class SuccessResponse[T](BaseResponse):
    success: Literal[True] = Field(True, init=False)
    message: str
    data: T | None = None


class ErrorDetail(BaseDTO):
    code: str
    details: list[ErrorDetails] | None = Field(None, init=False)


class ErrorResponse(BaseResponse):
    success: Literal[False] = Field(False, init=False)
    message: str
    error: ErrorDetail

    def include_error_details(self, e: ValidationError):
        self.error.details = [
            {
                'loc': error['loc'],
                'msg': error['msg'],
                'type': error['type'],
            }
            for error in e.errors()
        ]

        return self
