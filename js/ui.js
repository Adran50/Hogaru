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
function renderAvatar(fotoUrl, nombre, tamano) {
  var t = tamano || 44;
  var nom = nombre || 'Usuario';
  if (fotoUrl) {
    var url = fotoUrl.startsWith('http') ? fotoUrl : (API_URL + fotoUrl);
    return '<img src="' + esc(url) + '" alt="' + esc(nom) + '" class="avatar avatar-img" style="width:' + t + 'px;height:' + t + 'px;border-radius:50%;object-fit:cover;display:inline-block">';
  }
  return '<div class="avatar" style="width:' + t + 'px;height:' + t + 'px;font-size:' + Math.max(12, Math.round(t * 0.36)) + 'px">' + esc(iniciales(nom)) + '</div>';
}
function param(nombre) { return new URLSearchParams(location.search).get(nombre); }
function badge(estado) {
  return '<span class="badge badge-' + esc(estado) + '">' + esc(ETIQUETAS_ESTADO[estado] || estado) + '</span>';
}
function enlaceSeguro(url) {
  if (!url) return '—';
  var href = url;
  if (url.startsWith('/uploads/')) {
    href = (typeof API_URL !== 'undefined' ? API_URL : '') + url;
  }
  if (/^https?:\/\//i.test(href) || href.startsWith('/uploads/')) {
    var esPdf = /\.pdf$/i.test(url);
    var etiqueta = esPdf ? '📄 Ver PDF' : '📎 Ver archivo';
    return '<a href="' + esc(href) + '" target="_blank" rel="noopener" class="btn btn-claro btn-chico">' + etiqueta + '</a>';
  }
  return esc(url);
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

  if (!u || u.tipo_cuenta === 'cliente') {
    links.push([P + 'buscar.html', 'Buscar servicios']);
    links.push([P + 'anuncios.html', 'Avisos de trabajo']);
  }
  if (u && u.tipo_cuenta === 'cliente') links.push([P + 'solicitudes.html', 'Mis solicitudes']);
  if (u && u.tipo_cuenta === 'prestador') {
    links.push([P + 'anuncios.html', 'Bolsa de trabajos']);
    links.push([P + 'solicitudes.html', 'Mis trabajos']);
    links.push([P + 'panel-prestador.html', 'Mi panel']);
  }
  if (u && u.tipo_cuenta === 'administrador') {
    links.push([P + 'admin.html', 'Administración']);
    links.push([P + 'anuncios.html', 'Avisos']);
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
    var avatarHtml = renderAvatar(u.foto_perfil, u.nombre, 34);
    var avatarHtmlLg = renderAvatar(u.foto_perfil, u.nombre, 44);
    var rolLabel = u.tipo_cuenta === 'prestador'
      ? 'Prestador de Servicios'
      : (u.tipo_cuenta === 'administrador' ? 'Administrador' : 'Cliente');

    var rolItemHtml = '';
    if (u.tipo_cuenta === 'prestador') {
      rolItemHtml =
        '<a class="dropdown-item" href="' + P + 'panel-prestador.html">' +
          '<span class="dropdown-item-icono">⚙️</span>' +
          '<span class="dropdown-item-texto">Mi panel de prestador</span>' +
        '</a>';
    } else if (u.tipo_cuenta === 'administrador') {
      rolItemHtml =
        '<a class="dropdown-item" href="' + P + 'admin.html">' +
          '<span class="dropdown-item-icono">🛡️</span>' +
          '<span class="dropdown-item-texto">Panel de administración</span>' +
        '</a>';
    } else if (u.tipo_cuenta === 'cliente') {
      rolItemHtml =
        '<a class="dropdown-item" href="' + P + 'solicitudes.html">' +
          '<span class="dropdown-item-icono">📋</span>' +
          '<span class="dropdown-item-texto">Mis solicitudes</span>' +
        '</a>';
    }

    derecha =
      botonTema +
      '<div class="nav-perfil-contenedor" id="nav-perfil-contenedor">' +
        '<button type="button" class="btn-avatar-nav" id="btn-avatar-menu" title="Mi perfil y notificaciones" aria-haspopup="true" aria-expanded="false">' +
          '<div class="avatar-globo-wrap">' +
            avatarHtml +
            '<span class="globo oculto" id="globo"></span>' +
          '</div>' +
          '<span class="nav-usuario-nombre">' + esc(u.nombre) + '</span>' +
          '<span class="nav-flecha-menu" aria-hidden="true">▾</span>' +
        '</button>' +
        '<div class="dropdown-perfil oculto" id="dropdown-perfil" role="menu">' +
          '<div class="dropdown-header">' +
            '<div class="dropdown-avatar-preview">' + avatarHtmlLg + '</div>' +
            '<div class="dropdown-datos">' +
              '<strong class="dropdown-nombre">' + esc(u.nombre) + ' ' + esc(u.apellido || '') + '</strong>' +
              '<span class="dropdown-rol">' + esc(rolLabel) + '</span>' +
              (u.email ? '<span class="dropdown-email">' + esc(u.email) + '</span>' : '') +
            '</div>' +
          '</div>' +
          '<div class="dropdown-separador"></div>' +
          '<a class="dropdown-item" href="' + P + 'notificaciones.html" id="dropdown-item-notificaciones">' +
            '<span class="dropdown-item-icono">🔔</span>' +
            '<span class="dropdown-item-texto">Notificaciones</span>' +
            '<span class="dropdown-globo oculto" id="dropdown-globo">0</span>' +
          '</a>' +
          '<button type="button" class="dropdown-item" id="dropdown-btn-cambiar-foto">' +
            '<span class="dropdown-item-icono">📷</span>' +
            '<span class="dropdown-item-texto">Cambiar foto de perfil</span>' +
          '</button>' +
          rolItemHtml +
          '<div class="dropdown-separador"></div>' +
          '<button type="button" class="dropdown-item dropdown-item-salir" id="btn-salir">' +
            '<span class="dropdown-item-icono">🚪</span>' +
            '<span class="dropdown-item-texto">Cerrar sesión</span>' +
          '</button>' +
        '</div>' +
      '</div>';
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

  var btnAvatar = document.getElementById('btn-avatar-menu');
  var dropPerfil = document.getElementById('dropdown-perfil');
  if (btnAvatar && dropPerfil) {
    btnAvatar.addEventListener('click', function (e) {
      e.stopPropagation();
      var abriendo = dropPerfil.classList.contains('oculto');
      dropPerfil.classList.toggle('oculto');
      btnAvatar.setAttribute('aria-expanded', abriendo ? 'true' : 'false');
    });
  }

  var btnCambiarFoto = document.getElementById('dropdown-btn-cambiar-foto');
  if (btnCambiarFoto) {
    btnCambiarFoto.addEventListener('click', function () {
      if (dropPerfil) dropPerfil.classList.add('oculto');
      if (btnAvatar) btnAvatar.setAttribute('aria-expanded', 'false');
      abrirModalPerfil();
    });
  }

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

  if (!window._dropdownPerfilHandlerRegistrado) {
    window._dropdownPerfilHandlerRegistrado = true;
    document.addEventListener('click', function (e) {
      var wrap = document.getElementById('nav-perfil-contenedor');
      var drop = document.getElementById('dropdown-perfil');
      var btn = document.getElementById('btn-avatar-menu');
      if (wrap && drop && !wrap.contains(e.target)) {
        drop.classList.add('oculto');
        if (btn) btn.setAttribute('aria-expanded', 'false');
      }
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') {
        var drop = document.getElementById('dropdown-perfil');
        var btn = document.getElementById('btn-avatar-menu');
        if (drop && !drop.classList.contains('oculto')) {
          drop.classList.add('oculto');
          if (btn) btn.setAttribute('aria-expanded', 'false');
        }
      }
    });
  }

  if (u) {
    actualizarGlobo();
    if (window._intervalGlobo) clearInterval(window._intervalGlobo);
    window._intervalGlobo = setInterval(actualizarGlobo, 30000);
  }
}
async function actualizarGlobo() {
  var globo = document.getElementById('globo');
  var dropGlobo = document.getElementById('dropdown-globo');
  if (!globo && !dropGlobo) return;
  try {
    var r = await api('/notificaciones', { params: { limite: 1 } });
    var count = r.no_leidas || 0;
    var txt = count > 99 ? '99+' : String(count);
    if (globo) {
      globo.textContent = txt;
      globo.classList.toggle('oculto', count === 0);
    }
    if (dropGlobo) {
      dropGlobo.textContent = txt;
      dropGlobo.classList.toggle('oculto', count === 0);
    }
  } catch (e) { /* si falla, no se muestra el contador */ }
}

