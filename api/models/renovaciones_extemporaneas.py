from datetime import date, datetime
from sqlmodel import SQLModel, Field
from sqlalchemy import text


class RenovacionesExtemporaneas(SQLModel, table=True):
    __tablename__ = "renovaciones_extemporaneas"
    id: int | None = Field(default=None, primary_key=True)
    documento: str
    periodo: str
    fecha_inicio_renovacion: date
    fecha_fin_renovacion: date
    codigo_fondo_activacion: str
    radicado_pqrs: str
    responsable_activacion: str
    fecha_registro: datetime | None = Field(
        default=None,
        nullable=False,
        sa_column_kwargs={
            "server_default": text("CURRENT_TIMESTAMP"),
            "onupdate": text("CURRENT_TIMESTAMP"),
        },
    )


class RenovacionesExtemporaneasCreate(SQLModel):
    documento: str
    periodo: str
    fecha_inicio_renovacion: date
    fecha_fin_renovacion: date
    codigo_fondo_activacion: str
    radicado_pqrs: str


class RenovacionesExtemporaneasUpdate(SQLModel):
    documento: str | None = None
    periodo: str | None = None
    fecha_inicio_renovacion: date | None = None
    fecha_fin_renovacion: date | None = None
    codigo_fondo_activacion: str | None = None
    radicado_pqrs: str | None = None
    responsable_activacion: str | None = None
