# This is a generated file, do not edit

from typing import List

import pydantic


class Time(pydantic.BaseModel):
    sec: pydantic.conint(ge=-2147483648, le=2147483647) = 0  # int32
    nanosec: pydantic.conint(ge=0, le=4294967295) = 0  # uint32

    class Config:
        orm_mode = True
        schema_extra = {
            "required": [
                "sec",
                "nanosec",
            ],
        }


# # Time indicates a specific point in time, relative to a clock's 0 point.
#
# # The seconds component, valid over all int32 values.
# int32 sec
#
# # The nanoseconds component, valid in the range [0, 10e9).
# uint32 nanosec
