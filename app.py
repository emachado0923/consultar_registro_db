import streamlit as st
from sqlalchemy import create_engine, text
import hashlib
import secrets
import pandas as pd
from typing import Optional

# Configuración de la página
st.set_page_config(
    page_title="Consulta de Registros DB",
    page_icon="🔍",
    layout="wide"
)

# Título de la aplicación
st.title("🎓 Sistema de Consulta de Formularios - Matrícula Cero 2025-2")

# Configuración de bases de datos
LOGIN_DB_CONFIG = {
    'host': '10.124.80.4',
    'user': 'REDACTED',
    'password': 'REDACTED',
    'database': 'analitica_fondos',
    'port': 3306
}

APP_DB_CONFIG = {
    'host': '10.124.80.4',
    'user': 'REDACTED',
    'password': 'REDACTED',
    'database': 'REDACTED',
    'port': 3306
}


# Conexión a la base de datos de login
@st.cache_resource
def init_login_connection():
    try:
        connection_string = f"mysql+mysqlconnector://{LOGIN_DB_CONFIG['user']}:{LOGIN_DB_CONFIG['password']}@{LOGIN_DB_CONFIG['host']}:{LOGIN_DB_CONFIG['port']}/{LOGIN_DB_CONFIG['database']}"
        engine = create_engine(connection_string)
        return engine
    except Exception as e:
        st.error(f"Error al conectar con la base de datos de autenticación: {e}")
        return None


# Conexión a la base de datos de aplicación
@st.cache_resource
def init_app_connection():
    try:
        connection_string = f"mysql+mysqlconnector://{APP_DB_CONFIG['user']}:{APP_DB_CONFIG['password']}@{APP_DB_CONFIG['host']}:{APP_DB_CONFIG['port']}/{APP_DB_CONFIG['database']}"
        engine = create_engine(connection_string)
        return engine
    except Exception as e:
        st.error(f"Error al conectar con la base de datos de aplicación: {e}")
        return None


# Funciones de seguridad mejoradas
def crear_hash_con_sal(password: str) -> tuple:
    """Crea un hash seguro de la contraseña con sal"""
    try:
        sal = secrets.token_hex(16)
        hash_obj = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            sal.encode('utf-8'),
            100000
        )
        return sal, hash_obj.hex()
    except Exception as e:
        st.error(f"Error al crear hash: {str(e)}")
        return None, None


def verificar_password(sal: str, hash_almacenado: str, password_proporcionado: str) -> bool:
    """Verifica si el password proporcionado coincide con el hash almacenado"""
    try:
        if not all([sal, hash_almacenado, password_proporcionado]):
            return False

        hash_calculado = hashlib.pbkdf2_hmac(
            'sha256',
            password_proporcionado.encode('utf-8'),
            sal.encode('utf-8'),
            100000
        ).hex()

        return hash_calculado == hash_almacenado
    except Exception as e:
        st.error(f"Error al verificar contraseña: {str(e)}")
        return False


# Función de autenticación corregida
def autenticar_usuario(username: str, password: str) -> bool:
    """Autentica un usuario contra la base de datos"""
    engine = init_login_connection()
    if engine is None:
        st.error("No se pudo conectar a la base de datos")
        return False

    try:
        query = text("""
            SELECT password_hash, sal, activo 
            FROM usuarios 
            WHERE username = :username
        """)

        with engine.connect() as connection:
            result = connection.execute(query, {"username": username}).fetchone()

        if not result:
            st.error("Usuario no encontrado")
            return False

        hash_almacenado = result[0]
        sal = result[1]
        activo = bool(result[2])

        if not activo:
            st.error("Esta cuenta está desactivada")
            return False

        if not all([hash_almacenado, sal]):
            st.error("Credenciales inválidas en la base de datos")
            return False

        if verificar_password(sal, hash_almacenado, password):
            return True

        st.error("Contraseña incorrecta")
        return False

    except Exception as e:
        st.error(f"Error de autenticación: {str(e)}")
        return False


