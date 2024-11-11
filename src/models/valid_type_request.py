from typing import Optional

from pydantic import BaseModel


class HellowRequest(BaseModel):
    names: list[str]

class OpenAlexRequest(BaseModel):
    ids: list[str]

class WorkRequest(BaseModel):
    work_ids: list[str]