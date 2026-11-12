# Hogaru
Proyecto que tenemos con Patricio J. Feres en Proyecto de desarrollo de software para plataformas moviles.

App web (responsive, pensada primero para celular) para contratar servicios de limpieza doméstica con prestadores verificados.

## Decisiones tomadas
- **Frontend:** HTML + CSS + JavaScript vanilla (sin framework), varias páginas que hablan con la API usando `fetch`.
- **Backend:** Python + FastAPI (carpeta `backend/`). Ver `backend/README.md`.
- **Base de datos:** MySQL/MariaDB (carpeta `base_de_datos/`: esquema, datos de prueba y diagrama ER).

## Estructura
```
Hogaru-main/
├─ index.html              página de inicio (sin sesión)
├─ estilos.css             estilos compartidos de todas las páginas
├─ js/
│  ├─ config.js            dirección de la API (cambiala si usás otro puerto)
│  ├─ api.js               cliente de la API + manejo de sesión (token en localStorage)
│  ├─ ui.js                helpers, navbar compartida y componentes reutilizables
│  └─ <pagina>.js          la lógica de cada página
├─ paginas/
│  ├─ login.html · registro.html
│  ├─ buscar.html · servicio.html           (cliente)
│  ├─ solicitudes.html · solicitud.html     (historial y detalle: acciones, pago, calificación, reclamos, chat)
│  ├─ notificaciones.html
│  ├─ panel-prestador.html                  (verificación y publicación de servicios)
│  ├─ admin.html                            (verificaciones, disputas, usuarios)
│  └─ hogaru-desktop.html · estilos.css     mockup original (se dejó como referencia)
├─ componentes/            (navbar.html quedó vacío: la navbar se genera desde js/ui.js)
├─ backend/                API en FastAPI + tests
└─ base_de_datos/          hogaru_schema.sql · hogaru_datos_prueba.sql · diagrama ER
```

## Cómo correrlo
1. **Base y API:** seguí `backend/README.md` (cargar los `.sql`, `pip install -r requirements.txt`, `uvicorn app.main:app --reload`).
   Para entrar con los usuarios de ejemplo: `python manage.py passwords-demo` (clave `hogaru123`).
2. **Front:** servilo con un servidor estático desde esta carpeta, por ejemplo
   `python -m http.server 5500` y abrir <http://localhost:5500>, o la extensión *Live Server* de VS Code.
   (No lo abras con doble clic: el navegador guarda la sesión por origen y puede fallar.)
3. Si la API corre en otra dirección, cambiala en `js/config.js`.

Usuarios de ejemplo: `carla@hogaru.test` (cliente), `marisa@hogaru.test` y `roberto@hogaru.test` (prestadores),
`admin@hogaru.test` (administrador). Clave: `hogaru123`.

## Qué hace cada rol
- **Visitante:** ve prestadores destacados, busca y filtra servicios, ve disponibilidad y reseñas.
- **Cliente:** solicita turnos, chatea con el prestador, paga (simulado), cancela, califica y abre reclamos.
- **Prestador:** carga documentos para verificarse, publica servicios con sus horarios, acepta/inicia/finaliza trabajos.
- **Administrador:** aprueba o rechaza documentos, gestiona disputas (con reembolso) y suspende cuentas.

## Seguridad en el front
- Todo texto que escriben los usuarios (nombres, mensajes, motivos) se escapa con `esc()` antes de mostrarse: no se puede inyectar HTML.
- Los enlaces a documentos solo se generan si empiezan con `http://` o `https://`.
- El destino `?next=` del login solo acepta páginas internas.
- Los permisos reales los valida el backend; el front solo oculta lo que no corresponde al rol.
