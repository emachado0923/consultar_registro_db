from sqlmodel import create_engine, Session
from .config import CONVOCATORIA_DB_URL, ANALITICA_DB_URL, DTF_FINANCIERA_DB_URL

engine_analitica = create_engine(ANALITICA_DB_URL, pool_pre_ping=True)
engine_convocatoria = create_engine(CONVOCATORIA_DB_URL, pool_pre_ping=True)
engine_dtf_financiera = create_engine(DTF_FINANCIERA_DB_URL, pool_pre_ping=True)

# Expose a session dependency factory

def get_session_analitica():
    with Session(engine_analitica) as session:
        yield session

def get_session_convocatoria():
    with Session(engine_convocatoria) as session:
        yield session

def get_session_dtf_financiera():  # ← NUEVA FUNCIÓN
    with Session(engine_dtf_financiera) as session:
        yield session