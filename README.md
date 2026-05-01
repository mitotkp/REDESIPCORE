# REDESIPCORE — Hub Central de Aplicaciones

Portal centralizado que actúa como punto de acceso único para las aplicaciones internas de la organización. Permite la autenticación de usuarios contra múltiples servidores de base de datos remotos (MSSQL, PostgreSQL, MySQL), gestiona departamentos con roles por usuario y controla la visibilidad de aplicaciones según el perfil de cada usuario.

**Repositorio:** https://github.com/mitotkp/REDESIPCORE  
**Versión actual:** 1.0.0  
**Estado:** Backend completo — pendiente frontend

---

## Tabla de contenido

- [Arquitectura](#arquitectura)
- [Tecnologías](#tecnologías)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Instalación](#instalación)
  - [Sin Docker](#sin-docker)
  - [Con Docker](#con-docker)
- [Configuración](#configuración)
- [Base de datos MySQL](#base-de-datos-mysql)
- [Docker automático al arranque](#docker-automático-al-arranque)
- [Logs](#logs)
- [Tests](#tests)
- [API Reference](#api-reference)
  - [Autenticación](#autenticación)
  - [Servidores](#servidores)
  - [Departamentos](#departamentos)
  - [Aplicaciones](#aplicaciones)
  - [Auditoría](#auditoría)
- [Sistema de roles y visibilidad](#sistema-de-roles-y-visibilidad)
- [Formato de apps.json](#formato-de-appsjson)
- [Flujo completo de sesión](#flujo-completo-de-sesión)
- [Paginación](#paginación)

---

## Arquitectura

```
Cliente / Frontend
        │
        ▼
┌───────────────────────────────────────────────────────┐
│                  REDESIPCORE (FastAPI)                │
│                                                       │
│  ┌──────────┐ ┌────────────┐ ┌───────┐ ┌──────────┐  │
│  │  /auth   │ │/servidores │ │ /apps │ │ /audit   │  │
│  └────┬─────┘ └─────┬──────┘ └───┬───┘ └────┬─────┘  │
│       │             │            │           │        │
│  ┌────▼─────────────▼────────────▼───────────▼──────┐ │
│  │              MySQL Local (redesipcore_hub)        │ │
│  │  departamentos · usuarios_departamentos           │ │
│  │  refresh_tokens · auditoria                       │ │
│  └───────────────────────────────────────────────────┘ │
│                                                       │
│  ┌─────────────────────────────┐   ┌───────────────┐  │
│  │     Servidores Remotos      │   │   apps.json   │  │
│  │  MSSQL · PostgreSQL · MySQL │   │  Catálogo de  │  │
│  │  USUARIOS · EMPRESAS...     │   │  aplicaciones │  │
│  └─────────────────────────────┘   └───────────────┘  │
└───────────────────────────────────────────────────────┘
```

**Tres capas de datos:**

| Capa | Almacenamiento | Contenido |
|---|---|---|
| Remota | MSSQL / PostgreSQL / MySQL (servidores de la empresa) | Usuarios, empresas, contraseñas |
| Local BD | MySQL `redesipcore_hub` | Departamentos, roles, tokens, auditoría |
| Local JSON | `apps.json` / `connections.json` | Catálogo de apps, configs de servidores |

---

## Tecnologías

| Componente | Tecnología | Versión |
|---|---|---|
| Framework web | FastAPI | 0.136.1 |
| Servidor ASGI | Uvicorn | 0.46.0 |
| ORM | SQLAlchemy | 2.0.49 |
| Validación | Pydantic | 2.13.3 |
| Auth / JWT | python-jose | ≥ 3.3.0 |
| BD local | MySQL + PyMySQL | ≥ 1.1.0 |
| BD remotas MSSQL | pyodbc | ≥ 5.0.0 |
| BD remotas PG | psycopg2-binary | ≥ 2.9.0 |
| Docker SDK | docker | ≥ 7.0.0 |
| Tests | pytest + httpx | ≥ 8.0.0 |

---

## Estructura del proyecto

```
REDESIPCORE/
├── main.py                          # Punto de entrada — lifespan, logging, routers
├── .env                             # Variables de entorno (NO commitear)
├── .env.example                     # Plantilla de configuración
├── requirements.txt                 # Dependencias Python
├── Dockerfile                       # Imagen Docker de la app
├── docker-compose.yml               # Orquestación app + MySQL
├── .dockerignore
├── .gitignore
│
├── hub_central/
│   ├── classes/
│   │   └── models.py               # Schemas Pydantic (request/response bodies)
│   │
│   ├── database/
│   │   ├── database.py             # Engine MySQL, sesión, inicializar_db()
│   │   └── models.py               # ORM: Departamento, UsuarioDepartamento,
│   │                               #      RefreshToken, Auditoria
│   │
│   ├── helpers/
│   │   ├── auth_deps.py            # Dependencias JWT compartidas entre routers
│   │   ├── audit.py                # Helper auditar(db, payload, accion, detalle)
│   │   ├── apps_helper.py          # Lectura/escritura de apps.json
│   │   ├── connection_helper.py    # Constructor de URLs por tipo de BD
│   │   ├── db_helper.py            # Ejecutor de consultas en servidores remotos
│   │   ├── docker_check.py         # Verificación y arranque automático de MySQL via Docker
│   │   ├── encryption.py           # Encriptación de contraseñas (formato legado)
│   │   ├── jsonsPath.py            # Carga de connections.json
│   │   └── logging_config.py       # Configuración de logs estructurados
│   │
│   ├── jsons/
│   │   ├── connections.json        # Servidores remotos (generado por la API)
│   │   ├── connections.json.example
│   │   └── apps.json               # Catálogo de aplicaciones (generado por la API)
│   │
│   └── routers/
│       ├── auth.py                 # login, refresh, logout
│       ├── servidores.py           # Registro y consulta de servidores remotos
│       ├── deparments.py           # CRUD departamentos + asignación de roles
│       ├── apps.py                 # CRUD apps + visibilidad por rol
│       ├── audit.py                # Consulta de registros de auditoría
│       └── integrations.py         # (Reservado)
│
└── tests/
    ├── conftest.py                  # Fixtures: SQLite en memoria, mocks de JWT
    ├── test_auth.py                 # Tests de refresh token y logout
    ├── test_departamentos.py        # Tests de CRUD y asignación de roles
    ├── test_apps.py                 # Tests de catálogo y visibilidad
    └── test_servidores.py           # Tests de servidores y paginación
```

---

## Instalación

### Sin Docker

```bash
# 1. Clonar
git clone https://github.com/mitotkp/REDESIPCORE.git
cd REDESIPCORE

# 2. Entorno virtual
python -m venv venv
source venv/bin/activate        # Linux/macOS
venv\Scripts\activate           # Windows

# 3. Dependencias
pip install -r requirements.txt

# 4. Configuración
cp .env.example .env
# Editar .env con tus credenciales

# 5. Arrancar (la app crea la BD y tablas automáticamente)
uvicorn main:app --reload
```

### Con Docker

```bash
cp .env.example .env
# Editar .env con tus credenciales

docker compose up --build
```

El compose levanta **MySQL 8.0** y la **app** en orden correcto usando healthcheck. Los archivos `apps.json` y `connections.json` se montan como volumen y persisten entre reinicios.

---

## Configuración

Copia `.env.example` a `.env` y edita los valores:

```env
# ── JWT ───────────────────────────────────────────────
SECRET_KEY   = "clave_larga_y_aleatoria_minimo_32_caracteres"
ALGORITHM    = "HS256"

# ── Operaciones administrativas ───────────────────────
# Se envía como header X-Admin-Key en endpoints de escritura
ADMIN_SECRET = "clave_admin_segura"

# ── MySQL local (base de datos del hub) ───────────────
MYSQL_HOST = "localhost"
MYSQL_PORT = "3306"
MYSQL_DB   = "redesipcore_hub"
MYSQL_USER = "hub_user"
MYSQL_PASS = "password_mysql"

# ── Docker (opcional) ─────────────────────────────────
# Usado por docker-compose y por el check automático al arranque
MYSQL_ROOT_PASS      = "root_password_seguro"
MYSQL_CONTAINER_NAME = "redesipcore_mysql"
```

> El archivo `.env` real está excluido del repositorio por `.gitignore`.

---

## Base de datos MySQL

La app **crea la base de datos y todas las tablas automáticamente** al arrancar. No se requiere ningún comando SQL manual.

Si prefieres crearla tú mismo:

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
| servidor_id | VARCHAR(100) | Servidor remoto asociado |
| empresa_cod | VARCHAR(50) | Código de empresa (CODEMPRESA) |

#### `usuarios_departamentos`
| Columna | Tipo | Descripción |
|---|---|---|
| id | INT PK AUTO | Identificador único |
| cod_usuario | VARCHAR(50) | CODUSUARIO del servidor remoto |
| servidor_id | VARCHAR(100) | Servidor remoto del usuario |
| departamento_id | INT FK | → `departamentos.id` (CASCADE) |
| rol | VARCHAR(20) | `admin` \| `jefe` \| `empleado` |

> Restricción única: `(cod_usuario, servidor_id, departamento_id)` — un usuario tiene un solo rol por departamento.

#### `refresh_tokens`
| Columna | Tipo | Descripción |
|---|---|---|
| id | INT PK AUTO | Identificador único |
| token | VARCHAR(512) UNIQUE | Token seguro (64 bytes urlsafe) |
| cod_usuario | VARCHAR(50) | Usuario propietario |
| servidor_id | VARCHAR(100) | Servidor del usuario |
| usuario | VARCHAR(100) | Nombre de usuario |
| expires_at | DATETIME | Expiración (7 días desde creación) |
| revocado | BOOLEAN | `true` tras logout |
| created_at | DATETIME | Fecha de creación |

#### `auditoria`
| Columna | Tipo | Descripción |
|---|---|---|
| id | INT PK AUTO | Identificador único |
| timestamp | DATETIME | Fecha y hora del evento |
| cod_usuario | VARCHAR(50) | Quién realizó la acción |
| servidor_id | VARCHAR(100) | Desde qué servidor |
| accion | VARCHAR(100) | Tipo de acción (ver tabla abajo) |
| detalle | VARCHAR(500) | Información adicional opcional |

**Acciones registradas:**

| Acción | Cuándo se registra |
|---|---|
| `LOGIN` | Inicio de sesión exitoso |
| `LOGOUT` | Cierre de sesión |
| `TOKEN_REFRESH` | Renovación de access token |
| `SERVIDOR_REGISTRADO` | Registro de nuevo servidor remoto |
| `DEPARTAMENTO_CREADO` | Creación de departamento |
| `DEPARTAMENTO_ELIMINADO` | Eliminación de departamento |
| `USUARIO_ASIGNADO` | Asignación de usuario a departamento |
| `USUARIO_ROL_ACTUALIZADO` | Cambio de rol de un usuario |
| `USUARIO_REMOVIDO` | Remoción de usuario de departamento |
| `APP_CREADA` | Registro de nueva app |
| `APP_ACTUALIZADA` | Modificación de app |
| `APP_ELIMINADA` | Eliminación de app |
| `APP_PERMISOS_ACTUALIZADOS` | Cambio de permisos de una app |

---

## Docker automático al arranque

Al iniciar, la app intenta detectar Docker y garantizar que el contenedor MySQL esté disponible:

```
1. ¿Está el SDK de Docker instalado?
   NO → aviso en logs, continúa sin Docker
   SÍ → intenta conectar al daemon

2. ¿Responde el daemon Docker?
   NO → aviso en logs, continúa sin Docker
   SÍ → busca el contenedor "redesipcore_mysql"

3. ¿Existe el contenedor?
   SÍ, corriendo  → log informativo, nada que hacer
   SÍ, detenido   → lo arranca
   NO existe      → lo crea con las variables del .env

4. En cualquier error → solo se registra en logs, la app NO se detiene
```

Para instalar el SDK de Docker:
```bash
pip install docker
```

---

## Logs

Todos los logs siguen el formato:
```
2026-05-01 14:32:05 | INFO     | hub_central.routers.auth | Login exitoso — usuario=jperez servidor=local
2026-05-01 14:32:06 | WARNING  | hub_central.database.database | MySQL no disponible — reintento 1/10 en 3s...
2026-05-01 14:33:01 | ERROR    | hub_central.helpers.docker_check | No se pudo crear el contenedor MySQL: ...
```

Niveles usados:
- `INFO` — eventos normales de operación
- `WARNING` — situaciones recuperables (MySQL tardando, Docker no disponible)
- `ERROR` — fallos que requieren atención (contenedor no se pudo crear, error de auditoría)

---

## Tests

Los tests usan **SQLite en memoria** como base de datos y mockean las dependencias externas (servidores remotos, Docker). No requieren MySQL ni ningún servidor corriendo.

```bash
# Instalar dependencias de test
pip install pytest httpx

# Correr todos los tests
pytest tests/ -v

# Correr un archivo específico
pytest tests/test_apps.py -v
```

**19 casos de test distribuidos en 4 archivos:**

| Archivo | Qué prueba |
|---|---|
| `test_auth.py` | Refresh válido/inválido/expirado/revocado; logout y doble-logout |
| `test_departamentos.py` | Listar paginado, crear con/sin admin key, asignar roles, flujo CRUD completo |
| `test_apps.py` | Crear/duplicar/permisos inválidos, paginación, `mis-apps` filtrado por rol |
| `test_servidores.py` | Listar servidores, registrar (sin key, duplicado, fallo de conexión), paginación de empresas |

Para agregar tests:
```python
# tests/test_mi_modulo.py
def test_algo(client):          # client inyecta JWT mock + SQLite
    r = client.get("/api/...")
    assert r.status_code == 200

def test_admin(client):         # operaciones admin
    from tests.conftest import ADMIN_HEADERS
    r = client.post("/api/...", json={...}, headers=ADMIN_HEADERS)
    assert r.status_code == 201
```

---

## API Reference

Documentación interactiva: `http://localhost:8000/docs` (Swagger) · `http://localhost:8000/redoc`

### Convenciones

| Icono | Significado | Header requerido |
|---|---|---|
| (público) | Sin autenticación | — |
| 🔒 | Requiere JWT | `Authorization: Bearer <access_token>` |
| 🔒🔑 | Requiere JWT + clave admin | `Authorization: Bearer <token>` + `X-Admin-Key: <clave>` |

---

### Autenticación

#### `POST /api/auth/login`

Autentica contra un servidor remoto y devuelve ambos tokens.

**Request:**
```json
{ "servidor": "local", "password": "mi_password" }
```

**Response `200`:**
```json
{
  "status":        "success",
  "message":       "Login exitoso",
  "access_token":  "eyJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW...",
  "token_type":    "bearer"
}
```

| Código | Motivo |
|---|---|
| 404 | Servidor no registrado |
| 401 | Contraseña incorrecta |
| 403 | Usuario bloqueado o descatalogado |
| 500 | Error de conexión a BD remota |

> El **access token** expira en **8 horas**. El **refresh token** expira en **7 días**.

---

#### `POST /api/auth/refresh`

Renueva el access token usando el refresh token. No requiere relogeo.

**Request:**
```json
{ "refresh_token": "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW..." }
```

**Response `200`:**
```json
{
  "status":       "success",
  "access_token": "eyJhbGciOiJIUzI1NiJ9...",
  "token_type":   "bearer"
}
```

| Código | Motivo |
|---|---|
| 401 | Refresh token inexistente, expirado o revocado |

---

#### `POST /api/auth/logout`

Revoca el refresh token. El access token actual sigue válido hasta su expiración natural.

**Request:**
```json
{ "refresh_token": "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW..." }
```

**Response `200`:**
```json
{ "status": "success", "mensaje": "Sesión cerrada correctamente." }
```

> Si el token no existe, responde `200` igualmente (operación idempotente).

---

### Servidores

#### `GET /api/servidores/`

Lista los identificadores de servidores remotos registrados.

```json
{ "total": 2, "servidores_disponibles": ["local", "sede_central"] }
```

---

#### `POST /api/servidores/registrar` 🔒🔑

Registra un servidor remoto. Prueba la conexión antes de guardar. Soporta MSSQL, PostgreSQL y MySQL.

**Request:**
```json
{
  "servidor": "sucursal_norte",
  "host":     "10.0.0.50",
  "puerto":   1433,
  "db_name":  "GENERAL",
  "tipo":     "mssql",
  "driver":   "SQL Server",
  "usuario":  "sa",
  "password": "mi_pass"
}
```

**Tipos soportados:** `mssql` / `sqlserver`, `postgresql` / `postgres`, `mysql` / `mariadb`

---

#### `GET /api/servidores/listarEmpresas` 🔒

Lista todas las empresas del servidor del usuario autenticado. Paginado.

```
GET /api/servidores/listarEmpresas?pagina=1&tamano=20
```

---

#### `GET /api/servidores/listarEmpresasUsuario` 🔒

Lista las empresas asignadas al usuario autenticado. Paginado.

---

### Departamentos

Todos requieren 🔒. Los de escritura requieren además 🔑.

#### `GET /api/departamentos/` 🔒

Lista los departamentos del servidor del usuario. Paginado.

```
GET /api/departamentos/?pagina=1&tamano=20
```

**Response:**
```json
{
  "status": "success", "total": 3, "pagina": 1, "tamano": 20, "paginas": 1,
  "departamentos": [
    { "id": 1, "nombre": "Contabilidad", "descripcion": "...", "servidor_id": "local", "empresa_cod": "001" }
  ]
}
```

---

#### `POST /api/departamentos/` 🔒🔑 → `201`

```json
{ "nombre": "Recursos Humanos", "descripcion": "Gestión de personal", "servidor_id": "local", "empresa_cod": "001" }
```

---

#### `DELETE /api/departamentos/{id}` 🔒🔑

Elimina el departamento y sus asignaciones de usuarios en cascada.

---

#### `POST /api/departamentos/asignar-usuario` 🔒🔑

Asigna un usuario a un departamento. Si ya existe, actualiza su rol.

```json
{ "cod_usuario": "U001", "departamento_id": 1, "rol": "jefe" }
```

**Roles válidos:** `admin` · `jefe` · `empleado`

---

#### `DELETE /api/departamentos/asignaciones/{asignacion_id}` 🔒🔑

Remueve a un usuario de un departamento.

---

#### `GET /api/departamentos/{id}/usuarios` 🔒🔑

Lista los usuarios de un departamento con sus roles. Paginado.

```json
{
  "status": "success", "departamento": "Contabilidad",
  "total": 2, "pagina": 1, "tamano": 20, "paginas": 1,
  "usuarios": [
    { "id": 1, "cod_usuario": "U001", "rol": "jefe" },
    { "id": 2, "cod_usuario": "U002", "rol": "empleado" }
  ]
}
```

---

### Aplicaciones

#### `GET /api/apps/mis-apps` 🔒

**Endpoint principal del hub.** Devuelve las apps visibles para el usuario según sus roles.

```json
{
  "status": "success",
  "roles": ["jefe"],
  "apps": [
    { "name": "Sistema ERP", "version": "2.1.0", "description": "...", "href": "http://erp.local", "permissions": ["admin","jefe"] }
  ]
}
```

> Si el usuario no está asignado a ningún departamento, devuelve `apps: []`.

---

#### `GET /api/apps/` 🔒🔑

Lista todas las apps registradas. Paginado.

```
GET /api/apps/?pagina=1&tamano=20
```

---

#### `POST /api/apps/` 🔒🔑 → `201`

```json
{
  "name":        "Sistema de Inventario",
  "version":     "1.0.0",
  "description": "Control de almacén",
  "href":        "http://192.168.1.10:9090/inventario",
  "permissions": ["admin", "jefe"]
}
```

---

#### `PUT /api/apps/{nombre}` 🔒🔑

Actualiza campos específicos (todos opcionales):

```json
{ "version": "1.1.0", "permissions": ["admin", "jefe", "empleado"] }
```

---

#### `DELETE /api/apps/{nombre}` 🔒🔑

Elimina la app del catálogo.

---

#### `POST /api/apps/{nombre}/permisos` 🔒🔑

Reemplaza los permisos de la app:

```json
{ "permissions": ["admin"] }
```

---

### Auditoría

#### `GET /api/audit/` 🔒🔑

Consulta el registro de auditoría del servidor del usuario. Soporta filtros y paginación.

```
GET /api/audit/?pagina=1&tamano=50&cod_usuario=U001&accion=LOGIN
```

**Response:**
```json
{
  "status": "success", "total": 42, "pagina": 1, "tamano": 50, "paginas": 1,
  "registros": [
    {
      "id": 42,
      "timestamp": "2026-05-01T14:32:05",
      "cod_usuario": "U001",
      "accion": "LOGIN",
      "detalle": "usuario=jperez"
    }
  ]
}
```

---

## Sistema de roles y visibilidad

### Roles

| Rol | Descripción típica |
|---|---|
| `admin` | Acceso total al hub y sus apps de administración |
| `jefe` | Ve apps de gestión de su área + apps operativas |
| `empleado` | Ve únicamente apps operativas básicas |

### Lógica de visibilidad

1. Usuario hace login → recibe JWT con `cod_usuario` y `servidor_id`
2. `GET /api/apps/mis-apps` consulta MySQL → obtiene **todos los roles** del usuario en todos sus departamentos
3. Filtra `apps.json` → devuelve apps donde `permissions` contenga **al menos uno** de esos roles
4. Un usuario en múltiples departamentos obtiene la **unión** de sus roles

### Ejemplo

```
Usuario U001:
  Departamento "Contabilidad" → rol: jefe
  Departamento "Proyectos"    → rol: empleado

Apps:
  "ERP Financiero"    permissions: ["admin","jefe"]             → ✅ visible
  "Portal de Obras"   permissions: ["admin","jefe","empleado"]  → ✅ visible
  "Panel Admin"       permissions: ["admin"]                    → ❌ no visible
```

---

## Formato de apps.json

`hub_central/jsons/apps.json` — gestionado automáticamente por la API.

```json
{
    "apps": [
        {
            "name":        "Sistema ERP",
            "version":     "2.1.0",
            "description": "Gestión empresarial integrada",
            "href":        "http://192.168.1.10:8080/erp",
            "permissions": ["admin", "jefe", "empleado"]
        },
        {
            "name":        "Panel de Reportes",
            "version":     "1.5.0",
            "description": "Reportes y estadísticas gerenciales",
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

| Campo | Tipo | Requerido | Descripción |
|---|---|---|---|
| `name` | string | ✅ | Identificador único de la app |
| `version` | string | ✅ | Versión semántica |
| `description` | string | — | Descripción breve |
| `href` | string | ✅ | URL de acceso a la app |
| `permissions` | string[] | ✅ | Roles con acceso: `admin`, `jefe`, `empleado` |

---

## Flujo completo de sesión

```
┌─────────────────────────────────────────────────────────────────┐
│  INICIO DE SESIÓN                                               │
│                                                                 │
│  POST /api/auth/login { servidor, password }                    │
│       │                                                         │
│       ├─ Consulta USUARIOS en servidor remoto                   │
│       ├─ Valida contraseña (encriptación legado)                │
│       ├─ Genera access_token  (JWT, 8 horas)                    │
│       ├─ Genera refresh_token (64 bytes, 7 días, guardado en DB)│
│       └─ Registra LOGIN en auditoría                            │
│                                                                 │
│  USO NORMAL (acciones con access_token)                         │
│       │                                                         │
│       ├─ GET /api/apps/mis-apps → apps filtradas por rol        │
│       ├─ GET /api/departamentos/ → mis departamentos            │
│       └─ ... otros endpoints 🔒                                 │
│                                                                 │
│  RENOVACIÓN (access_token expirado, refresh_token válido)       │
│       │                                                         │
│       └─ POST /api/auth/refresh { refresh_token }               │
│              └─ Devuelve nuevo access_token                     │
│                                                                 │
│  CIERRE DE SESIÓN                                               │
│       │                                                         │
│       └─ POST /api/auth/logout { refresh_token }                │
│              └─ Revoca el refresh_token en BD                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Paginación

Todos los endpoints de listado aceptan los parámetros:

| Parámetro | Tipo | Default | Máximo | Descripción |
|---|---|---|---|---|
| `pagina` | int | 1 | — | Número de página (base 1) |
| `tamano` | int | 20 | 100–200 | Resultados por página |

**Estructura de respuesta paginada:**
```json
{
  "status":  "success",
  "total":   150,
  "pagina":  2,
  "tamano":  20,
  "paginas": 8,
  "data":    [...]
}
```

**Endpoints paginados:**
- `GET /api/departamentos/`
- `GET /api/departamentos/{id}/usuarios`
- `GET /api/apps/`
- `GET /api/servidores/listarEmpresas`
- `GET /api/servidores/listarEmpresasUsuario`
- `GET /api/audit/`

---

## Despliegue rápido

```bash
# Desarrollo local
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Producción con Docker
docker compose up -d

# Ver logs
docker compose logs -f hub

# Correr tests
pytest tests/ -v
```

---

## Licencia

Proyecto interno — RedesIP © 2026
