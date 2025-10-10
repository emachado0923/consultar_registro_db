from typing import Annotated, Any, Dict, List, Optional


from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select, distinct, text
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


from collections import defaultdict

@router.get("/filtros-completo/", summary="Consulta por convocatoria, fondo, documento y periodo académico (opcional)", description="Retorna registros agrupados por documento, convocatoria y fondo")
def consultar_por_filtros_avanzados(
    convocatoria: str = Query(..., description="Nombre de la convocatoria (requerido)"),
    fondo: str = Query(..., description="Nombre del fondo (requerido)"),
    documento: str = Query(..., description="Número de documento (requerido)"),
    periodo_academico: str = Query(None, description="Periodo académico (opcional)"),
    db: Session = Depends(get_session_dtf_financiera),
    _: Dict[str, Any] = Depends(get_current_user)
):
    try:
        # Usar SQLModel para construir la consulta
        statement = select(VwGirosGeneralHistoricoIes).where(
            VwGirosGeneralHistoricoIes.convocatoria == convocatoria,
            VwGirosGeneralHistoricoIes.fondo == fondo,
            VwGirosGeneralHistoricoIes.documento == documento
        )
        
        if periodo_academico:
            statement = statement.where(VwGirosGeneralHistoricoIes.periodo_academico == periodo_academico)
        
        # Ejecutar con db.execute (compilando el statement a SQL)
        compiled_statement = statement.compile(
            bind=db.get_bind(), 
            compile_kwargs={"literal_binds": True}
        )
        
        result = db.execute(text(str(compiled_statement)))
        rows = result.fetchall()
        
        # Convertir a diccionarios
        resultados_dict = []
        for row in rows:
            resultados_dict.append(dict(row._mapping))
        
        if not resultados_dict:
            if periodo_academico:
                detail_msg = f"No se encontraron registros para convocatoria '{convocatoria}', fondo '{fondo}', documento '{documento}' y periodo académico '{periodo_academico}'"
            else:
                detail_msg = f"No se encontraron registros para convocatoria '{convocatoria}', fondo '{fondo}' y documento '{documento}'"
            
            raise HTTPException(status_code=404, detail=detail_msg)
        
        # Agrupar los resultados por documento, convocatoria y fondo
        grupos = defaultdict(lambda: {
            "documento": None,
            "nombre": None,
            "convocatoria": None,
            "fondo": None,
            "periodos_academicos": [],
            "ies": [],
            "programas": [],
            "modalidades": [],
            "estados": [],
            "valores_pagar_matricula": [],  # NUEVO CAMPO
            "valores_pagar_sostenimiento": [],  # NUEVO CAMPO
            "valores_girar": [],
            "fechas_registro": [],
            "total_registros": 0
        })
        
        for registro in resultados_dict:
            # Crear clave única para el grupo
            clave = (registro["documento"], registro["convocatoria"], registro["fondo"])
            
            # Actualizar datos del grupo
            grupo = grupos[clave]
            grupo["documento"] = registro["documento"]
            grupo["nombre"] = registro["nombre"]
            grupo["convocatoria"] = registro["convocatoria"]
            grupo["fondo"] = registro["fondo"]
            
            # Agregar datos a los arrays
            if registro.get("periodo_academico"):
                grupo["periodos_academicos"].append(registro["periodo_academico"])
            
            if registro.get("ies"):
                grupo["ies"].append(registro["ies"])
            
            if registro.get("programa"):
                grupo["programas"].append(registro["programa"])
            
            if registro.get("modalidad"):
                grupo["modalidades"].append(registro["modalidad"])
            
            if registro.get("estado"):
                grupo["estados"].append(registro["estado"])
            
            # NUEVOS CAMPOS - agregados antes de valor_girar
            if registro.get("valor_pagar_matricula") is not None:
                grupo["valores_pagar_matricula"].append(registro["valor_pagar_matricula"])
            
            if registro.get("valor_pagar_sostenimiento") is not None:
                grupo["valores_pagar_sostenimiento"].append(registro["valor_pagar_sostenimiento"])
            
            if registro.get("valor_girar") is not None:
                grupo["valores_girar"].append(registro["valor_girar"])
            
            if registro.get("fecha_registro"):
                grupo["fechas_registro"].append(registro["fecha_registro"])
            
            grupo["total_registros"] += 1
        
        # Convertir a lista
        resultados_agrupados = list(grupos.values())
        
        return resultados_agrupados
        
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