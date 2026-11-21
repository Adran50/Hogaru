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

## 🚀 Cómo correr el programa en cualquier otra computadora (Paso a Paso)

Si vas a clonar o pasar este proyecto a otra computadora para la entrega o presentación, seguí estos simples pasos:

### 1. Requisitos Previos
- **Python 3.10 o superior** instalado (asegurate de marcar la casilla *"Add python.exe to PATH"* durante la instalación).
- **MySQL Server** o **XAMPP / WampServer** en ejecución (puerto estándar 3306).

### 2. Configurar la Base de Datos y el `.env`
1. Abrí MySQL (o phpMyAdmin en XAMPP) y creá la base de datos vacía:
   ```sql
   CREATE DATABASE IF NOT EXISTS hogaru CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```
2. Asegurate de tener el archivo `.env` dentro de la carpeta `backend/` (podés copiar `backend/.env.example` como `backend/.env`):
   ```env
   DB_HOST=localhost
   DB_PORT=3306
   DB_USER=root
   DB_PASSWORD=
   DB_NAME=hogaru
   JWT_SECRET=hogaru-secreto-2024-cambiar-en-produccion
   JWT_HORAS=12
   COMISION_PLATAFORMA=0.10
   MOMENTO_PAGO=flexible
   CORS_ORIGINS=*
   ```

### 3. Instalar librerías necesarias
Abrí una terminal (PowerShell o CMD) en la raíz del proyecto y ejecutá:
```bash
pip install -r backend/requirements.txt
```

### 4. Iniciar la aplicación
Simplemente ejecutá:
```bash
python run.py
```
*(O hacé doble clic en el archivo **`iniciar.bat`** en Windows)*.

> **¿Qué hace `python run.py` de forma 100% automática?**
> 1. Conecta con MySQL y aplica todas las migraciones pendientes (tablas, columnas de perfil, categorías, fotos, etc.).
> 2. Crea las carpetas de subida necesarias (`backend/uploads/documentos` y `backend/uploads/perfiles`).
> 3. Inicia el servidor con auto-recarga y sirve tanto la **API REST** como todo el **Frontend** en el mismo puerto:
>    - 🌐 **Aplicación Web integrada:** <http://127.0.0.1:8000>
>    - 📘 **Documentación Swagger interactiva:** <http://127.0.0.1:8000/docs>

---

## 🛠️ Cambios Finales Aplicados (Última Sesión de Entrega)

1. **Personalización Dinámica de Categorías ("Otros"):**
   - Tanto al crear un servicio como al publicar un aviso de trabajo, los usuarios tienen la opción **"Otros (especificar nueva categoría)..."**.
   - Al seleccionarla, se despliega un campo para indicar el nombre y emoji del rubro.
   - Al confirmar el formulario, la nueva categoría se crea y se activa de inmediato en la base de datos, quedando disponible para todos los demás usuarios de la plataforma.
   - Los **administradores** pueden gestionar, activar o eliminar de forma segura categorías repetidas o redundantes desde el panel de control.

2. **Personalización Integral del Perfil:**
   - Cada usuario puede personalizar desde el menú de navegación (`Mi Perfil`):
     - **Nombre y Apellido:** Protegido con **bloqueo antifraude de 2 semanas**. Si el usuario cambia su nombre, no podrá volver a alterarlo hasta que pasen 14 días (mostrando el contador de días restantes).
     - **Foto de perfil:** Subida, previsualización y eliminación en tiempo real (JPG, PNG, WebP).
     - **Biografía:** Campo de presentación personal con contador dinámico en vivo de **máximo 200 caracteres**.
     - **Redes Sociales:** Hasta 5 enlaces a redes sociales y webs 100% personalizables con título y URL, botón de prueba y eliminación.
   - La biografía y los enlaces a redes se reflejan automáticamente en la ficha pública del profesional (`servicio.html`).

3. **Corrección Visual del Nombre de Marca:**
   - Se unificó el título y logo a **`Hogaru`** en una sola pieza continua en la barra de navegación y vistas, corrigiendo la separación visual previa (`Hoga ru`).

4. **Diseño Mobile-First y Responsividad Celular Completa:**
   - Se implementó un menú hamburguesa (`☰`) táctil y desplegable para pantallas menores a 768px.
   - Todas las tablas del sistema cuentan con desplazamiento horizontal suave (`overflow-x: auto`) para que no rompan el ancho en celulares.
   - Formularios, tarjetas y modales adaptados a pantallas táctiles con tipografía optimizada (previene zoom forzado en iOS/Android).

5. **Revisión General e Inconsistencias Corregidas:**
   - Sincronización y ejecución de todas las migraciones pendientes en MySQL (004 a 009).
   - Incorporación e instalación de la dependencia `python-multipart` para subida de fotos y documentos.
   - Corrección de imports en el panel de administración (`insertar` en `admin.py`).
   - Suite de pruebas automatizadas actualizada con cobertura para perfiles, categorías dinámicas y reglas antifraude.

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
