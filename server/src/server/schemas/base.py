from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class BaseDTO(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        str_min_length=1,
        from_attributes=True,
    )


class BaseResult(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        str_min_length=1,
        from_attributes=True,
    )


class BaseResponse(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra='forbid',
        str_min_length=1,
        from_attributes=True,
    )
