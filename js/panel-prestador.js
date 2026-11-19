// ===== Panel del prestador: verificación, carga de archivos y servicios =====
(function () {
  if (!requerirSesion(['prestador'])) return;
  var aviso = document.getElementById('aviso');
  var verificado = false;
  var TIPOS_DOC = {
    dni: 'DNI (Completo)',
    dni_frente: 'DNI Frente',
    dni_dorso: 'DNI Dorso',
    antecedentes_penales: 'Antecedentes penales',
    otro: 'Otro comprobante',
  };
  var TEXTOS_VERIF = {
    pendiente: 'Cargá tu DNI y tu certificado de antecedentes. Un administrador los revisará.',
    aprobado: 'Tu cuenta está verificada: ya podés publicar servicios y postularte a la bolsa de trabajos.',
    rechazado: 'Alguno de tus documentos fue rechazado. Volvé a cargarlo para que lo revisemos de nuevo.',
  };

  var modalSugerir = document.getElementById('modal-sugerir');
  var btnAbrirSugerir = document.getElementById('btn-abrir-sugerir');
  var btnCerrarSugerir = document.getElementById('btn-cerrar-sugerir');

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
    
    // Actualizar badges específicos de DNI (Frente / Dorso o Unificado) y Antecedentes
    var ultimoDni = docs.find(function (d) { return d.tipo_documento === 'dni'; });
    var ultimoFrente = docs.find(function (d) { return d.tipo_documento === 'dni_frente'; });
    var ultimoDorso = docs.find(function (d) { return d.tipo_documento === 'dni_dorso'; });
    var ultimoAnt = docs.find(function (d) { return d.tipo_documento === 'antecedentes_penales'; });

    var badgeFrente = document.getElementById('badge-doc-dni-frente');
    if (badgeFrente) {
      if (ultimoFrente) {
        badgeFrente.innerHTML = badge(ultimoFrente.estado);
      } else if (ultimoDni) {
        badgeFrente.innerHTML = '<span class="badge" title="Presentado en DNI unificado">' + (ultimoDni.estado === 'aprobado' ? 'Aprobado (DNI)' : badge(ultimoDni.estado)) + '</span>';
      } else {
        badgeFrente.innerHTML = '<span class="badge">No presentado</span>';
      }
    }

    var badgeDorso = document.getElementById('badge-doc-dni-dorso');
    if (badgeDorso) {
      if (ultimoDorso) {
        badgeDorso.innerHTML = badge(ultimoDorso.estado);
      } else if (ultimoDni) {
        badgeDorso.innerHTML = '<span class="badge" title="Presentado en DNI unificado">' + (ultimoDni.estado === 'aprobado' ? 'Aprobado (DNI)' : badge(ultimoDni.estado)) + '</span>';
      } else {
        badgeDorso.innerHTML = '<span class="badge">No presentado</span>';
      }
    }

    var badgeAnt = document.getElementById('badge-doc-ant');
    if (badgeAnt) {
      badgeAnt.innerHTML = ultimoAnt ? badge(ultimoAnt.estado) : '<span class="badge">No presentado</span>';
    }

    // Tabla de historial de documentos presentados
    document.getElementById('docs').innerHTML = docs.length
      ? '<div class="tabla-envoltorio"><table><thead><tr><th>Documento</th><th>Archivo</th><th>Cargado</th><th>Estado</th></tr></thead><tbody>' +
        docs.map(function (d) {
          return '<tr><td>' + esc(TIPOS_DOC[d.tipo_documento] || d.tipo_documento) + '</td><td>' + enlaceSeguro(d.archivo_url) + '</td><td>' + fechaCorta(d.fecha_carga) + '</td><td>' + badge(d.estado) + '</td></tr>';
        }).join('') + '</tbody></table></div>'
      : '<p class="muted">Todavía no cargaste ningún documento.</p>';
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

  async function cargarCategoriasSelect() {
    var categorias = await api('/categorias');
    document.getElementById('categoria').innerHTML = categorias.map(function (c) {
      return '<option value="' + c.id_categoria + '">' + esc(c.icono || '🧹') + ' ' + esc(c.nombre) + '</option>';
    }).join('');
  }

  async function subirArchivoDoc(tipoDoc, fileInput, btnSubmit) {
    if (!fileInput || !fileInput.files || !fileInput.files[0]) {
      toast('Elegí un archivo para subir.', true);
      return;
    }

    var token = Sesion.token();
    if (!token) {
      toast('No hay sesión activa. Por favor volvé a ingresar.', true);
      return;
    }

    var formData = new FormData();
    formData.append('tipo_documento', tipoDoc);
    formData.append('archivo', fileInput.files[0]);

    ocupado(btnSubmit, true);
    try {
      var res = await fetch(API_URL + '/verificacion/subir', {
        method: 'POST',
        headers: { 'Authorization': 'Bearer ' + token },
        body: formData,
      });
      var data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Error al subir el archivo');
      toast('¡' + (TIPOS_DOC[tipoDoc] || 'Documento') + ' subido con éxito! Queda pendiente de revisión.');
      fileInput.value = '';
      await cargarVerificacion();
    } catch (err) {
      toast(err.message, true);
    } finally {
      ocupado(btnSubmit, false);
    }
  }

  // 1a. Subir DNI Frente
  var formDniFrente = document.getElementById('form-doc-dni-frente');
  if (formDniFrente) {
    formDniFrente.addEventListener('submit', function (e) {
      e.preventDefault();
      subirArchivoDoc('dni_frente', document.getElementById('archivo-dni-frente'), document.getElementById('btn-subir-dni-frente'));
    });
  }

  // 1b. Subir DNI Dorso
  var formDniDorso = document.getElementById('form-doc-dni-dorso');
  if (formDniDorso) {
    formDniDorso.addEventListener('submit', function (e) {
      e.preventDefault();
      subirArchivoDoc('dni_dorso', document.getElementById('archivo-dni-dorso'), document.getElementById('btn-subir-dni-dorso'));
    });
  }

  // 1c. Subir DNI unificado
  var formDniUnificado = document.getElementById('form-doc-dni-unificado');
  if (formDniUnificado) {
    formDniUnificado.addEventListener('submit', function (e) {
      e.preventDefault();
      subirArchivoDoc('dni', document.getElementById('archivo-dni-unificado'), document.getElementById('btn-subir-dni-unificado'));
    });
  }

  // 2. Subir Antecedentes
  var formAnt = document.getElementById('form-doc-ant');
  if (formAnt) {
    formAnt.addEventListener('submit', function (e) {
      e.preventDefault();
      subirArchivoDoc('antecedentes_penales', document.getElementById('archivo-ant'), document.getElementById('btn-subir-ant'));
    });
  }

  // 3. Subir manual / otro
  var formManual = document.getElementById('form-doc-manual');
  if (formManual) {
    formManual.addEventListener('submit', async function (e) {
      e.preventDefault();
      var tipo = document.getElementById('tipo-doc-manual').value;
      var url = document.getElementById('url-doc-manual').value.trim();
      var btn = formManual.querySelector('button[type="submit"]');
      ocupado(btn, true);
      try {
        await api('/verificacion/documentos', {
          metodo: 'POST',
          cuerpo: { tipo_documento: tipo, archivo_url: url },
        });
        toast('Comprobante cargado.');
        document.getElementById('url-doc-manual').value = '';
        await cargarVerificacion();
      } catch (err) {
        toast(err.message, true);
      } finally {
        ocupado(btn, false);
      }
    });
  }

  // Publicar servicio
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

  // Modal para sugerir categoría
  if (btnAbrirSugerir) {
    btnAbrirSugerir.addEventListener('click', function () {
      document.getElementById('form-sugerir-cat').reset();
      modalSugerir.classList.remove('oculto');
    });
  }
  if (btnCerrarSugerir) {
    btnCerrarSugerir.addEventListener('click', function () {
      modalSugerir.classList.add('oculto');
    });
  }

  document.getElementById('form-sugerir-cat').addEventListener('submit', async function (e) {
    e.preventDefault();
    try {
      var r = await api('/categorias/sugerir', {
        metodo: 'POST',
        cuerpo: {
          nombre: document.getElementById('sugerir-nombre').value.trim(),
          icono: document.getElementById('sugerir-icono').value.trim() || '✨',
          descripcion: document.getElementById('sugerir-desc').value.trim() || null,
        },
      });
      toast(r.mensaje || '¡Categoría propuesta enviada al administrador!');
      modalSugerir.classList.add('oculto');
    } catch (err) {
      toast(err.message, true);
    }
  });

  // Modificar tarifas o pausar servicios
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

  async function iniciar() {
    try {
      await cargarCategoriasSelect();
      await cargarVerificacion();
      await cargarServicios();
    } catch (e) { mostrarAviso(aviso, 'error', e.message); }
  }

  iniciar();
})();
