"""
Modelos de respuesta para el nuevo módulo "Información Financiera" (tercera
tarjeta del selector de apps, junto a Consulta+Tablero y Seguimiento
Convenios MC).

Fuentes:
  - convenios_seg_proceso_mc: valor total del contrato (columna
    `valor_inicial`, renombrada por Migue — antes se llamaba `valor`;
    confirmado con Migue que ya cubre "valor total"), adiciones_recursos
    (modificaciones al contrato), fechas de inicio/fin (para "% ejecución
    tiempo"). El campo `valor_total` de la API/JSON no cambió de nombre,
    solo cambió de qué columna se lee (vía `AS valor` en el SELECT del
    router).
  - convenio_ejecucion_financiera_mc: ejecución por período que envía el
    financiero. "valor ejecutado" = SUM(valor_pagado) (confirmado con
    Migue: lo que realmente salió de caja, no el CDP reservado ni el valor
    conciliado con el MEN). "valor proyectado" = SUM(valor_proyectado_periodo)
    — a diferencia del intento anterior (una columna en convenios_seg_proceso_mc,
    ya eliminada), el valor proyectado varía POR PERÍODO, así que a nivel de
    convenio se suma across todos sus períodos.

valor_pagado_men ("Valor pagado por el MEN", columna nueva del excel
"VALOR PAGADO MEN") sigue el mismo patrón de valor_ejecutado: existe por
período (`PeriodoFinanciero`) y se agrega sumando across períodos tanto a
nivel de convenio (`ConvenioFinanciero`) como en el consolidado de la
selección (`ResumenFinanciero`) — a pedido de Migue, visible en los 3
niveles. `observaciones` (columna nueva "OBSERVACIONES") es texto libre
por período, sin agregación (no tiene sentido "sumar" observaciones) — solo
vive en `PeriodoFinanciero`.

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
from datetime import datetime
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
    valor_pagado_men: float  # SUM(valor_pagado_men) de los períodos con datos
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
    valor_pagado_men: Optional[float] = None
    valor_proyectado_periodo: Optional[float] = None
    valor_no_ejecutado: Optional[float] = None  # = valor_cdp - valor_pagado (fórmula exacta del excel)
    pct_ejecucion_valor: Optional[float] = None  # = valor_pagado / valor_cdp (fórmula exacta del excel)
    observaciones: Optional[str] = None


class ResumenFinanciero(BaseModel):
    valor_total: float
    valor_cdp: float
    valor_ejecutado: float
    valor_proyectado: float
    valor_pagado_men: float
    valor_no_ejecutado: float
    pct_ejecucion_valor: Optional[float] = None
    convenios: int


class ReporteFinancieroResponse(BaseModel):
    resumen: ResumenFinanciero
    convenios: List[ConvenioFinanciero]
    opciones_ies: List[str]
    opciones_convenio: List[str]
    # A pedido de Migue: filtro nuevo de período (además de IES/Convenio) —
    # facetado con el mismo criterio que los otros 2 (calculado contra las
    # OTRAS 2 dimensiones activas, nunca contra sí mismo). Ver
    # `_construir_where` y el nuevo parámetro `periodo` en /resumen.
    opciones_periodo: List[str]


class FilaCargaExcel(BaseModel):
    """Resultado de UNA fila del excel de ejecución financiera ("MC_Financiera")
    que sube el financiero — ver POST /reportes-financieros/cargar-excel.
    `estado` decide qué se hizo con la fila:
      - "ok": se validó sin problemas (o se aplicó, si `confirmar=true`).
      - "advertencia": se aplicó igual, pero hay algo que vale la pena que el
        financiero revise (ej. la IES del excel no coincide con la del
        convenio, o el valor de "adiciones de recursos" difiere entre filas
        del mismo convenio).
      - "error": la fila NO se aplicó (convenio_id o período no existen) —
        se necesita corregir el excel o crear el período primero en
        Administración > Convenios.

    `accion` dice qué va a pasar en convenio_ejecucion_financiera_mc si la
    fila se aplica (calculado contra el estado de la BD ANTES de esta carga
    — es el mismo tanto en la previsualización como al confirmar, no
    depende de `confirmar`): "crear" si ese convenio+período no tenía
    ejecución financiera todavía, "actualizar" si ya existía y se va a
    sobrescribir con los valores de este excel. None cuando la fila está en
    error (no se puede saber, y no se va a aplicar de todas formas)."""
    fila_excel: int  # número de fila tal cual se vería al abrir el excel (encabezado = fila 1)
    convenio_id: Optional[int] = None
    codigo: Optional[str] = None
    periodo: Optional[str] = None
    estado: str
    accion: Optional[str] = None  # "crear" | "actualizar" | None (si estado="error")
    mensajes: List[str]


class ResumenCargaExcel(BaseModel):
    confirmado: bool  # false = solo previsualización, no se escribió nada en la BD
    filas_leidas: int
    filas_aplicadas: int
    filas_con_advertencia: int
    filas_con_error: int
    convenios_afectados: int
    # Desglose de filas_aplicadas (o, en previsualización, de las filas que
    # SERÍAN aplicables) por tipo de acción — a pedido de Migue, para que se
    # vea de una si la carga va a pisar datos que ya existían.
    filas_nuevas: int
    filas_actualizadas: int


class CargaExcelResponse(BaseModel):
    resumen: ResumenCargaExcel
    filas: List[FilaCargaExcel]


class UltimaActualizacionResponse(BaseModel):
    """Ver GET /reportes-financieros/ultima-actualizacion — a pedido de
    Migue, para la tarjeta de "fecha de actualización" de cada módulo en el
    selector de apps. `fecha` = MAX(actualizado_en) de
    convenio_ejecucion_financiera_mc (ver migración
    2026-09_actualizado_en_ejecucion_financiera.sql) — None solo si la
    tabla está completamente vacía (nunca se ha cargado ningún excel)."""
    fecha: Optional[datetime] = None