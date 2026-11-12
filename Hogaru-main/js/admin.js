// ===== Panel de administración: verificaciones, disputas y usuarios =====
(function () {
  if (!requerirSesion(['administrador'])) return;
  var vista = document.getElementById('vista');
  var aviso = document.getElementById('aviso');
  var tabActual = 'documentos';
  var TIPOS_DOC = { dni: 'DNI', antecedentes_penales: 'Antecedentes penales', otro: 'Otro' };

  // ---------- verificaciones ----------
  async function vistaDocumentos() {
    var docs = await api('/admin/documentos', { params: { estado: 'pendiente' } });
    if (!docs.length) { vista.innerHTML = '<p class="muted">No hay documentos pendientes de revisión. 🎉</p>'; return; }
    vista.innerHTML = '<table><thead><tr><th>Prestador</th><th>Documento</th><th>Archivo</th><th>Cargado</th><th></th></tr></thead><tbody>' +
      docs.map(function (d) {
        return '<tr><td>' + esc(d.prestador) + '</td><td>' + esc(TIPOS_DOC[d.tipo_documento] || d.tipo_documento) + '</td><td>' + enlaceSeguro(d.archivo_url) + '</td><td>' + fechaCorta(d.fecha_carga) + '</td>' +
          '<td class="fila"><button class="btn btn-chico" data-doc="' + d.id_documento + '" data-estado="aprobado">Aprobar</button>' +
          '<button class="btn btn-peligro btn-chico" data-doc="' + d.id_documento + '" data-estado="rechazado">Rechazar</button></td></tr>';
      }).join('') + '</tbody></table>';
  }

  // ---------- disputas ----------
  var filtroDisputa = '';
  async function vistaDisputas() {
    var lista = await api('/admin/disputas', { params: { estado: filtroDisputa } });
    var filtros = [['', 'Todas'], ['abierta', 'Abiertas'], ['en_revision', 'En revisión'], ['resuelta', 'Resueltas']].map(function (f) {
      return '<button class="chip' + (f[0] === filtroDisputa ? ' activo' : '') + '" data-filtro="' + f[0] + '">' + f[1] + '</button>';
    }).join('');
    var cuerpo = lista.length ? lista.map(function (d) {
      var acciones = '';
      if (d.estado !== 'resuelta') {
        acciones = '<div class="fila" style="margin-top:8px">' +
          (d.estado === 'abierta' ? '<button class="btn btn-claro btn-chico" data-tomar="' + d.id_disputa + '">Tomar disputa</button>' : '') +
          '<button class="btn btn-chico" data-resolver="' + d.id_disputa + '">Resolver…</button></div>' +
          '<form class="oculto" data-form-resolver="' + d.id_disputa + '" style="margin-top:10px">' +
          '<div class="campo"><label>Resolución</label><textarea required maxlength="2000" placeholder="Explicá la decisión para ambas partes"></textarea></div>' +
          '<div class="campo-check"><input type="checkbox" id="reem-' + d.id_disputa + '"><label for="reem-' + d.id_disputa + '">Reembolsar el pago al cliente</label></div>' +
          '<button class="btn btn-chico" type="submit">Confirmar resolución</button></form>';
      }
      return '<div style="padding:14px 0;border-bottom:1px solid var(--gris-claro)"><div class="fila">' + badge(d.estado) +
        '<strong>Disputa #' + d.id_disputa + '</strong><a href="solicitud.html?id=' + d.id_solicitud + '">Ver solicitud #' + d.id_solicitud + '</a>' +
        '<span class="muted">' + fechaCorta(d.fecha_apertura) + '</span></div><p style="margin:6px 0 0">' + esc(d.motivo) + '</p>' +
        (d.resolucion ? '<p class="muted" style="margin:4px 0 0"><strong>Resolución:</strong> ' + esc(d.resolucion) + '</p>' : '') + acciones + '</div>';
    }).join('') : '<p class="muted">No hay disputas en este estado.</p>';
    vista.innerHTML = '<div class="chips" style="justify-content:flex-start;margin-top:0">' + filtros + '</div>' + cuerpo;
  }

  // ---------- usuarios ----------
  async function vistaUsuarios() {
    var lista = await api('/admin/usuarios', { params: { limite: 200 } });
    var yo = Sesion.usuario().id_usuario;
    vista.innerHTML = '<table><thead><tr><th>Nombre</th><th>Email</th><th>Tipo</th><th>Registro</th><th>Estado</th><th></th></tr></thead><tbody>' +
      lista.map(function (u) {
        var boton = u.id_usuario === yo ? '' :
          '<button class="btn btn-chico ' + (u.estado === 'activo' ? 'btn-peligro' : 'btn-claro') + '" data-usuario="' + u.id_usuario + '" data-nuevo="' + (u.estado === 'activo' ? 'suspendido' : 'activo') + '">' +
          (u.estado === 'activo' ? 'Suspender' : 'Reactivar') + '</button>';
        return '<tr><td>' + esc(u.nombre + ' ' + u.apellido) + '</td><td>' + esc(u.email) + '</td><td>' + esc(u.tipo_cuenta) + '</td><td>' + fechaCorta(u.fecha_registro) + '</td><td>' + badge(u.estado) + '</td><td>' + boton + '</td></tr>';
      }).join('') + '</tbody></table>';
  }

  var VISTAS = { documentos: vistaDocumentos, disputas: vistaDisputas, usuarios: vistaUsuarios };
  async function mostrar() {
    ocultarAviso(aviso);
    try { await VISTAS[tabActual](); } catch (e) { mostrarAviso(aviso, 'error', e.message); }
  }

  document.querySelector('.tabs').addEventListener('click', function (ev) {
    var b = ev.target.closest('button[data-tab]');
    if (!b) return;
    tabActual = b.dataset.tab;
    document.querySelectorAll('.tabs .chip').forEach(function (c) { c.classList.toggle('activo', c === b); });
    mostrar();
  });

  vista.addEventListener('click', async function (ev) {
    var t = ev.target;
    try {
      var doc = t.closest('button[data-doc]');
      var filtro = t.closest('button[data-filtro]');
      var tomar = t.closest('button[data-tomar]');
      var resolver = t.closest('button[data-resolver]');
      var usuario = t.closest('button[data-usuario]');
      if (doc) {
        var r = await api('/admin/documentos/' + doc.dataset.doc + '/resolver', { metodo: 'POST', cuerpo: { estado: doc.dataset.estado } });
        toast('Documento ' + doc.dataset.estado + '. Verificación del prestador: ' + r.estado_verificacion_prestador + '.');
        mostrar();
      } else if (filtro) {
        filtroDisputa = filtro.dataset.filtro;
        mostrar();
      } else if (tomar) {
        await api('/admin/disputas/' + tomar.dataset.tomar, { metodo: 'PATCH', cuerpo: { estado: 'en_revision' } });
        toast('Disputa tomada.');
        mostrar();
      } else if (resolver) {
        vista.querySelector('form[data-form-resolver="' + resolver.dataset.resolver + '"]').classList.toggle('oculto');
      } else if (usuario) {
        if (usuario.dataset.nuevo === 'suspendido' && !confirm('¿Suspender esta cuenta? No va a poder iniciar sesión.')) return;
        await api('/admin/usuarios/' + usuario.dataset.usuario + '/estado', { metodo: 'PATCH', cuerpo: { estado: usuario.dataset.nuevo } });
        toast('Cuenta actualizada.');
        mostrar();
      }
    } catch (e) { toast(e.message, true); }
  });

  vista.addEventListener('submit', async function (ev) {
    var form = ev.target.closest('form[data-form-resolver]');
    if (!form) return;
    ev.preventDefault();
    var idDisputa = form.dataset.formResolver;
    try {
      var r = await api('/admin/disputas/' + idDisputa, { metodo: 'PATCH', cuerpo: {
        estado: 'resuelta',
        resolucion: form.querySelector('textarea').value.trim(),
        reembolsar: form.querySelector('input[type=checkbox]').checked,
      } });
      toast(r.pago_reembolsado ? 'Disputa resuelta y pago reembolsado.' : 'Disputa resuelta.');
      mostrar();
    } catch (e) { toast(e.message, true); }
  });

  mostrar();
})();
