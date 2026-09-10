"""
Lógica de mapeo: fila de excel de conciliación -> fila de la tabla mc_final.

Este módulo es una copia fiel (funciones puras, sin cambios de lógica de
negocio) de `mapping.py` del script de carga que Migue corre por fuera del
portal (main.py/mapping.py/db.py, no vive en ningún repo de este proyecto).
Se porta acá para que el nuevo endpoint POST
/matricula-cero/tablero/cargar-mc-final pueda ofrecer la MISMA carga desde
el portal (con previsualización), sin duplicar ni reinterpretar las reglas
de negocio — son las mismas funciones, con el mismo comportamiento
verificado.

IMPORTANTE — dos copias, un solo dueño de la lógica: mientras exista el
script aparte de Migue (para cargas manuales fuera del portal, si las
sigue necesitando), este archivo y ese `mapping.py` deben mantenerse
sincronizados a mano si la lógica de negocio cambia. No hay import
compartido entre los 2 porque viven en repos/entornos distintos.

Es puro (no toca la base de datos ni el sistema de archivos), para poder
probarlo fácilmente. `db_lookup_previous_mc` es la única función que
necesita datos externos (el histórico de mc_final) y se recibe como
parámetro (inyección de dependencia) para poder probar map_row() sin BD.
"""

import math
import unicodedata
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

# ---------------------------------------------------------------------------
# Constantes de negocio
# ---------------------------------------------------------------------------

IES_DISTRITALES = {"ITM", "PASCUAL", "COLMAYOR"}

MOTIVO_NO_BENEFICIARIO_DESCUENTO_GIRO = "No beneficiario con descuento de giro"

# Nombre de las columnas "de historial" que trae el propio archivo de
# conciliación (iguales en todas las IES, confirmado por Migue).
COL_DOCPERIODO_ULTIMO_MC = "DOCPERIODO_(ULTIMO_PERIODO_FINANCIADO)"
COL_ULTIMO_PERIODO_SI_MC = "NUEVO_O_ULTIMO_PERIODO_SI_MC"

# Columna de respaldo para valor_matricula_con_ajuste_15 cuando
# VALOR_CON_APOYO_1.5 viene como "NO APLICA".
COL_VALOR_MAT_COMPL_DESC = "VALOR_MATRICULA_COMPLEMENTARIOS_DESCUENTOS"

# Columna real de ajust_n; si no existe en el archivo (caso departamentales,
# confirmado en IU Digital), se guarda "0".
COL_NETO_PAGAR_AJUSTE = "NETO_PAGAR_AJUSTE_1.5"

VALOR_NO_APLICA = "NO APLICA"

# "No encontrado": no existe ninguna fila en mc_final con ese docperiodo (o
# hay 2+, ambiguo) -> problema de emparejamiento/formato, hay que revisar el
# docperiodo en sí. Si el docperiodo SÍ hizo match, se copia tal cual lo que
# haya en el histórico (valor o vacío/NULL), sin ningún placeholder.
# Ya en mayúsculas: normalize_row() normaliza TODOS los campos de la fila
# (incluido este) antes de devolverla, así que el valor real guardado en BD
# queda en mayúsculas. Se define así de una vez para que el router pueda
# comparar contra el mismo valor exacto que termina en la fila (para
# contarlas como "RENUEVA sin historial" en el resumen de previsualización).
PLACEHOLDER_NO_ENCONTRADO = "NO ENCONTRADO"


class FilaInvalidaError(Exception):
    """Se lanza cuando una fila no tiene los datos mínimos para procesarse."""


# ---------------------------------------------------------------------------
# Helpers de limpieza / casteo
# ---------------------------------------------------------------------------

def _is_blank(value):
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    return False


def to_text(value):
    """Convierte cualquier valor leído de excel a texto "limpio" para guardar
    en una columna VARCHAR/TEXT. None si la celda está vacía."""
    if _is_blank(value):
        return None
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, (int, float)):
        return str(value)
    return str(value).strip()


