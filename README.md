# REDESIPCORE — Hub Central de Aplicaciones

Portal centralizado que actúa como punto de acceso único para las aplicaciones internas de la organización. Permite la autenticación de usuarios contra múltiples servidores de base de datos remotos, gestiona departamentos y roles, y controla la visibilidad de aplicaciones según el perfil de cada usuario.

---

## Tabla de contenido

- [Arquitectura](#arquitectura)
- [Tecnologías](#tecnologías)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Instalación](#instalación)
- [Configuración](#configuración)
- [Base de datos MySQL](#base-de-datos-mysql)
- [API Reference](#api-reference)
  - [Autenticación](#autenticación)
  - [Servidores](#servidores)
  - [Departamentos](#departamentos)
  - [Aplicaciones](#aplicaciones)
- [Sistema de roles y visibilidad](#sistema-de-roles-y-visibilidad)
- [Formato de apps.json](#formato-de-appsjson)
- [Flujo de autenticación](#flujo-de-autenticación)

---

## Arquitectura

```
Cliente / Frontend
        │
        ▼
┌──────────────────────────────────────────┐
│            REDESIPCORE (FastAPI)         │
│                                          │
│  ┌─────────┐  ┌────────────┐  ┌───────┐ │
│  │  /auth  │  │/servidores │  │ /apps │ │
│  └────┬────┘  └─────┬──────┘  └───┬───┘ │
│       │             │             │      │
│  ┌────▼─────────────▼──────┐  ┌───▼───┐ │
│  │   Servidores Remotos    │  │MySQL  │ │
│  │  (MSSQL / PostgreSQL)   │  │Local  │ │
│  │  USUARIOS, EMPRESAS...  │  │Depto/ │ │
│  └─────────────────────────┘  │Roles  │ │
│                                └───────┘ │
│                             ┌──────────┐ │
│                             │apps.json │ │
│                             └──────────┘ │
└──────────────────────────────────────────┘
```

**Dos capas de datos:**

| Capa | Almacenamiento | Contenido |
|---|---|---|
| Remota | MSSQL / PostgreSQL (servidores de la empresa) | Usuarios, empresas, contraseñas |
| Local | MySQL + JSON | Departamentos, roles, catálogo de apps |

---

## Tecnologías

| Componente | Tecnología | Versión |
|---|---|---|
| Framework web | FastAPI | 0.136.1 |
| Servidor ASGI | Uvicorn | 0.46.0 |
| ORM | SQLAlchemy | 2.0.49 |
| Validación | Pydantic | 2.13.3 |
| Auth tokens | python-jose | — |
| BD local | MySQL + PyMySQL | — |
| BD remotas | MSSQL / PostgreSQL | — |

---

## Estructura del proyecto

```
REDESIPCORE/
├── main.py                          # Punto de entrada FastAPI
├── .env                             # Variables de entorno (no commitear)
│
├── hub_central/
│   ├── classes/
│   │   └── models.py               # Schemas Pydantic (request/response)
│   │
│   ├── database/
│   │   ├── database.py             # Conexión MySQL + sesión SQLAlchemy
│   │   └── models.py               # Modelos ORM: Departamento, UsuarioDepartamento
│   │
│   ├── helpers/
│   │   ├── db_helper.py            # Ejecutor de consultas en servidores remotos
│   │   ├── encryption.py           # Encriptación de contraseñas (formato legado)
│   │   ├── jsonsPath.py            # Carga de connections.json
│   │   └── apps_helper.py          # Lectura/escritura de apps.json
│   │
│   ├── jsons/
│   │   ├── connections.json        # Configuración de servidores remotos
│   │   └── apps.json               # Catálogo de aplicaciones registradas
│   │
│   └── routers/
│       ├── auth.py                 # Autenticación de usuarios
│       ├── servidores.py           # Gestión de servidores remotos
│       ├── deparments.py           # Departamentos y asignación de roles
│       ├── apps.py                 # Registro y visibilidad de aplicaciones
│       └── integrations.py         # (Reservado para integraciones futuras)
│
└── venv/                           # Entorno virtual Python
```

---

## Instalación

```bash
# 1. Clonar el repositorio
git clone https://github.com/<usuario>/REDESIPCORE.git
cd REDESIPCORE

# 2. Crear y activar entorno virtual
python -m venv venv

# Windows
venv\Scripts\activate

# Linux / macOS
source venv/bin/activate

# 3. Instalar dependencias
pip install fastapi uvicorn sqlalchemy pymysql python-dotenv \
            python-jose[cryptography] pydantic pyodbc

# 4. Configurar variables de entorno (ver sección Configuración)
cp .env.example .env

# 5. Crear la base de datos MySQL (ver sección MySQL)

# 6. Iniciar el servidor
uvicorn main:app --reload
```

---

## Configuración

Edita el archivo `.env` en la raíz del proyecto:

```env
# JWT
SECRET_KEY   = "tu_clave_secreta_muy_larga"
ALGORITHM    = "HS256"

# Clave para operaciones administrativas (header X-Admin-Key)
ADMIN_SECRET = "tu_clave_admin_segura"

# MySQL — base de datos local del hub
MYSQL_HOST = "localhost"
MYSQL_PORT = "3306"
MYSQL_DB   = "redesipcore_hub"
MYSQL_USER = "hub_user"
MYSQL_PASS = "tu_password_mysql"
```

> **Importante:** nunca subas el `.env` real a un repositorio público. El `.gitignore` ya lo excluye.

---

## Base de datos MySQL

El hub usa MySQL para almacenar su información propia (departamentos y roles). Las tablas se crean automáticamente al iniciar la aplicación.

### Crear la base de datos y el usuario

```sql
CREATE DATABASE redesipcore_hub CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER 'hub_user'@'localhost' IDENTIFIED BY 'tu_password';
GRANT ALL PRIVILEGES ON redesipcore_hub.* TO 'hub_user'@'localhost';
FLUSH PRIVILEGES;
```

### Tablas generadas automáticamente

#### `departamentos`

| Columna | Tipo | Descripción |
|---|---|---|
| id | INT PK AUTO | Identificador único |
| nombre | VARCHAR(100) | Nombre del departamento |
| descripcion | VARCHAR(255) | Descripción opcional |
| servidor_id | VARCHAR(100) | Servidor remoto al que pertenece |
| empresa_cod | VARCHAR(50) | Código de empresa (CODEMPRESA) |

#### `usuarios_departamentos`

| Columna | Tipo | Descripción |
|---|---|---|
| id | INT PK AUTO | Identificador único |
| cod_usuario | VARCHAR(50) | CODUSUARIO del servidor remoto |
| servidor_id | VARCHAR(100) | Servidor remoto del usuario |
| departamento_id | INT FK | Referencia a `departamentos.id` |
| rol | VARCHAR(20) | Rol: `admin`, `jefe` o `empleado` |

> La combinación `(cod_usuario, servidor_id, departamento_id)` es única — un usuario no puede tener dos roles en el mismo departamento.

---

## API Reference

La documentación interactiva está disponible en:
- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

### Convenciones de autenticación

| Tipo de acceso | Requerido |
|---|---|
| Endpoints públicos | Sin token |
| Endpoints de usuario | Header `Authorization: Bearer <token>` |
| Endpoints administrativos | Header `Authorization: Bearer <token>` + Header `X-Admin-Key: <clave>` |

---

### Autenticación

#### `POST /api/auth/login`

Autentica a un usuario contra un servidor remoto registrado y devuelve un JWT.

**Request body:**
```json
{
  "servidor": "local",
  "password": "mi_password"
}
```

**Response exitoso `200`:**
```json
{
  "status": "success",
  "message": "login exitoso",
  "access_token": "eyJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer"
}
```

**Errores posibles:**

| Código | Motivo |
|---|---|
| 404 | Servidor no registrado |
| 401 | Contraseña incorrecta |
| 403 | Usuario bloqueado o descatalogado |
| 500 | Error de conexión a la base de datos remota |

> El token tiene una vigencia de **8 horas**. Incluye `cod_usuario`, `usuario` y `servidor_id`.

---

### Servidores

#### `GET /api/servidores/`

Lista los servidores remotos registrados en el hub.

**Response `200`:**
```json
{
  "total": 3,
  "servidores_disponibles": ["sede_central", "sucursal_norte", "local"]
}
```

---

#### `POST /api/servidores/registrar`

Registra un nuevo servidor remoto. Antes de guardarlo, prueba la conexión.

**Request body:**
```json
{
  "servidor":  "mi_servidor",
  "host":      "192.168.1.50",
  "puerto":    1433,
  "db_name":   "GENERAL",
  "tipo":      "mssql",
  "driver":    "SQL Server",
  "usuario":   "hub_user",
  "password":  "mi_pass"
}
```

**Response `200`:**
```json
{
  "status": "success",
  "mensaje": "Servidor 'mi_servidor' verificado y registrado correctamente."
}
```

---

#### `GET /api/servidores/listarEmpresas` 🔒

Lista todas las empresas disponibles en el servidor del usuario autenticado.

**Response `200`:**
```json
{
  "status": "success",
  "empresas": [
    { "CODEMPRESA": "001", "TITULO": "Empresa Principal", "PATHBD": "...", "PAIS": "VE" }
  ]
}
```

---

#### `GET /api/servidores/listarEmpresasUsuario` 🔒

Lista únicamente las empresas asignadas al usuario autenticado.

---

### Departamentos

Todos los endpoints requieren JWT (`Authorization: Bearer <token>`).  
Los endpoints de escritura requieren además `X-Admin-Key`.

#### `GET /api/departamentos/` 🔒

Lista los departamentos del servidor del usuario autenticado.

**Response `200`:**
```json
{
  "status": "success",
  "departamentos": [
    {
      "id": 1,
      "nombre": "Contabilidad",
      "descripcion": "Departamento de finanzas",
      "servidor_id": "local",
      "empresa_cod": "001"
    }
  ]
}
```

---

#### `POST /api/departamentos/` 🔒🔑

Crea un nuevo departamento.

**Headers:** `X-Admin-Key: <clave>`

**Request body:**
```json
{
  "nombre":      "Recursos Humanos",
  "descripcion": "Gestión de personal",
  "servidor_id": "local",
  "empresa_cod": "001"
}
```

---

#### `DELETE /api/departamentos/{id}` 🔒🔑

Elimina un departamento y todas sus asignaciones de usuarios en cascada.

---

#### `POST /api/departamentos/asignar-usuario` 🔒🔑

Asigna un usuario a un departamento con un rol específico.  
Si el usuario ya existe en ese departamento, actualiza su rol.

**Request body:**
```json
{
  "cod_usuario":     "U001",
  "departamento_id": 1,
  "rol":             "jefe"
}
```

**Roles válidos:** `admin`, `jefe`, `empleado`

---

#### `DELETE /api/departamentos/usuarios/{asignacion_id}` 🔒🔑

Remueve a un usuario de un departamento.

---

#### `GET /api/departamentos/{id}/usuarios` 🔒🔑

Lista los usuarios asignados a un departamento con sus roles.

**Response `200`:**
```json
{
  "status": "success",
  "departamento": "Contabilidad",
  "usuarios": [
    { "id": 1, "cod_usuario": "U001", "rol": "jefe" },
    { "id": 2, "cod_usuario": "U002", "rol": "empleado" }
  ]
}
```

---

### Aplicaciones

#### `GET /api/apps/mis-apps` 🔒

Devuelve las aplicaciones visibles para el usuario según sus roles en los departamentos. **Este es el endpoint principal del hub.**

**Response `200`:**
```json
{
  "status": "success",
  "roles": ["jefe"],
  "apps": [
    {
      "name":        "Sistema de Ventas",
      "version":     "1.2.0",
      "description": "Gestión y seguimiento de ventas",
      "href":        "http://192.168.1.10:8080/ventas",
      "permissions": ["admin", "jefe", "empleado"]
    },
    {
      "name":        "Panel de Reportes",
      "version":     "2.0.1",
      "description": "Reportes gerenciales",
      "href":        "http://192.168.1.10:8080/reportes",
      "permissions": ["admin", "jefe"]
    }
  ]
}
```

> Si el usuario no está asignado a ningún departamento, devuelve `apps: []`.

---

#### `GET /api/apps/` 🔒🔑

Lista todas las apps registradas con sus permisos.

---

#### `POST /api/apps/` 🔒🔑

Registra una nueva aplicación en `apps.json`.

**Request body:**
```json
{
  "name":        "Sistema de Inventario",
  "version":     "3.0.0",
  "description": "Control de inventario y almacén",
  "href":        "http://192.168.1.10:9090/inventario",
  "permissions": ["admin", "jefe"]
}
```

---

#### `PUT /api/apps/{nombre}` 🔒🔑

Actualiza los datos de una app existente (campos opcionales).

**Request body:**
```json
{
  "version":     "3.1.0",
  "permissions": ["admin", "jefe", "empleado"]
}
```

---

#### `DELETE /api/apps/{nombre}` 🔒🔑

Elimina una app del catálogo.

---

#### `POST /api/apps/{nombre}/permisos` 🔒🔑

Reemplaza los permisos de una app por los nuevos indicados.

**Request body:**
```json
{
  "permissions": ["admin"]
}
```

---

## Sistema de roles y visibilidad

### Roles disponibles

| Rol | Descripción |
|---|---|
| `admin` | Administrador del sistema. Acceso total. |
| `jefe` | Jefe de departamento. Ve apps de gestión y operativas. |
| `empleado` | Empleado regular. Ve solo apps operativas básicas. |

### Cómo se determina la visibilidad

1. El usuario se autentica → obtiene un JWT con su `cod_usuario` y `servidor_id`
2. Al llamar a `GET /api/apps/mis-apps`, el hub consulta MySQL y obtiene **todos los roles** del usuario en todos sus departamentos
3. Se filtran las apps de `apps.json` donde `permissions` contenga al menos uno de esos roles
4. Un usuario en varios departamentos obtiene la **unión** de apps de todos sus roles

### Ejemplo práctico

```
Usuario U001:
  - Departamento "Contabilidad" → rol: jefe
  - Departamento "Proyectos"    → rol: empleado

Apps disponibles:
  - "ERP Financiero"   permissions: ["admin", "jefe"]      → ✅ visible (tiene jefe)
  - "Sistema de Obras" permissions: ["admin", "jefe", "empleado"] → ✅ visible (tiene empleado)
  - "Panel Admin"      permissions: ["admin"]               → ❌ no visible
```

---

## Formato de apps.json

Archivo ubicado en `hub_central/jsons/apps.json`. Se gestiona automáticamente a través de la API.

```json
{
    "apps": [
        {
            "name":        "Sistema de Ventas",
            "version":     "1.2.0",
            "description": "Gestión y seguimiento de ventas",
            "href":        "http://192.168.1.10:8080/ventas",
            "permissions": ["admin", "jefe", "empleado"]
        },
        {
            "name":        "Panel de Reportes",
            "version":     "2.0.1",
            "description": "Reportes gerenciales y estadísticas",
            "href":        "http://192.168.1.10:8080/reportes",
            "permissions": ["admin", "jefe"]
        },
        {
            "name":        "Panel de Administración",
            "version":     "1.0.0",
            "description": "Gestión interna del hub",
            "href":        "http://192.168.1.10:8000/admin",
            "permissions": ["admin"]
        }
    ]
}
```

| Campo | Tipo | Descripción |
|---|---|---|
| `name` | string | Nombre único de la app (actúa como identificador) |
| `version` | string | Versión actual de la app |
| `description` | string | Descripción breve (opcional) |
| `href` | string | URL de acceso a la aplicación |
| `permissions` | string[] | Roles que pueden ver esta app |

---

## Flujo de autenticación

```
1. POST /api/auth/login
   body: { servidor, password }
        │
        ▼
2. El hub busca el servidor en connections.json
   y se conecta con la cuenta de servicio (hub_user/hub_pass)
        │
        ▼
3. Consulta la tabla USUARIOS del servidor remoto
   Valida: NEWPASS == encriptar(password)
   Verifica: BLOQUEADO != 'T' y DESCATALOGADO != 'T'
        │
        ▼
4. Genera JWT (8 horas)
   payload: { sub: CODUSUARIO, usuario: USUARIO, servidor_id }
        │
        ▼
5. Cliente usa el token en cada request:
   Authorization: Bearer <token>
        │
        ▼
6. GET /api/apps/mis-apps
   → Busca roles en MySQL (tabla usuarios_departamentos)
   → Filtra apps.json según roles
   → Devuelve apps visibles
```

---

## connections.json

Archivo de configuración de servidores remotos en `hub_central/jsons/connections.json`. Se gestiona a través del endpoint `/api/servidores/registrar`.

```json
{
    "servidores": {
        "sede_central": {
            "host":     "192.168.1.10",
            "puerto":   5432,
            "db_name":  "db_corporativa",
            "tipo":     "postgresql",
            "hub_user": "coreUser",
            "hub_pass": "password_de_servicio"
        },
        "local": {
            "host":     "10.10.10.212",
            "puerto":   1433,
            "db_name":  "GENERAL",
            "tipo":     "mssql",
            "driver":   "SQL Server",
            "hub_user": "sa",
            "hub_pass": "password_de_servicio"
        }
    }
}
```

---

## Licencia

Proyecto interno — RedesIP © 2026
