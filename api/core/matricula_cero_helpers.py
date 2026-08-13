"""
Helpers de negocio de Matrícula Cero — portados tal cual de
app/pages/tablero_mc.py del portal Streamlit (_label_periodo y sus
constantes de anclaje), para que el tablero nuevo en la API use la misma
lógica ya validada.
"""
from typing import Optional

# El campo "periodo" en convocatoria_sapiencia.matricula_cero es un entero
# secuencial. Periodo CONFIRMADO como el primero del programa: 10 = 2023-2.
# A partir de ese ancla, cada periodo siguiente suma 1 por semestre
# (alternando 1/2 cada año), sin saltos.
PRIMER_PERIODO = 10
PRIMER_ANIO = 2023
PRIMER_SEMESTRE = 2

# Excepciones puntuales: si algún día aparece un periodo que NO siga el
# patrón consecutivo (un salto real en la numeración), fuérzalo aquí con
# "periodo: 'AAAA-S'" y tendrá prioridad sobre el cálculo automático.
PERIODOS_CONOCIDOS = {
    10: "2023-2",
    16: "2026-2",
}


def calcular_periodo_label(periodo_raw) -> Optional[str]:
    """
    Devuelve 'N (AAAA-S)' para un código de periodo de
    convocatoria_sapiencia.matricula_cero. Réplica exacta de
    tablero_mc.py::_label_periodo.
    """
    if periodo_raw is None:
        return None
    texto = str(periodo_raw).strip()
    if texto in ("", "—"):
        return None

    try:
        periodo_num = int(float(texto))
    except (ValueError, TypeError):
        return texto

    if periodo_num in PERIODOS_CONOCIDOS:
        return f"{periodo_num} ({PERIODOS_CONOCIDOS[periodo_num]})"

    if periodo_num > PRIMER_PERIODO:
        semestres_totales_base = PRIMER_ANIO * 2 + (PRIMER_SEMESTRE - 1)
        pasos = periodo_num - PRIMER_PERIODO
        semestres_totales = semestres_totales_base + pasos
        anio = semestres_totales // 2
        semestre = (semestres_totales % 2) + 1
        return f"{periodo_num} ({anio}-{semestre})"

    # Periodo anterior al primero del programa: no debería ocurrir.
    return str(periodo_num)
