from typing import Annotated, Any, Dict, List, Optional


from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select, distinct
from api.core.database import get_session_dtf_financiera
from api.models.vw_giros_general_historico_ies import VwGirosGeneralHistoricoIes

from .auth import get_current_user

router = APIRouter(tags=["Vista Giros General Historico IES"])

@router.get("/", summary="Obtener todos los registros", description="Retorna todos los registros de la vista con paginación y filtros")
def obtener_vista_giros(
    skip: int = 0,
    limit: int = 100,
    documento: str = Query(None, description="Filtrar por documento"),
    estado: str = Query(None, description="Filtrar por estado"),
    fondo: str = Query(None, description="Filtrar por fondo"),
    ies: str = Query(None, description="Filtrar por IES"),
    db: Session = Depends(get_session_dtf_financiera),
    _: Dict[str, Any] = Depends(get_current_user)
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

@router.get("/documento/{documento}/periodo-academico/{periodo_academico}", summary="Buscar por documento y periodo académico", description="Retorna registros específicos por documento y periodo académico")
def obtener_por_documento_periodo_academico(
    documento: str,
    periodo_academico: str,
    db: Session = Depends(get_session_dtf_financiera),
    _: Dict[str, Any] = Depends(get_current_user)
):
    try:
        statement = select(VwGirosGeneralHistoricoIes).where(
            VwGirosGeneralHistoricoIes.documento == documento,
            VwGirosGeneralHistoricoIes.periodo_academico == periodo_academico
        )
        resultados = db.exec(statement).all()
        
        if not resultados:
            raise HTTPException(
                status_code=404, 
                detail=f"No se encontraron registros para documento {documento} y periodo académico {periodo_academico}"
            )
        return resultados
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al consultar: {str(e)}")


from sqlalchemy import text

@router.get("/filtros-completo/", summary="Consulta por convocatoria, fondo, documento y periodo académico (opcional)", description="Retorna registros filtrados por convocatoria, fondo, documento y periodo académico (opcional)")
def consultar_por_filtros_avanzados(
    convocatoria: str = Query(..., description="Nombre de la convocatoria (requerido)"),
    fondo: str = Query(..., description="Nombre del fondo (requerido)"),
    documento: str = Query(..., description="Número de documento (requerido)"),
    periodo_academico: str = Query(None, description="Periodo académico (opcional)"),
    db: Session = Depends(get_session_dtf_financiera),
    _: Dict[str, Any] = Depends(get_current_user)
):
    try:
        # Construir query SQL directo
        query_base = """
            SELECT * FROM vw_giros_general_historico_ies 
            WHERE convocatoria = :convocatoria 
            AND fondo = :fondo 
            AND documento = :documento
        """
        params = {
            "convocatoria": convocatoria,
            "fondo": fondo,
            "documento": documento
        }
        
        if periodo_academico:
            query_base += " AND periodo_academico = :periodo_academico"
            params["periodo_academico"] = periodo_academico
        
        query = text(query_base)
        resultados = db.exec(query, params).all()
        resultados_dict = [dict(row._mapping) for row in resultados]
        
        if not resultados_dict:
            if periodo_academico:
                detail_msg = f"No se encontraron registros para convocatoria '{convocatoria}', fondo '{fondo}', documento '{documento}' y periodo académico '{periodo_academico}'"
            else:
                detail_msg = f"No se encontraron registros para convocatoria '{convocatoria}', fondo '{fondo}' y documento '{documento}'"
            
            raise HTTPException(status_code=404, detail=detail_msg)
            
        return {
            "filtros_aplicados": {
                "convocatoria": convocatoria,
                "fondo": fondo,
                "documento": documento,
                "periodo_academico": periodo_academico
            },
            "total_resultados": len(resultados_dict),
            "resultados": resultados_dict
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al consultar: {str(e)}")

@router.get("/resumen-documento/{documento}", tags=["Consulta"], summary="Consultar convocatorias y fondos de un beneficiario")
def consulta_convocatorias_fondos(
    documento: str, 
    db: Session = Depends(get_session_dtf_financiera),
    _: Dict[str, Any] = Depends(get_current_user)
):
    try:
        # Consulta usando SQLModel
        statement = select(
            VwGirosGeneralHistoricoIes.nombre,
            VwGirosGeneralHistoricoIes.convocatoria,
            VwGirosGeneralHistoricoIes.fondo
        ).where(
            VwGirosGeneralHistoricoIes.documento == documento
        ).distinct().order_by(VwGirosGeneralHistoricoIes.convocatoria)
        
        resultados = db.exec(statement).all()
        
        if not resultados:
            return {}
        
        # Convertir a la estructura deseada
        aggregated_result = {
            "nombre": resultados[0].nombre if resultados else "",
            "convocatoria": [r.convocatoria for r in resultados],
            "fondo": [r.fondo for r in resultados],
        }
        
        return aggregated_result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al consultar: {str(e)}")