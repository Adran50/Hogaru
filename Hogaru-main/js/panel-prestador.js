// ===== Panel del prestador: verificación y servicios =====
(function () {
  if (!requerirSesion(['prestador'])) return;
  var aviso = document.getElementById('aviso');
  var verificado = false;
  var TIPOS_DOC = { dni: 'DNI', antecedentes_penales: 'Antecedentes penales', otro: 'Otro' };
  var TEXTOS_VERIF = {
    pendiente: 'Cargá tu DNI y tu certificado de antecedentes. Un administrador los revisa.',
    aprobado: 'Tu cuenta está verificada: ya podés publicar servicios.',
    rechazado: 'Alguno de tus documentos fue rechazado. Volvé a cargarlo para que lo revisemos de nuevo.',
  };

  montarEditorDisponibilidad(document.getElementById('editor-horarios'));

  async function cargarVerificacion() {
    var yo = await api('/auth/me');
    var estado = yo.perfil.estado_verificacion;
    verificado = estado === 'aprobado';
    document.getElementById('estado-verif').innerHTML = badge(estado);
    document.getElementById('texto-verif').textContent = TEXTOS_VERIF[estado];
    document.getElementById('bloqueo-publicar').classList.toggle('oculto', verificado);
    document.getElementById('btn-publicar').disabled = !verificado;

    var docs = await api('/verificacion/documentos');
    document.getElementById('docs').innerHTML = docs.length
      ? '<div class="tabla-envoltorio"><table><thead><tr><th>Documento</th><th>Archivo</th><th>Cargado</th><th>Estado</th></tr></thead><tbody>' +
        docs.map(function (d) {
          return '<tr><td>' + esc(TIPOS_DOC[d.tipo_documento] || d.tipo_documento) + '</td><td>' + enlaceSeguro(d.archivo_url) + '</td><td>' + fechaCorta(d.fecha_carga) + '</td><td>' + badge(d.estado) + '</td></tr>';
        }).join('') + '</tbody></table></div>'
      : '<p class="muted">Todavía no cargaste documentos.</p>';
  }

  async function cargarServicios() {
    var lista = await api('/mis-servicios');
    document.getElementById('servicios').innerHTML = lista.length
      ? '<table><thead><tr><th>Categoría</th><th>Descripción</th><th>Tarifa</th><th>Estado</th><th></th></tr></thead><tbody>' +
        lista.map(function (s) {
          return '<tr><td>' + esc(s.categoria) + '</td><td>' + esc(s.descripcion || '—') + '</td><td>' + peso(s.tarifa) + '</td>' +
            '<td>' + badge(s.activo ? 'activo' : 'suspendido').replace('Suspendido', 'Pausado') + '</td>' +
            '<td class="fila"><button class="btn btn-claro btn-chico" data-tarifa="' + s.id_servicio + '" data-actual="' + s.tarifa + '">Cambiar tarifa</button>' +
            '<button class="btn btn-borde btn-chico" data-activo="' + s.id_servicio + '" data-valor="' + (s.activo ? '0' : '1') + '">' + (s.activo ? 'Pausar' : 'Reactivar') + '</button>' +
            (s.activo ? '<a class="btn btn-claro btn-chico" href="servicio.html?id=' + s.id_servicio + '">Ver</a>' : '') + '</td></tr>';
        }).join('') + '</tbody></table>'
      : '<p class="muted">Todavía no publicaste servicios.</p>';
  }

  async function iniciar() {
    try {
      var categorias = await api('/categorias');
      document.getElementById('categoria').innerHTML = categorias.map(function (c) {
        return '<option value="' + c.id_categoria + '">' + esc(c.nombre) + '</option>';
      }).join('');
      await cargarVerificacion();
      await cargarServicios();
    } catch (e) { mostrarAviso(aviso, 'error', e.message); }
  }

  document.getElementById('form-doc').addEventListener('submit', async function (e) {
    e.preventDefault();
    try {
      await api('/verificacion/documentos', { metodo: 'POST', cuerpo: {
        tipo_documento: document.getElementById('tipo-doc').value,
        archivo_url: document.getElementById('url-doc').value.trim(),
      } });
      document.getElementById('url-doc').value = '';
      toast('Documento cargado. Queda pendiente de revisión.');
      await cargarVerificacion();
    } catch (err) { toast(err.message, true); }
  });

  document.getElementById('form-servicio').addEventListener('submit', async function (e) {
    e.preventDefault();
    var franjas = leerDisponibilidad(document.getElementById('editor-horarios'));
    if (!franjas.length) { toast('Elegí al menos un día de atención.', true); return; }
    var btn = document.getElementById('btn-publicar');
    ocupado(btn, true);
    try {
      await api('/servicios', { metodo: 'POST', cuerpo: {
        id_categoria: Number(document.getElementById('categoria').value),
        descripcion: document.getElementById('descripcion').value.trim() || null,
        tarifa: document.getElementById('tarifa').value,
        disponibilidad: franjas,
      } });
      toast('¡Servicio publicado!');
      e.target.reset();
      montarEditorDisponibilidad(document.getElementById('editor-horarios'));
      await cargarServicios();
    } catch (err) { toast(err.message, true); }
    ocupado(btn, !verificado);
  });

  document.getElementById('servicios').addEventListener('click', async function (ev) {
    var tarifaBtn = ev.target.closest('button[data-tarifa]');
    var activoBtn = ev.target.closest('button[data-activo]');
    try {
      if (tarifaBtn) {
        var nueva = prompt('Nueva tarifa por hora ($):', tarifaBtn.dataset.actual);
        if (nueva === null) return;
        if (!(Number(nueva) > 0)) { toast('Ingresá un número mayor a 0.', true); return; }
        await api('/servicios/' + tarifaBtn.dataset.tarifa, { metodo: 'PATCH', cuerpo: { tarifa: nueva } });
        toast('Tarifa actualizada.');
        await cargarServicios();
      } else if (activoBtn) {
        await api('/servicios/' + activoBtn.dataset.activo, { metodo: 'PATCH', cuerpo: { activo: activoBtn.dataset.valor === '1' } });
        toast(activoBtn.dataset.valor === '1' ? 'Servicio reactivado.' : 'Servicio pausado: ya no aparece en las búsquedas.');
        await cargarServicios();
      }
    } catch (err) { toast(err.message, true); }
  });

  iniciar();
})();
