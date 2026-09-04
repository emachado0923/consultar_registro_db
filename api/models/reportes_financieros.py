"""
Modelos de respuesta para el nuevo módulo "Información Financiera" (tercera
tarjeta del selector de apps, junto a Consulta+Tablero y Seguimiento
Convenios MC).

Fuentes:
  - convenios_seg_proceso_mc: valor total del contrato (columna `valor`,
    confirmado con Migue que ya cubre "valor total"), adiciones_recursos
    (modificaciones al contrato), fechas de inicio/fin (para "% ejecución
    tiempo").
  - convenio_ejecucion_financiera_mc: ejecución por período que envía el
    financiero. "valor ejecutado" = SUM(valor_pagado) (confirmado con
    Migue: lo que realmente salió de caja, no el CDP reservado ni el valor
    conciliado con el MEN). "valor proyectado" = SUM(valor_proyectado_periodo)
    — a diferencia del intento anterior (una columna en convenios_seg_proceso_mc,
    ya eliminada), el valor proyectado varía POR PERÍODO, así que a nivel de
    convenio se suma across todos sus períodos.

Campos que NO se guardan en ninguna tabla porque son fórmulas de Excel
recalculables, no dato real — se calculan aquí mismo, al vuelo, cada vez que
se pide el reporte:
  - pct_ejecucion_tiempo: días transcurridos / días totales del convenio
    (usa CURRENT_DATE, no una fecha congelada).
  - pct_ejecucion_valor y valor_no_ejecutado: en el Excel del financiero son
    fórmulas POR PERÍODO, contra el VALOR DE CDP de ese período (no contra
    el valor total del contrato) — confirmado leyendo las fórmulas reales
    del archivo: `% EJECUCIÓN (VALOR) = VALOR PAGADO / VALOR DE CDP` y
    `VALOR NO EJECUTADO = VALOR DE CDP - VALOR PAGADO`. `PeriodoFinanciero`
    replica exactamente esa fórmula. A nivel de convenio (agregando todos
    sus períodos) el Excel no tiene un equivalente — se definió con Migue
    usar el mismo criterio (CDP como base), sumando el CDP de todos los
    períodos con datos: `pct_ejecucion_valor = SUM(valor_pagado) /
    SUM(valor_cdp)`, `valor_no_ejecutado = SUM(valor_cdp) - SUM(valor_pagado)`.
    Antes de esta corrección, el % a nivel de convenio se calculaba contra
    `valor_total` (el valor total del contrato) — daba números mucho más
    bajos que el Excel porque comparaba lo pagado contra el contrato
    completo en vez de contra lo efectivamente presupuestado (CDP) hasta el
    momento.
"""
from typing import List, Optional

from pydantic import BaseModel


class ConvenioFinanciero(BaseModel):
    convenio_id: int
    codigo: str
    ies_nombre: str
    ies_sigla: Optional[str] = None
    periodo_academico: str
    estado: str

    valor_total: float
    adiciones_recursos: float
    valor_cdp: float  # SUM(valor_cdp) de los períodos con datos — base del % de ejecución (valor)
    valor_ejecutado: float
    valor_proyectado: float
    valor_no_ejecutado: float  # valor_cdp - valor_ejecutado (antes: valor_total - valor_ejecutado)
    pct_ejecucion_valor: Optional[float] = None  # valor_ejecutado / valor_cdp; None si valor_cdp es 0
    pct_ejecucion_tiempo: Optional[float] = None  # None si faltan fecha_inicio/fecha_fin


class PeriodoFinanciero(BaseModel):
    """Detalle de ejecución financiera de un convenio, por período —
    convenio_periodos_seg_mc LEFT JOIN convenio_ejecucion_financiera_mc, así
    que un período sin datos del financiero todavía aparece igual, con los
    campos de ejecución en None en vez de desaparecer de la lista."""
    periodo: str
    numero_rp: Optional[str] = None
    numero_cdp: Optional[str] = None
    valor_cdp: Optional[float] = None
    estudiantes_postulados: Optional[int] = None
    estudiantes_conciliados: Optional[int] = None
    valor_conciliado: Optional[float] = None
    valor_pagado_matricula: Optional[float] = None
    valor_pagado_complementarios: Optional[float] = None
    valor_pagado_ajuste: Optional[float] = None
    valor_pagado: Optional[float] = None
    valor_proyectado_periodo: Optional[float] = None
    valor_no_ejecutado: Optional[float] = None  # = valor_cdp - valor_pagado (fórmula exacta del excel)
    pct_ejecucion_valor: Optional[float] = None  # = valor_pagado / valor_cdp (fórmula exacta del excel)


class ResumenFinanciero(BaseModel):
    valor_total: float
    valor_cdp: float
    valor_ejecutado: float
    valor_proyectado: float
    valor_no_ejecutado: float
    pct_ejecucion_valor: Optional[float] = None
    convenios: int


class ReporteFinancieroResponse(BaseModel):
    resumen: ResumenFinanciero
    convenios: List[ConvenioFinanciero]
    opciones_ies: List[str]
    opciones_convenio: List[str]
