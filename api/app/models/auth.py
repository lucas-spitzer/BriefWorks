from dataclasses import dataclass

from pydantic import BaseModel


@dataclass(frozen=True)
class CurrentUser:
    id: str
    email: str
    role: str


class CurrentUserResponse(BaseModel):
    id: str
    email: str
    role: str
