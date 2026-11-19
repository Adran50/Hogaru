# Hogaru — Backend (API REST)

Marketplace de servicios de limpieza doméstica que conecta clientes con prestadores independientes.
Proyecto de Prácticas Profesionalizantes (7° año, E.E.S.T. N°6).

- **Framework**: Python 3.10+ con **FastAPI** y **Uvicorn**
- **Base de datos**: **MySQL 8 / MariaDB** (InnoDB, UTF-8)
- **Acceso a datos**: SQL parametrizado transaccional vía `pymysql` (DictCursor) con rollback automático ante excepciones
- **Seguridad**: Hash **PBKDF2-HMAC-SHA256** (200.000 iteraciones) + Tokens **JWT** (HMAC-SHA256)
- **Prefijo de API**: `/api/v1` (con soporte gemelo en raíz para retrocompatibilidad con frontend estático)
- **Integraciones desacopladas**: Pasarela de pagos (`PaymentGateway`), verificación de antecedentes (`BackgroundCheckProvider`) y notificaciones push/email (`NotificationSender`)

---

## 🚀 Puesta en Marcha Rápida (Sin Entorno Virtual)

Ya no es necesario crear ni activar entornos virtuales (`.venv`). El sistema corre directamente con tu Python 3.10+ global.

### 1. Iniciar con un solo comando (Recomendado)
Desde la **raíz del proyecto**, simplemente ejecutá:
```bash
python run.py
```
O hacé doble clic en el archivo **`iniciar.bat`** (en Windows).

> **¿Qué hace `python run.py` automáticamente?**
> - Comprueba la conexión con MySQL y aplica de forma automática cualquier migración pendiente.
> - Inicia Uvicorn con **auto-recarga activada** (`reload=True`) ante cualquier cambio de código.
> - Sirve tanto la **API REST** como el **Frontend web** en el puerto 8000.
> - **API y Web**: <http://127.0.0.1:8000>
> - **Swagger Docs**: <http://127.0.0.1:8000/docs>
> - **ReDoc**: <http://127.0.0.1:8000/redoc>

---

### 2. Comandos Administrativos desde `backend/`

Si preferís gestionar el servidor o la base de datos de forma granular desde la carpeta `backend/`:

```bash
# Iniciar el servidor API con auto-recarga
python manage.py servidor

# Aplicar migraciones versionadas de base de datos
python manage.py migrar

# Cargar los datos de prueba iniciales (seed)
python manage.py seed

# Asignar la contraseña 'hogaru123' a todos los usuarios demo
python manage.py passwords-demo

# Crear un nuevo administrador
python manage.py crear-admin admin@ejemplo.com tuPassword123 Admin Hogaru
```

---

### 3. Configuración de Variables de Entorno (`.env`)
El proyecto incluye la plantilla `backend/.env.example`. Podés copiarla a `backend/.env` si necesitás cambiar tus credenciales de MySQL o el puerto:
```ini
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=
DB_NAME=hogaru

JWT_SECRET=hogaru-secreto-super-seguro-cambiar-en-produccion
JWT_HORAS=12

COMISION_PLATAFORMA=0.10
MOMENTO_PAGO=flexible
CORS_ORIGINS=*
```

---

### 4. Instalación de Dependencias (si clonás en una máquina nueva)
Si ejecutás el proyecto en una computadora nueva:
```bash
pip install -r requirements.txt
```

## 👥 Usuarios de Prueba Preconfigurados

Todos los usuarios del seed vienen con la contraseña **`hogaru123`** lista para usar:

| Rol | Email | Contraseña | Estado / Detalle |
|---|---|---|---|
| **Administrador** | `admin@hogaru.test` | `hogaru123` | Nivel `superadmin` |
| **Prestador** | `marisa@hogaru.test` | `hogaru123` | Verificación `aprobado` (Morón) |
| **Prestador** | `roberto@hogaru.test` | `hogaru123` | Verificación `aprobado` (Haedo) |
| **Prestador** | `lucia@hogaru.test` | `hogaru123` | Verificación `pendiente` (Castelar) |
| **Prestador** | `esteban@hogaru.test` | `hogaru123` | Verificación `rechazado` (Ramos Mejía) |
| **Cliente** | `carla@hogaru.test` | `hogaru123` | Morón |
| **Cliente** | `julian@hogaru.test` | `hogaru123` | Haedo |
| **Cliente** | `lucas@hogaru.test` | `hogaru123` | Castelar |

