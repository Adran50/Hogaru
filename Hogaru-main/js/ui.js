// ===== Helpers de interfaz + navbar compartida =====
// Inicializar tema claro u oscuro antes de renderizar para evitar destellos
(function () {
  var t = localStorage.getItem('hogaru_tema');
  if (!t) {
    t = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'oscuro' : 'claro';
  }
  document.documentElement.setAttribute('data-tema', t);
})();

// Cada página define <body data-raiz=""> (index) o <body data-raiz="../"> (carpeta paginas/)
const RAIZ = document.body.dataset.raiz || '';
const DIAS = ['', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'];
const ETIQUETAS_ESTADO = {
  pendiente: 'Pendiente', aceptada: 'Aceptada', en_curso: 'En curso', finalizada: 'Finalizada',
  cancelada: 'Cancelada', completado: 'Pagado', reembolsado: 'Reembolsado', aprobado: 'Aprobado',
  rechazado: 'Rechazado', abierta: 'Abierta', en_revision: 'En revisión', resuelta: 'Resuelta',
  activo: 'Activo', suspendido: 'Suspendido',
};

// ---------- texto y formatos ----------
// IMPORTANTE: todo texto que viene de usuarios (nombres, mensajes, motivos) se pasa por esc()
// antes de armar HTML, para que nadie pueda inyectar código en la página.
function esc(texto) {
  return String(texto === null || texto === undefined ? '' : texto).replace(/[&<>"']/g, function (c) {
    return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
  });
}
function peso(n) {
  return '$' + Number(n).toLocaleString('es-AR', { minimumFractionDigits: 0, maximumFractionDigits: 2 });
}
function fechaHora(iso) {
  return new Date(iso).toLocaleString('es-AR', { dateStyle: 'medium', timeStyle: 'short' });
}
function fechaCorta(iso) {
  return new Date(iso).toLocaleDateString('es-AR', { dateStyle: 'medium' });
}
function iniciales(nombre) {
  return String(nombre || '?').split(' ').filter(Boolean).slice(0, 2).map(function (p) { return p[0].toUpperCase(); }).join('');
}
function param(nombre) { return new URLSearchParams(location.search).get(nombre); }
function badge(estado) {
  return '<span class="badge badge-' + esc(estado) + '">' + esc(ETIQUETAS_ESTADO[estado] || estado) + '</span>';
}
function enlaceSeguro(url) {
  // solo se enlazan URLs http/https; cualquier otra cosa se muestra como texto
  return /^https?:\/\//i.test(url) ? '<a href="' + esc(url) + '" target="_blank" rel="noopener">' + esc(url) + '</a>' : esc(url);
}

// ---------- avisos ----------
function toast(mensaje, esError) {
  var cont = document.getElementById('toasts');
  if (!cont) {
    cont = document.createElement('div');
    cont.id = 'toasts';
    document.body.appendChild(cont);
  }
  var t = document.createElement('div');
  t.className = 'toast' + (esError ? ' toast-error' : '');
  t.textContent = mensaje;
  cont.appendChild(t);
  setTimeout(function () { t.remove(); }, 4000);
}
function mostrarAviso(el, tipo, mensaje) {
  el.className = 'aviso aviso-' + tipo;
  el.textContent = mensaje;
  el.classList.remove('oculto');
}
function ocultarAviso(el) { el.classList.add('oculto'); }
function ocupado(boton, estaOcupado) { boton.disabled = estaOcupado; }

// ---------- sesión y navegación ----------
function irALogin() {
  var archivo = location.pathname.split('/').pop() || 'index.html';
  var next = (RAIZ ? '' : '../') + archivo + location.search;
  location.href = RAIZ + 'paginas/login.html?next=' + encodeURIComponent(next);
}
function inicioSegunTipo(tipo) {
  if (tipo === 'prestador') return RAIZ + 'paginas/panel-prestador.html';
  if (tipo === 'administrador') return RAIZ + 'paginas/admin.html';
  return RAIZ + 'paginas/buscar.html';
}
// Devuelve true si el usuario puede ver la página; si no, lo redirige y devuelve false.
function requerirSesion(tiposPermitidos) {
  if (!Sesion.logueado()) { irALogin(); return false; }
  var u = Sesion.usuario();
  if (tiposPermitidos && (!u || tiposPermitidos.indexOf(u.tipo_cuenta) === -1)) {
    location.href = RAIZ + 'index.html';
    return false;
  }
  return true;
}

// ---------- navbar ----------
function renderNavbar() {
  var cont = document.getElementById('navbar');
  if (!cont) return;
  var u = Sesion.usuario();
  var actual = location.pathname.split('/').pop() || 'index.html';
  var P = RAIZ + 'paginas/';
  var links = [[RAIZ + 'index.html', 'Inicio']];

  if (!u || u.tipo_cuenta === 'cliente') links.push([P + 'buscar.html', 'Buscar servicios']);
  if (u && u.tipo_cuenta === 'cliente') links.push([P + 'solicitudes.html', 'Mis solicitudes']);
  if (u && u.tipo_cuenta === 'prestador') {
    links.push([P + 'solicitudes.html', 'Mis trabajos']);
    links.push([P + 'panel-prestador.html', 'Mi panel']);
  }
  if (u && u.tipo_cuenta === 'administrador') {
    links.push([P + 'admin.html', 'Administración']);
    links.push([P + 'solicitudes.html', 'Solicitudes']);
  }

  var linksHtml = links.map(function (l) {
    var activo = l[0].split('/').pop() === actual ? ' activo' : '';
    return '<a class="' + activo.trim() + '" href="' + l[0] + '">' + l[1] + '</a>';
  }).join('');

  var temaActual = document.documentElement.getAttribute('data-tema') || 'claro';
  var iconoTema = temaActual === 'oscuro' ? '☀️' : '🌙';
  var tituloTema = temaActual === 'oscuro' ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro';
  var botonTema = '<button class="btn-tema" id="btn-tema" type="button" title="' + tituloTema + '" aria-label="' + tituloTema + '">' + iconoTema + '</button>';

  var derecha;
  if (u) {
    derecha =
      '<a class="campana" href="' + P + 'notificaciones.html" title="Notificaciones">🔔<span class="globo oculto" id="globo"></span></a>' +
      '<span class="nav-usuario">' + esc(u.nombre) + '</span>' +
      botonTema +
      '<button class="btn btn-claro btn-chico" id="btn-salir">Salir</button>';
  } else {
    derecha =
      botonTema +
      '<a class="btn btn-borde btn-chico" href="' + P + 'login.html">Ingresar</a>' +
      '<a class="btn btn-chico" href="' + P + 'registro.html">Registrarme</a>';
  }

  cont.className = 'navbar';
  cont.innerHTML =
    '<div class="navbar-interna">' +
    '<a class="logo" href="' + RAIZ + 'index.html">' +
      '<img src="' + RAIZ + 'assets/logo.png" alt="Hogaru" class="logo-img">' +
      'Hoga<span>ru</span>' +
    '</a>' +
    '<nav class="nav-links">' + linksHtml + '</nav>' +
    '<div class="nav-derecha">' + derecha + '</div></div>';

  var btnTema = document.getElementById('btn-tema');
  if (btnTema) {
    btnTema.addEventListener('click', function () {
      var act = document.documentElement.getAttribute('data-tema') || 'claro';
      var nuevo = act === 'oscuro' ? 'claro' : 'oscuro';
      document.documentElement.setAttribute('data-tema', nuevo);
      localStorage.setItem('hogaru_tema', nuevo);
      btnTema.textContent = nuevo === 'oscuro' ? '☀️' : '🌙';
      btnTema.title = nuevo === 'oscuro' ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro';
    });
  }

  var salir = document.getElementById('btn-salir');
  if (salir) salir.addEventListener('click', function () {
    Sesion.cerrar();
    location.href = RAIZ + 'index.html';
  });
  if (u) {
    actualizarGlobo();
    setInterval(actualizarGlobo, 30000);
  }
}
async function actualizarGlobo() {
  var globo = document.getElementById('globo');
  if (!globo) return;
  try {
    var r = await api('/notificaciones', { params: { limite: 1 } });
    globo.textContent = r.no_leidas > 99 ? '99+' : r.no_leidas;
    globo.classList.toggle('oculto', r.no_leidas === 0);
  } catch (e) { /* si falla, no se muestra el contador */ }
}

// ---------- componentes reutilizables ----------
function tarjetaServicio(s) {
  var tiene = Number(s.puntuacion_promedio) > 0;
  var rating = tiene
    ? '★ ' + Number(s.puntuacion_promedio).toFixed(1) + ' · ' + s.servicios_realizados + ' realizados'
    : '★ Nuevo · Sin calificaciones';
  return '<a class="card" href="' + RAIZ + 'paginas/servicio.html?id=' + s.id_servicio + '">' +
    '<div class="card-top">' +
      '<div class="avatar">' + esc(iniciales(s.nombre_publico)) + '</div>' +
      '<div>' +
        '<div class="nombre">' + esc(s.nombre_publico) + '</div>' +
        '<div class="rol">' + esc(s.categoria) + '</div>' +
        '<span class="verif-chip">✓ Verificado</span>' +
      '</div>' +
    '</div>' +
    '<div class="rating">' + rating + '</div>' +
    '<div class="precio">' + peso(s.tarifa) + ' <span style="font-size:0.85rem; font-weight:500; color:var(--gris);">/ hora</span></div>' +
    '<span class="card-btn">Ver disponibilidad →</span></a>';
}

// Editor de disponibilidad semanal: una fila por día (casilla + desde + hasta)
function montarEditorDisponibilidad(cont) {
  cont.innerHTML = DIAS.slice(1).map(function (dia, i) {
    var n = i + 1;
    return '<div class="franja" data-dia="' + n + '">' +
      '<div class="campo-check"><input type="checkbox" id="dia-' + n + '"><label for="dia-' + n + '">' + dia + '</label></div>' +
      '<input type="time" value="08:00" aria-label="' + dia + ' desde">' +
      '<input type="time" value="16:00" aria-label="' + dia + ' hasta"></div>';
  }).join('');
}
function leerDisponibilidad(cont) {
  return Array.from(cont.querySelectorAll('.franja')).filter(function (f) {
    return f.querySelector('input[type=checkbox]').checked;
  }).map(function (f) {
    var horas = f.querySelectorAll('input[type=time]');
    return { dia_semana: Number(f.dataset.dia), hora_inicio: horas[0].value, hora_fin: horas[1].value };
  });
}

document.addEventListener('DOMContentLoaded', renderNavbar);
