# 🔍 Consulta de Registros en Base de Datos MySQL - Streamlit

Una aplicación web desarrollada con Streamlit que permite consultar registros en una base de datos MySQL mediante número de documento.

## 📋 Características

- **Interfaz intuitiva**: Text input para ingresar el número de documento
- **Consulta SQL**: Ejecuta `SELECT * FROM tabla WHERE documento = id`
- **Configuración flexible**: Credenciales de prueba o personalizadas
- **Resultados dinámicos**: 
  - Muestra mensaje si no hay resultados
  - Muestra las primeras 10 columnas si hay resultados
  - Información adicional sobre el total de registros y columnas

## 🚀 Instalación y Uso

### 1. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 2. Configurar MySQL
Asegúrate de tener MySQL ejecutándose y crea la base de datos:
```sql
CREATE DATABASE test_database;
CREATE USER 'test_user'@'localhost' IDENTIFIED BY 'test_password';
GRANT ALL PRIVILEGES ON test_database.* TO 'test_user'@'localhost';
FLUSH PRIVILEGES;
```

### 3. Crear tabla y datos de ejemplo (opcional)
```bash
python create_sample_mysql_db.py
```

### 4. Ejecutar la aplicación
```bash
streamlit run app.py
```

## 🗃️ Estructura de la Base de Datos

### Configuración por defecto:
- **Host**: localhost
- **Puerto**: 3306  
- **Usuario**: test_user
- **Contraseña**: test_password
- **Base de datos**: test_database

### Tabla requerida: `tabla`
- **Campo principal**: `documento` (VARCHAR)
- **Otras columnas**: Cualquier estructura adicional

### Ejemplo de estructura MySQL:
```sql
CREATE TABLE tabla (
    id INT AUTO_INCREMENT PRIMARY KEY,
    documento VARCHAR(50) NOT NULL,
    nombre VARCHAR(100),
    apellido VARCHAR(100),
    email VARCHAR(150),
    telefono VARCHAR(20),
    direccion VARCHAR(200),
    ciudad VARCHAR(100),
    estado VARCHAR(50),
    fecha_registro DATE,
    activo BOOLEAN,
    observaciones TEXT,
    codigo_postal VARCHAR(10),
    INDEX idx_documento (documento)
);
```

## 📊 Datos de Ejemplo

Si ejecutas `create_sample_mysql_db.py`, se crearán datos de ejemplo con los siguientes documentos:
- `12345678`: Juan Pérez (Bogotá)
- `87654321`: María González (Medellín)
- `11223344`: Carlos Rodríguez (Cali)
- `99887766`: Ana López (Barranquilla)
- `55443322`: Pedro Martínez (Cartagena)
- `33221100`: Laura Silva (Bucaramanga)
- `77889900`: Diego Herrera (Pereira)

## 🔧 Configuración

### Credenciales en la Aplicación
La aplicación incluye un panel lateral para configurar las credenciales:

1. **Credenciales de prueba**: Usa la configuración por defecto
2. **Credenciales personalizadas**: Permite ingresar tus propias credenciales

### Personalización en Código
Para cambiar las credenciales por defecto, modifica `DB_CONFIG` en `app.py`:

```python
DB_CONFIG = {
    'host': 'tu_servidor',
    'user': 'tu_usuario', 
    'password': 'tu_contraseña',
    'database': 'tu_base_datos',
    'port': 3306
}
```

## 📝 Funcionalidades

### Consulta por Documento
1. Configura las credenciales en el panel lateral
2. Ingresa el número de documento en el campo de texto
3. Haz clic en "🔍 Consultar"
4. La aplicación ejecuta: `SELECT * FROM tabla WHERE documento = ?`
5. Muestra los resultados:
   - ⚠️ Mensaje si no hay resultados
   - ✅ Primeras 10 columnas si hay resultados
   - 📊 Información adicional sobre registros y columnas

### Seguridad
- **Consultas parametrizadas**: Previene inyección SQL
- **Validación de entrada**: Verifica que el campo no esté vacío
- **Manejo de errores**: Captura y muestra errores de conexión y consulta
- **Credenciales en sidebar**: Configuración segura y flexible

## 🛠️ Tecnologías Utilizadas

- **Streamlit**: Framework web para Python
- **Pandas**: Manipulación y análisis de datos
- **MySQL Connector**: Conexión a base de datos MySQL
- **Python**: Lenguaje de programación

## 📂 Estructura del Proyecto

```
streamlit_consultar_registro_db/
├── app.py                     # Aplicación principal
├── requirements.txt           # Dependencias
├── create_sample_mysql_db.py  # Script para crear datos de ejemplo
├── README.md                  # Documentación
└── create_sample_db.py       # Script SQLite (legacy)
```

## 🚨 Solución de Problemas

### Error de Conexión
Si obtienes errores de conexión:

1. **Verificar MySQL**: Asegúrate de que MySQL esté ejecutándose
2. **Crear base de datos**: 
   ```sql
   CREATE DATABASE test_database;
   ```
3. **Crear usuario**:
   ```sql
   CREATE USER 'test_user'@'localhost' IDENTIFIED BY 'test_password';
   GRANT ALL PRIVILEGES ON test_database.* TO 'test_user'@'localhost';
   FLUSH PRIVILEGES;
   ```
4. **Verificar credenciales**: Usa credenciales personalizadas en el sidebar

### Dependencias
Si faltan dependencias:
```bash
pip install mysql-connector-python streamlit pandas
```

## 🎯 Próximas Mejoras

- [ ] Soporte para múltiples tipos de base de datos
- [ ] Exportación de resultados (CSV, Excel)
- [ ] Filtros avanzados y búsqueda múltiple
- [ ] Paginación de resultados
- [ ] Historial de consultas
- [ ] Configuración de columnas a mostrar
- [ ] Autenticación de usuarios
- [ ] Logs de consultas

## 🤝 Contribuir

¡Las contribuciones son bienvenidas! Por favor:

1. Haz fork del proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📜 Licencia

Este proyecto está bajo la licencia MIT. Ver el archivo `LICENSE` para más detalles.