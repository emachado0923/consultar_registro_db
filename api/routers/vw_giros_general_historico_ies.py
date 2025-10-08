from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from api.core.database import get_session_dtf_financiera
from api.models.vw_giros_general_historico_ies import VwGirosGeneralHistoricoIes

router = APIRouter()

@router.get("/")
def obtener_vista_giros(
    skip: int = 0,
    limit: int = 100,
    documento: str = None,
    estado: str = None,
    fondo: str = None,
    ies: str = None,
    db: Session = Depends(get_session_dtf_financiera)
):
    try:
        statement = select(VwGirosGeneralHistoricoIes)
        
        # Aplicar filtros
        if documento:
            statement = statement.where(VwGirosGeneralHistoricoIes.documento.contains(documento))
        if estado:
            statement = statement.where(VwGirosGeneralHistoricoIes.estado == estado)
        if fondo:
            statement = statement.where(VwGirosGeneralHistoricoIes.fondo.contains(fondo))
        if ies:
            statement = statement.where(VwGirosGeneralHistoricoIes.ies.contains(ies))
        
        # Aplicar paginación
        statement = statement.offset(skip).limit(limit)
        
        resultados = db.exec(statement).all()
        return resultados
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al consultar vista: {str(e)}")

@router.get("/documento/{documento}")
def obtener_por_documento(
    documento: str, 
    db: Session = Depends(get_session_dtf_financiera)
):
    try:
        statement = select(VwGirosGeneralHistoricoIes).where(VwGirosGeneralHistoricoIes.documento == documento)
        resultado = db.exec(statement).first()
        
        if not resultado:
            raise HTTPException(status_code=404, detail="Registro no encontrado")
        return resultado
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al consultar: {str(e)}")

@router.get("/estadisticas/resumen")
def obtener_estadisticas(db: Session = Depends(get_session_dtf_financiera)):
    try:
        # Conteo por estado
        statement = select(VwGirosGeneralHistoricoIes.estado).distinct()
        estados = db.exec(statement).all()
        
        resumen = {
            "total_estados": len(estados),
            "estados_disponibles": estados,
            "total_registros": db.exec(select(VwGirosGeneralHistoricoIes)).all().__len__()
        }
        return resumen
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener estadísticas: {str(e)}")