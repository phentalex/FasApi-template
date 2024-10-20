from typing import Optional

from pydantic import BaseModel


class HellowRequest(BaseModel):
    names: list[str]

class OpenAlexRequest(BaseModel):
    ids: list[str]