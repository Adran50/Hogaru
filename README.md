# Hogaru
Proyecto de desarrollo de software para plataformas móviles y web — Prácticas Profesionalizantes (7° Año).

App web (responsive, Mobile First) para contratar servicios de limpieza doméstica y oficios con prestadores verificados mediante DNI y antecedentes penales.

## Decisiones tomadas
- **Frontend:** HTML + CSS + JavaScript vanilla (sin framework), varias páginas que hablan con la API usando `fetch`.
- **Backend:** Python + FastAPI (carpeta `backend/`). Ver `backend/README.md`.
- **Base de datos:** MySQL/MariaDB (carpeta `base_de_datos/`: esquema, migraciones versionadas y datos de prueba).

## Estructura
```
Hogaru/
├─ run.py                  script de inicio rápido unificado (migraciones + uvicorn)
├─ iniciar.bat             acceso directo para iniciar el proyecto en Windows
├─ index.html              página de inicio (buscador, destacados, acceso a la bolsa)
├─ estilos.css             estilos compartidos de todas las páginas
├─ Hogaru_Informe_Requerimientos_y_Etapas.docx   informe técnico completo por etapas
├─ js/
│  ├─ config.js            dirección de la API
│  ├─ api.js               cliente de la API + manejo de sesión (token en localStorage)
│  ├─ ui.js                helpers, navbar compartida y componentes reutilizables
│  ├─ anuncios.js          lógica de la bolsa de trabajos y postulación
│  └─ <pagina>.js          la lógica de cada página
├─ paginas/
│  ├─ login.html · registro.html                (permite adjuntar PDF/imagen en registro)
│  ├─ buscar.html · servicio.html               (cliente)
│  ├─ anuncios.html                             (bolsa de trabajos y avisos de clientes)
│  ├─ solicitudes.html · solicitud.html         (historial y detalle: pago, chat, disputas)
│  ├─ notificaciones.html
│  ├─ panel-prestador.html                      (subida de PDFs, categorías y servicios)
│  ├─ admin.html                                (verificaciones, categorías, disputas, usuarios)
│  └─ hogaru-desktop.html · estilos.css         mockup original
├─ backend/
│  ├─ app/routers/anuncios.py                   (marketplace inverso: avisos y cotizaciones)
│  ├─ uploads/documentos/                       (archivos PDF/imágenes subidos sanitizados)
│  └─ tests/test_fase7_mejoras_anuncios_archivos.py
└─ base_de_datos/
   ├─ migraciones/004_mejoras_anuncios_y_archivos.sql
   └─ hogaru_schema.sql
```

## Cómo correrlo (Inicio Rápido)

Ya no es necesario crear ni activar entornos virtuales. Tu Python del sistema ejecuta todo directamente.

### Opción 1: Un solo comando (Recomendada)
Desde la terminal en la raíz del proyecto:
```bash
python run.py
```
> **¿Qué hace automáticamente `python run.py`?**
> 1. Conecta con MySQL y aplica de forma automática cualquier migración pendiente.
> 2. Inicia el servidor con **auto-recarga activada** (`reload=True`), de modo que ante cualquier cambio de código el servidor se actualiza solo.
> 3. Sirve tanto la **API REST** como el **Frontend web** en el mismo puerto:
>    - 🌐 **Aplicación Web:** <http://127.0.0.1:8000>
>    - 📘 **Documentación Swagger:** <http://127.0.0.1:8000/docs>
>    - 📕 **ReDoc:** <http://127.0.0.1:8000/redoc>

### Opción 2: Doble clic en Windows
Hacé doble clic en el archivo **`iniciar.bat`** en la carpeta principal del proyecto.

### Opción 3: Comandos tradicionales con `manage.py`
Si preferís ejecutar comandos individuales desde la carpeta `backend/`:
```bash
python manage.py servidor    # Inicia Uvicorn con auto-recarga
python manage.py migrar      # Aplica migraciones versionadas
python manage.py seed        # Carga datos de prueba
python manage.py passwords-demo  # Asigna 'hogaru123' a todos los usuarios demo
```

Usuarios de ejemplo: `carla@hogaru.test` (cliente), `marisa@hogaru.test` y `roberto@hogaru.test` (prestadores), `admin@hogaru.test` (administrador). Clave: `hogaru123`.

## Qué hace cada rol
- **Visitante:** ve prestadores destacados, busca y filtra servicios, explora la bolsa de avisos de trabajo.
- **Cliente:**
  - Contrata turnos directos por catálogo o **publica avisos de trabajo** con presupuesto, horario y dirección.
  - Recibe ofertas de prestadores en su aviso, compara cotizaciones y reputación, y adjudica al mejor candidato.
  - Chatea en tiempo real, paga (simulado), califica con estrellas y abre disputas si hay inconvenientes.
- **Prestador:**
  - **Sube sus documentos reales en formato PDF o imagen** (DNI y Certificado de Antecedentes) tanto en el registro como en su panel.
  - **Sugiere nuevas categorías** de servicios si no encuentra su especialidad.
  - **Explora la Bolsa de Trabajos** y se postula a avisos de clientes enviando cotizaciones personalizadas.
  - Publica servicios directos con agenda semanal y gestiona el estado de sus trabajos.
- **Administrador:**
  - Audita y aprueba/rechaza documentos PDF o imágenes subidos por los prestadores.
  - **Administra el catálogo de categorías**: aprueba sugerencias de la comunidad y crea categorías activas con iconos.
  - Resuelve disputas mediando reembolsos y gestiona el estado de las cuentas.