# Carácter "raro" (uso privado de Unicode, no aparece en datos reales) usado
# para proteger la Ñ/ñ mientras se le quitan las tildes al resto del texto.
_ENYE_PLACEHOLDER = ""


def normalize_text(value):
    """Mayúsculas y sin tildes/diacríticos, para dejar el dato "normalizado"
    antes de guardarlo en mc_final. None se queda en None (no se convierte
    en el string "NONE"). La Ñ/ñ SÍ se conserva (no se trata como una tilde
    a quitar)."""
    if value is None:
        return None
    text = str(value)
    # Excel/Windows a veces guarda la Ñ "descompuesta" (una N + un acento
    # combinante aparte) en vez de como un solo carácter. Se normaliza a
    # forma compuesta (NFC) ANTES de proteger la Ñ, para que la protección
    # de abajo la detecte sin importar cómo venía guardada en el archivo.
    text = unicodedata.normalize("NFC", text)
    text = text.replace("ñ", _ENYE_PLACEHOLDER).replace("Ñ", _ENYE_PLACEHOLDER)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.replace(_ENYE_PLACEHOLDER, "Ñ")
    return text.upper().strip()


def normalize_row(row):
    """Aplica normalize_text a todos los valores de la fila ya mapeada
    (mayúsculas, sin tildes). Se aplica al final, después de resolver toda
    la lógica de negocio (para no afectar comparaciones como grupo_ies)."""
    return {col: normalize_text(val) for col, val in row.items()}


def to_number(value, default=0.0):
    """Convierte a número para poder comparar/calcular. Si no se puede
    (ej. "NO APLICA", vacío, texto no numérico), devuelve `default`."""
    if _is_blank(value):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace("$", "").replace(",", "")
    try:
        return float(text)
    except ValueError:
        return default


def to_money_text(value):
    """Para columnas de valores en pesos (que en mc_final siempre deben
    quedar como enteros, sin decimales). El excel a veces muestra un número
    entero pero la celda en realidad tiene un decimal "parásito" (ej. por
    una fórmula: se ve "151896" pero el valor real es 151896.5) — eso hacía
    que se subiera con el .5 a la BD. Acá se redondea al entero más cercano,
    con el mismo criterio de Excel (0.5 siempre sube, no "redondeo bancario"
    de Python), para que la cifra en mc_final siempre coincida con lo que se
    ve/calcula en el excel de origen.

    Si el valor no es numérico (ej. "NO APLICA" en una columna que no aplica
    para departamentales), se deja tal cual, igual que to_text."""
    if _is_blank(value):
        return None
    if isinstance(value, (int, float)):
        numero = value
    else:
        limpio = str(value).strip().replace("$", "").replace(",", "")
        try:
            numero = float(limpio)
        except ValueError:
            return str(value).strip()
    try:
        entero = Decimal(str(numero)).to_integral_value(rounding=ROUND_HALF_UP)
    except InvalidOperation:
        return str(value).strip()
    return str(int(entero))


def to_int_or_none(value):
    """Intenta convertir un valor (posiblemente texto, posiblemente el
    placeholder 'No encontrado') a entero. Devuelve None si no se puede."""
    if _is_blank(value):
        return None
    try:
        return int(float(str(value).strip()))
    except (ValueError, TypeError):
        return None


def clean_documento(value):
    """DOCUMENTO puede venir como int64 de pandas, float, o texto (acá,
    directo de openpyxl). Nunca se debe perder un cero a la izquierda si
    viniera como texto."""
    if _is_blank(value):
        return None
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, int):
        return str(value)
    return str(value).strip()


def build_docperiodo(documento, periodo):
    return f"{documento}{periodo}"


def map_grupo_ies(ies_value):
    ies_clean = (ies_value or "").strip()
    if ies_clean in IES_DISTRITALES:
        return "DISTRITAL"
    return "DEPARTAMENTAL"


