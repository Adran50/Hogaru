// ===== Bolsa de Trabajos y Marketplace Inverso =====
(function () {
  var u = Sesion.usuario();
  var aviso = document.getElementById('aviso');
  var listaCont = document.getElementById('lista-anuncios');
  var vistaActual = 'bolsa'; // 'bolsa' | 'mis_anuncios'
  var categorias = [];

  // Elementos
  var btnAbrirPub = document.getElementById('btn-abrir-publicar');
  var tabBolsa = document.getElementById('tab-bolsa');
  var tabMisAnuncios = document.getElementById('tab-mis-anuncios');
  var filtroCat = document.getElementById('filtro-categoria');
  var filtroTxt = document.getElementById('filtro-texto');
  var filtrosBolsa = document.getElementById('filtros-bolsa');

  var modalPublicar = document.getElementById('modal-publicar');
  var modalPostular = document.getElementById('modal-postular');
  var modalPostulaciones = document.getElementById('modal-postulaciones');

  // Configuración según rol
  if (u && u.tipo_cuenta === 'cliente') {
    btnAbrirPub.classList.remove('oculto');
    tabMisAnuncios.classList.remove('oculto');
  }

  async function cargarCategorias() {
    try {
      categorias = await api('/categorias');
      var opts = categorias.map(function (c) {
        return '<option value="' + c.id_categoria + '">' + esc(c.icono || '🧹') + ' ' + esc(c.nombre) + '</option>';
      }).join('');
      filtroCat.innerHTML = '<option value="">Todas las categorías</option>' + opts;
      document.getElementById('pub-categoria').innerHTML = opts;
    } catch (e) { /* silencioso */ }
  }

  async function cargarBolsa() {
    listaCont.innerHTML = '<p class="muted">Cargando avisos disponibles…</p>';
    var params = {};
    if (filtroCat.value) params.categoria = filtroCat.value;
    if (filtroTxt.value.trim()) params.q = filtroTxt.value.trim();

    try {
      var avisos = await api('/anuncios', { params: params });
      if (!avisos.length) {
        listaCont.innerHTML = '<div class="panel text-center"><p class="muted">No hay avisos de trabajo abiertos en este momento.</p>' +
          (u && u.tipo_cuenta === 'cliente' ? '<button class="btn btn-claro" style="margin-top:10px" onclick="document.getElementById(\'btn-abrir-publicar\').click()">+ Publicar el primero</button>' : '') +
          '</div>';
        return;
      }

      listaCont.innerHTML = avisos.map(function (a) {
        var esMio = u && u.id_usuario === a.id_cliente;
        var esPrestador = u && u.tipo_cuenta === 'prestador';
        var accionHtml = '';

        if (esMio) {
          accionHtml = '<span class="badge badge-activo">Publicado por vos</span>';
        } else if (esPrestador) {
          accionHtml = '<button class="btn btn-chico btn-postular" data-id="' + a.id_anuncio + '" data-titulo="' + esc(a.titulo) + '" data-precio="' + a.presupuesto + '">Postularme</button>';
        } else if (!u) {
          accionHtml = '<a class="btn btn-claro btn-chico" href="login.html?next=anuncios.html">Ingresá para postularte</a>';
        }

        return '<div class="anuncio-card">' +
          '<div class="anuncio-header">' +
            '<div>' +
              '<span class="badge">' + esc(a.icono || '🧹') + ' ' + esc(a.categoria) + '</span>' +
              '<h3 style="margin:6px 0 2px 0">' + esc(a.titulo) + '</h3>' +
              '<div class="anuncio-meta">' +
                '<span style="display:inline-flex; align-items:center; gap:6px;">' +
                  renderAvatar(a.cliente_foto, a.cliente_nombre, 22) +
                  ' ' + esc(a.cliente_nombre) +
                '</span>' +
                '<span>📍 ' + esc(a.direccion) + '</span>' +
                '<span>📅 ' + fechaHora(a.fecha_servicio) + ' (' + a.duracion_horas + ' hs)</span>' +
                '<span>📩 ' + a.total_postulaciones + ' oferta' + (a.total_postulaciones === 1 ? '' : 's') + '</span>' +
              '</div>' +
            '</div>' +
            '<div style="text-align:right">' +
              '<div class="anuncio-precio">' + peso(a.presupuesto) + '</div>' +
              '<div style="margin-top:8px">' + accionHtml + '</div>' +
            '</div>' +
          '</div>' +
          '<p style="margin:4px 0; color:var(--texto); line-height:1.4">' + esc(a.descripcion) + '</p>' +
        '</div>';
      }).join('');
    } catch (err) {
      listaCont.innerHTML = '<div class="aviso aviso-error">' + esc(err.message) + '</div>';
    }
  }

  async function cargarMisAnuncios() {
    listaCont.innerHTML = '<p class="muted">Cargando tus avisos…</p>';
    try {
      var misAvisos = await api('/anuncios/mis-anuncios');
      if (!misAvisos.length) {
        listaCont.innerHTML = '<div class="panel text-center">' +
          '<p class="muted">Todavía no publicaste ningún aviso de trabajo.</p>' +
          '<button class="btn" style="margin-top:10px" onclick="document.getElementById(\'btn-abrir-publicar\').click()">+ Publicar mi primer aviso</button>' +
        '</div>';
        return;
      }

      listaCont.innerHTML = misAvisos.map(function (a) {
        var estadoBadge = badge(a.estado === 'abierto' ? 'activo' : (a.estado === 'adjudicado' ? 'aprobado' : 'cancelada'));
        var botones = '';

        if (a.estado === 'abierto') {
          botones =
            '<button class="btn btn-chico btn-ver-ofertas" data-id="' + a.id_anuncio + '" data-titulo="' + esc(a.titulo) + '">Ver ofertas (' + a.total_postulaciones + ')</button> ' +
            '<button class="btn btn-borde btn-chico btn-cancelar-anuncio" data-id="' + a.id_anuncio + '">Cancelar aviso</button>';
        } else if (a.estado === 'adjudicado') {
          botones = '<span class="badge badge-aprobado">✓ Adjudicado</span>';
        } else {
          botones = '<span class="badge badge-cancelada">Cancelado</span>';
        }

        return '<div class="anuncio-card">' +
          '<div class="anuncio-header">' +
            '<div>' +
              '<div class="fila" style="gap:8px">' +
                '<span class="badge">' + esc(a.icono || '🧹') + ' ' + esc(a.categoria) + '</span>' +
                estadoBadge.replace('Activo', 'Abierto').replace('Aprobado', 'Adjudicado') +
              '</div>' +
              '<h3 style="margin:6px 0 2px 0">' + esc(a.titulo) + '</h3>' +
              '<div class="anuncio-meta">' +
                '<span>📍 ' + esc(a.direccion) + '</span>' +
                '<span>📅 ' + fechaHora(a.fecha_servicio) + ' (' + a.duracion_horas + ' hs)</span>' +
                '<span>📩 ' + a.total_postulaciones + ' ofertas recibidas</span>' +
              '</div>' +
            '</div>' +
            '<div style="text-align:right">' +
              '<div class="anuncio-precio">' + peso(a.presupuesto) + '</div>' +
              '<div style="margin-top:8px" class="fila">' + botones + '</div>' +
            '</div>' +
          '</div>' +
          '<p style="margin:4px 0; color:var(--texto); line-height:1.4">' + esc(a.descripcion) + '</p>' +
        '</div>';
      }).join('');
    } catch (err) {
      listaCont.innerHTML = '<div class="aviso aviso-error">' + esc(err.message) + '</div>';
    }
  }

  // Pestañas
  tabBolsa.addEventListener('click', function () {
    vistaActual = 'bolsa';
    tabBolsa.classList.add('activo');
    tabMisAnuncios.classList.remove('activo');
    filtrosBolsa.classList.remove('oculto');
    cargarBolsa();
  });

  tabMisAnuncios.addEventListener('click', function () {
    vistaActual = 'mis_anuncios';
    tabMisAnuncios.classList.add('activo');
    tabBolsa.classList.remove('activo');
    filtrosBolsa.classList.add('oculto');
    cargarMisAnuncios();
  });

  filtroCat.addEventListener('change', cargarBolsa);
  var debounceTimer;
  filtroTxt.addEventListener('input', function () {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(cargarBolsa, 300);
  });

  // Modal Publicar
  btnAbrirPub.addEventListener('click', function () {
    document.getElementById('form-publicar-anuncio').reset();
    var manana = new Date();
    manana.setDate(manana.getDate() + 1);
    manana.setHours(10, 0, 0, 0);
    document.getElementById('pub-fecha').value = manana.toISOString().slice(0, 16);
    modalPublicar.classList.remove('oculto');
  });
  document.getElementById('btn-cerrar-publicar').addEventListener('click', function () {
    modalPublicar.classList.add('oculto');
  });

  document.getElementById('form-publicar-anuncio').addEventListener('submit', async function (e) {
    e.preventDefault();
    var btn = document.getElementById('btn-confirmar-publicar');
    ocupado(btn, true);
    try {
      var cuerpo = {
        titulo: document.getElementById('pub-titulo').value.trim(),
        id_categoria: Number(document.getElementById('pub-categoria').value),
        presupuesto: Number(document.getElementById('pub-presupuesto').value),
        fecha_servicio: new Date(document.getElementById('pub-fecha').value).toISOString(),
        duracion_horas: Number(document.getElementById('pub-duracion').value),
        direccion: document.getElementById('pub-direccion').value.trim(),
        descripcion: document.getElementById('pub-descripcion').value.trim(),
      };
      await api('/anuncios', { metodo: 'POST', cuerpo: cuerpo });
      toast('¡Aviso publicado con éxito en la Bolsa de Trabajos!');
      modalPublicar.classList.add('oculto');
      tabMisAnuncios.click();
    } catch (err) {
      toast(err.message, true);
    } finally {
      ocupado(btn, false);
    }
  });

  // Eventos de delegación en la lista
  listaCont.addEventListener('click', async function (e) {
    var btnPost = e.target.closest('.btn-postular');
    if (btnPost) {
      document.getElementById('postular-id-anuncio').value = btnPost.dataset.id;
      document.getElementById('postular-anuncio-titulo').textContent = 'Aviso: ' + btnPost.dataset.titulo;
      document.getElementById('postular-precio').value = btnPost.dataset.precio || '';
      document.getElementById('postular-mensaje').value = '';
      modalPostular.classList.remove('oculto');
      return;
    }

    var btnVer = e.target.closest('.btn-ver-ofertas');
    if (btnVer) {
      abrirOfertas(btnVer.dataset.id, btnVer.dataset.titulo);
      return;
    }

    var btnCancel = e.target.closest('.btn-cancelar-anuncio');
    if (btnCancel) {
      if (!confirm('¿Estás seguro de que querés cancelar este aviso de trabajo?')) return;
      try {
        await api('/anuncios/' + btnCancel.dataset.id, { metodo: 'DELETE' });
        toast('Aviso cancelado');
        cargarMisAnuncios();
      } catch (err) { toast(err.message, true); }
    }
  });

  // Modal Postular
  document.getElementById('btn-cerrar-postular').addEventListener('click', function () {
    modalPostular.classList.add('oculto');
  });

  document.getElementById('form-postular').addEventListener('submit', async function (e) {
    e.preventDefault();
    var id = document.getElementById('postular-id-anuncio').value;
    var btn = document.getElementById('btn-confirmar-postular');
    ocupado(btn, true);
    try {
      var cuerpo = {
        propuesta_precio: Number(document.getElementById('postular-precio').value),
        mensaje: document.getElementById('postular-mensaje').value.trim() || null,
      };
      await api('/anuncios/' + id + '/postular', { metodo: 'POST', cuerpo: cuerpo });
      toast('¡Cotización enviada al cliente!');
      modalPostular.classList.add('oculto');
      cargarBolsa();
    } catch (err) {
      toast(err.message, true);
    } finally {
      ocupado(btn, false);
    }
  });

  // Modal Ver Ofertas y Adjudicar
  async function abrirOfertas(idAnuncio, titulo) {
    document.getElementById('modal-postulaciones-subtitulo').textContent = 'Aviso: ' + titulo;
    var contOfertas = document.getElementById('lista-postulaciones-recibidas');
    contOfertas.innerHTML = '<p class="muted">Cargando ofertas recibidas…</p>';
    modalPostulaciones.classList.remove('oculto');

    try {
      var ofertas = await api('/anuncios/' + idAnuncio + '/postulaciones');
      if (!ofertas.length) {
        contOfertas.innerHTML = '<p class="muted">Todavía no recibiste ofertas para este aviso.</p>';
        return;
      }

      contOfertas.innerHTML = ofertas.map(function (o) {
        var estrellas = '⭐ ' + Number(o.puntuacion_promedio).toFixed(1);
        var esGanadora = o.estado === 'aceptada';
        var botonAdjudicar = esGanadora
          ? '<span class="badge badge-aprobado">Aceptada</span>'
          : '<button class="btn btn-chico btn-adjudicar" data-anuncio="' + idAnuncio + '" data-postulacion="' + o.id_postulacion + '">Aceptar y contratar</button>';

        return '<div class="postulacion-item" style="display:flex; justify-content:space-between; align-items:center; gap:12px">' +
          '<div style="display:flex; align-items:center; gap:12px">' +
            renderAvatar(o.foto_perfil, o.nombre + ' ' + o.apellido, 40) +
            '<div>' +
              '<strong>' + esc(o.nombre) + ' ' + esc(o.apellido) + '</strong> ' +
              '<span style="font-size:0.85rem; color:var(--texto-secundario)">(' + estrellas + ')</span>' +
              '<div style="font-size:0.9rem; margin-top:4px">' + esc(o.mensaje || 'Sin mensaje adicional.') + '</div>' +
              '<div style="font-size:0.8rem; color:var(--texto-secundario); margin-top:4px">Enviada: ' + fechaCorta(o.fecha_postulacion) + '</div>' +
            '</div>' +
          '</div>' +
          '<div style="text-align:right">' +
            '<div style="font-weight:700; font-size:1.15rem; color:var(--verde-700,#1b4332); margin-bottom:6px">' + peso(o.propuesta_precio) + '</div>' +
            botonAdjudicar +
          '</div>' +
        '</div>';
      }).join('');
    } catch (err) {
      contOfertas.innerHTML = '<div class="aviso aviso-error">' + esc(err.message) + '</div>';
    }
  }

  document.getElementById('btn-cerrar-ver-postulaciones').addEventListener('click', function () {
    modalPostulaciones.classList.add('oculto');
  });

  document.getElementById('lista-postulaciones-recibidas').addEventListener('click', async function (e) {
    var btn = e.target.closest('.btn-adjudicar');
    if (!btn) return;
    if (!confirm('¿Querés aceptar esta oferta y agendar el trabajo? Se creará la contratación formal.')) return;

    ocupado(btn, true);
    try {
      var r = await api('/anuncios/' + btn.dataset.anuncio + '/adjudicar/' + btn.dataset.postulacion, { metodo: 'POST' });
      toast('¡Trabajo adjudicado con éxito!');
      modalPostulaciones.classList.add('oculto');
      cargarMisAnuncios();
      // Redirigir a la contratación
      setTimeout(function () {
        location.href = 'solicitud.html?id=' + r.id_solicitud;
      }, 1000);
    } catch (err) {
      toast(err.message, true);
      ocupado(btn, false);
    }
  });

  // Inicio
  cargarCategorias().then(cargarBolsa);
})();
