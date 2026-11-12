// ===== Bandeja de notificaciones =====
(function () {
  if (!requerirSesion()) return;
  var ICONOS = { mensaje: '💬', solicitud: '📩', cambio_estado: '🔔', pago: '💳', disputa: '⚠️' };
  var aviso = document.getElementById('aviso');
  var lista = document.getElementById('lista');

  async function cargar() {
    try {
      var r = await api('/notificaciones', { params: { limite: 100 } });
      document.getElementById('leer-todas').classList.toggle('oculto', r.no_leidas === 0);
      if (!r.notificaciones.length) {
        lista.innerHTML = '<p class="muted" style="padding:20px">No tenés notificaciones.</p>';
        return;
      }
      lista.innerHTML = r.notificaciones.map(function (n) {
        return '<div class="item-notif' + (n.leida ? '' : ' no-leida') + '" data-id="' + n.id_notificacion + '" data-solicitud="' + (n.id_solicitud || '') + '">' +
          '<span class="icono">' + (ICONOS[n.tipo] || '🔔') + '</span>' +
          '<div><div>' + esc(n.texto) + '</div><div class="muted">' + fechaHora(n.fecha) + '</div></div></div>';
      }).join('');
    } catch (e) {
      mostrarAviso(aviso, 'error', e.message);
    }
  }

  lista.addEventListener('click', async function (ev) {
    var item = ev.target.closest('.item-notif');
    if (!item) return;
    try { await api('/notificaciones/' + item.dataset.id + '/leer', { metodo: 'POST' }); } catch (e) { /* no bloquea la navegación */ }
    if (item.dataset.solicitud) location.href = 'solicitud.html?id=' + item.dataset.solicitud;
    else { cargar(); actualizarGlobo(); }
  });

  document.getElementById('leer-todas').addEventListener('click', async function () {
    try {
      await api('/notificaciones/leer-todas', { metodo: 'POST' });
      await cargar();
      actualizarGlobo();
    } catch (e) { toast(e.message, true); }
  });

  cargar();
})();
