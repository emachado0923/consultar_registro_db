from typing import Any, Dict, List
from pydantic import BaseModel


class ConsultaResponse(BaseModel):
    count: int
    results: List[Dict[str, Any]]