---

## 📦 Estructura de Endpoints (`/api/v1`)

### 1. Usuarios y Autenticación (`/api/v1/auth`)
- `POST /auth/registro`: Registro de cliente o prestador con coordenadas opcionales
- `POST /auth/login`: Autenticación con email y contraseña, retorno de token JWT
- `GET /auth/me`: Perfil completo del usuario autenticado (sin contraseñas)
- `PUT /auth/me`: Actualización de datos de perfil, contacto y ubicación
- `POST /auth/cambiar-password`: Cambio de contraseña validando la anterior

### 2. Verificación de Prestadores (`/api/v1/verificacion`)
- `POST /verificacion/subir`: Carga física multipart (`UploadFile`) de DNI (Frente y Dorso) y Antecedentes Penales en PDF o imagen (.jpg, .png) hasta 10 MB, sanitizado con UUIDv4.
- `POST /verificacion/documentos`: Prestador sube enlace/documento con prechequeo automático (`BackgroundCheckProvider`).
- `GET /verificacion/documentos`: Lista de documentos presentados y estado de auditoría.

### 3. Catálogo y Búsqueda de Servicios (`/api/v1/servicios`)
- `GET /categorias`: Listado de categorías activas con iconos.
- `POST /categorias/sugerir`: Sugerencia colaborativa de nuevo oficio/categoría por clientes o prestadores (estado 'propuesta').
- `GET /servicios`: Búsqueda multicriterio con **Haversine** (`lat`, `lng`, `radio_km`), rango de tarifa (`tarifa_min`, `tarifa_max`), puntuación (`puntuacion_min`), día/horario (`dia_semana`, `hora`), paginación y orden.
- `GET /servicios/{id}`: Detalle de servicio y agenda semanal formateada en `HH:MM`.
- `POST /servicios`: Prestador aprobado publica nuevo servicio y disponibilidad.
- `GET /mis-servicios`: Servicios propios del prestador.
- `PATCH /servicios/{id}`: Modificación de tarifa, descripción o pausa/reactivación.
- `PUT /servicios/{id}/disponibilidad`: Reemplazo integral de disponibilidad semanal.

### 4. Bolsa de Trabajos / Marketplace Inverso (`/api/v1/anuncios`)
- `POST /anuncios`: Cliente publica un aviso con presupuesto ofrecido, fecha, duración y dirección.
- `GET /anuncios`: Lista de avisos activos en la Bolsa de Trabajos para prestadores.
- `GET /anuncios/mis-anuncios`: Avisos publicados por el cliente autenticado.
- `POST /anuncios/{id}/postular`: Prestador verificado postula una cotización y propuesta técnica.
- `GET /anuncios/{id}/postulaciones`: Cliente visualiza las ofertas recibidas.
- `POST /anuncios/{id}/adjudicar/{id_postulacion}`: Cliente adjudica la propuesta ganadora y formaliza automáticamente la solicitud.

### 5. Contrataciones y Agenda (`/api/v1/solicitudes`)
- `POST /solicitudes`: Cliente solicita turno directo (valida fecha futura y horario disponible).
- `GET /solicitudes`: Listado de solicitudes del usuario (o todas si es admin).
- `GET /solicitudes/{id}`: Detalle de la contratación.
- `POST /solicitudes/{id}/aceptar`: Prestador aprobado acepta (valida superposiciones horarias).
- `POST /solicitudes/{id}/rechazar`: Prestador rechaza solicitud pendiente.
- `POST /solicitudes/{id}/iniciar`: Prestador marca inicio del trabajo.
- `POST /solicitudes/{id}/finalizar`: Prestador finaliza el servicio.
- `POST /solicitudes/{id}/cancelar`: Cancelación por cliente, prestador o admin (reembolso automático si estaba pagado).

### 6. Pagos Desacoplados estilo Mercado Pago (`/api/v1/solicitudes/{id}/pago`)
- `POST /solicitudes/{id}/pago`: Cliente abona en 1 solo clic mediante pasarela desacoplada (Modo Sandbox) con cálculo de comisión (10%) y opción de simular rechazo (`simular_fallo: true`).
- `GET /solicitudes/{id}/pago`: Consulta del pago registrado y referencia emitida.

