# Portal Matrícula Cero — Frontend (React)

Primera pieza de la migración del portal Streamlit a FastAPI + React (ver
`Plan_Migracion_FastAPI_React.md`). **Esta carpeta es SOLO el frontend** —
no aloja ningún backend propio. Consume por HTTP los endpoints ya
construidos en `consultar_registro_db-main` (el repo del equipo de datos),
que se queda tal cual, sirviendo la API.

Módulos migrados hasta ahora:

1. **Consulta Matrícula Cero + Tablero** (primera entrega) — solo lectura,
   para validar el patrón de auth, llamadas a la API y componentes.
2. **Seguimiento Convenios MC · Reporte de actividades** (segunda entrega)
   — la parte "corazón" del módulo más grande y complejo: línea de tiempo
   de actividades por convenio/período, con su modal de detalle+edición.
   Es lo que el plan de migración señala como el verdadero dolor de UX de
   Streamlit hoy (ver sección 5.2 de `Plan_Migracion_FastAPI_React.md`).
   Incluye además una pantalla de selección de aplicativo tras el login
   (`/inicio`) y colores de alerta en las tarjetas de convenio, calcados
   del Streamlit original.
3. **Seguimiento Convenios MC · Administración** (tercera entrega) — fase 3
   del plan: CRUD de IES, Convenios (alta/edición + gestión de períodos),
   Catálogo de actividades y Usuarios, todo en `/seguimiento/admin` con
   pestañas (igual estructura que `pagina_admin()` en el Streamlit
   original). Solo visible/accesible para el rol **ADMIN**. Los campos
   Supervisor y Apoyo a la supervisión del convenio son listas
   desplegables (usuarios activos con rol DIRECTORA / AST respectivamente,
   más "— Sin asignar —"), igual que en el Streamlit original — no texto
   libre.
4. **Seguimiento Convenios MC · Informes** (cuarta entrega, rediseñada en el
   punto 11) — descarga de informes en PDF. Desde
   `/seguimiento/convenios/:id` hay un botón "Informe de este período"
   (siempre que haya un período seleccionado) y, solo si el convenio tiene
   más de un período, un botón "Informe consolidado". Ambos abren un modal
   con 8 checkboxes (alerta, fechas clave, ejecución, liquidación, cierre,
   comentarios, resumen ejecutivo, detalle de actividades) y, justo antes
   del botón de descarga, un bloque colapsable por subcategoría con
   comentario opcional y evidencia fotográfica (nada de esto se guarda —
   ver punto 11). El PDF se descarga con `POST` (antes `GET`, ver punto 11)
   con el nombre de archivo real que arma el backend
   (`Informe_{codigo}_{timestamp}.pdf`).
5. **Seguimiento Convenios MC · pulido de Administración** (quinta entrega)
   — dos mejoras puntuales sobre lo ya migrado:
   - **Sincronización automática del catálogo**: en el Streamlit original,
     agregar una actividad nueva al catálogo requería entrar convenio por
     convenio, período por período, y darle clic manual a "🔄 Sincronizar"
     en cada uno para que la actividad nueva apareciera ahí. Acá eso ya no
     existe como paso manual — `POST /seguimiento/catalogo/{tipo}` ahora,
     apenas crea la actividad, recorre TODOS los períodos existentes de
     TODOS los convenios y le agrega automáticamente la actividad nueva
     como "Pendiente" (reutilizando `crear_instancias_actividades`, que ya
     era idempotente vía `INSERT IGNORE`). El formulario de "Agregar
     actividad" en Administración → Catálogo muestra un mensaje
     confirmando en cuántos períodos existentes se sincronizó.
   - **Campo Valor como moneda**: en Administración → Convenios (alta y
     edición), el campo "Valor" ya no es un `<input type="number">` plano
     — ahora es un input con prefijo "$" que muestra el número con
     separador de miles (`16.562.226.354` en vez de `16562226354`) a
     medida que se escribe, aunque por dentro sigue guardando solo dígitos
     (mismo formato que ya esperaba el backend).
6. **Fix: "Agregar actividad" fallaba con 422** — bug real reportado tras
   la entrega anterior. `POST /seguimiento/catalogo/{tipo}` exigía un campo
   `tipo` en el body vía el modelo `ActividadBaseCreate`, pero `tipo` ya
   viaja en la URL (`/seguimiento/catalogo/ejecucion`, etc.) y el código del
   endpoint nunca leía `data.tipo` — usa el `tipo` de la ruta para todo. El
   frontend (correctamente) no mandaba `tipo` en el body, así que CADA
   intento de agregar una actividad fallaba con 422 "tipo: Field required".
   Se corrigió haciendo `tipo` opcional en `ActividadBaseCreate` (nunca se
   usa, así que no cambia ningún comportamiento). De paso, se corrigió
   también `getErrorMessage` en el frontend: FastAPI manda el `detail` de
   un 422 como una LISTA de errores de validación (uno por campo), no como
   texto — meterla directo en un template string producía literalmente
   "[object Object]" en vez de decir qué campo falló. Ahora se formatea
   como `campo: motivo` (ej. "tipo: Field required"), útil para diagnosticar
   cualquier futuro error de validación sin tener que abrir la consola del
   navegador.
7. **Fix: faltaba el campo de fecha manual en las actividades de ejecución
   74 y 71** — bug real reportado tras agregar en n8n las dos cadenas de
   recordatorio de ejecución (74→73 firma directora DTF → publicación SECOP
   II informe/recibo, y 71→76 orden de pago → publicación SECOP II/cierre
   plan de pagos). El backend (`PATCH /seguimiento/actividades/:id/avance`)
   siempre aceptó `fecha_manual` para cualquier actividad, pero el frontend
   solo MOSTRABA ese campo de fecha para las actividades 36 y 22 (las de la
   cadena de liquidación) — la lista `ACTIVIDADES_CON_FECHA_MANUAL` en
   `ActividadModal.tsx` estaba hardcodeada a esas dos. Por eso al marcar la
   74 o la 71 como Completada (100%), no aparecía dónde poner la fecha real
   y el sistema guardaba la fecha de hoy en vez de la fecha real de firma/pago
   que el apoyo necesita registrar. Se agregaron las entradas 74 y 71 a esa
   lista, cada una con su propia etiqueta.
8. **Actividades 85→86 y 88→89 y 97→98: mismo patrón firma/pago → SECOP,
   ahora en más subcategorías** — el catálogo de ejecución fue creciendo y
   varias subcategorías repiten la misma pareja de actividades (firma
   directora DTF → publicación en SECOP II, u orden de pago → publicación en
   SECOP II). Se agregaron las 3 parejas nuevas al flujo de n8n (mismo
   archivo `Alertas liquidaciones convenios MC.json`, no vive en este repo)
   y sus 3 actividades de origen (85, 88, 97) a
   `ACTIVIDADES_CON_FECHA_MANUAL` en `ActividadModal.tsx`, para que no
   repitan el bug del punto 7. Para no tener que inventar un
   `tipo_notificacion` distinto por cada subcategoría (y así no volver a
   tocar el Code node de n8n cada vez que aparezca una pareja nueva), las
   notificaciones ahora comparten tipo por familia
   (`recordatorio_firma_ejecucion` / `recordatorio_pago_ejecucion`) y el
   correo agrega dos filas nuevas — **Categoría** (Ejecución/Liquidación/
   Cierre) y **Subcategoría** (ej. "DESEMBOLSO ANTICIPADO") — leídas del
   catálogo (`actividades_base_seg_mc`) para la actividad destino de cada
   notificación, así el destinatario siempre distingue de cuál subcategoría
   se trata aunque el asunto/tipo del correo sea el mismo. Se le preguntó
   explícitamente a Migue si convenía mover esta lista de parejas a una
   tabla de configuración en la base de datos (para no tener que tocar n8n
   cada vez que aparezca una subcategoría nueva) y prefirió mantenerlo igual
   que las anteriores por ahora — queda como posible mejora futura si el
   catálogo sigue creciendo.