def map_si_no_estricto(value):
    """Para columnas que en mc_final deben quedar SOLO en 'SI' o 'NO', pero
    en el excel de origen pueden traer otros valores (ej. "No aplica" para
    quienes no tuvieron PQRS). Queda en "SI" únicamente si el valor original
    es exactamente "SI" (sin importar mayúsculas/tildes); cualquier otro
    valor (NO, NO APLICA, vacío, etc.) queda en "NO"."""
    texto = normalize_text(to_text(value))
    return "SI" if texto == "SI" else "NO"


# ---------------------------------------------------------------------------
# Mapeo principal
# ---------------------------------------------------------------------------

def map_row(row, periodo, estado_col, motivo_col, fecha_cargue, db_lookup_previous_mc=None):
    """
    row: dict-like (una fila del excel de conciliación de UNA sola IES, ya
         convertida a dict columna->valor).
    periodo: string, ej. "2026-1".
    estado_col / motivo_col: nombres literales (varían por periodo) de las
         columnas "ESTADO_(RESULTADO_xx-x)" y "MOTIVO_ESTADO_xx-x".
    fecha_cargue: `datetime.date` — el día de esta carga (el frontend manda
         hoy por defecto). Se guarda tal cual en la columna `fecha_cargue`
         de mc_final, para "última actualización" del Tablero histórico.
         Se recibe como parámetro (no se calcula acá con `date.today()`)
         para que map_row() siga siendo una función pura y fácil de
         probar — el resultado depende solo de sus argumentos, nunca del
         reloj del sistema.
    db_lookup_previous_mc: función `docperiodo -> dict|None` que consulta
         mc_final y devuelve la fila anterior (con al menos semestre_ingreso,
         giros_proyectados_totales, giros_realizados) o None si no existe.
         Si se deja en None, cualquier caso RENUEVA cae directo a
         "No encontrado" (útil para pruebas sin BD).

    Devuelve un dict con exactamente las 40 columnas de mc_final (las 39 de
    siempre + `fecha_cargue`), listo para upsert, o lanza FilaInvalidaError
    si falta el documento.
    """
    documento = clean_documento(row.get("DOCUMENTO"))
    if not documento:
        raise FilaInvalidaError("Fila sin DOCUMENTO, se omite.")

    docperiodo = build_docperiodo(documento, periodo)

    ies_raw = to_text(row.get("IES"))
    grupo_ies = map_grupo_ies(ies_raw)

    nuevo_renueva = to_text(row.get("NUEVO_RENUEVA"))
    estado_semestral = to_text(row.get(estado_col))
    motivo_estado = to_text(row.get(motivo_col))
    es_mc = estado_semestral == "MC"

    # --- Historial para RENUEVA (semestre_ingreso, giros_proyectados_totales,
    #     giros_realizados) usando el docperiodo del último periodo en MC que
    #     ya trae calculado el propio archivo de conciliación. ---
    previous = None
    if nuevo_renueva == "RENUEVA":
        docperiodo_ultimo_mc = to_text(row.get(COL_DOCPERIODO_ULTIMO_MC))
        if docperiodo_ultimo_mc and db_lookup_previous_mc is not None:
            previous = db_lookup_previous_mc(docperiodo_ultimo_mc)

    def renueva_o_no_encontrado(campo):
        if previous is None:
            return PLACEHOLDER_NO_ENCONTRADO  # el docperiodo no hizo match en mc_final
        # El docperiodo sí hizo match: se copia tal cual lo que haya en ese
        # campo del histórico (si tiene valor, ese valor; si está vacío,
        # queda vacío/NULL también).
        return to_text(previous.get(campo))

    # --- semestre_ingreso ---
    if nuevo_renueva == "NUEVO":
        semestre_ingreso = to_text(row.get("N_SEMESTRE_ENCUENTRA"))
    elif nuevo_renueva == "RENUEVA":
        semestre_ingreso = renueva_o_no_encontrado("semestre_ingreso")
    else:
        semestre_ingreso = None

    # --- giros_proyectados_totales ---
    if nuevo_renueva == "NUEVO":
        if es_mc:
            sem_prog = to_int_or_none(row.get("N_SEMESTRES_PROGRAMA_ACTUAL"))
            sem_actual = to_int_or_none(row.get("N_SEMESTRE_ENCUENTRA"))
            if sem_prog is not None and sem_actual is not None:
                giros_proyectados_totales = str(sem_prog - sem_actual + 1)
            else:
                giros_proyectados_totales = None
        else:
            giros_proyectados_totales = None  # confirmado: NULL si NUEVO y no quedó en MC
    elif nuevo_renueva == "RENUEVA":
        giros_proyectados_totales = renueva_o_no_encontrado("giros_proyectados_totales")
    else:
        giros_proyectados_totales = None

    # --- giros_realizados ---
    if nuevo_renueva == "NUEVO":
        giros_realizados = "1" if es_mc else "0"
    elif nuevo_renueva == "RENUEVA":
        if previous is None:
            giros_realizados = PLACEHOLDER_NO_ENCONTRADO  # el docperiodo no hizo match
        else:
            prev_val = to_int_or_none(previous.get("giros_realizados"))
            if prev_val is not None:
                giros_realizados = str(prev_val + 1) if es_mc else str(prev_val)
            else:
                # El docperiodo sí hizo match. Si el campo estaba vacío en el
                # histórico, queda vacío (None) igual acá; si tenía un valor
                # no numérico, se copia tal cual (no se le puede sumar 1).
                giros_realizados = to_text(previous.get("giros_realizados"))
    else:
        giros_realizados = None

    # --- novedad / tipo_de_novedad ---
    if es_mc:
        novedad = nuevo_renueva
    else:
        if nuevo_renueva == "RENUEVA":
            if motivo_estado == MOTIVO_NO_BENEFICIARIO_DESCUENTO_GIRO:
                novedad = None
            else:
                novedad = "SUSPENSION"
        else:  # NUEVO u otro
            novedad = None

    if es_mc:
        tipo_de_novedad = None
    elif novedad == "SUSPENSION":
        tipo_de_novedad = "TEMPORAL"
    else:
        tipo_de_novedad = None

    # --- valor_matricula_con_ajuste_15 (con respaldo si "NO APLICA") ---
    valor_apoyo_15_raw = row.get("VALOR_CON_APOYO_1.5")
    valor_apoyo_15_texto = to_text(valor_apoyo_15_raw)
    if valor_apoyo_15_texto and valor_apoyo_15_texto.upper() == VALOR_NO_APLICA:
        valor_matricula_con_ajuste_15 = to_money_text(row.get(COL_VALOR_MAT_COMPL_DESC))
    else:
        valor_matricula_con_ajuste_15 = to_money_text(valor_apoyo_15_raw)

    # --- concurrencia / aporte_men (dependen de VALOR_MEN_FINAL) ---
    valor_men_final_num = to_number(row.get("VALOR_MEN_FINAL"))
    concurrencia = "SI" if (grupo_ies == "DISTRITAL" and valor_men_final_num > 0) else "NO"
    aporte_men = "1" if valor_men_final_num > 0 else "0"

    # --- ajust_n: columna NETO_PAGAR_AJUSTE_1.5 no existe en archivos
    #     departamentales (confirmado); si no está en el archivo, "0". ---
    if COL_NETO_PAGAR_AJUSTE in row:
        ajust_n = to_money_text(row.get(COL_NETO_PAGAR_AJUSTE))
        if ajust_n is None:
            ajust_n = "0"
    else:
        ajust_n = "0"

    result = {
        "documento": documento,
        "periodo": periodo,
        "docperiodo": docperiodo,
        "grupo_ies": grupo_ies,
        "ies": ies_raw,
        "programa": to_text(row.get("PROGRAMA_MATRICULADO_NORMALIZADO")),
        "snies": to_text(row.get("SNIES_PROGRAMA")),
        "nivel_de_formacion": to_text(row.get("NIVEL_FORMACION")),
        "promedio_academico_acumulado": to_text(row.get("PROM_ACADEMICO_ACUMULADO")),
        "creditos_aprobados_semestre_anterior": to_text(
            row.get("N_CREDITOS_APROBADOS_SEMESTRE_ANTERIOR_BALANCE_ACADEMICO")
        ),
        "creditos_matriculados_semestre_actual": to_text(
            row.get("N_CREDITOS_MATRICULADOS_SEMESTRE_ACTUAL")
        ),
        "semestre_actual": to_text(row.get("N_SEMESTRE_ENCUENTRA")),
        "semestre_ingreso": semestre_ingreso,
        "semestres_del_programa": to_text(row.get("N_SEMESTRES_PROGRAMA_ACTUAL")),
        "semestres_restantes": to_text(row.get("SEMESTRES_RESTANTES_PARA_SIGUIENTE_SEMESTRE")),
        "giros_restantes": to_text(row.get("SEMESTRES_RESTANTES_PARA_SIGUIENTE_SEMESTRE")),
        "giros_proyectados_totales": giros_proyectados_totales,
        "giros_realizados": giros_realizados,
        "estado_semestral": estado_semestral,
        "motivo_estado": motivo_estado,
        # motivo_estado_2 es tipo double en mc_final (y hoy está vacía en toda
        # la tabla) -> no puede guardar el texto "No aplica" que pedía el
        # mapeo original. Se deja en NULL para no romper el insert y quedar
        # igual de vacía que está hoy (confirmado con Migue).
        "motivo_estado_2": None,
        "novedad": novedad,
        "tipo_de_novedad": tipo_de_novedad,
        "valor_matricula_con_ajuste_15": valor_matricula_con_ajuste_15,
        "valor_total": to_money_text(row.get("VALOR_INICIAL_CONVENIO")),
        "valor_ajuste": to_money_text(row.get("VALOR_AJUSTE")),
        "valor_convenio": to_money_text(row.get("VALOR_FINAL_CONVENIO")),
        "concurrencia": concurrencia,
        "beneficiario_del_men": to_text(row.get("ES_BENEFICIARIO_MEN_FINAL")),
        "va_por_ciclo": map_si_no_estricto(row.get("PRIMERA_RENOVACION_CICLO")),
        "valor_mat": to_money_text(row.get("VALOR_MATRICULA")),
        "valor_der_comp": to_money_text(row.get("VALOR_DERECHOS_PECUNIARIOS_COMPLEMENTARIOS")),
        "valor_desc": to_money_text(row.get("VALOR_DESCUENTO_MATRICULA")),
        "val_mat_desc": to_money_text(row.get(COL_VALOR_MAT_COMPL_DESC)),
        "valor_men": to_money_text(row.get("VALOR_MEN_FINAL")),
        "aporte_men": aporte_men,
        "mat_n": to_money_text(row.get("NETO_PAGAR_MATRICULA")),
        "der_comp_n": to_money_text(row.get("NETO_PAGAR_DER_COMP")),
        "ajust_n": ajust_n,
    }

    # fecha_cargue se agrega DESPUÉS de normalize_row a propósito: es un
    # valor `date` de sistema (cuándo se cargó este lote), no un dato de
    # negocio que venga del excel — no tiene sentido pasarlo por
    # normalize_text (que es para texto tipo mayúsculas/tildes de datos de
    # la conciliación).
    mapped = normalize_row(result)
    mapped["fecha_cargue"] = fecha_cargue
    return mapped


