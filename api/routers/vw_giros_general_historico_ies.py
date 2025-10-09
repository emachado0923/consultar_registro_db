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
    
@router.get("/filtros-completo/", summary="Consulta por convocatoria, fondo, periodo académico y documento", description="Retorna registros filtrados por convocatoria, fondo, periodo académico y documento")
def consultar_por_filtros_avanzados(
    convocatoria: str = Query(..., description="Nombre de la convocatoria (requerido)"),
    fondo: str = Query(..., description="Nombre del fondo (requerido)"),
    periodo_academico: str = Query(..., description="Periodo académico (requerido)"),
    documento: str = Query(..., description="Número de documento (requerido)"),
    db: Session = Depends(get_session_dtf_financiera),
    _: Dict[str, Any] = Depends(get_current_user)
):
    try:
        statement = select(VwGirosGeneralHistoricoIes).where(
            VwGirosGeneralHistoricoIes.convocatoria == convocatoria,
            VwGirosGeneralHistoricoIes.fondo == fondo,
            VwGirosGeneralHistoricoIes.periodo_academico == periodo_academico,
            VwGirosGeneralHistoricoIes.documento == documento
        )
        
        resultados = db.exec(statement).all()
        
        if not resultados:
            raise HTTPException(
                status_code=404, 
                detail=f"No se encontraron registros para convocatoria '{convocatoria}', fondo '{fondo}', periodo académico '{periodo_academico}' y documento '{documento}'"
            )
            
        return {
            "filtros_aplicados": {
                "convocatoria": convocatoria,
                "fondo": fondo,
                "periodo_academico": periodo_academico,
                "documento": documento
            },
            "total_resultados": len(resultados),
            "resultados": resultados
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al consultar: {str(e)}")

@router.get("/info-documento-convocatoria/{documento}", summary="Resumen por documento", description="Retorna un resumen único por combinación de documento y convocatoria, mostrando solo nombre, convocatoria y fondo")
def obtener_resumen_por_documento(
    documento: str,
    db: Session = Depends(get_session_dtf_financiera),
    _: Dict[str, Any] = Depends(get_current_user)
):
    try:
        # Seleccionar solo las columnas específicas y usar distinct para evitar duplicados
        statement = select(
            VwGirosGeneralHistoricoIes.documento,
            VwGirosGeneralHistoricoIes.nombre,
            VwGirosGeneralHistoricoIes.convocatoria,
            VwGirosGeneralHistoricoIes.fondo
        ).where(
            VwGirosGeneralHistoricoIes.documento == documento
        ).distinct()  # Esto evita duplicados de documento+convocatoria
        
        resultados = db.exec(statement).all()
        
        if not resultados:
            raise HTTPException(
                status_code=404, 
                detail=f"No se encontraron registros para el documento {documento}"
            )
        
        # Convertir a formato de respuesta
        resumen = []
        for resultado in resultados:
            resumen.append({
                "documento": resultado.documento,
                "nombre": resultado.nombre,
                "convocatoria": resultado.convocatoria,
                "fondo": resultado.fondo
            })
            
        return {
            "documento": documento,
            "total_convocatorias": len(resumen),
            "resumen": resumen
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al consultar: {str(e)}")