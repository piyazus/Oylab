from pydantic import BaseModel, Field, conint
from pydantic import BaseModel, Field, conint
from typing import Annotated


class Breakdown(BaseModel):
    team:    Annotated[int, conint(ge=0, le=100)]
    market:  Annotated[int, conint(ge=0, le=100)]
    product: Annotated[int, conint(ge=0, le=100)]
    finance: Annotated[int, conint(ge=0, le=100)]
    design:  Annotated[int, conint(ge=0, le=100)]

class AnalyzeResponse(BaseModel):
    score:  Annotated[int, conint(ge=0, le=100)]
    breakdown: Breakdown
    recommendations: list[str] = Field(default_factory=list)

class ApiError(BaseModel):
    error: str

class AuthSignup(BaseModel):
    email: str
    password: str

class AuthLogin(BaseModel):
    email: str
    password: str