# Orden exacto de columnas de la tabla mc_final (útil para el INSERT/UPDATE).
# `fecha_cargue` (columna nueva, ver
# sql/migraciones/2026-09_fecha_cargue_mc_final.sql) se agregó acá para que
# quede incluida automáticamente tanto al insertar filas nuevas como al
# actualizar filas existentes.
MC_FINAL_COLUMNS = [
    "documento", "periodo", "fecha_cargue", "docperiodo", "grupo_ies", "ies", "programa",
    "snies", "nivel_de_formacion", "promedio_academico_acumulado",
    "creditos_aprobados_semestre_anterior", "creditos_matriculados_semestre_actual",
    "semestre_actual", "semestre_ingreso", "semestres_del_programa",
    "semestres_restantes", "giros_restantes", "giros_proyectados_totales",
    "giros_realizados", "estado_semestral", "motivo_estado", "motivo_estado_2",
    "novedad", "tipo_de_novedad", "valor_matricula_con_ajuste_15", "valor_total",
    "valor_ajuste", "valor_convenio", "concurrencia", "beneficiario_del_men",
    "va_por_ciclo", "valor_mat", "valor_der_comp", "valor_desc", "val_mat_desc",
    "valor_men", "aporte_men", "mat_n", "der_comp_n", "ajust_n",
]

