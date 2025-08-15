from pydantic import BaseModel


class ChangeLogRequest(BaseModel):
    tipo_cambio: str
    documento_beneficiario_cambio: str