# Funciones de gestión de usuarios
def obtener_info_usuario(username: str):
    """Obtiene información del usuario"""
    engine = init_login_connection()
    if engine is None:
        return None

    try:
        query = text("SELECT id, nombre_completo FROM usuarios WHERE username = :username")
        with engine.connect() as connection:
            result = connection.execute(query, {"username": username}).fetchone()
        return {'id': result[0], 'nombre_completo': result[1]} if result else None
    except Exception as e:
        st.error(f"Error al obtener información del usuario: {e}")
        return None


def cambiar_password(username: str, password_actual: str, nuevo_password: str) -> bool:
    """Cambia la contraseña de un usuario"""
    engine = init_login_connection()
    if engine is None:
        return False

    try:
        with engine.connect() as connection:
            # Verificar contraseña actual
            result = connection.execute(
                text("SELECT password_hash, sal FROM usuarios WHERE username = :username"),
                {"username": username}
            ).fetchone()

            if not result:
                st.error("Usuario no encontrado")
                return False

            hash_almacenado, sal = result[0], result[1]

            if not verificar_password(sal, hash_almacenado, password_actual):
                st.error("La contraseña actual es incorrecta")
                return False

            # Generar nuevo hash
            nueva_sal, nuevo_hash = crear_hash_con_sal(nuevo_password)
            if not nueva_sal or not nuevo_hash:
                return False

            # Actualizar en base de datos
            connection.execute(
                text("""
                    UPDATE usuarios 
                    SET password_hash = :nuevo_hash, sal = :nueva_sal
                    WHERE username = :username
                """),
                {
                    "nuevo_hash": nuevo_hash,
                    "nueva_sal": nueva_sal,
                    "username": username
                }
            )
            connection.commit()
        st.success("¡Contraseña cambiada exitosamente!")
        return True
    except Exception as e:
        st.error(f"Error al cambiar contraseña: {e}")
        return False


def crear_usuario(username: str, password: str, nombre_completo: str) -> bool:
    """Crea un nuevo usuario en el sistema"""
    engine = init_login_connection()
    if engine is None:
        return False

    try:
        with engine.connect() as connection:
            # Verificar si el usuario ya existe
            existe = connection.execute(
                text("SELECT COUNT(*) FROM usuarios WHERE username = :username"),
                {"username": username}
            ).scalar()

            if existe:
                st.error("El nombre de usuario ya existe")
                return False

            # Crear hash de contraseña
            sal, password_hash = crear_hash_con_sal(password)
            if not sal or not password_hash:
                return False

            # Insertar nuevo usuario
            connection.execute(
                text("""
                    INSERT INTO usuarios (username, password_hash, sal, nombre_completo)
                    VALUES (:username, :password_hash, :sal, :nombre_completo)
                """),
                {
                    "username": username,
                    "password_hash": password_hash,
                    "sal": sal,
                    "nombre_completo": nombre_completo
                }
            )
            connection.commit()
        st.success("Usuario registrado exitosamente!")
        return True
    except Exception as e:
        st.error(f"Error al crear usuario: {e}")
        return False


# Función de consulta principal
def ejecutar_consulta(documento_id: str) -> Optional[pd.DataFrame]:
    """Ejecuta la consulta SQL para buscar registros por documento"""
    engine = init_app_connection()
    if engine is None:
        return None

    try:
        query = text("SELECT * FROM vw_matricula_cero_2025_2 WHERE documento = :documento_id")
        with engine.connect() as connection:
            df = pd.read_sql_query(query, connection, params={"documento_id": documento_id})
        return df
    except Exception as e:
        st.error(f"Error al ejecutar la consulta: {e}")
        return None


