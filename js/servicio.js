// ===== Detalle de un servicio + formulario para solicitarlo =====
(async function () {
  var id = param('id');
  var contenido = document.getElementById('contenido');
  var aviso = document.getElementById('aviso');
  if (!id) { mostrarAviso(aviso, 'error', 'Falta indicar el servicio.'); return; }

  var servicio, reputacion;
  try {
    servicio = await api('/servicios/' + encodeURIComponent(id));
    reputacion = await api('/prestadores/' + servicio.id_prestador + '/calificaciones');
  } catch (e) {
    mostrarAviso(aviso, 'error', e.message);
    return;
  }

  document.title = servicio.nombre_publico + ' — Hogaru';
  var usuario = Sesion.usuario();
  var prom = reputacion.promedios;

  // horarios agrupados por día
  var filasHorario = servicio.disponibilidad.length
    ? servicio.disponibilidad.map(function (f) {
        return '<tr><td>' + DIAS[f.dia_semana] + '</td><td>' + esc(f.hora_inicio) + ' a ' + esc(f.hora_fin) + ' hs</td></tr>';
      }).join('')
    : '<tr><td colspan="2" class="muted">El prestador todavía no cargó horarios.</td></tr>';

  var resenas = reputacion.calificaciones.length
    ? reputacion.calificaciones.map(function (c) {
        var media = ((c.puntuacion_puntualidad + c.puntuacion_prolijidad + c.puntuacion_trato) / 3).toFixed(1);
        return '<div style="padding:10px 0;border-bottom:1px solid var(--gris-claro)">' +
          '<strong>' + esc(c.cliente) + '</strong> <span style="color:var(--ambar)">★ ' + media + '</span> ' +
          '<span class="muted">· ' + fechaCorta(c.fecha) + '</span>' +
          (c.comentario ? '<p style="margin:4px 0 0">' + esc(c.comentario) + '</p>' : '') + '</div>';
      }).join('')
    : '<p class="muted">Todavía no tiene reseñas.</p>';

  var detalleNotas = prom.total
    ? '<div class="datos" style="margin-top:12px">' +
      '<div class="dato"><div class="etiqueta">Puntualidad</div><div class="valor">' + prom.puntualidad + ' / 5</div></div>' +
      '<div class="dato"><div class="etiqueta">Prolijidad</div><div class="valor">' + prom.prolijidad + ' / 5</div></div>' +
      '<div class="dato"><div class="etiqueta">Trato</div><div class="valor">' + prom.trato + ' / 5</div></div></div>'
    : '';

  var bloqueSolicitud;
  if (!usuario) {
    bloqueSolicitud = '<div class="aviso aviso-info">Ingresá o creá una cuenta de cliente para solicitar este servicio.</div>' +
      '<a class="btn btn-ancho" href="login.html?next=' + encodeURIComponent('servicio.html?id=' + id) + '">Ingresar</a>';
  } else if (usuario.tipo_cuenta !== 'cliente') {
    bloqueSolicitud = '<div class="aviso aviso-info">Solo las cuentas de cliente pueden solicitar servicios.</div>';
  } else {
    bloqueSolicitud =
      '<div id="aviso-form" class="oculto"></div>' +
      '<form id="form-solicitud">' +
      '<div class="campo"><label for="fecha">Día y hora de inicio</label><input type="datetime-local" id="fecha" required></div>' +
      '<div class="campo"><label for="duracion">Duración (horas)</label><input type="number" id="duracion" min="0.5" max="12" step="0.5" value="2" required></div>' +
      '<div class="campo"><label for="direccion">Dirección del trabajo</label><input id="direccion" maxlength="200" placeholder="Si lo dejás vacío usamos la de tu perfil"></div>' +
      '<p><strong>Total estimado: <span id="total"></span></strong></p>' +
      '<button class="btn btn-ancho" type="submit" id="btn-solicitar">Solicitar servicio</button></form>';
  }

  contenido.innerHTML =
    '<div class="dos-col">' +
    '<div>' +
      '<div class="panel"><div class="card-top"><div class="avatar" style="width:60px;height:60px;font-size:1.2rem">' + esc(iniciales(servicio.nombre_publico)) + '</div>' +
      '<div><h1 style="margin:0">' + esc(servicio.nombre_publico) + '</h1><div class="muted">' + esc(servicio.categoria) + ' · Prestador verificado ✔</div></div></div>' +
      '<p>' + (servicio.descripcion ? esc(servicio.descripcion) : '<span class="muted">Sin descripción.</span>') + '</p>' +
      '<div class="datos"><div class="dato"><div class="etiqueta">Tarifa</div><div class="valor">' + peso(servicio.tarifa) + ' / hora</div></div>' +
      '<div class="dato"><div class="etiqueta">Calificación</div><div class="valor">' + (Number(servicio.puntuacion_promedio) > 0 ? '★ ' + Number(servicio.puntuacion_promedio).toFixed(1) : 'Sin calificar') + '</div></div>' +
      '<div class="dato"><div class="etiqueta">Servicios realizados</div><div class="valor">' + servicio.servicios_realizados + '</div></div></div>' +
      detalleNotas + '</div>' +
      '<div class="panel"><h2>Disponibilidad semanal</h2><div class="tabla-envoltorio"><table><tbody>' + filasHorario + '</tbody></table></div></div>' +
      '<div class="panel"><h2>Reseñas (' + prom.total + ')</h2>' + resenas + '</div>' +
    '</div>' +
    '<div class="panel lateral"><h2>Solicitar este servicio</h2>' + bloqueSolicitud + '</div></div>';

  var form = document.getElementById('form-solicitud');
  if (!form) return;

  // el turno no puede ser en el pasado
  var campoFecha = document.getElementById('fecha');
  var ahora = new Date(Date.now() + 3600 * 1000 - new Date().getTimezoneOffset() * 60000);
  campoFecha.min = ahora.toISOString().slice(0, 16);

  var totalEl = document.getElementById('total');
  function actualizarTotal() {
    var horas = parseFloat(document.getElementById('duracion').value) || 0;
    totalEl.textContent = peso(servicio.tarifa * horas);
  }
  document.getElementById('duracion').addEventListener('input', actualizarTotal);
  actualizarTotal();

  var avisoForm = document.getElementById('aviso-form');
  form.addEventListener('submit', async function (e) {
    e.preventDefault();
    ocultarAviso(avisoForm);
    var btn = document.getElementById('btn-solicitar');
    ocupado(btn, true);
    try {
      var s = await api('/solicitudes', { metodo: 'POST', cuerpo: {
        id_servicio: Number(id),
        fecha_hora_programada: campoFecha.value,
        duracion_horas: parseFloat(document.getElementById('duracion').value),
        direccion_trabajo: document.getElementById('direccion').value.trim() || null,
      } });
      location.href = 'solicitud.html?id=' + s.id_solicitud;
    } catch (err) {
      mostrarAviso(avisoForm, 'error', err.message);
      ocupado(btn, false);
    }
  });
})();