### 7. Calificaciones y Reputación (`/api/v1/calificaciones`)
- `POST /solicitudes/{id}/calificacion`: Cliente califica servicio finalizado y pagado (recalcula `puntuacion_promedio` del prestador en capa de servicio).
- `GET /prestadores/{id}/calificaciones`: Reputación pública y desglose de reseñas.

### 8. Disputas y Arbitraje (`/api/v1/solicitudes/{id}/disputas`)
- `POST /solicitudes/{id}/disputas`: Apertura de reclamo sobre solicitud aceptada/en curso/finalizada.
- `GET /solicitudes/{id}/disputas`: Historial de reclamos de una solicitud.

### 9. Notificaciones y Chat de Trabajo
- `GET /api/v1/notificaciones`: Bandeja de notificaciones y conteo de no leídas.
- `POST /api/v1/notificaciones/leer-todas`: Marcar todas como leídas.
- `POST /api/v1/notificaciones/{id}/leer`: Marcar notificación individual.
- `POST /api/v1/solicitudes/{id}/mensajes`: Chat directo entre cliente y prestador.
- `GET /api/v1/solicitudes/{id}/mensajes`: Historial de conversación.

### 10. Administración (`/api/v1/admin`)
- `GET /admin/documentos`: Cola de documentos pendientes con prechequeo de antecedentes.
- `POST /admin/documentos/{id}/resolver`: Admin aprueba o rechaza DNI / antecedentes (recalcula verificación).
- `GET /admin/categorias`: Listado de categorías y propuestas de usuarios.
- `POST /admin/categorias`: Creación de nuevas categorías por el admin.
- `POST /admin/categorias/{id}/aprobar`: Aprobación y activación de categorías propuestas.
- `GET /admin/disputas`: Listado de reclamos de la plataforma.
- `PATCH /admin/disputas/{id}`: Admin pasa a revisión o resuelve con opción de reembolso.
- `GET /admin/usuarios`: Listado de usuarios con filtro por rol.
- `PATCH /admin/usuarios/{id}/estado`: Suspensión o reactivación de cuentas.
- `GET /admin/metricas`: Métricas globales (solicitudes por estado, finanzas, comisiones acumuladas, usuarios y prestadores).

---

## 🛡️ Formato Centralizado de Errores

Todas las respuestas de error siguen una estructura JSON consistente:
```json
{
  "error": {
    "codigo": "VALIDACION_ERROR | NO_AUTORIZADO | ACCESO_DENEGADO | NO_ENCONTRADO | CONFLICTO | REGLA_NEGOCIO",
    "mensaje": "Descripción legible del error",
    "detalles": [
      {
        "campo": "email",
        "mensaje": "value is not a valid email address",
        "tipo": "value_error"
      }
    ]
  },
  "detail": "Descripción legible del error"
}
```

---

## 🧪 Pruebas Automatizadas

El proyecto cuenta con suites de tests integrales con **Pytest**:
```bash
# Correr todos los tests
pytest -v

# Correr tests por fase específica
pytest tests/test_fase2_auth_errores.py -v
pytest tests/test_fase3_verificacion_servicios.py -v
pytest tests/test_fase4_contratacion_estados.py -v
pytest tests/test_fase5_pagos_calificaciones_disputas.py -v
pytest tests/test_fase6_admin_metricas.py -v

# Correr flujo de contratación y casos límite históricos
pytest tests/test_flujo.py tests/test_casos_limite.py -v
```
Las pruebas validan:
- Flujo feliz completo (registro $\rightarrow$ verificación $\rightarrow$ servicio $\rightarrow$ solicitud $\rightarrow$ aceptación $\rightarrow$ cobro $\rightarrow$ finalización $\rightarrow$ calificación $\rightarrow$ recálculo de promedio).
- Todas las transiciones prohibidas de la máquina de estados (retorno 409).
- Permisos por recurso y roles (cliente intentando ver o cancelar solicitud ajena, prestador no verificado intentando publicar).
- Búsqueda geoespacial con Haversine, filtros de tarifa, puntuación y agenda semanal.
- Regla determinística de antecedentes penales (`BackgroundCheckProvider`).
- Cancelación con reembolso automático, disputa resuelta con reintegro y prevención de calificación duplicada.
- Panel de métricas y operaciones administrativas.