// ---------- modal de perfil de usuario ----------
function abrirModalPerfil() {
  var u = Sesion.usuario();
  if (!u) return;
  var idModal = 'modal-mi-perfil-global';
  var modal = document.getElementById(idModal);
  if (!modal) {
    modal = document.createElement('div');
    modal.id = idModal;
    modal.className = 'modal-envoltorio oculto';
    modal.innerHTML =
      '<div class="modal panel" style="max-width:440px; width:95%;">' +
        '<div class="fila-entre" style="margin-bottom:12px">' +
          '<h2 style="margin:0">Mi Perfil</h2>' +
          '<button type="button" class="btn btn-borde btn-chico" id="modal-perfil-cerrar">✕</button>' +
        '</div>' +
        '<div style="text-align:center; margin:16px 0;" id="modal-perfil-avatar-preview"></div>' +
        '<h3 style="text-align:center; margin:0 0 4px;" id="modal-perfil-nombre-txt"></h3>' +
        '<p class="muted" style="text-align:center; margin:0 0 16px; font-size:0.9rem;" id="modal-perfil-rol-txt"></p>' +
        '<hr style="border:0; border-top:1px solid var(--borde); margin:16px 0">' +
        '<h4 style="margin:0 0 8px; font-size:0.95rem">Foto de perfil</h4>' +
        '<p class="muted" style="font-size:0.85rem; margin-top:0">Subí una foto en formato JPG, PNG o WebP (máx 10 MB).</p>' +
        '<form id="form-modal-foto-perfil">' +
          '<input type="file" id="modal-input-foto" accept="image/jpeg,image/png,image/webp" required style="width:100%; margin-bottom:12px">' +
          '<div class="fila" style="gap:10px; justify-content:space-between">' +
            '<button class="btn btn-claro btn-chico" type="submit" id="btn-modal-guardar-foto">Guardar foto</button>' +
            '<button class="btn btn-borde btn-chico" type="button" id="btn-modal-quitar-foto" style="color:var(--peligro); border-color:var(--peligro)">Quitar foto</button>' +
          '</div>' +
        '</form>' +
      '</div>';
    document.body.appendChild(modal);

    modal.querySelector('#modal-perfil-cerrar').addEventListener('click', function () {
      modal.classList.add('oculto');
    });
    modal.addEventListener('click', function (e) {
      if (e.target === modal) modal.classList.add('oculto');
    });

    var formFoto = modal.querySelector('#form-modal-foto-perfil');
    formFoto.addEventListener('submit', async function (ev) {
      ev.preventDefault();
      var input = modal.querySelector('#modal-input-foto');
      var btn = modal.querySelector('#btn-modal-guardar-foto');
      if (!input.files || !input.files[0]) {
        toast('Elegí una imagen para subir.', true);
        return;
      }
      var fd = new FormData();
      fd.append('archivo', input.files[0]);
      ocupado(btn, true);
      try {
        var res = await fetch(API_URL + '/auth/foto-perfil', {
          method: 'POST',
          headers: { 'Authorization': 'Bearer ' + Sesion.token() },
          body: fd,
        });
        var data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Error al subir la imagen');
        var user = Sesion.usuario();
        user.foto_perfil = data.foto_perfil;
        Sesion.guardar(Sesion.token(), user);
        toast('¡Foto de perfil actualizada con éxito!');
        input.value = '';
        renderNavbar();
        actualizarVistaModalPerfil();
      } catch (err) {
        toast(err.message, true);
      } finally {
        ocupado(btn, false);
      }
    });

    var btnQuitar = modal.querySelector('#btn-modal-quitar-foto');
    btnQuitar.addEventListener('click', async function () {
      if (!confirm('¿Eliminar tu foto de perfil?')) return;
      btnQuitar.disabled = true;
      try {
        await api('/auth/foto-perfil', { metodo: 'DELETE' });
        var user = Sesion.usuario();
        user.foto_perfil = null;
        Sesion.guardar(Sesion.token(), user);
        toast('Foto de perfil eliminada.');
        renderNavbar();
        actualizarVistaModalPerfil();
      } catch (err) {
        toast(err.message, true);
      } finally {
        btnQuitar.disabled = false;
      }
    });
  }

  function actualizarVistaModalPerfil() {
    var curUser = Sesion.usuario();
    if (!curUser) return;
    modal.querySelector('#modal-perfil-avatar-preview').innerHTML = renderAvatar(curUser.foto_perfil, curUser.nombre, 84);
    modal.querySelector('#modal-perfil-nombre-txt').textContent = (curUser.nombre || '') + ' ' + (curUser.apellido || '');
    var rolLabel = curUser.tipo_cuenta === 'prestador' ? 'Prestador de Servicios' : (curUser.tipo_cuenta === 'administrador' ? 'Administrador' : 'Cliente');
    modal.querySelector('#modal-perfil-rol-txt').textContent = rolLabel + (curUser.email ? ' · ' + curUser.email : '');
    var btnQuitar = modal.querySelector('#btn-modal-quitar-foto');
    if (btnQuitar) btnQuitar.style.display = curUser.foto_perfil ? 'inline-block' : 'none';
  }

  actualizarVistaModalPerfil();
  modal.classList.remove('oculto');
}

// ---------- componentes reutilizables ----------
function tarjetaServicio(s) {
  var tiene = Number(s.puntuacion_promedio) > 0;
  var rating = tiene
    ? '★ ' + Number(s.puntuacion_promedio).toFixed(1) + ' · ' + s.servicios_realizados + ' realizados'
    : '★ Nuevo · Sin calificaciones';
  var zonaHtml = s.zona_cobertura
    ? '<div style="font-size:0.8rem;color:var(--gris);margin-top:3px">📍 ' + esc(s.zona_cobertura) + '</div>'
    : '';
  return '<a class="card" href="' + RAIZ + 'paginas/servicio.html?id=' + s.id_servicio + '">' +
    '<div class="card-top">' +
      renderAvatar(s.foto_perfil, s.nombre_publico, 48) +
      '<div>' +
        '<div class="nombre">' + esc(s.nombre_publico) + '</div>' +
        '<div class="rol">' + esc(s.categoria) + '</div>' +
        zonaHtml +
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