UPDATE_COLUMNS = [c for c in MC_FINAL_COLUMNS if c != "docperiodo"]


# ---------------------------------------------------------------------------
# Columnas que el EXCEL de conciliación (no la tabla mc_final) debe traer —
# a pedido de Migue: si falta alguna de estas, el endpoint de carga debe
# rechazar el archivo con un error claro (nombrando cuáles faltan) en vez de
# procesarlo con esa columna en blanco silenciosamente. No incluye
# estado_col/motivo_col (los nombres literales varían cada período — el
# router los valida aparte, con el nombre que el usuario indicó para esa
# carga) ni las 2 columnas que son opcionales A PROPÓSITO:
#   - SUBIR_A_BD (o el nombre que se configure): si el archivo no la trae,
#     simplemente no se excluye ninguna fila — nunca fue obligatoria.
#   - NETO_PAGAR_AJUSTE_1.5 (COL_NETO_PAGAR_AJUSTE): NO existe en los
#     archivos de IES departamentales (confirmado en IU Digital) — si falta,
#     ajust_n se guarda en "0"; exigirla rompería toda carga departamental.
# ---------------------------------------------------------------------------
COLUMNAS_ESPERADAS_MC_FINAL = [
    "DOCUMENTO",
    "IES",
    "NUEVO_RENUEVA",
    COL_DOCPERIODO_ULTIMO_MC,
    "N_SEMESTRE_ENCUENTRA",
    "N_SEMESTRES_PROGRAMA_ACTUAL",
    "VALOR_CON_APOYO_1.5",
    COL_VALOR_MAT_COMPL_DESC,
    "VALOR_MEN_FINAL",
    "ES_BENEFICIARIO_MEN_FINAL",
    "PRIMERA_RENOVACION_CICLO",
    "VALOR_MATRICULA",
    "VALOR_DERECHOS_PECUNIARIOS_COMPLEMENTARIOS",
    "VALOR_DESCUENTO_MATRICULA",
    "NETO_PAGAR_MATRICULA",
    "NETO_PAGAR_DER_COMP",
    "VALOR_INICIAL_CONVENIO",
    "VALOR_AJUSTE",
    "VALOR_FINAL_CONVENIO",
    "PROGRAMA_MATRICULADO_NORMALIZADO",
    "SNIES_PROGRAMA",
    "NIVEL_FORMACION",
    "PROM_ACADEMICO_ACUMULADO",
    "N_CREDITOS_APROBADOS_SEMESTRE_ANTERIOR_BALANCE_ACADEMICO",
    "N_CREDITOS_MATRICULADOS_SEMESTRE_ACTUAL",
    "SEMESTRES_RESTANTES_PARA_SIGUIENTE_SEMESTRE",
]