# Componentes de la UI
def mostrar_formulario_login():
    """Muestra el formulario de login"""
    with st.form("login_form"):
        st.markdown("## 🔐 Inicio de Sesión")
        username = st.text_input("Usuario", key="login_username")
        password = st.text_input("Contraseña", type="password", key="login_password")
        submit_button = st.form_submit_button("Iniciar Sesión")

        if submit_button:
            if not username or not password:
                st.error("Por favor complete todos los campos")
                return

            if autenticar_usuario(username, password):
                st.session_state.autenticado = True
                st.session_state.username = username
                st.session_state.user_info = obtener_info_usuario(username)
                st.success("¡Inicio de sesión exitoso!")
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos")


def mostrar_formulario_cambio_password():
    """Muestra el formulario para cambiar contraseña"""
    with st.form("cambio_password_form"):
        st.markdown("## 🔄 Cambiar Contraseña")
        password_actual = st.text_input("Contraseña actual", type="password")
        nueva_password = st.text_input("Nueva contraseña", type="password")
        confirmar_password = st.text_input("Confirmar nueva contraseña", type="password")
        submit_button = st.form_submit_button("Cambiar Contraseña")

        if submit_button:
            if not all([password_actual, nueva_password, confirmar_password]):
                st.error("Por favor complete todos los campos")
                return

            if nueva_password != confirmar_password:
                st.error("Las nuevas contraseñas no coinciden")
            elif len(nueva_password) < 8:
                st.error("La nueva contraseña debe tener al menos 8 caracteres")
            else:
                cambiar_password(st.session_state.username, password_actual, nueva_password)


def mostrar_formulario_registro():
    """Muestra el formulario de registro de nuevos usuarios"""
    # Solo permitir el registro si el usuario es 'admin'
    if st.session_state.username == 'admin':
        with st.form("registro_form"):
            st.markdown("## 📝 Registrar Nuevo Usuario")
            nuevo_username = st.text_input("Nombre de usuario")
            nuevo_nombre = st.text_input("Nombre completo")
            nueva_password = st.text_input("Contraseña", type="password")
            confirmar_password = st.text_input("Confirmar contraseña", type="password")
            submit_button = st.form_submit_button("Registrar Usuario")

            if submit_button:
                if not all([nuevo_username, nuevo_nombre, nueva_password, confirmar_password]):
                    st.error("Por favor complete todos los campos")
                    return

                if nueva_password != confirmar_password:
                    st.error("Las contraseñas no coinciden")
                elif len(nueva_password) < 8:
                    st.error("La contraseña debe tener al menos 8 caracteres")
                else:
                    crear_usuario(nuevo_username, nueva_password, nuevo_nombre)
    else:
        st.warning("🚨 Solo el usuario 'admin' puede registrar nuevos usuarios.")


def mostrar_interfaz_principal():
    """Muestra la interfaz principal de consulta"""

    st.markdown(f"### 🔍 Consulta de Registros de Matrícula Cero | Usuario: {st.session_state.username}")

    # Menú de opciones
    menu_options = ["Consultar", "Cambiar contraseña"]
    if st.session_state.username == 'admin':
        menu_options.append("Registrar usuario")
    menu_options.append("Cerrar sesión")

    opcion = st.sidebar.selectbox(
        "Menú",
        menu_options
    )

    if opcion == "Consultar":
        mostrar_formulario_consulta()
    elif opcion == "Cambiar contraseña":
        mostrar_formulario_cambio_password()
    elif opcion == "Registrar usuario":
        mostrar_formulario_registro()
    elif opcion == "Cerrar sesión":
        if st.button("Confirmar cierre de sesión"):
            del st.session_state.autenticado
            del st.session_state.username
            del st.session_state.user_info
            st.rerun()