9. **Actividad 99→100 (fase CIERRE) + Directora notificada también en
   liquidación voluntaria/unilateral** — dos pedidos nuevos:
   - **99→100**: "Firma de acta de cierre por parte del supervisor" (id=99)
     → "Publicación en SECOP II..." (id=100). A diferencia de las cadenas de
     ejecución (74→73, 71→76, 85→86, 88→89, 97→98), que se rastrean por
     `convenio_periodo_id` porque se repiten cada período, esta es de la
     fase **cierre** — que ocurre una sola vez al final de la vida del
     convenio (igual que liquidación: el propio backend, en
     `TRANSICION_ESTADO`, trata "cierre" como una transición de convenio
     completo, `'En cierre' → 'Cerrado'`, no por período) — así que este
     bloque se colapsa por `convenio_id`, igual que los bloques 7/8 de
     liquidación, en vez de por período. Se agregó su propio
     `tipo_notificacion` (`recordatorio_firma_acta_cierre`, distinto de los
     de ejecución porque es una actividad distinta — no es "firma directora
     DTF" ni "orden de pago") y su actividad de origen (99) a
     `ACTIVIDADES_CON_FECHA_MANUAL` en el frontend.
   - **Directora en voluntaria/unilateral**: la Directora (el campo
     "Supervisor" del convenio en Administración → Convenios corresponde a
     un usuario con rol DIRECTORA — ver punto 3 de este mismo listado) solo
     recibía las 3 alertas judiciales (`judicial_2m/1m/15d`), no las de
     liquidación voluntaria/unilateral. A pedido de ella, ahora también las
     recibe — la póliza de cumplimiento sigue siendo solo para el Apoyo, ya
     que no se pidió cambiar eso.
10. **Corrección: 99→100 en realidad es el mismo patrón que "firma directora
    DTF", no un caso aparte de cierre** — al revisar el punto 9, Migue cayó
    en cuenta de que la actividad 99 ("Firma de acta de cierre por parte
    del supervisor") es conceptualmente la MISMA firma que 74/85/97
    ("firma directora DTF"): el campo "Supervisor" del convenio siempre es
    un usuario con rol DIRECTORA (ver punto 3), así que "firma del
    supervisor" y "firma de la Directora" son la misma persona/evento, solo
    con nombres distintos según la subcategoría del catálogo. Se corrigió:
    - En n8n, el bloque 99→100 pasó de estar colapsado por `convenio_id`
      (tratándolo como un caso de "cierre" de una sola vez, como
      liquidación) a rastrear por `convenio_periodo_id` con
      `tipo_notificacion='recordatorio_firma_ejecucion'` — exactamente el
      mismo patrón que 74→73/85→86/97→98 — y se eliminó el tipo aparte
      `recordatorio_firma_acta_cierre` que ya no se usa (tipos, etiquetas,
      asunto y título correspondientes, además de su exclusión en el nodo
      `If1`).
    - En el frontend, se corrigió la etiqueta de la actividad 99 en
      `ACTIVIDADES_CON_FECHA_MANUAL` de "Fecha real de firma del acta de
      cierre" a "Fecha real de firma de la Directora", igual que 74/85/97
      (el campo ya estaba habilitado desde el punto 9, solo tenía el texto
      equivocado).
11. **Rediseño de Informes: resumen ejecutivo + comentarios/imágenes por
    subcategoría** — Migue pidió que el informe dejara de ser un volcado
    plano del avance de actividades y pasara a ser "algo más útil": un
    resumen ejecutivo por subcategoría, y la posibilidad de agregar un
    comentario y evidencia fotográfica por cada subcategoría justo antes de
    generar el PDF. Restricción explícita: nada de esto se guarda en
    ninguna tabla — ni el comentario ni las imágenes se persisten en ningún
    lado (ni siquiera como BLOB), se usan una única vez para armar ESE PDF
    puntual y se descartan al terminar la petición.
    - **Backend**: `get_datos_informe_periodo` ahora calcula, por
      subcategoría, el % promedio (solo sobre actividades `es_relevante`,
      igual criterio que el % global) y el conteo por estado (Completada/En
      curso/Pendiente/Bloqueada/Atrasada/No aplica). `generar_pdf_informe`
      recibe ahora un segundo parámetro opcional con las notas por
      `(tipo, subcategoría)` y arma dos secciones nuevas en el PDF: una
      tabla de "resumen ejecutivo" con barra de progreso coloreada
      (rojo/ámbar/verde) por subcategoría, y una sección "Comentarios y
      evidencias" con el texto y las imágenes que el usuario haya agregado.
      El detalle actividad-por-actividad (la tabla completa que ya existía)
      pasa a ser opcional vía un nuevo checkbox, no se elimina.
    - **Procesamiento de imágenes** (`procesar_imagen_para_pdf`, con
      Pillow): corrige la orientación según el tag EXIF (una foto tomada en
      vertical con el celular no sale rotada en el PDF), aplana transparencia
      sobre fondo blanco (los PNG con transparencia no salen con fondo negro
      al convertir a JPEG), y reduce el tamaño (máx. 1600px de lado, calidad
      85) antes de insertarlas — todo en memoria, nunca se escribe a disco
      ni a una tabla. El acomodo en la grilla (1/2/3 imágenes por
      subcategoría) usa "contain-fit" real: la escala se calcula a partir
      del tamaño real en píxeles de cada imagen, nunca se distorsiona ni se
      recorta. Límites de defensa en el servidor (además de los que ya
      valida el frontend): máximo 5 imágenes por subcategoría, 12MB por
      imagen (las que se pasan se omiten en silencio en vez de tumbar todo
      el informe).
    - **Los 2 endpoints de PDF pasan de `GET` a `POST` multipart/form-data**
      (`/seguimiento/informes/periodo/:id/pdf` y
      `/seguimiento/informes/convenio/:id/pdf`) porque ahora pueden llevar
      imágenes adjuntas, que no caben en query params de una URL. Los 2
      endpoints JSON (para la previsualización en el modal) siguen igual,
      sin cambios, y ya devuelven el `pct`/conteos nuevos por subcategoría
      porque ese cálculo se movió a `get_datos_informe_periodo`, que
      comparten ambos.
    - **Frontend**: `InformeModal` ahora trae, además de los 6 checkboxes de
      siempre, 2 nuevos ("Resumen ejecutivo", "Detalle de actividades") y,
      justo antes del botón de descarga, un bloque colapsable por cada
      subcategoría (con su % actual) con un textarea de comentario y una
      zona de arrastrar-o-hacer-clic para adjuntar imágenes (con
      miniaturas y botón de quitar). Esos bloques se arman una sola vez al
      abrir el modal a partir del JSON de previsualización, y se ocultan
      dinámicamente si el usuario desmarca el checkbox del tipo
      correspondiente (ejecución/liquidación/cierre) — sin volver a pedir
      datos al servidor. `seguimientoInformes.ts` se reescribió para armar
      un `FormData` (checkboxes + un campo `notas` en JSON + las imágenes
      bajo `imagenes::<clave>`) y pedir el PDF con `POST` en vez de `GET`.
12. **Ajuste al resumen ejecutivo del PDF: se quitan las columnas
    "Atrasadas" y "Bloq."** — a pedido de Migue, la tabla de resumen
    ejecutivo (punto 11) queda solo con Subcategoría, %, Progreso, Compl.,
    En curso y Pend. El ancho que dejaron libres esas 2 columnas se
    repartió entre la barra de progreso (más ancha, más legible) y el
    nombre de la subcategoría. El backend sigue calculando los conteos de
    "Atrasada"/"Bloqueada" en `get_datos_informe_periodo` (por si se
    necesitan más adelante, p. ej. para otra vista), solo se dejaron de
    mostrar en esta tabla.
13. **Renombrado de los botones del menú superior** — en
    `components/Layout.tsx`, "Consulta" pasó a "Consulta formulario" y
    "Tablero" a "Tablero histórico" (mismos links, `/consulta` y
    `/tablero`, solo cambió el texto visible).
14. **Administración → Usuarios: eliminar y cambiar contraseña** — Migue
    pidió poder eliminar usuarios y cambiarles la contraseña desde el
    aplicativo (antes solo se podía crear y activar/desactivar).
    - **Cambiar contraseña** (`PATCH /seguimiento/usuarios/{id}/password`,
      solo ADMIN): el botón "🔑 Cambiar contraseña" en cada fila abre un
      formulario en línea para poner una contraseña nueva (mínimo 8
      caracteres, igual que al crear). Al guardarla, el usuario queda con
      `primer_login=1` otra vez — la próxima vez que inicie sesión está
      obligado a poner una contraseña que el admin ya no conoce, en vez de
      seguir usando la que el admin le asignó. Esto es un reseteo hecho por
      un ADMIN sobre OTRO usuario — distinto del endpoint ya existente
      `/seguimiento/auth/cambiar-password`, que es el propio usuario
      cambiando su contraseña en su primer login.
    - **Eliminar** (`DELETE /seguimiento/usuarios/{id}`, solo ADMIN): borra
      el registro por completo (no es lo mismo que "Desactivar", que solo
      lo marca inactivo y sigue existiendo). Dos protecciones: (1) un ADMIN
      no puede eliminar su propio usuario mientras tiene la sesión iniciada
      con él — el botón sale deshabilitado en su propia fila; (2)
      `actividades_convenio_seg_mc.responsable_id` y
      `historial_actividades_seg_mc.usuario_id` tienen un FOREIGN KEY hacia
      `usuarios_seg_proceso_mc.id`, así que un usuario que ya haya
      reportado avance o quedado como responsable de alguna actividad no se
      puede eliminar sin romper esa integridad — el backend captura ese
      error de base de datos (`IntegrityError`) y devuelve un 409 con un
      mensaje claro pidiendo desactivar en su lugar, en vez de dejar
      pasar un error 500 genérico. Para usuarios que nunca llegaron a
      usarse (p. ej. creados por error), sí se eliminan sin problema.
15. **Apoyo a la supervisión en las tarjetas de convenio** — en
    `/seguimiento`, cada tarjeta ya mostraba "Períodos" y "Supervisor"; se
    agregó una línea más con "Apoyo a la supervisión" (mismo dato que ya se
    ve en el detalle del convenio, y que `GET /seguimiento/convenios` ya
    traía en su SELECT — no hizo falta tocar el backend). Se oculta igual
    que Supervisor cuando el convenio no tiene ese dato cargado.
16. **Fecha límite por subcategoría + barra de progreso semaforizada** —
    Migue pidió poder poner, por cada subcategoría de la línea de tiempo,
    una fecha estimada para terminar todas sus actividades, y que la barra
    de progreso cambie de color según qué tan cerca esté esa fecha: azul
    (el degradado de siempre) si no hay fecha definida, verde en el primer
    tercio del plazo, ámbar en el segundo tercio, rojo en el último tercio
    (y se queda en rojo si la fecha ya pasó). Si la subcategoría ya llegó
    al 100%, la barra se queda verde fija sin importar la fecha.
    - **Es la primera funcionalidad de esta migración que necesita una
      tabla nueva en la base de datos.** No hay acceso directo a la BD de
      Migue desde este entorno, así que se entrega un script SQL
      (`sql/migraciones/2026-08_fechas_limite_subcategoria.sql` en el repo
      de la API) con un `CREATE TABLE IF NOT EXISTS` para
      `fechas_limite_subcategoria_seg_mc` — hay que correrlo una sola vez
      contra la base de datos antes de usar esta funcionalidad; no toca
      ninguna tabla existente ni requiere downtime.
    - **Backend**: 3 endpoints nuevos en `seguimiento_actividades.py` —
      `GET /seguimiento/periodos/{id}/fechas-limite` (lista las fechas ya
      definidas para ese período), `PUT` (define o actualiza la fecha
      límite de una subcategoría — mismo permiso que el resto de edición
      de actividades, el rol Directora no puede) y `DELETE` (la quita, la
      barra vuelve a azul). El campo clave es `fecha_definicion`: es el
      ancla desde la que se cuentan los tercios verde/ámbar/rojo, y se
      REESCRIBE a "ahora" cada vez que se guarda o cambia la fecha límite
      (no es un timestamp de creación fijo) — si hoy pones una fecha a 30
      días, esos 30 días se parten en tercios de 10 desde hoy; si en 5 días
      cambias la fecha, el conteo se reinicia desde ese momento con el
      nuevo plazo. `actualizado_por` referencia al usuario que la definió,
      con `ON DELETE SET NULL` (a propósito distinto del `RESTRICT` que ya
      protege a `responsable_id`/`historial_actividades_seg_mc.usuario_id`
      del punto 14 — este es solo un dato de auditoría menor, no bloquea
      poder eliminar a un usuario que únicamente haya definido fechas
      límite).
    - **Frontend**: el color se calcula en el cliente (`TimelineActividad`),
      sin tocar el servidor cada vez — solo necesita `fecha_limite` y
      `fecha_definicion`, que se piden una vez por período. En el
      encabezado de cada subcategoría hay un control en línea ("Definir" /
      "Editar" / "Quitar", con un `<input type="date">"`) visible solo para
      los roles que pueden editar actividades. Los mismos tonos verde
      (`#15803D`) / ámbar (`#B45309`) / rojo (`#B91C1C`) que ya se usaban en
      el resumen ejecutivo del PDF de informes (punto 11), para que el
      código de colores sea consistente en toda la app.
17. **Informe PDF: "último comentario" por subcategoría en vez del checkbox
    "Historial de comentarios"** — Migue notó que el historial completo de
    comentarios casi nunca se veía en la práctica (dependía de activar
    "Detalle de actividades", que viene desactivado por defecto), así que se
    reemplazó por algo siempre visible: el comentario más reciente de cada
    subcategoría, mostrado directamente dentro de la tabla de resumen
    ejecutivo (el checkbox "Historial de comentarios" se eliminó del modal).
    - **Backend** (`informes_seguimiento.py`): se reutilizan los mismos
      comentarios que ya se traían de `historial_actividades_seg_mc` (no se
      agregó ninguna consulta nueva) — por cada subcategoría se toma, entre
      todas sus actividades, el comentario con la fecha más reciente
      (`get_datos_informe_periodo` ahora calcula `info["ultimo_comentario"]`
      con `{fecha, usuario, comentario, actividad}`, o `None` si ninguna
      actividad de esa subcategoría tiene comentarios). En el PDF
      (`generar_pdf_informe`), cuando existe se inserta una fila adicional
      fusionada (`SPAN`) justo debajo de la fila de esa subcategoría en la
      tabla de resumen ejecutivo, con fondo gris claro para distinguirla.
    - **Ojo con el texto libre**: como el comentario, el nombre de usuario y
      el nombre de la actividad los escribe/nombra el propio equipo, se
      escapan con `xml.sax.saxutils.escape` antes de insertarlos en el PDF —
      `reportlab` interpreta el texto de cada `Paragraph` como si fuera XML,
      así que un comentario con un `<` o un `&` sueltos (algo muy posible en
      la escritura normal) habría reventado la generación de *todo* el
      informe sin este escape. Se probó puntualmente con un comentario que
      incluía `<`, `>`, `&` y comillas para confirmar que ya no rompe nada.
    - Como consecuencia, el historial completo de comentarios por actividad
      (el que aparecía bajo "Detalle de actividades" cuando el checkbox
      estaba activo) se quitó del informe — el resumen ejecutivo ahora
      siempre trae el dato más útil de un vistazo (el comentario más
      reciente) en vez de un historial que casi nadie llegaba a activar.
      También se limpió `incluir_comentarios` de los endpoints, del
      formulario del modal y de los tipos del frontend, ya que dejó de
      existir esa opción.
18. **2 tarjetas KPI en Seguimiento Convenios MC** — arriba de todo en
    `/seguimiento`, antes incluso de la tarjeta del repositorio de
    expedientes: "Total de convenios" (el conteo sin filtrar, siempre fijo
    mientras no cambien los datos) y "Convenios con filtros actuales" (se
    recalcula al vuelo con cada cambio de categoría/estado, IES o el
    buscador de código — es el mismo arreglo `convenios` que ya se usaba
    para pintar las tarjetas de abajo, así que no hizo falta pedir nada
    nuevo al backend). La segunda tarjeta además muestra debajo del número
    qué filtros están activos ahora mismo (p. ej. "Categoría: En ejecución ·
    IES: Universidad X"), o "Sin filtros activos" cuando no hay ninguno, para
    que quede claro de un vistazo qué se está contando.
19. **Barra de progreso con mínimo visible cuando hay fecha límite y 0% de
    avance** — Migue notó que, con una subcategoría en 0% (ninguna actividad
    relevante completada todavía), la barra semaforizada de la fecha límite
    (punto 16) queda con `width: 0%` y no se alcanza a ver ningún color, aunque
    ya haya una fecha límite definida y por lo tanto un color real que mostrar
    (verde/ámbar/rojo). Se agregó un `min-width` a la barra (Migue lo ajustó
    después a 30px, tras probar el valor inicial de 6px y verlo muy poco
    visible), pero SOLO cuando hay un color de fecha límite calculado — así
    siempre queda un trocito visible para identificar en qué zona del
    semáforo está la subcategoría, incluso sin avance real. Cuando no hay
    fecha límite definida (la barra usa el degradado morado/azul de siempre)
    se deja tal cual, sin mínimo, porque ahí no hay ningún color de semáforo
    que identificar.
20. **Filtro por nivel de alerta en Seguimiento Convenios MC** — en
    `/seguimiento`, debajo del filtro de categoría/estado, se agregó una fila
    de botones "Nivel de alerta": Todos, Sin alerta, Aviso, Urgente y
    Crítico. Filtra sobre el mismo `nivel_alerta` que ya trae cada convenio
    desde el backend (no hizo falta tocar el backend), combinándose con los
    demás filtros (categoría, IES, código) y con la tarjeta KPI "Convenios
    con filtros actuales" (punto 18), que ahora también muestra "Alerta:
    AVISO" (o el nivel que corresponda) en su nota cuando este filtro está
    activo. Cada botón activo toma el mismo color de acento que ya usa la
    tarjeta de ese nivel de alerta (ámbar/naranja/rojo/azul oscuro para "Sin
    alerta"), para que el filtro se sienta visualmente conectado con las
    tarjetas que filtra.

21. **Nuevo módulo "Inversión y Beneficios"** — dentro del aplicativo de
    Consulta + Tablero (NO toca Seguimiento), una tercera página en
    `/inversion` (link "📈 Inversión y beneficios" en el mismo nav de
    Consulta/Tablero) con KPIs y gráficas de la inversión ejecutada en
    Matrícula Cero. Fuente de datos: `analitica_fondos.mc_final` (confirmado
    con Migue como la fuente autoritativa), una fila por documento+período,
    con 3 columnas de valor neto pagado: `mat_n` (matrícula), `der_comp_n`
    (derechos complementarios) y `ajust_n` (ajuste/apoyo 1.5 SMMLV — lo que
    Sapiencia le da a las IES distritales para completar el valor de la
    matrícula hasta 1.5 SMMLV en las que no lo superen; no tiene relación con
    la tabla `reintegros`). Una fila solo cuenta como beneficio real (tanto
    para los conteos como para las sumas de dinero) si además
    `estado_semestral = 'MC'` — confirmado con Migue, sin este filtro se
    contarían/sumarían filas que no corresponden a un beneficio vigente ese
    período. "Beneficios otorgados" cuenta filas (documento+período) que
    cumplen ese filtro; "Beneficiarios" cuenta documentos ÚNICOS entre esas
    filas (una misma persona en varios períodos cuenta una sola vez) —
    ambos criterios confirmados con Migue antes de programar.
    - Filtros: IES, año y período, cada uno de **selección múltiple**
      (se puede combinar, por ejemplo, 2 IES + 1 año a la vez — un dropdown
      con checkboxes propio, `MultiSelectDropdown.tsx`, reutilizable). El
      desplegable de período se acota solo a los períodos de los años
      elegidos, si hay alguno elegido. Modelo "todas marcadas por defecto,
      desmarcar para excluir" (a pedido de Migue): al abrir cualquiera de
      los 3 dropdowns con "Todos/Todas" seleccionado, TODAS las casillas
      aparecen marcadas — para excluir una sola opción basta con
      desmarcarla (antes había que marcar todas las demás una por una). El
      botón muestra "Todas menos {nombre}" cuando se excluye solo una, o
      "Todas menos N" cuando se excluyen varias pero siguen siendo mayoría;
      si se vuelven a marcar todas, el filtro se normaliza de nuevo a
      "Todos/Todas" (mismo resultado — filtrar por todos los valores
      existentes equivale a no filtrar — pero se ve más limpio en el
      botón).
    - 6 tarjetas KPI en 2 filas: "Inversión ejecutada" (total, matrícula,
      derechos complementarios, ajuste 1.5 SMMLV) y "Alcance" (beneficios
      otorgados, beneficiarios) — separadas a pedido de Migue para no
      mezclar plata con conteos de personas en la misma fila. Cada rubro
      tiene su propio color de acento, reutilizado también en el pie chart
      de abajo.
    - Gráfica de pie "Participación por rubro": qué porcentaje del total
      ejecutado corresponde a cada rubro, con el filtro actual aplicado. El
      porcentaje se muestra en la leyenda (no como etiqueta con línea guía
      saliendo de la porción) — con rubros muy desbalanceados (ej. uno en
      3% del total) esas líneas y su texto terminaban saliéndose del área
      del gráfico y cortándose contra el borde de la tarjeta; en la leyenda
      siempre hay espacio, sin importar qué tan desbalanceado esté.
    - Gráfica de barras "Beneficios vs. beneficiarios": si no hay ninguna
      IES seleccionada, compara el top 12 de IES por total ejecutado
      (respetando el filtro de año/período); si hay una o más IES
      seleccionadas, cambia automáticamente a mostrar la tendencia por
      período de esa IES (o grupo de IES) — comparar contra el resto de IES
      dejaría de tener sentido en ese caso.
    - Nuevo endpoint en el backend, `GET /reportes-inversion/resumen`
      (`api/routers/reportes_inversion.py`), con la misma autenticación de
      Seguimiento que ya usan los demás endpoints de Consulta/Tablero (de
      solo lectura, cualquier rol autenticado puede consultarlo). Cada
      filtro llega como parámetro repetido (`?ies=A&ies=B`, sin notación de
      corchetes) y se arma dinámicamente un `IN (...)` por dimensión con
      bind params "expandibles" de SQLAlchemy. Se agregó también la
      librería `recharts` (nueva dependencia del frontend — no había
      ninguna librería de gráficas instalada todavía).

22. **Columna `valor_proyectado` en convenios (primer paso hacia el módulo
    financiero)** — Migue confirmó con el financiero que el `valor_total`
    del convenio ya está cubierto por la columna `valor` que existe desde
    antes en `convenios_seg_proceso_mc` (no hace falta pedírselo aparte).
    Lo único que faltaba era `valor_proyectado` (una proyección hacia
    adelante — no se puede derivar de la ejecución histórica, tiene que
    venir directo del financiero). Como es un solo valor por convenio (no
    varía por período), se agregó como columna nueva en esa misma tabla —
    mismo patrón que `valor` — y no como una tabla aparte. Requiere correr
    una vez `sql/agregar_valor_proyectado_convenios.sql` contra la base de
    datos de analítica (no se pudo ejecutar desde este entorno por no tener
    acceso a la BD real). Se agregó el campo "Valor proyectado" (mismo
    componente `InputMoneda` que ya usa "Valor") tanto en el formulario de
    "Registrar nuevo convenio" como en el de edición, en Administración →
    Convenios; el modelo `ConvenioSeguimientoCreate`/`ConvenioSeguimientoUpdate`
    (backend) y las respuestas de `GET /seguimiento/convenios` y `GET
    /seguimiento/convenios/{id}` ya incluyen `valor_proyectado`.

    Además, a pedido de Migue, se agregó una consulta SQL de referencia
    (`sql/referencia_convenios_periodos_para_financiero.sql`) con el
    `convenio_id` + código + IES + períodos ya existentes en Seguimiento —
    para pasarle al equipo financiero ANTES de que arme su Excel de
    ejecución por período, y que copie el texto EXACTO de cada período en
    vez de escribirlo de memoria (el emparejamiento de períodos solo
    normaliza mayúsculas/espacios, no el formato — "2024-I" vs "2024-1" no
    cruzarían). Esta consulta se corre directo contra la base desde el
    cliente que use Migue (MySQL Workbench, DBeaver, etc.) y se exporta a
    CSV/Excel desde ahí — a diferencia de un intento anterior en esta misma
    entrega, NO quedó como una funcionalidad dentro del aplicativo (se
    había agregado un botón de descarga en Administración → Convenios, pero
    Migue pidió revertirlo: quería la consulta SQL directa, no una feature
    nueva en la app).

    > **Nota (superado por el punto 23):** esta columna `valor_proyectado`
    > por convenio se eliminó después de que Migue confirmó con el
    > financiero que el proyectado en realidad cambia por período, no es un
    > valor único por convenio. Ver el punto 23 para el detalle de la
    > corrección y de dónde vive ahora el dato correcto.

23. **Corrección de `valor_proyectado` (de columna por convenio a columna
    por período) + módulo "Información Financiera"** — Migue le pidió al
    financiero la ejecución por período (en vez de que le pidiéramos
    resumen + proyectado ya armados) y compartió el Excel real
    (`MC_Financiera.xlsx`). Del análisis de ese Excel (fórmulas vs. valores,
    y el caché de un VLOOKUP externo que coincidía exactamente con la
    consulta de referencia de la entrega anterior) y de la confirmación
    final de Migue salieron dos cosas:

    - El `valor_total` del convenio efectivamente ya está cubierto por la
      columna `valor` existente (como se había asumido en el punto 22), así
      que ese dato NO se vuelve a pedir.
    - El `valor_proyectado`, en cambio, **no es un solo valor por
      convenio** — cambia por período. La columna que se había agregado en
      el punto 22 quedó redundante e incluso incorrecta, y Migue pidió
      quitarla: `sql/migraciones/2026-09_quitar_valor_proyectado_convenio.sql`
      (correr una sola vez contra `analitica_fondos`; si ya habías cargado
      valores ahí se pierden, pero el dato correcto ya vive en la tabla de
      ejecución financiera). El dato correcto, por período, se guarda en
      `analitica_fondos.convenio_ejecucion_financiera_mc.valor_proyectado_periodo`
      (tabla creada en la migración
      `sql/migraciones/2026-09_ejecucion_financiera_convenios.sql`, ya
      entregada, junto con el resto de columnas de ejecución por período:
      número de RP/CDP, valor CDP, estudiantes postulados/conciliados,
      valor conciliado, y los 3 rubros pagados —
      `valor_pagado_matricula`/`valor_pagado_complementarios`/`valor_pagado_ajuste`,
      renombrados según la captura que mandó Migue — más `valor_pagado`
      total). Esa misma migración había agregado también `adiciones_recursos`
      en `convenios_seg_proceso_mc` (valor de modificaciones al contrato,
      un concepto distinto de `valor_proyectado` — esta columna SÍ se
      conserva) — se quitaron todas las referencias a `valor_proyectado` de
      `ConvenioSeguimientoCreate`/`ConvenioSeguimientoUpdate`/`ConvenioDetalleOut`
      y del formulario de Administración → Convenios (alta y edición), y se
      reemplazó por `adiciones_recursos` donde correspondía mostrarlo.

    Con la tabla de ejecución ya alimentada por Migue, se implementó el
    módulo **Información Financiera** (tercera tarjeta del selector de
    aplicativos, `/financiero`, icono 💰) — backend nuevo
    (`api/models/reportes_financieros.py`,
    `api/routers/reportes_financieros.py`, prefix propio
    `/reportes-financieros`, mismo esquema de autenticación de Seguimiento
    que el resto):

    - `GET /reportes-financieros/resumen` — filtros de IES y convenio con
      el mismo patrón "todas marcadas, desmarcar para excluir" y parámetros
      repetidos sin corchetes (`?ies=A&ies=B`) ya usado en Inversión.
      Devuelve un resumen agregado (valor total/ejecutado/proyectado/no
      ejecutado, número de convenios, % ejecución) y la lista de convenios
      con sus propios totales — `valor_ejecutado` = `SUM(valor_pagado)` y
      `valor_proyectado` (a nivel convenio, solo para mostrar un total) =
      `SUM(valor_proyectado_periodo)`, sumando todos los períodos de cada
      convenio. Esta forma de agregar es una decisión propia — si Migue
      quiere un criterio distinto (ej. solo el período vigente en vez de la
      suma de todos), se ajusta.
    - `GET /reportes-financieros/convenios/{id}/periodos` — el detalle por
      período de un convenio, cruzando los períodos ya conocidos en
      Seguimiento (`convenio_periodos_seg_mc`) con la ejecución financiera
      por período (`LEFT JOIN` normalizando mayúsculas/espacios), para que
      un período sin datos del financiero todavía aparezca en la tabla con
      sus campos en blanco ("Pendiente"/"Sin conciliar") en vez de no
      aparecer.

    En el frontend (`src/pages/FinancieroPage.tsx` +
    `src/api/reportesFinancieros.ts`): dos filtros multi-select (IES,
    Convenio), tarjetas KPI (Valor total/ejecutado/proyectado/no ejecutado,
    Convenios, % Ejecución), y una lista expandible de convenios — cada
    fila muestra dos barras de progreso semafóricas (verde ≥70%, ámbar
    ≥35%, rojo <35%) para "% ejecución (valor)" y "% ejecución (tiempo)", y
    al expandir se ve la tabla de períodos con las 12 columnas del Excel
    original. Las fórmulas del Excel que Migue confirmó que NO se guardan
    (`% ejecución (tiempo)`, `% ejecución (valor)`, `valor no ejecutado`)
    **no se persisten en la base de datos** — se recalculan en cada request
    dentro del backend (`% ejecución (tiempo)` usa la fecha de hoy contra
    fecha inicio/fin del convenio, con el resultado limitado entre 0% y
    100%).

    > **Nota (corregido en el punto 24):** la primera versión calculaba
    > `% ejecución (valor)` como `valor_ejecutado / valor_total`, contra el
    > valor total del contrato. Migue reportó que daba muy distinto al
    > Excel del financiero — ver el punto 24 para la fórmula correcta
    > (contra el Valor CDP, no contra el valor total).

24. **Fix: `% ejecución (valor)` y `valor no ejecutado` calculaban contra la
    base equivocada** — Migue reportó que el % que mostraba la app quedaba
    muy distinto al que traía el Excel del financiero, y preguntó si tenía
    que ver con los períodos. Sí: revisando las fórmulas reales del Excel
    (`data_only=False` sobre el archivo que ya había mandado el financiero)
    se confirmó que ahí `% EJECUCIÓN (VALOR)` y `VALOR NO EJECUTADO` son
    fórmulas **por período**, contra el **Valor de CDP** de ese período
    (`= VALOR PAGADO / VALOR DE CDP` y `= VALOR DE CDP - VALOR PAGADO`) —
    no contra el valor total del contrato ni contra el valor proyectado. La
    primera versión del punto 23 calculaba el % a nivel de convenio contra
    `valor_total` (el contrato completo), lo que lo subestimaba fuerte
    mientras el convenio tuviera períodos futuros aún sin CDP emitido (con
    los números reales que mandó Migue, daba 38-43% en vez del 87-93% real).

    Se corrigió en dos niveles:
    - Por período (`GET /reportes-financieros/convenios/{id}/periodos`):
      ahora replica la fórmula exacta del Excel, `valor_pagado / valor_cdp`
      y `valor_cdp - valor_pagado` — esto no es una decisión, es la fórmula
      literal del archivo.
    - Por convenio (el resumen agregado — el Excel no tiene un equivalente
      ahí, hay que definirlo): se acordó con Migue sumar el `valor_cdp` de
      todos los períodos con datos y usar esa suma como base
      (`SUM(valor_pagado) / SUM(valor_cdp)`), mismo criterio que el Excel
      pero agregado en vez de por fila. Se agregó `valor_cdp` como campo
      nuevo (en `ConvenioFinanciero` y `ResumenFinanciero`) para que quede
      visible cuál es esa base — tarjeta KPI "Valor CDP" y valor mini "CDP"
      en cada fila de convenio, más una nota debajo de los KPIs explicando
      el criterio.

    De paso, a pedido de Migue, se reemplazó el filtro de IES/Convenio de
    Información Financiera: antes era el dropdown de casillas "todas
    marcadas, desmarcar para excluir" (`MultiSelectDropdown`, el mismo que
    sigue usando Inversión); ahora es un cuadro con buscador donde cada
    convenio/IES que se selecciona se agrega como "chip" con su propia "×"
    para quitarlo (`SearchMultiSelect`, componente nuevo) — arranca vacío
    (sin chips = todas, mismo comportamiento de siempre) y se construye la
    lista agregando explícitamente lo que se quiere ver, en vez de excluir
    de una lista larga. Por ahora es solo para Financiero; Inversión se deja
    con su filtro actual.

25. **Filtros de IES/Convenio conectados entre sí + detalle por período en
    tarjetas (en vez de tabla)** — dos ajustes a Información Financiera que
    pidió Migue después de usar el módulo.

    - **Filtros facetados**: antes las opciones de IES y de Convenio salían
      siempre completas, sin importar qué había elegido en el otro filtro.
      Ahora se conectan: si eliges una IES, el desplegable de Convenio solo
      ofrece los convenios de esa IES (y viceversa) —
      `GET /reportes-financieros/resumen` calcula cada lista de opciones
      con el filtro de la OTRA dimensión únicamente (nunca con el propio,
      para no hacer desaparecer del desplegable algo que ya elegiste ahí
      mismo). De paso, las opciones de IES ahora solo incluyen IES que
      tienen al menos un convenio (antes salían todas las IES de
      `ies_seg_proceso_mc`, incluso sin convenios — no tenía sentido
      dejarlas elegibles en un filtro que nunca iba a traer resultados).
    - **Detalle por período en tarjetas**: Migue pidió no tener que hacer un
      clic adicional para ver el detalle de cada período, y que en vez de
      una tabla (que además se cortaba en 14 columnas con scroll horizontal)
      la información saliera en tarjetas agrupadas por secciones — como ya
      hacían "Valores"/"Alcance" a nivel de página, pero dentro del detalle
      de cada convenio. Se mantiene el clic para elegir QUÉ convenio ver en
      detalle (evita que la página se vuelva excesivamente larga con muchos
      convenios), pero una vez expandido, ya no hay tabla: primero una
      sección "Consolidado" (los totales del convenio, con `% Ejecución` y
      `Valor ejecutado`/`% Ejecución (tiempo)` destacados por ser los más
      relevantes) y luego, bien diferenciado con su propia tarjeta
      contenedora, cada período con 4 secciones internas en orden de
      relevancia: "Ejecución" (valor pagado, % ejecución, valor no
      ejecutado, valor proyectado — destacada, es lo primero que se quiere
      ver), "CDP y RP", "Postulación y conciliación", y "Rubros pagados"
      (el desglose más fino: matrícula/complementarios/ajuste).

    > **Nota (superado por el punto 26):** el "clic para elegir QUÉ
    > convenio ver en detalle" que se menciona arriba se quitó — ver el
    > punto 26.

26. **La información financiera ahora requiere elegir convenio (ya no se
    listan todos desde el principio, ni hace falta clic para ver detalle)**
    — simplificación pedida por Migue: antes, al entrar a Información
    Financiera, se veían de una vez los KPIs y la lista de TODOS los
    convenios (con clic en cada uno para expandir su detalle). Ahora la
    página no muestra nada — ni los KPIs "Valores"/"Alcance" ni ningún
    convenio — hasta que se elige al menos un convenio en el filtro de
    búsqueda (`SearchMultiSelect` del punto 24); mientras tanto se ve un
    mensaje invitando a elegir uno. El filtro de Convenio sigue permitiendo
    elegir varios a la vez (se mantiene esa flexibilidad, a pedido de
    Migue) — al elegir uno o más, su detalle completo (Consolidado +
    tarjetas por período del punto 25) se muestra directo, ya sin ningún
    clic adicional (se quitó el toggle de expandir/colapsar por completo).
    El filtro de IES se deja igual, sigue sirviendo para acotar la
    búsqueda de convenios (los dos filtros se mantienen conectados entre
    sí, punto 25) pero por sí solo, sin elegir convenio, no alcanza para
    mostrar información. Los desplegables de IES/Convenio siguen trayendo
    sus opciones desde el primer momento (se sigue pidiendo el reporte al
    backend aunque no haya convenio elegido — sino no habría con qué
    buscar), solo se dejó de RENDERIZAR el contenido hasta que se elige.

27. **Limpieza visual: se quitó la sección "Alcance" y los números repetidos
    arriba de las barras de progreso** — dos ajustes de Migue tras usar el
    módulo con datos reales. La sección "Alcance" (tarjetas "Convenios" y
    "% Ejecución (valor)" consolidadas entre TODOS los convenios elegidos)
    se quitó por completo — Migue no la vio relevante, ya que agrupar el %
    de ejecución entre varios convenios distintos no dice mucho por sí solo
    (cada convenio ya trae su propio % en su tarjeta "Consolidado", que es
    el dato que realmente importa). La sección "Valores" (con los montos en
    pesos) se deja igual — solo se pidió quitar "Alcance". Además, las 2
    barras de progreso de cada convenio ("% ejecución (valor)" y "%
    ejecución (tiempo)") ya no muestran el número al lado del label —
    quedaba repetido, porque ese mismo % ya aparece en las tarjetas
    "Consolidado" de abajo. Se quitó de ambas barras por consistencia
    (Migue solo mencionó explícitamente la de tiempo, pero el mismo
    argumento de "se repite en las tarjetas" aplica igual a la de valor,
    así que se dejaron las dos parejas — si prefiere que alguna mantenga el
    número, se ajusta). La barra sigue siendo informativa por sí sola: el
    color semafórico y qué tanto está llena no cambiaron.

    > **Nota (corregido en el punto 28):** este punto interpretó mal a qué
    > "números repetidos arriba de las barras" se refería Migue — no eran
    > el % de la propia barra, sino la fila Total/CDP/Ejecutado/Proyectado
    > que aparecía arriba de las barras, en el encabezado de cada convenio.
    > Ver el punto 28: el % de la barra se restauró, y la fila de
    > Total/CDP/Ejecutado/Proyectado del encabezado es la que se quitó.

28. **Corrección: se restauró el % en las barras, y se quitó la fila
    Total/CDP/Ejecutado/Proyectado del encabezado de cada convenio** —
    Migue aclaró que el punto 27 había entendido mal cuáles eran los
    "números repetidos arriba de las barras de progreso": no se refería al
    porcentaje dentro de la propia barra (`% ejecución (valor)`/`%
    ejecución (tiempo)`, que ya se había quitado en el 27), sino a la fila
    con 4 valores en pesos (Total/CDP/Ejecutado/Proyectado) que aparecía en
    el encabezado de cada convenio, justo arriba de las barras. Esa fila sí
    quedaba repetida — los mismos 4 valores ya aparecen en la sección
    "Consolidado" del detalle, que siempre está visible desde el punto 26 —
    así que se quitó (junto con el componente `ValorMini` que ya no se usa
    en ningún otro lado). El % dentro de las barras se restauró tal como
    estaba antes del punto 27.

29. **Ajustes de texto de Migue + reordenar los KPIs principales** — Migue
    hizo directamente 3 cambios de texto en su copia del frontend antes de
    esta entrega (se tomaron como base, sin revertirlos): el título de la
    fila de KPIs pasó de "Valores" a "Valores - consolidado convenios
    seleccionados"; el subtítulo "Consolidado" dentro del detalle de cada
    convenio pasó a "Consolidado periodos convenio"; y se acortó la nota
    debajo de los KPIs que explica la base del % (se quitó la frase final
    "— igual criterio que usa el financiero en su Excel, por período."). A
    partir de esa versión, se reordenaron los 5 KPIs principales (fila
    "Valores - consolidado convenios seleccionados") a pedido de Migue: el
    orden pasó de Total/CDP/Ejecutado/Proyectado/No ejecutado a
    **Total/CDP/Proyectado/Ejecutado/No ejecutado** — después del CDP ahora
    va el proyectado, y luego el ejecutado. Nota: este reordenamiento fue
    solo en la fila de KPIs principales de la página; la sección
    "Consolidado periodos convenio" dentro del detalle de cada convenio
    mantiene su propio orden (no se tocó, ya que no se pidió ahí).

    > **Nota (extendido en el punto 30):** el orden de "Consolidado
    > periodos convenio" y de la sección "Ejecución" por período sí se
    > tocaron después — ver el punto 30.

30. **Ejecutado y No ejecutado quedan seguidas (continuidad), en Consolidado
    y en el detalle por período** — Migue pidió que, como mínimo, las
    tarjetas de Valor ejecutado y Valor no ejecutado queden una al lado de
    la otra (para leerlas como pareja: lo pagado vs. lo que falta), y dejó
    abierta la propuesta del resto del orden.

    - **"Consolidado periodos convenio"** (dentro del detalle de cada
      convenio): pasó de Total/Ejecutado/%valor/%tiempo/CDP/Proyectado/No
      ejecutado a **Total → CDP → Proyectado → Ejecutado → No ejecutado →
      % Ejecución (valor) → % Ejecución (tiempo)** — mismo orden de lectura
      que ya tienen los KPIs principales de la página (punto 29) para los
      primeros 5, con Ejecutado y No ejecutado ahora sí consecutivas, y los
      2 porcentajes al final como resumen de esa pareja. "Valor no
      ejecutado" pasó a destacada (antes no lo era) para que tenga el mismo
      peso visual que "Valor ejecutado", ya que se leen juntas.
    - **Sección "Ejecución" del detalle por período**: mismo criterio,
      pasó de Pagado/%valor/No ejecutado/Proyectado a **Proyectado → Pagado
      → No ejecutado → % Ejecución (valor)** — Proyectado como referencia
      antes de la pareja Pagado/No ejecutado (ahora consecutivas), y el %
      al final. "Valor no ejecutado" también pasó a destacada acá por la
      misma razón.

    Es una decisión propia de qué tan "derecho" queda leer el resto — si
    prefiere otro orden, se ajusta.

31. **Rediseño de color del módulo financiero — menos colores, reservados solo
    para estado real** — Migue pidió que el módulo se viera "más amigable a
    la vista", porque tenía muchos colores, muy distintos y muy juntos en
    tarjetas seguidas. Al revisar el código, el problema de raíz era que
    cada tarjeta (`CampoCard`/`KpiCard`) pintaba el número mismo (el texto)
    con un color distinto por campo — incluyendo campos que no representan
    ningún estado real (valores en pesos, números de CDP/RP, conteos de
    postulados/conciliados), solo por costumbre visual. Eso hacía que la
    vista se sintiera "arcoíris" sin que el color comunicara nada. La
    corrección, siguiendo el mismo criterio que ya usan aplicativos de
    datos serios: el color debe reservarse para lo que de verdad es un
    estado (semáforo), y el texto de los valores nunca debe llevar color —
    la identidad/estado se muestra con una marca aparte (un punto de color)
    al lado del texto, no coloreando el número.
    - **Tarjetas "planas"** (valor total, CDP, proyectado, ejecutado, no
      ejecutado, № CDP, № RP, postulados, conciliados, valor conciliado,
      rubros pagados, etc.): todas comparten ahora un solo esquema neutro
      (texto azul-marino oscuro `#1a2b4a`, borde gris `#d1d5db`/`#e5e7eb`),
      sin ningún color de acento por campo.
    - **Únicamente los 2 campos que sí son un estado real** (% Ejecución
      (valor) y % Ejecución (tiempo), tanto en "Consolidado periodos
      convenio" como en el detalle por período) conservan color, pero ahora
      expresado como un punto/semáforo al lado del número (no en el texto)
      y en el borde izquierdo de la tarjeta — con la misma escala de
      siempre: verde `#0ca30c` (bueno, >=70%), amarillo `#fab219`
      (alerta, 35-70%), rojo `#d03b3b` (bajo, <35%), gris `#9ca3af` (sin
      dato).
    - Las 2 barras de progreso de arriba de cada convenio usan la misma
      escala de color (sin cambios en su lógica, solo se les quitó el color
      del número de porcentaje en la cabecera, que ya no lo llevaba ningún
      otro número del módulo).
    - Es una decisión propia de diseño (no un pedido literal de una paleta
      específica) — si algún color puntual no se ve bien, se ajusta.

32. **Rediseño "panel ejecutivo" del módulo financiero (landing moderna,
    pensada para lectura rápida)** — Migue pidió, un paso más allá del punto
    31, una vista más moderna y práctica de leer para presentarle el
    tablero a la directora (perfil muy visual). Se rediseñó la interfaz
    completa del módulo (solo Financiero, sin tocar el resto del
    aplicativo) con 3 decisiones de diseño, explicadas también en el chat:
    - **Tipografía**: "Manrope" (semibold/bold) para títulos y etiquetas de
      sección, e "Inter" para el resto del texto y los valores — pareo
      típico de tableros de datos: Manrope aporta carácter en los títulos
      sin perder seriedad, e Inter es el estándar de legibilidad para
      cifras a tamaños chicos (tiene muy buen soporte de números
      tabulares). Se cargan solo para esta página (no afecta el resto del
      aplicativo).
    - **Un solo color de identidad (violeta `#7c3aed`)**, reservado
      exclusivamente para jerarquía y marca — no para estado. Es, de hecho,
      el mismo tono que ya usa el menú superior de todo el aplicativo para
      la sección activa, así que el módulo queda visualmente conectado con
      el resto del portal en vez de introducir un color nuevo. Se usa en:
      el marcador de cada título de sección, el borde superior de las 5
      tarjetas KPI, el encabezado de cada convenio (franja con fondo
      violeta muy suave), el borde de las tarjetas "destacadas", y el
      borde/título de cada período.
    - **Más aire y jerarquía por capas**: el consolidado principal ahora
      vive en su propio panel elevado ("hero") claramente separado del
      listado de convenios — es lo primero que debe leerse. Se
      reemplazaron bordes duros por sombras suaves, se agrandaron los
      radios de esquina, y se agregó un **fondo suave a juego con el color
      de estado** en las 2 tarjetas de "% Ejecución" (además del borde y el
      punto que ya tenían desde el punto 31) — así una directora que solo
      mira por encima detecta de inmediato si un convenio va bien
      (verde), regular (ámbar) o mal (rojo), sin tener que leer el número.
    - El color de estado (verde/ámbar/rojo/gris) sigue reservado
      exclusivamente para "% Ejecución (valor)" y "% Ejecución (tiempo)" —
      ningún otro campo del módulo lleva ese código de color, siguiendo el
      mismo criterio del punto 31.
    - Es una decisión propia de estilo/paleta/tipografía (Migue pidió
      explícitamente "escoge tú") — si algo puntual no cuaja al verlo en
      vivo, se ajusta.

33. **Carga del excel financiero desde el aplicativo (botón para ADMIN/AF)**
    — antes, cada vez que el financiero mandaba su excel "MC_Financiera",
    alguien tenía que correr a mano
    `scripts/generar_sql_ejecucion_financiera.py` (backend) para traducirlo
    a SQL y pegarlo en un cliente MySQL. Ahora hay un botón "📤 Cargar excel
    financiero" en Información Financiera, visible SOLO para los roles
    ADMIN y AF (Apoyo Financiero) — el backend exige el mismo rol de nuevo
    (`POST /reportes-financieros/cargar-excel`, `require_rol("ADMIN", "AF")`),
    así que el botón oculto no es la única barrera.
    - **Flujo en 2 pasos, mismo archivo las 2 veces**: primero se sube con
      "Previsualizar" — el backend SOLO valida, no escribe nada — y se
      muestra una tabla fila por fila (✅ ok / ⚠️ advertencia / ⛔ error) con
      un resumen de conteos arriba. Si hay al menos 1 fila aplicable,
      "Confirmar y guardar" reenvía el mismo archivo y recién ahí se aplican
      los cambios.
    - **Validaciones que el script manual NO podía hacer** (no tenía acceso
      a la base real desde donde se escribió): que el `convenio_id` de cada
      fila exista, y que el `PERIODO` ya esté creado para ese convenio en
      Administración > Convenios (mismo criterio case/espacios-insensible
      que ya usa la lectura de períodos) — si no, la fila queda en ⛔ error y
      no se aplica.
    - **Advertencias** (se aplican igual, pero vale la pena revisarlas): el
      código o la IES del excel no coinciden con los reales de ese
      convenio_id (posible fila pegada con el ID equivocado); "ADICIONES DE
      RECURSOS" trae valores distintos entre filas del mismo convenio; el
      mismo convenio+período aparece repetido dentro del propio archivo (se
      aplica la última fila leída).
    - **Reutiliza la limpieza de datos ya probada** del script manual:
      "Pendiente"/"Esp. Conci. MEN" se vuelven NULL, montos en texto tipo
      "$ 526.567.802" se convierten a número. Sigue sin guardar columnas
      que son fórmulas de Excel o que ya administra Convenios ("FECHA DE
      INICIO/FINALIZACIÓN", "FECHAS HOY", "% EJECUCIÓN (TIEMPO)", "VALOR
      TOTAL DEL CONTRATO", "VALOR NO EJECUTADO", "% EJECUCIÓN (VALOR)").
    - Subir el mismo archivo 2 veces actualiza en vez de duplicar (usa el
      UNIQUE (convenio_id, periodo) que ya tenía la tabla desde su
      migración original).

## Qué incluye

- Login contra el login de **Seguimiento** (`POST /seguimiento/auth/login`,
  tabla `usuarios_seg_proceso_mc`) — el mismo que ya usa el módulo de
  Seguimiento Convenios MC. Se decidió unificar bajo un solo sistema de
  usuarios/roles (ADMIN, DIRECTORA, LMC, AST, AD, AF, AJ) en vez de usar el
  login genérico de la API, ya que quien necesita Consulta+Tablero es el
  mismo equipo que ya tiene (o puede tener) cuenta de Seguimiento. Cualquier
  rol autenticado puede consultar — es de solo lectura, no se restringe por
  rol específico aquí. Los endpoints de matrícula cero (`api/routers/matricula_cero.py`
  en el backend) usan `Depends(get_current_user_seguimiento)` en vez de
  `Depends(get_current_user)`.
- Si el usuario tiene `primer_login=1` (cuenta recién creada, sin cambiar la
  contraseña por defecto), el login lo redirige obligatoriamente a
  `/cambiar-password` (`POST /seguimiento/auth/cambiar-password`) antes de
  dejarlo usar el resto de la app — mismo requisito de seguridad que ya
  existe en el Seguimiento de Streamlit.
- **Consulta** (`/consulta`): búsqueda por documento contra
  `GET /matricula-cero/consulta` (vista `vw_matricula_cero_2026_2`).
- **Tablero** (`/tablero`): información personal
  (`GET /matricula-cero/tablero/info-personal`) + historial de giros/seguimiento
  académico (`GET /matricula-cero/tablero/giros`), con el mismo filtro de
  "solo períodos del proyecto (2023-2 en adelante)" que tenía el Streamlit.
- **`/inicio`** (pantalla tras el login): selector entre los dos
  aplicativos (Consulta+Tablero / Seguimiento) — login y cambio de
  contraseña de primer ingreso redirigen aquí, y el logo del header
  también es un link de vuelta a esta pantalla.
- **Seguimiento** (`/seguimiento`): arriba de todo, una tarjeta "Repositorio
  de expedientes" con un botón "Abrir carpeta ↗" que enlaza directo a la
  carpeta compartida de OneDrive donde se cargan los documentos — mismo
  link y ubicación que la `onedrive-card` del Streamlit original (justo
  antes de los filtros). Luego, lista de convenios (con filtro por
  estado, buscador por código y selector de IES — igual que
  `filtro_codigo`/`filtro_ies` en `pagina_tablero()` del Streamlit
  original: el código hace match parcial sin distinguir mayúsculas, la
  IES es coincidencia exacta contra el dropdown, y ambos se combinan con
  el filtro de estado; un botón "🗑️ Limpiar filtros" aparece solo cuando
  hay código o IES activos y resetea solo esos dos, sin tocar el estado)
  contra `GET /seguimiento/convenios`. Cada tarjeta se pinta con
  los mismos colores del Streamlit original según su nivel de alerta más
  urgente vigente (`nivel_alerta`/`motivos_alerta`, ahora calculados
  también en el listado, no solo en el detalle — ver
  `calcular_nivel_alerta_convenio` en `list_convenios`). Debajo del
  encabezado, cada tarjeta desglosa uno por uno los períodos del convenio
  (`GET /seguimiento/convenios/:id/periodos`), cada uno con su propia
  barra de progreso (reutiliza `.global-progress-bg`/`.global-progress-fill`
  de la línea de tiempo) — igual que la vista de resumen del Streamlit
  original, que mostraba un `pct_periodo` por período dentro de cada
  tarjeta. El backend calcula ese `porcentaje_avance` por período sobre la
  etapa (tipo) actualmente activa del convenio según su estado (mismo
  criterio que `ESTADO_A_TIPO_ACTIVO`), reutilizando la misma lógica de
  promedio que ya existía para los Informes
  (`_get_progreso_periodo` en `api/core/informes_seguimiento.py`). Hacer
  clic en la fila de un período específico navega directo a
  `/seguimiento/convenios/:id?periodo=<id>`, dejando ese período
  preseleccionado en el detalle (en vez del período que se autoselecciona
  por `periodo_academico`). El texto de estas tarjetas (código, IES,
  badges, filas de período y su %) se agrandó un poco — se veía
  demasiado pequeño comparado con el resto de la app.
  Cada convenio abre en
  `/seguimiento/convenios/:id` con: datos generales completos (Supervisor,
  Apoyo a la supervisión, Valor — formateado como moneda con separador de
  miles, Fecha inicio y fin del convenio, Todos los períodos, las 3 fechas
  límite de liquidación —voluntaria/unilateral/judicial— más Vencimiento de
  póliza, Registrado por y Observaciones generales — igual al panel "📁
  Información general del convenio" del Streamlit original; el backend ya
  traía casi todos estos campos en `GET /seguimiento/convenios/:id` pero el
  frontend no los estaba mostrando, y `creado_por` no venía en absoluto —
  se agregó a la consulta y al modelo `ConvenioDetalleOut`) + banner de
  nivel de alerta (`AVISO`/`URGENTE`/`CRÍTICO`, cuando aplica), selector de
  período
  (`GET /seguimiento/convenios/:id/periodos`) y tabs de etapa
  (Ejecución/Liquidación/Cierre — arranca en la etapa activa según el
  estado del convenio, igual que el Streamlit original). La línea de
  tiempo (`<TimelineActividad>`) agrupa las actividades por subcategoría
  con burbujas coloreadas por estado (`GET /seguimiento/periodos/:id/actividades`);
  al hacer clic en una burbuja se abre `<ActividadModal>` con el historial
  de comentarios de esa actividad y, si el rol lo permite, un formulario
  para actualizar avance/comentario (`PATCH .../avance`), marcar o
  revertir "No aplica" (`PATCH .../no-aplica`), y programar/desactivar un
  recordatorio por correo (`PATCH .../recordatorio`). Si el avance hace
  que el convenio cambie de estado automáticamente, se muestra un aviso
  (igual que el `st.success` del Streamlit original) y se refrescan los
  datos del convenio.
  - El rol **DIRECTORA** es de solo lectura en todo este módulo (así lo
    exige el backend con 403 en los PATCH) — la UI oculta el formulario de
    edición y muestra un aviso en su lugar, en vez de dejar que el usuario
    intente guardar y se encuentre con el error recién en la respuesta.
- **Informes** (botones dentro de `/seguimiento/convenios/:id`): la
  descarga se hace con `apiClient.post(url, formData, { responseType:
  "blob" })` en vez de un `<a href>` directo, porque el PDF requiere el
  header `Authorization: Bearer` (que un link plano no puede llevar) y
  ahora puede llevar imágenes adjuntas (que no caben en query params de un
  `GET`). El nombre de archivo se lee del header `Content-Disposition` de
  la respuesta. Los comentarios/imágenes por subcategoría que se agregan en
  el modal no se guardan en ningún lado — viajan en ese mismo `FormData` y
  se descartan en el backend apenas se termina de generar ese PDF puntual
  (ver punto 11 del historial arriba).

## Qué NO incluye todavía (a propósito)

- El bloque de **Solicitudes** del tablero viejo (hoy lee un Excel) — queda
  pendiente hasta que ese dato pase a vivir en una tabla de la base de datos,
  como se acordó.

## Cómo correrlo

```bash
npm install
cp .env.example .env   # ajusta VITE_API_BASE_URL a donde esté corriendo la API
npm run dev
```

La API (`consultar_registro_db-main`) debe estar corriendo aparte y
accesible en la URL que pongas en `VITE_API_BASE_URL` — por defecto
`http://localhost:8080`. `app.py` ya tiene `CORSMiddleware` habilitado
(`allow_origins=["*"]`, seguro porque la auth es 100% por header Bearer, sin
cookies) y ahora también `expose_headers=["Content-Disposition"]` — sin
esto último, el navegador bloquea la lectura de ese header cross-origin por
defecto y la descarga de Informes en PDF cae siempre al nombre de archivo
genérico (`informe.pdf`) en vez del nombre real que arma el backend. Si
despliegas la API en otro entorno, confirma que esta configuración de CORS
viaje con el despliegue.

## Stack

Vite + React 19 + TypeScript, TanStack Query (estado de servidor / caché),
React Router (rutas), Axios (HTTP), tal como se recomendó en el plan de
migración. Todavía no se agregaron pruebas automatizadas (ver "Preguntas
abiertas" del plan) ni una librería de componentes (Mantine / shadcn) — el
estilo actual es CSS propio simple, mínimo, para esta primera entrega.

## Sesión / autenticación

El token JWT (emitido por `/seguimiento/auth/login`, con claim
`"modulo": "seguimiento"`) se guarda en `localStorage` (`portal_mc_token`,
junto con `portal_mc_user` y `portal_mc_primer_login`) y se adjunta
automáticamente a cada request vía un interceptor de Axios
(`src/api/client.ts`). Si la API responde 401, el token se limpia
automáticamente y la siguiente navegación a una ruta protegida redirige a
`/login`. Si `primer_login` está pendiente, `<ProtectedRoute>` redirige a
`/cambiar-password` en vez de mostrar el contenido. Nota de seguridad:
`localStorage` es más simple que el patrón recomendado en el plan (refresh
token en cookie `httpOnly`), pero el backend actual solo emite un
`access_token` de 7 días sin refresh — migrar a cookies `httpOnly`
requeriría cambios en el backend, fuera del alcance de esta primera
entrega.

## Estructura

```
src/
  api/            Llamadas HTTP (auth, matriculaCero, seguimientoConvenios,
                  seguimientoActividades, seguimientoIes, seguimientoCatalogo,
                  seguimientoUsuarios) + cliente Axios
  context/        AuthContext (sesión, incluye primer_login)
  constants/      roles.ts (ROL_LABELS, permisos por rol), estados.ts (colores por estado/alerta)
  components/     Layout, ProtectedRoute, TimelineActividad, ActividadModal
  components/admin/  AdminIesTab, AdminConveniosTab, AdminCatalogoTab, AdminUsuariosTab
  pages/          LoginPage, ChangePasswordPage, AppSelectorPage, ConsultaPage,
                  TableroPage, SeguimientoListPage, SeguimientoConvenioPage,
                  SeguimientoAdminPage
```

## Verificación hecha en esta entrega

- `tsc -b` sin errores, `npm run build` compila.
- Probado con Playwright contra respuestas simuladas de la API (sin acceso
  real a la BD desde este entorno):
  - Auth: login contra `/seguimiento/auth/login`, redirección de rutas
    protegidas, flujo de cambio de contraseña forzado en primer login,
    cierre de sesión.
  - Consulta/Tablero: búsqueda con y sin resultados.
  - Seguimiento (Reporte de actividades): lista de convenios con banner de
    alerta, apertura del detalle con línea de tiempo, apertura del modal de
    actividad con su historial, guardar avance al 100% y verificar el aviso
    de transición automática de estado del convenio, marcar y revertir "No
    aplica", guardar un recordatorio, y confirmar que el rol DIRECTORA ve
    todo en modo solo lectura (sin formulario de edición ni botones de
    acción).
  - Selector de aplicativo (`/inicio`): el login aterriza ahí, y el menú
    superior muestra solo las secciones del aplicativo activo (Consulta+Tablero
    o Seguimiento), nunca ambas mezcladas.
  - Administración: alta en cada una de las 4 pestañas (IES, Convenios,
    Catálogo, Usuarios) contra sus endpoints reales, y confirmación de que
    un rol distinto a ADMIN (probado con AST) ve el mensaje de "solo para
    administradores" y no ve el link de Administración en el menú.
  - Informes: el botón "Informe de este período" aparece siempre que hay un
    período seleccionado; el botón "Informe consolidado" aparece solo si el
    convenio tiene más de un período (y no aparece con uno solo); el modal
    abre con los 6 checkboxes marcados por defecto; al desmarcar uno y
    descargar, se dispara un evento de descarga real del navegador con el
    nombre de archivo correcto (leído de `Content-Disposition`) y los query
    params correctos (`incluir_comentarios=false`, resto `true`); el modal
    se cierra solo tras una descarga exitosa. Esta prueba fue la que
    detectó que faltaba `expose_headers=["Content-Disposition"]` en el CORS
    del backend — sin eso, el nombre de archivo siempre caía al genérico
    `informe.pdf`, ya corregido en `app.py`.
  - Barras de progreso por período en `/seguimiento`: cada tarjeta muestra
    el número correcto de filas de período con su % y ancho de barra
    correspondientes (probado con un convenio de 2 períodos con distinto
    avance, y otro con 1 período en 0%); hacer clic en la fila de un
    período específico navega a `/seguimiento/convenios/:id?periodo=<id>`
    y ese período queda preseleccionado en el selector del detalle. La
    lógica de `porcentaje_avance` por período en el backend (tipo activo
    según el estado del convenio) se probó además con un test unitario
    (mockeando la conexión a la BD) para confirmar que usa la etapa
    correcta — ej. "En liquidación" → se promedia sobre actividades tipo
    `liquidacion`, no `ejecucion`.
  - Grilla de 3 tarjetas por línea en `/seguimiento`: confirmado con
    Playwright a 1440px de ancho que 6 tarjetas se acomodan en 2 filas de 3.
  - Buscador de convenios en `/seguimiento`: el dropdown de IES arma sus
    opciones ("Todas" + únicas, ordenadas) a partir de los convenios
    cargados; buscar por código hace match parcial sin distinguir
    mayúsculas/minúsculas; el filtro de IES y el de código se combinan
    entre sí y con el filtro de estado (probado filtrando por IES, luego
    por código, luego por estado + código a la vez); "Limpiar filtros"
    solo aparece con código o IES activos, y al hacer clic resetea ambos
    sin tocar el filtro de estado.
  - Tarjeta de repositorio de expedientes en `/seguimiento`: aparece antes
    del buscador, el botón "Abrir carpeta ↗" apunta a la URL correcta de
    OneDrive, abre en pestaña nueva (`target="_blank"`) y con
    `rel="noopener noreferrer"` (buena práctica de seguridad para links
    externos). Tamaño de letra de las tarjetas de convenio confirmado con
    valores computados de fuente (código, IES, filas de período y %, todos
    más grandes que antes).
  - Sincronización automática del catálogo: probado con un test unitario
    (mockeando la conexión a la BD) que `create_actividad_catalogo` recorre
    todos los períodos existentes y llama `crear_instancias_actividades`
    con el `tipo` correcto para cada uno, y que el conteo de
    `periodos_sincronizados` refleja cuántos períodos realmente recibieron
    la actividad nueva (no cuántos se revisaron). Con Playwright: crear una
    actividad en Administración → Catálogo muestra el mensaje "Actividad
    agregada y sincronizada automáticamente en N de M período(s)
    existente(s)".
  - Campo Valor como moneda: escribir dígitos en el input muestra el valor
    formateado con separador de miles en tiempo real; al expandir un
    convenio existente para editarlo, el valor ya guardado aparece
    preformateado igual (probado con `16562226354` → `16.562.226.354` en
    ambos casos).
  - Información completa del convenio en `/seguimiento/convenios/:id`:
    probados con Playwright los 12 campos del panel de datos generales
    (Supervisor, Apoyo, Valor formateado, Fecha inicio, Fecha fin, Todos
    los períodos, las 3 fechas límite de liquidación, Vencimiento póliza,
    Registrado por y Observaciones generales), confirmando en particular
    los 3 que antes no se mostraban en absoluto (Límite liquidación
    unilateral, Límite liquidación judicial, Registrado por) y los que ya
    venían de la API pero no se renderizaban (Valor, fechas de inicio/fin,
    Todos los períodos, Observaciones).
  - Fix del 422 en "Agregar actividad": reproducido el bug original
    directamente contra `ActividadBaseCreate` de Pydantic con el body real
    que manda el frontend (sin `tipo`) — antes del fix lanzaba
    `ValidationError: tipo Field required`; después, valida sin error.
    También probado el endpoint completo (`create_actividad_catalogo`)
    mockeando la conexión a la BD, confirmando que crea la actividad e
    inicia la sincronización igual que antes. Con Playwright: simulando la
    respuesta 422 exacta que el backend real devolvía (`detail` como lista
    con `{loc: ["body","tipo"], msg: "Field required"}`), el mensaje de
    error ahora dice "tipo: Field required" en vez de "[object Object]"; y
    reintentando con el backend ya corregido, la actividad se crea sin
    error.
  Falta la prueba end-to-end contra la API real con credenciales reales de
  Seguimiento — pendiente de correr en tu máquina/entorno con conectividad
  a la base de datos real.
  - Actividad 99→100 y Directora en voluntaria/unilateral: verificado
    corriendo el Code node real de n8n (Node.js) contra filas simuladas —
    confirmado que `recordatorio_firma_acta_cierre` genera título/asunto
    propios ("...falta publicar en SECOP II (acta de cierre)") y que
    `categoria_legible` resuelve a "Cierre"; confirmado que `voluntaria` y
    `unilateral` ahora incluyen al Supervisor(a) en destinatarios
    (`Apoyo a la Supervisión y Supervisor(a)`) mientras que `poliza` sigue
    siendo solo para el Apoyo (sin cambios). También se verificó que las 15
    ramas del `UNION ALL` del SQL siguen teniendo las mismas 12 columnas en
    el mismo orden (chequeo automático por bloque) y que el nodo `If1`
    excluye correctamente los 6 tipos recurrentes (incluyendo el nuevo) de
    la tabla de notificaciones de una sola vez. Y, como en el punto 8, se
    agregó 99 a `ACTIVIDADES_CON_FECHA_MANUAL` — confirmado con `tsc -b` y
    una prueba directa en Node de que 99 resuelve a su etiqueta mientras que
    100 (la actividad destino) correctamente no la muestra.
  - Rediseño de Informes (punto 11): el pipeline de procesamiento de
    imágenes se probó de forma aislada — construyendo una imagen de
    referencia sin ambigüedad (franjas de color + texto), rotándola 90°
    para simular una foto "cruda" de celular, etiquetándola con
    `orientation=6`, y confirmando que `procesar_imagen_para_pdf` la
    recupera pixel a pixel igual a la referencia original; una imagen PNG
    con transparencia se aplana sobre blanco (no negro); y bytes inválidos
    lanzan un error controlado (se omiten en el PDF en vez de tumbar la
    petición). Se generó un PDF de prueba completo (2 tipos, 3
    subcategorías, con 3/1/0 imágenes respectivamente) y se renderizó a PNG
    con `pdftoppm` para inspección visual página por página: la grilla de 3
    imágenes, la de 1 imagen grande, y la subcategoría sin imágenes (solo
    comentario) se ven correctas, sin distorsión ni recortes. En el
    frontend, se probó el modal completo con Playwright contra respuestas
    simuladas del backend (checkboxes, bloques por subcategoría con su %,
    escribir un comentario, adjuntar una imagen real y ver la miniatura,
    colapsar un bloque, desmarcar "Actividades de liquidación" y confirmar
    que su bloque desaparece, y generar/descargar el PDF confirmando el
    `POST` multipart y el nombre de archivo). Esta prueba fue la que
    detectó un bug real: al adjuntar una imagen, el `onChange` del `<input
    type="file">` limpiaba `e.target.value = ""` inmediatamente después de
    llamar al actualizador de estado — pero como ese actualizador se
    ejecuta de forma diferida (no en el mismo tick), para cuando React lo
    corría el `FileList` en vivo ya había quedado vacío por la limpieza del
    input, así que la imagen "se adjuntaba" sin ningún error pero nunca
    aparecía la miniatura. Se corrigió copiando los archivos a un array
    plano de forma síncrona antes de limpiar el input; repetida la prueba,
    la miniatura aparece correctamente.
  - Corrección del punto 10 (99→100 = mismo patrón que firma directora
    DTF): verificado que el bloque SQL reescrito sigue con 12 columnas
    (chequeo automático de las 15 ramas del `UNION ALL`), que no queda
    ningún rastro de `recordatorio_firma_acta_cierre` en el SQL ni en el
    Code node (`grep` en 0), y que `If1` quedó con 5 condiciones (las 3
    originales más `recordatorio_firma_ejecucion`/`recordatorio_pago_ejecucion`,
    sin la del tipo eliminado). Corriendo el Code node real con una fila
    simulada para 99→100, el título/asunto ahora sale igual que
    74→73/85→86/97→98 ("Van N día(s) pendientes de publicar en SECOP II —
    {{subcategoría}}"), y `tsc -b` sigue sin errores tras corregir la
    etiqueta de la actividad 99 en el frontend.
  - Fix del campo de fecha manual en actividades 74/71: confirmado por
    inspección de `ACTIVIDADES_CON_FECHA_MANUAL` (mismo mecanismo ya usado
    en producción para las actividades 36/22 de liquidación, solo se
    agregaron las 2 entradas nuevas) y `tsc -b` sin errores. Verificado con
    un script en Node que las actividades 74 y 71 ahora resuelven a su
    etiqueta ("Fecha real de firma de la Directora (informe y recibo)" y
    "Fecha real de orden de pago" respectivamente) mientras que las
    actividades objetivo 73, 76 y 23 correctamente NO muestran el campo
    (la fecha manual se diligencia solo en la actividad de origen de cada
    cadena, no en la que se está esperando).
  - Administración → Usuarios: eliminar y cambiar contraseña (punto 14):
    probado con una base SQLite en memoria (mismo esquema de
    `usuarios_seg_proceso_mc` + una tabla con FOREIGN KEY hacia ella, para
    reproducir el mismo bloqueo de integridad que dispara MySQL) llamando
    directamente a los endpoints del router: un ADMIN no puede eliminarse a
    sí mismo (400), eliminar un id inexistente da 404, eliminar un usuario
    con historial asociado lanza el `IntegrityError` esperado y el endpoint
    lo captura devolviendo 409 con el mensaje claro (confirmado que el
    usuario sigue existiendo después, sin quedar la conexión en un estado
    roto), eliminar un usuario sin historial sí lo borra, y el reseteo de
    contraseña actualiza el hash y vuelve a marcar `primer_login=1`. Con
    Playwright (respuestas simuladas): el botón "Eliminar" sale
    deshabilitado en la fila del usuario con la sesión iniciada; el
    formulario de "Cambiar contraseña" rechaza una contraseña de menos de 8
    caracteres, acepta una válida y se cierra solo; al intentar eliminar un
    usuario con historial se ve el mensaje de error 409 tal cual lo manda
    el backend y la fila no desaparece; eliminar uno sin historial sí lo
    quita de la lista.
  - Fecha límite por subcategoría (punto 16): probado con SQLite en memoria
    llamando directamente a los 3 endpoints — el rol Directora no puede
    definir ni quitar una fecha límite (403), un `tipo` inválido se
    rechaza (400), definir una fecha por primera vez crea la fila,
    volverla a definir la ACTUALIZA en vez de duplicarla (se confirmó que
    sigue habiendo una sola fila para esa subcategoría) y reescribe
    `fecha_definicion`, y quitarla la borra. En el frontend, con Playwright
    y 6 subcategorías de prueba: sin fecha límite se ve el degradado
    morado/azul de siempre; con fecha límite recién definida (elapsed ≈0%)
    se ve verde; a la mitad del plazo, ámbar; cerca del vencimiento y ya
    vencida, rojo en ambos casos; una subcategoría 100% completada con
    fecha ya vencida se ve verde igual (la regla acordada de "completada
    manda sobre la fecha" se cumple) — los 5 casos se verificaron leyendo
    el `background-color`/`background-image` computado del navegador, no
    solo mirando la captura. Definir una fecha nueva desde "Sin fecha
    límite" y luego "Quitar" una ya definida funcionan de punta a punta
    (dispara el `PUT`/`DELETE`, refresca el texto y el color). Con el rol
    Directora, los botones "Definir"/"Editar"/"Quitar" no aparecen en
    absoluto (0 en la página), aunque los colores se siguen calculando
    igual — confirma que es una restricción real de UI, no solo un dato
    que el backend rechazaría si se intentara.
  - "Último comentario" en el resumen ejecutivo del informe (punto 17):
    generado un PDF de prueba invocando `generar_pdf_informe` directamente
    con datos simulados (dos subcategorías, una con último comentario y otra
    sin ninguno) y revisado visualmente convirtiéndolo a imagen — la fila de
    comentario aparece fusionada (`SPAN`) justo debajo de su subcategoría,
    con fondo gris para distinguirla, y la subcategoría sin comentarios no
    trae fila extra. Se probó a propósito con un comentario, un nombre de
    usuario y texto conteniendo `<`, `>`, `&` y comillas dobles — el PDF se
    generó sin errores y esos caracteres se ven tal cual, en vez de romper
    la generación o interpretarse como markup. (De paso se encontró que el
    emoji 💬 pensado originalmente para esa fila salía como un cuadro vacío
    — la fuente estándar del PDF no tiene esos glifos — así que se cambió
    por el texto en mayúsculas "ÚLTIMO COMENTARIO".) En el frontend, con
    Playwright y el backend simulado: el modal de informes ya no muestra el
    checkbox "Historial de comentarios" (quedan 7 opciones en vez de 8), y
    generar y descargar el informe completo sigue funcionando de punta a
    punta — confirmado además que el `FormData` enviado al backend ya no
    incluye el campo `incluir_comentarios`.
  - Tarjetas KPI en `/seguimiento` (punto 18): probado con Playwright y 5
    convenios simulados (2 IES distintas, 3 estados distintos) — "Total de
    convenios" muestra 5 sin importar los filtros; sin ningún filtro activo,
    "Convenios con filtros actuales" también muestra 5 y la nota dice "Sin
    filtros activos"; al activar el filtro de categoría "En ejecución" el
    número baja a 2 y la nota cambia a "Categoría: En ejecución"; al agregar
    además el filtro de IES el número baja a 1 y la nota muestra ambos
    filtros juntos — en los tres casos el número coincidió exactamente con
    la cantidad de tarjetas de convenio visibles debajo. Sin errores de
    consola en ningún paso.
  - Mínimo visible en la barra semaforizada con 0% de avance (punto 19):
    probado con Playwright, 4 subcategorías simuladas en 0% de avance — una
    con fecha límite recién definida (zona verde), una a mitad de plazo
    (zona ámbar), una cerca del vencimiento (zona roja) y una sin fecha
    límite. Se midió el ancho renderizado real de la barra (`boundingBox`) y
    su color computado: las 3 con fecha límite mostraron exactamente 6px de
    ancho con el color esperado (verde/ámbar/rojo, respectivamente) pese al
    0% de avance; la que no tiene fecha límite se quedó en 0px, igual que
    antes de este cambio — confirma que el mínimo no se activa cuando no hay
    ningún color de semáforo que mostrar. (La prueba se hizo con el valor
    inicial de 6px, antes de que Migue lo ajustara a 30px por su cuenta; el
    comportamiento — se activa solo cuando hay color de semáforo definido —
    no cambia con el nuevo valor.)
  - Filtro por nivel de alerta en `/seguimiento` (punto 20): probado con
    Playwright y 5 convenios simulados (2 sin alerta, 1 con AVISO, 1 con
    URGENTE, 1 con CRÍTICO) — al hacer clic en cada botón del nuevo filtro
    "Nivel de alerta" el conteo de tarjetas visibles bajó exactamente a lo
    esperado en cada caso (5 → 2 con "Sin alerta" → 1 con "Aviso" → 1 con
    "Urgente" → 1 con "Crítico" → 5 de vuelta con "Todos"), y la nota de la
    tarjeta KPI "Convenios con filtros actuales" (punto 18) mostró "Alerta:
    Sin alerta" / "Alerta: AVISO" / etc. en cada paso. Se confirmó además,
    leyendo el `background-color` computado del botón activo en cada caso,
    que coincide exactamente con el color de acento que ya usa la tarjeta de
    ese mismo nivel de alerta (por ejemplo, el botón "Crítico" activo quedó
    en el mismo rojo que el borde/badge de las tarjetas en estado crítico) —
    no solo mirando la captura de pantalla, sino el valor real aplicado en
    el DOM.
  - Módulo "Inversión y Beneficios" en `/inversion` (punto 21): backend
    verificado con `python3 -m py_compile` sobre el nuevo modelo/router y
    con `import app` (arranca sin errores, confirmando que el router quedó
    bien registrado en app.py). La lógica de filtros (`_construir_where`) se
    probó aparte de forma unitaria (sin necesidad de la base de datos real,
    que está en una IP privada no alcanzable desde este sandbox): se armó
    una base SQLite en memoria con filas de ejemplo — incluida una fila con
    `estado_semestral='RETIRADO'` con montos altísimos a propósito — y se
    confirmó que esa fila queda excluida tanto de los conteos
    (beneficios/beneficiarios) como de las sumas de dinero; que combinar
    varias IES + un año a la vez filtra correctamente con `IN (...)`; y que
    "por_ies" con `excluir="ies"` efectivamente ignora el filtro de IES
    (para mantener el ranking completo) mientras sigue respetando año.
    Frontend verificado con `npx tsc -b` limpio y con Playwright contra un
    backend simulado (mockeando `GET /reportes-inversion/resumen`): se
    confirmó que las 6 tarjetas KPI muestran los valores del mock, que el
    pie chart renderiza sus 3 porciones con las etiquetas de porcentaje
    correctas, que el nuevo `MultiSelectDropdown` permite marcar 2 IES a la
    vez (el botón cambió a "2 seleccionadas") y que el request real llevó
    `?ies=Universidad+A&ies=Universidad+B` (parámetros repetidos, sin
    corchetes — confirmado leyendo la URL interceptada, no solo la
    pantalla); que al agregar además el filtro de año, el desplegable de
    período se acotó a los períodos de ese año; y que la gráfica de barras
    cambia de "por IES (top 12)" a "por período" en cuanto hay al menos una
    IES seleccionada. Se confirmó también que "Limpiar filtros" deja la URL
    sin parámetros. Sin errores de consola en ningún paso.
  - Reagrupación de las tarjetas KPI y ajuste del pie chart (dentro del
    punto 21): probado con Playwright usando montos grandes y realistas
    (ej. $96.544.208.064 en total, 71.510 beneficios) para forzar un caso de
    rubros desbalanceados (46% / 3% / 52%). Se confirmó que las 4 tarjetas
    de dinero quedan en la fila "Inversión ejecutada" y las 2 de conteos en
    la fila "Alcance" (leyendo el texto de cada tarjeta por fila, no solo
    mirando la captura), y que las tarjetas de "Alcance" ya no se estiran a
    la mitad de la pantalla cada una. Con ese mismo escenario desbalanceado
    se confirmó que el pie chart (ahora con el porcentaje en la leyenda, no
    en etiquetas con línea guía) ya no corta ningún texto contra el borde
    de la tarjeta — antes, con el rubro en 3%, la etiqueta "Derechos
    complementarios: 3%" quedaba parcialmente cortada.
  - Modelo "todas marcadas, desmarcar para excluir" en `MultiSelectDropdown`
    (dentro del punto 21): probado con Playwright con el filtro de año (6
    años simulados, 2020-2025) — se leyó el estado `checked` real de las 6
    casillas al abrir el dropdown por primera vez (con el filtro en "Todos
    los años") y se confirmó que las 6 vienen marcadas, no vacías. Al
    desmarcar 2025, se confirmó tanto el texto del botón ("Todas menos
    2025") como los parámetros reales enviados al backend (leyendo la URL
    interceptada: `anio=2020&anio=2021&anio=2022&anio=2023&anio=2024`, es
    decir, todos menos el excluido). Al desmarcar también 2024, el botón
    cambió a "Todas menos 2" y la URL reflejó los 4 años restantes. Al
    volver a marcar ambos, el filtro se normalizó de nuevo a "Todos los
    años" y la URL quedó sin ningún parámetro de año — confirmando que
    "todas marcadas" y "sin filtro" se tratan como el mismo estado.
  - Columna `valor_proyectado` en convenios (punto 22): backend verificado
    con `python3 -m py_compile` sobre el router y los modelos editados, y
    con `import app` (arranca sin errores). Frontend verificado con `npx
    tsc -b` limpio y con Playwright contra un backend simulado: en el
    formulario "Registrar nuevo convenio" se llenó el campo "Valor
    proyectado" y se confirmó que el `POST /seguimiento/convenios`
    interceptado llevó `valor_proyectado: 6000000`; al expandir un convenio
    ya existente (mock con `valor_proyectado: 1200000`), el campo del
    formulario de edición apareció pre-cargado como "1.200.000" (mismo
    formato de miles que "Valor"); al cambiarlo y guardar, se confirmó que
    el `PUT /seguimiento/convenios/1` interceptado llevó
    `valor_proyectado: 7500000`. Sin errores de consola en ningún paso. El
    servidor de desarrollo (`vite`) se detuvo y se eliminaron los archivos
    temporales de la prueba al terminar.

  - Corrección de `valor_proyectado` a por período + módulo "Información
    Financiera" (punto 23): backend verificado con `python3 -m py_compile`
    e `import app` sobre todos los archivos tocados (modelos y router de
    Seguimiento Convenios editados, y los nuevos `reportes_financieros.py`
    de modelos y router), sin errores. La lógica SQL del nuevo router se
    verificó contra un stand-in de SQLite en memoria (no hay acceso a la
    BD real desde este entorno): la suma `SUM(valor_pagado)` /
    `SUM(valor_proyectado_periodo)` agrupada por convenio da el total
    correcto con varios períodos; `COALESCE` deja los convenios sin
    ninguna fila de ejecución todavía en 0 (no los excluye ni lanza
    error); el filtro de IES acota correctamente la lista de convenios; y
    el `LEFT JOIN` de períodos con `UPPER(TRIM())` muestra los períodos
    que el financiero aún no ha alimentado con sus campos en blanco, no
    los omite. La función `_pct_ejecucion_tiempo` se probó de forma
    aislada para los casos borde: convenio que aún no empieza (0%),
    convenio ya terminado (100%, no más), fechas faltantes (`None`, no
    error) y duración cero (`None`). Frontend verificado con `npx tsc -b`
    limpio (se corrigió un import de `useMemo` sin usar) y con Playwright
    contra un backend simulado: el selector de aplicativos (`/inicio`)
    muestra las 3 tarjetas (Consulta+Tablero, Seguimiento, Información
    Financiera); en `/financiero` las tarjetas KPI muestran los valores
    del mock (confirmado el total de $50.046.215.457 sumando los
    convenios simulados); el filtro "todas marcadas, desmarcar para
    excluir" se probó igual que en Inversión — al hacer clic en "505 DE
    2025" (marcado por defecto) el request real quedó como
    `?convenio=506+DE+2025`, confirmando que excluyó el que se
    desmarcó; al expandir un convenio se ve la tabla de períodos, con
    "Sin conciliar" en los 3 rubros pagados de un período que el mock
    dejó sin esos datos. Sin errores de consola en ningún paso. El
    servidor de desarrollo (`vite`) se detuvo y se eliminaron los
    archivos temporales de la prueba al terminar.

  - Fix de `% ejecución (valor)` / `valor no ejecutado` contra la base
    correcta, y filtro con buscador + chips (punto 24): la fórmula corregida
    se validó primero directo contra el excel real del financiero con un
    script de `openpyxl` (`data_only=False`) que confirmó las fórmulas
    exactas de las columnas W y X (`=N2-V2` y `=V2/N2` — CDP y pagado, no
    valor total ni proyectado); luego con un stand-in de SQLite en memoria
    usando los valores reales de 2 convenios se confirmó que la fórmula
    nueva da 87.3% (igual al resultado de la fórmula del excel,
    6.363.357.116/7.289.831.152) donde la fórmula vieja daba 38.4% contra
    el valor total. Backend verificado además con `python3 -m py_compile` e
    `import app` sin errores. Frontend: `npx tsc -b` limpio, y con Playwright
    contra un backend simulado (con los mismos 2 convenios reales) se
    confirmó que la tarjeta KPI "Valor CDP" aparece, que "% Ejecución
    (valor)" agregado muestra 91% (no el ~40% de antes), que la fila de
    convenio muestra el mini-valor "CDP", y que al expandir un convenio la
    tabla de períodos trae las 2 columnas nuevas ("Valor no ejecutado", "%
    Ejecución (valor)") con el 87% esperado en la fila de período. Para el
    filtro nuevo (`SearchMultiSelect`): se confirmó que el de Convenio
    arranca sin ningún chip (0 chips, no todas marcadas); que buscar "ITM"
    en el de IES deja una sola opción visible en el desplegable
    ("Instituto ITM"); que hacer clic en "505 DE 2025" agrega el chip y que
    el `GET /reportes-financieros/resumen` interceptado quedó con
    `?convenio=505+DE+2025`; y que hacer clic en la "×" del chip lo quita y
    la siguiente request ya no lleva el parámetro `convenio` (vuelve a
    "todas"). Sin errores de consola en ningún paso. El servidor de
    desarrollo (`vite`) se detuvo y se eliminaron los archivos temporales de
    la prueba al terminar.

  - Filtros facetados y detalle en tarjetas (punto 25): la lógica de
    facetado se verificó primero contra un stand-in de SQLite en memoria
    con 3 convenios (2 de una IES, 1 de otra) — confirmando que filtrar por
    IES "Politécnico ABC" deja solo sus 2 convenios como opción en el
    desplegable de Convenio (excluyendo el de la otra IES), y que filtrar
    por el convenio de la otra IES deja una sola opción en el desplegable
    de IES. Backend verificado además con `python3 -m py_compile` e
    `import app` sin errores. Con Playwright, contra un backend simulado
    con esos mismos 3 convenios: se confirmó que sin filtro aparecen los 3;
    que al elegir la IES "Politécnico ABC" el desplegable de Convenio queda
    con exactamente `{505 DE 2025, 507 DE 2025}` (sin el 506); y que, tras
    limpiar y elegir el convenio "506 DE 2025", el desplegable de IES queda
    con una sola opción ("Instituto ITM"). Para las tarjetas: se confirmó
    que al expandir un convenio no queda ningún `<table>` en la página, que
    aparece la sección "Consolidado", que cada período tiene su propia
    tarjeta contenedora con las 4 secciones internas en el orden esperado
    ("Ejecución", "CDP y RP", "Postulación y conciliación", "Rubros
    pagados"), y que la sección "Ejecución" trae el 87% correcto (mismo
    valor validado en el punto 24). Sin errores de consola en ningún paso.
    El servidor de desarrollo (`vite`) se detuvo y se eliminaron los
    archivos temporales de la prueba al terminar.

  - Información obligada a elegir convenio, sin clic para ver detalle
    (punto 26): `npx tsc -b` limpio tras quitar el estado de
    expandir/colapsar. Con Playwright, contra un backend simulado con 2
    convenios: se confirmó que al entrar a la página no aparece ningún
    `.fin-item` ni ninguna fila de KPIs (`.fin-kpi-row`), solo el mensaje
    de "Elige uno o más convenios..."; que al elegir un convenio en el
    filtro (sin tocar el de IES) aparecen de una, sin ningún clic
    adicional, tanto los KPIs como la sección "Consolidado" y la tarjeta
    del período de ese convenio (y que ya no queda ningún elemento de
    "caret"/flecha de expandir en la interfaz); que al agregar un segundo
    convenio se apilan los 2 detalles completos (2 `.fin-item`, 2
    `.fin-periodo`); y que al limpiar los filtros vuelve el mensaje vacío
    inicial. Sin errores de consola en ningún paso. El servidor de
    desarrollo (`vite`) se detuvo y se eliminaron los archivos temporales
    de la prueba al terminar.

  - Limpieza visual: sin sección "Alcance" ni números repetidos en las
    barras (punto 27): `npx tsc -b` limpio. Con Playwright, contra un
    backend simulado: se confirmó que en la página ya no aparece ningún
    título de sección "Alcance" ni el bloque `.fin-kpi-row--alcance"`,
    mientras que "Valores" sigue apareciendo igual; que las cabeceras de
    ambas barras de progreso ("% ejecución (valor)" y "% ejecución
    (tiempo)") ya no traen ningún número (verificado con una expresión
    regular que busca un patrón "dígito%" y no encuentra ninguno), pero sí
    conservan su label; y que la barra de tiempo con 100% simulado sigue
    pintando su relleno al ancho correcto (`width: 100%` en el estilo
    inline), confirmando que solo se quitó el texto, no la lógica visual
    de la barra. Sin errores de consola. El servidor de desarrollo
    (`vite`) se detuvo y se eliminaron los archivos temporales de la
    prueba al terminar.

  - Corrección: % de vuelta en las barras, fila de mini-valores fuera del
    encabezado (punto 28): `npx tsc -b` limpio tras quitar el componente
    `ValorMini` (ya sin usos). Con Playwright, contra un backend simulado
    con un convenio real (7% ejecución valor, 100% ejecución tiempo): se
    confirmó que la fila `.fin-item__valores` (Total/CDP/Ejecutado/
    Proyectado) ya NO aparece en el encabezado de la tarjeta; que las
    cabeceras de ambas barras sí traen de nuevo el número ("% ejecución
    (valor) 7%", "% ejecución (tiempo) 100%"); y que esos mismos 4 valores
    en pesos siguen disponibles, ahora solo en la sección "Consolidado" del
    detalle (que se sigue mostrando siempre, sin clic, desde el punto 26).
    Sin errores de consola. El servidor de desarrollo (`vite`) se detuvo y
    se eliminaron los archivos temporales de la prueba al terminar.

  - Reordenar KPIs principales (punto 29): `npx tsc -b` limpio. Con
    Playwright, contra un backend simulado con un convenio real: se leyó el
    orden real de los 5 labels de la fila de KPIs
    (`.fin-kpi-row .fin-kpi-card__label`) y se confirmó exactamente
    `["Valor total", "Valor CDP", "Valor proyectado", "Valor ejecutado",
    "Valor no ejecutado"]`. También se confirmó que el título de esa
    sección (el texto que Migue ya había cambiado) sigue mostrándose
    correctamente. Sin errores de consola. El servidor de desarrollo
    (`vite`) se detuvo y se eliminaron los archivos temporales de la
    prueba al terminar.

  - Ejecutado y No ejecutado consecutivas (punto 30): `npx tsc -b` limpio.
    Con Playwright, contra un backend simulado con un convenio y un
    período: se leyó el orden real de los labels en "Consolidado periodos
    convenio" y se confirmó exactamente Total → CDP → Proyectado →
    Ejecutado → No ejecutado → % Ejecución (valor) → % Ejecución (tiempo),
    con Ejecutado y No ejecutado en posiciones consecutivas (verificado
    programáticamente, no solo leyendo la lista); y se leyó el orden de la
    sección "Ejecución" del detalle por período, confirmando Proyectado →
    Pagado → No ejecutado → % Ejecución (valor), con Pagado y No ejecutado
    también consecutivas. Sin errores de consola. El servidor de desarrollo
    (`vite`) se detuvo y se eliminaron los archivos temporales de la prueba
    al terminar.

  - Rediseño de color (punto 31): `npx tsc -b` limpio. Con Playwright,
    contra un backend simulado con un convenio y un período: se confirmó
    que las 5 tarjetas KPI principales comparten exactamente un solo color
    de borde y un solo color de texto (sin variación entre ellas); que
    dentro de "Consolidado periodos convenio" las 7 tarjetas comparten un
    único color de texto (incluidas las 2 de %, que ya no colorean el
    número), y que de los 7 bordes, exactamente 5 comparten el mismo color
    neutro mientras que los 2 campos de % Ejecución llevan un color de
    borde distinto (el de su estado); y que la tarjeta de "% Ejecución
    (valor)" sí incluye el punto de estado (`.fin-campo__punto`). Sin
    errores de consola. El servidor de desarrollo (`vite`) se detuvo y se
    eliminaron los archivos temporales de la prueba al terminar.

  - Rediseño "panel ejecutivo" (punto 32): `npx tsc -b` limpio. Con
    Playwright, contra un backend simulado con 2 convenios (uno con 93% de
    ejecución, otro con 9%) y un período: se confirmó que el título
    principal usa la familia tipográfica "Manrope"; que el marcador de la
    sección principal y el borde superior de las tarjetas KPI usan
    exactamente el violeta de identidad (`rgb(124, 58, 237)`); y que la
    tarjeta de "% Ejecución (valor)" del convenio con 93% lleva el fondo
    suave verde esperado (`rgb(238, 251, 238)`), distinto del fondo neutro
    del resto de tarjetas. Se tomó además una captura de pantalla completa
    del módulo con los 2 convenios (uno bueno, uno en rojo) para revisión
    visual. Sin errores de consola. El servidor de desarrollo (`vite`) se
    detuvo y se eliminaron los archivos temporales de la prueba al
    terminar.

  - Carga de excel financiero (punto 33): backend verificado con una
    instancia real de MariaDB local (no un sustituto SQLite) creada con el
    esquema exacto de
    `sql/migraciones/2026-09_ejecucion_financiera_convenios.sql`, contra el
    excel REAL "MC_Financiera" (16 filas, 8 convenios): previsualización
    (confirmar=false) validó las 16 filas sin escribir nada; confirmar=true
    las aplicó todas correctamente (valores de CDP/pagado exactos,
    "Pendiente"/"Esp. Conci. MEN" -> NULL, "$ 526.567.802" -> número, y sin
    advertencia falsa en el convenio con adiciones repetidas en sus 2
    filas); re-confirmar el mismo excel no duplicó filas (upsert real);
    permisos probados con tokens reales de cada rol (ADMIN y AF -> 200,
    AST y DIRECTORA -> 403, sin token -> 401). Con un excel sintético se
    probaron a propósito: convenio_id inexistente y período inexistente
    (⛔ error, no se aplican), código/IES que no coinciden con el
    convenio_id real (⚠️ advertencia, se aplica igual), y la misma fila
    convenio+período repetida 2 veces con distinta "adiciones de recursos"
    (⚠️ advertencia, se aplicó la última leída, confirmado en la BD). Un
    archivo sin las columnas requeridas y uno sin filas de datos devolvieron
    400 con un mensaje claro. `npx tsc -b` limpio. En el frontend, con
    Playwright: el botón "Cargar excel financiero" aparece para AF y ADMIN y
    NO aparece para AST; el flujo completo (elegir archivo -> Previsualizar
    -> tabla con las 3 filas de ejemplo coloreadas por estado -> Confirmar y
    guardar) se probó de punta a punta contra respuestas simuladas,
    confirmando que la primera llamada al backend va con confirmar=false y
    la segunda con confirmar=true. Sin errores de consola.
