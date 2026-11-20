// ===== Listado de solicitudes (historial del cliente / trabajos del prestador / todas para admin) =====
(function () {
  if (!requerirSesion()) return;
  var usuario = Sesion.usuario();
  var tipo = usuario.tipo_cuenta;
  var aviso = document.getElementById('aviso');
  var estadoActual = '';

  var TEXTOS = {
    cliente: ['Mis solicitudes', 'Tu historial de servicios contratados.'],
    prestador: ['Mis trabajos', 'Solicitudes que recibiste. Entrá a una para aceptarla o gestionarla.'],
    administrador: ['Solicitudes', 'Todas las solicitudes de la plataforma.'],
  };
  document.getElementById('titulo').textContent = TEXTOS[tipo][0];
  document.getElementById('subtitulo').textContent = TEXTOS[tipo][1];

  // Perfil del usuario actual en la cabecera
  function actualizarPerfilCabecera() {
    var cur = Sesion.usuario();
    if (!cur) return;
    var contAvatar = document.getElementById('avatar-perfil-solicitudes');
    var txtNombre = document.getElementById('nombre-perfil-solicitudes');
    var txtInfo = document.getElementById('info-perfil-solicitudes');
    if (contAvatar) contAvatar.innerHTML = renderAvatar(cur.foto_perfil, cur.nombre, 54);
    if (txtNombre) txtNombre.textContent = (cur.nombre || '') + ' ' + (cur.apellido || '');
    var rolTxt = cur.tipo_cuenta === 'prestador' ? 'Prestador de Servicios' : (cur.tipo_cuenta === 'administrador' ? 'Administrador' : 'Cliente');
    if (txtInfo) txtInfo.textContent = rolTxt + (cur.email ? ' · ' + cur.email : '');
  }
  actualizarPerfilCabecera();

  var btnCambiarFoto = document.getElementById('btn-cambiar-foto-solicitudes');
  if (btnCambiarFoto) {
    btnCambiarFoto.addEventListener('click', function () {
      abrirModalPerfil();
    });
  }

  var ESTADOS = [['', 'Todas'], ['pendiente', 'Pendientes'], ['aceptada', 'Aceptadas'], ['en_curso', 'En curso'], ['finalizada', 'Finalizadas'], ['cancelada', 'Canceladas']];
  var filtros = document.getElementById('filtros');
  filtros.innerHTML = ESTADOS.map(function (e) {
    return '<button class="chip' + (e[0] === '' ? ' activo' : '') + '" data-estado="' + e[0] + '">' + e[1] + '</button>';
  }).join('');
  filtros.addEventListener('click', function (ev) {
    var b = ev.target.closest('button[data-estado]');
    if (!b) return;
    estadoActual = b.dataset.estado;
    filtros.querySelectorAll('.chip').forEach(function (c) { c.classList.toggle('activo', c === b); });
    cargar();
  });

  async function cargar() {
    ocultarAviso(aviso);
    var tabla = document.getElementById('tabla');
    try {
      var lista = await api('/solicitudes', { params: { estado: estadoActual } });
      if (!lista.length) {
        tabla.innerHTML = '<p class="muted">No hay solicitudes' + (estadoActual ? ' en este estado' : ' todavía') + '.</p>' +
          (tipo === 'cliente' && !estadoActual ? '<a class="btn" href="buscar.html">Buscar un servicio</a>' : '');
        return;
      }
      var colCliente = tipo !== 'cliente';
      var colPrestador = tipo !== 'prestador';
      tabla.innerHTML = '<table><thead><tr><th>Servicio</th>' +
        (colCliente ? '<th>Cliente</th>' : '') + (colPrestador ? '<th>Prestador</th>' : '') +
        '<th>Fecha</th><th>Monto</th><th>Estado</th><th>Pago</th></tr></thead><tbody>' +
        lista.map(function (s) {
          var clienteTd = colCliente
            ? '<td><div style="display:inline-flex;align-items:center;gap:8px">' +
                renderAvatar(s.cliente_foto, s.cliente, 26) +
                '<span>' + esc(s.cliente) + '</span></div></td>'
            : '';
          var prestadorTd = colPrestador
            ? '<td><div style="display:inline-flex;align-items:center;gap:8px">' +
                renderAvatar(s.prestador_foto, s.prestador, 26) +
                '<span>' + esc(s.prestador) + '</span></div></td>'
            : '';

          return '<tr class="fila-link" data-id="' + s.id_solicitud + '"><td>' + esc(s.servicio) + '</td>' +
            clienteTd + prestadorTd +
            '<td>' + fechaHora(s.fecha_hora_programada) + '</td><td>' + peso(s.monto_estimado) + '</td>' +
            '<td>' + badge(s.estado) + '</td><td>' + (s.pago_estado ? badge(s.pago_estado) : '<span class="muted">—</span>') + '</td></tr>';
        }).join('') + '</tbody></table>';
    } catch (e) {
      mostrarAviso(aviso, 'error', e.message);
    }
  }

  document.getElementById('tabla').addEventListener('click', function (ev) {
    var fila = ev.target.closest('tr[data-id]');
    if (fila) location.href = 'solicitud.html?id=' + fila.dataset.id;
  });
  cargar();
})();