def mostrar_formulario_consulta():
    """Muestra el formulario de consulta principal"""
    st.markdown("### 📚 Sobre el Programa Matrícula Cero")
    st.markdown("""
    **Matrícula Cero** es un programa de Sapiencia.

    **¿Qué puedes consultar aquí?**
    - Si el estudiante realizó satisfactoriamente el proceso de registro del formulario de matrícula ceros
    - Información personal y académica
    - Columnas importantes
    - Datos de contacto registrados
    """)

    # Input para el documento
    documento_input = st.text_input(
        "Ingrese su número de documento:",
        placeholder="Ejemplo: 12345678",
        help="Ingrese su número de documento de identidad (cédula de ciudadanía, tarjeta de identidad, etc.)",
        max_chars=15
    )

    # Botón de consulta
    consulta_habilitada = documento_input.strip() and documento_input.isdigit() and 6 <= len(documento_input) <= 15

    if st.button("🔍 Consultar Registro", type="primary", disabled=not consulta_habilitada):
        if documento_input.strip():
            with st.spinner("🔄 Consultando base de datos... Por favor espere..."):
                resultado = ejecutar_consulta(documento_input.strip())

                if resultado is not None:
                    if len(resultado) == 0:
                        st.warning("⚠️ No se encontraron registros para el documento ingresado.")
                        st.info(
                            "💡 **Posibles razones:**\n- El documento no está registrado en el programa de Matrícula Cero 2025-2\n- Verifique que el número de documento sea correcto\n- Contacte al área de admisiones para más información")
                    else:
                        st.success(
                            f"✅ ¡Registro encontrado! Se encontraron {len(resultado)} registro(s) para su documento.")

                        columnas_a_mostrar = resultado.columns[:6]
                        df_mostrar = resultado[[*columnas_a_mostrar, "ies_adscritas", "programa_admitido"]]

                        st.info(
                            f"📊 Mostrando las primeras {len(columnas_a_mostrar)} columnas de {len(resultado.columns)} columnas disponibles")

                        st.markdown("#### 📋 Información de su registro:")
                        st.dataframe(
                            df_mostrar,
                            use_container_width=True,
                            hide_index=True
                        )

                        if len(resultado) > 0:
                            csv = resultado.to_csv(index=False)
                            st.download_button(
                                label="📥 Descargar información completa (CSV)",
                                data=csv,
                                file_name=f"matricula_cero_{documento_input.strip()}.csv",
                                mime="text/csv"
                            )

                        with st.expander("ℹ️ Información adicional del registro"):
                            st.write(f"**Total de registros encontrados:** {len(resultado)}")
                            st.write(f"**Columnas disponibles:** {len(resultado.columns)}")
                            st.write(f"**Columnas mostradas:** {list(columnas_a_mostrar)}")

                            if len(resultado.columns) > 10:
                                st.write(f"**Columnas adicionales disponibles:** {len(resultado.columns) - 10}")
                                st.write(f"**Columnas ocultas:** {list(resultado.columns[10:])}")
                                st.info("💡 Descargue el archivo CSV para ver toda la información disponible")
                else:
                    st.error("❌ Error al ejecutar la consulta. Por favor, intente nuevamente.")
                    st.info("💡 Si el problema persiste, contacte al administrador del sistema.")
        else:
            st.warning("⚠️ Por favor, ingrese un número de documento válido.")

    if not consulta_habilitada and documento_input:
        st.info("💡 Complete correctamente el número de documento para habilitar la consulta")

    # Footer con información de contacto
    st.markdown("---")
    st.markdown("### 📞 Información de Contacto")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        **Sapiencia** Programa Matrícula Cero 2025-2
        """)

    with col2:
        st.markdown("""
        **Horarios de Atención:** Lunes a Viernes: 8:00 AM - 5:00 PM  
        """)

    st.markdown("---")
    st.caption("🔒 Sistema seguro - Información protegida por Sapiencia")


# Punto de entrada de la aplicación
if __name__ == "__main__":
    # Inicializar estado de sesión
    if 'autenticado' not in st.session_state:
        st.session_state.autenticado = False

    # Mostrar contenido según autenticación
    if st.session_state.autenticado:
        mostrar_interfaz_principal()
    else:
        mostrar_formulario_login()
