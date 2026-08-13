from typing import Any, Dict, Optional

from pydantic import BaseModel


class InfoPersonalMCResponse(BaseModel):
    """Respuesta de /matricula-cero/tablero/info-personal — equivalente a
    tablero_mc.py::_cargar_info_personal, para el período más reciente
    diligenciado por el documento."""
    encontrado: bool
    periodo_label: Optional[str] = None
    datos: Optional[Dict[str, Any]] = None
