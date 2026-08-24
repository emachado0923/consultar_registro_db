"""
Modelos de respuesta para el nuevo módulo de reportes de inversión y
beneficios (dentro del aplicativo de Consulta + Tablero, NO de Seguimiento).
 
Fuente de datos: analitica_fondos.mc_final (confirmado con Migue) — una fila
por documento+periodo (clave "docperiodo"), con 3 columnas de valor neto
pagado ese periodo para ese estudiante:
  - mat_n:       matrícula
  - der_comp_n:  derechos complementarios
  - ajust_n:     ajuste/apoyo 1.5 SMMLV (lo que Sapiencia le da a las IES
                 distritales para completar el valor de la matrícula hasta
                 1.5 SMMLV en las que no lo superen — nada que ver con la
                 tabla `reintegros`, que es un concepto distinto)
 
"Beneficios" = cantidad de filas (docperiodo) que cumplen el filtro.
"Beneficiarios" = cantidad de documentos ÚNICOS (una persona que aparece en
varios periodos solo cuenta una vez) — confirmado con Migue.
"""
from typing import List
from pydantic import BaseModel
 
 
class ResumenInversion(BaseModel):
    matricula: float
    complementarios: float
    ajuste: float
    total: float
    beneficios: int
    beneficiarios: int
 
 
class GrupoInversion(BaseModel):
    clave: str
    matricula: float
    complementarios: float
    ajuste: float
    total: float
    beneficios: int
    beneficiarios: int
 
 
class ReporteInversionResponse(BaseModel):
    resumen: ResumenInversion
    # Desglose por IES — respeta los filtros de período/año, pero NO el de
    # IES (así el frontend siempre tiene el ranking completo entre IES para
    # graficar, sin importar cuál esté seleccionada en el filtro).
    por_ies: List[GrupoInversion]
    # Desglose por período — respeta los filtros de IES/año, pero NO el de
    # período (para poder graficar la tendencia histórica completa).
    por_periodo: List[GrupoInversion]
    opciones_ies: List[str]
    opciones_periodo: List[str]
    opciones_anio: List[str]