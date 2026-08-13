"""
Cálculo de fechas límite de liquidación — portado tal cual de la app
Streamlit (app/seguimiento/db.py::calcular_fechas_liquidacion), misma regla
de negocio, sin cambios:

  Voluntaria/mutuo acuerdo : fecha_fin_convenio + 4 meses      (notificar 10 días antes)
  Unilateral (admón.)      : voluntaria + 2 meses = +6 meses   (notificar 10 días antes)
  Judicial                 : unilateral + 2 años = +2 años 6m  (notificar 2 meses antes)

El conteo inicia el día SIGUIENTE a fecha_fin_convenio, ya que ese día
todavía corresponde a la etapa de ejecución, no de liquidación.
"""
import calendar
from datetime import date, timedelta
from typing import Optional, Tuple


def _add_months(source_date: date, months: int) -> Optional[date]:
    if source_date is None:
        return None
    month_index = source_date.month - 1 + months
    year = source_date.year + month_index // 12
    month = month_index % 12 + 1
    day = min(source_date.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def calcular_fechas_liquidacion(
    fecha_fin_convenio: Optional[date],
) -> Tuple[Optional[date], Optional[date], Optional[date]]:
    """Retorna (fecha_limite_voluntaria, fecha_limite_unilateral, fecha_limite_judicial)."""
    if not fecha_fin_convenio:
        return None, None, None
    inicio_liquidacion = fecha_fin_convenio + timedelta(days=1)
    voluntaria = _add_months(inicio_liquidacion, 4)
    unilateral = _add_months(voluntaria, 2)
    judicial = _add_months(unilateral, 24)
    return voluntaria, unilateral, judicial
