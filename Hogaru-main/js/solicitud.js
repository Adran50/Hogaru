// ===== Detalle de una solicitud: estado, acciones, pago, calificación, disputas y chat =====
(function () {
  if (!requerirSesion()) return;

  var usuario = Sesion.usuario();
  var id = param('id');
  var raiz = document.getElementById('contenido');
  var aviso = document.getElementById('aviso');
  if (!id) { mostrarAviso(aviso, 'error', 'Falta indicar la solicitud.'); raiz.innerHTML = ''; return; }

  var sol, pago, disputas;
  var esCliente, esPrestador, esAdmin;
  var mensajesMostrados = -1;
  var HITOS = [['pendiente', 'Pendiente'], ['aceptada', 'Aceptada'], ['en_curso', 'En curso'], ['finalizada', 'Finalizada']];
  var ICONO_NOTIF_ACCION = { aceptar: 'Solicitud aceptada', iniciar: 'Servicio iniciado', finalizar: 'Servicio finalizado', cancelar: 'Solicitud cancelada' };

  // ---------- carga ----------
  async function cargar() {
    ocultarAviso(aviso);
    try {
      sol = await api('/solicitudes/' + encodeURIComponent(id));
      pago = null;
      try { pago = await api('/solicitudes/' + id + '/pago'); }
      catch (e) { if (e.status !== 404) throw e; }
      disputas = await api('/solicitudes/' + id + '/disputas');
    } catch (e) {
      raiz.innerHTML = '';
      mostrarAviso(aviso, 'error', e.message);
      return;
    }
    esCliente = usuario.id_usuario === sol.id_cliente;
    esPrestador = usuario.id_usuario === sol.id_prestador;
    esAdmin = usuario.tipo_cuenta === 'administrador';
    render();
    if (esCliente || esPrestador) cargarChat();
  }

  // ---------- render ----------
  function render() {
    document.title = 'Solicitud #' + sol.id_solicitud + ' — Hogaru';
    raiz.innerHTML = [panelEncabezado(), panelAcciones(), panelPago(), panelCalificacion(), panelDisputas(), panelChat()].join('');
    mensajesMostrados = -1;
    iniciarEventosPago();
  }

  function panelEncabezado() {
    var linea;
    if (sol.estado === 'cancelada') {
      linea = '<div class="aviso aviso-error">Esta solicitud fue cancelada.</div>';
    } else {
      var actual = HITOS.findIndex(function (h) { return h[0] === sol.estado; });
      linea = '<div class="linea-tiempo">' + HITOS.map(function (h, i) {
        return '<div class="hito' + (i <= actual ? ' hecho' : '') + '">' + h[1] + '</div>';
      }).join('') + '</div>';
    }
    return '<div class="panel"><div class="fila-entre"><h1>' + esc(sol.servicio) + ' <span class="muted" style="font-size:1rem">#' + sol.id_solicitud + '</span></h1>' + badge(sol.estado) + '</div>' +
      linea +
      '<div class="datos" style="margin-top:14px">' +
      dato('Cliente', esc(sol.cliente)) + dato('Prestador', esc(sol.prestador)) +
      dato('Fecha y hora', fechaHora(sol.fecha_hora_programada)) + dato('Duración', sol.duracion_horas + ' hs') +
      dato('Dirección', esc(sol.direccion_trabajo)) + dato('Tarifa', peso(sol.tarifa) + ' / hora') +
      dato('Total', '<strong>' + peso(sol.monto_estimado) + '</strong>') + '</div></div>';
  }
  function dato(etiqueta, valor) {
    return '<div class="dato"><div class="etiqueta">' + etiqueta + '</div><div class="valor">' + valor + '</div></div>';
  }

  function panelAcciones() {
    var botones = [];
    if (esPrestador) {
      if (sol.estado === 'pendiente') botones.push('<button class="btn" data-accion="aceptar">Aceptar solicitud</button>');
      if (sol.estado === 'aceptada') botones.push('<button class="btn" data-accion="iniciar">Iniciar servicio</button>');
      if (sol.estado === 'en_curso') botones.push('<button class="btn" data-accion="finalizar">Marcar como finalizado</button>');
    }
    if ((esCliente || esPrestador) && (sol.estado === 'pendiente' || sol.estado === 'aceptada')) {
      botones.push('<button class="btn btn-peligro" data-accion="cancelar">Cancelar solicitud</button>');
    }
    if (!botones.length) return '';
    var ayuda = esPrestador && sol.estado === 'pendiente'
      ? '<p class="muted">Al aceptar, el turno queda agendado en tu calendario.</p>' : '';
    return '<div class="panel"><h2>Acciones</h2><div class="fila">' + botones.join('') + '</div>' + ayuda + '</div>';
  }

  function panelPago() {
    if (esAdmin && !pago) return '';
    var cuerpo;
    if (pago) {
      var verComision = esPrestador || esAdmin;
      cuerpo = '<div class="datos">' + dato('Monto', peso(pago.monto)) + dato('Método', esc(pago.metodo_pago.replace('_', ' '))) + dato('Estado', badge(pago.estado)) +
        (verComision ? dato('Comisión de la plataforma', peso(pago.comision_plataforma)) + dato('Neto para el prestador', peso(pago.monto - pago.comision_plataforma)) : '') + '</div>' +
        (pago.estado === 'completado' ? '<div style="margin-top:18px"><button type="button" class="btn btn-claro" id="btn-comprobante">🧾 Ver / Imprimir Comprobante Oficial</button></div>' : '');
    } else if (esCliente && ['aceptada', 'en_curso', 'finalizada'].indexOf(sol.estado) !== -1) {
      cuerpo = '<form id="form-pago">' +
        '<div class="campo"><label for="metodo">Método de pago</label>' +
        '<select id="metodo">' +
          '<option value="tarjeta" selected>💳 Tarjeta de Crédito / Débito</option>' +
          '<option value="mercado_pago">📱 Mercado Pago</option>' +
          '<option value="transferencia">🏦 Transferencia Bancaria</option>' +
          '<option value="efectivo">💵 Efectivo al finalizar</option>' +
        '</select></div>' +

        '<!-- Simulador de Tarjeta Interactiva -->' +
        '<div id="contenedor-tarjeta-ui">' +
          '<div class="tarjeta-simulador">' +
            '<div class="tc-plastico" id="tc-plastico">' +
              '<div class="tc-fila-top">' +
                '<div class="tc-chip"></div>' +
                '<div class="tc-contactless">)))</div>' +
                '<div class="tc-marca" id="tc-marca-logo">VISA</div>' +
              '</div>' +
              '<div class="tc-numero" id="tc-numero-display">•••• •••• •••• ••••</div>' +
              '<div class="tc-fila-bottom">' +
                '<div><div class="tc-label">TITULAR</div><div class="tc-valor" id="tc-nombre-display">' + esc((usuario.nombre || 'CLIENTE').toUpperCase()) + '</div></div>' +
                '<div><div class="tc-label">VENCE</div><div class="tc-valor" id="tc-vence-display">MM/AA</div></div>' +
              '</div>' +
            '</div>' +
          '</div>' +
          '<div class="campo" style="margin-top:16px">' +
            '<label for="tc-numero">Número de tarjeta</label>' +
            '<input type="text" id="tc-numero" placeholder="4540 1234 5678 9012" maxlength="19" autocomplete="cc-number">' +
          '</div>' +
          '<div class="grilla-2">' +
            '<div class="campo">' +
              '<label for="tc-nombre">Nombre del titular</label>' +
              '<input type="text" id="tc-nombre" value="' + esc(usuario.nombre || '') + '" placeholder="Como figura en la tarjeta" autocomplete="cc-name">' +
            '</div>' +
            '<div class="grilla-2">' +
              '<div class="campo">' +
                '<label for="tc-vence">Vencimiento</label>' +
                '<input type="text" id="tc-vence" placeholder="MM/AA" maxlength="5" autocomplete="cc-exp">' +
              '</div>' +
              '<div class="campo">' +
                '<label for="tc-cvv">CVV</label>' +
                '<input type="password" id="tc-cvv" placeholder="123" maxlength="4" autocomplete="cc-csc">' +
              '</div>' +
            '</div>' +
          '</div>' +
        '</div>' +

        '<div id="contenedor-otro-metodo" class="oculto">' +
          '<div class="aviso aviso-info" id="texto-otro-metodo"></div>' +
        '</div>' +

        '<div class="campo-check" style="margin-top:14px">' +
          '<input type="checkbox" id="simular-fallo">' +
          '<label for="simular-fallo">Simular pago rechazado (modo demo para evaluación)</label>' +
        '</div>' +
        '<button class="btn btn-ancho" type="submit" id="btn-submit-pago" style="margin-top:8px">🔒 Pagar ' + peso(sol.monto_estimado) + ' de forma segura</button>' +
      '</form>';
    } else if (esCliente && sol.estado === 'pendiente') {
      cuerpo = '<p class="muted">Vas a poder pagar cuando el prestador acepte la solicitud.</p>';
    } else if (sol.estado === 'cancelada') {
      return '';
    } else {
      cuerpo = '<p class="muted">El cliente todavía no realizó el pago.</p>';
    }
    return '<div class="panel"><h2>Pago</h2>' + cuerpo + '</div>';
  }

  function iniciarEventosPago() {
    var selMetodo = document.getElementById('metodo');
    var contTarjeta = document.getElementById('contenedor-tarjeta-ui');
    var contOtro = document.getElementById('contenedor-otro-metodo');
    var textoOtro = document.getElementById('texto-otro-metodo');

    if (selMetodo && contTarjeta && contOtro) {
      selMetodo.addEventListener('change', function () {
        var val = selMetodo.value;
        if (val === 'tarjeta') {
          contTarjeta.classList.remove('oculto');
          contOtro.classList.add('oculto');
        } else {
          contTarjeta.classList.add('oculto');
          contOtro.classList.remove('oculto');
          if (val === 'mercado_pago') {
            textoOtro.innerHTML = '<strong>Mercado Pago Checkout Pro:</strong> Se procesará de forma segura con tu cuenta o dinero en cuenta.';
          } else if (val === 'transferencia') {
            textoOtro.innerHTML = '<strong>Transferencia inmediata:</strong> Alias: <code>HOGARU.OFICIAL.MP</code> · CBU: <code>0000003100012345678901</code>. Se valida automáticamente.';
          } else if (val === 'efectivo') {
            textoOtro.innerHTML = '<strong>Efectivo al finalizar:</strong> Abonás directamente al prestador cuando el servicio termine satisfactoriamente.';
          }
        }
      });
    }

    // Sincronización en tiempo real del simulador de tarjeta
    var inputNum = document.getElementById('tc-numero');
    var displayNum = document.getElementById('tc-numero-display');
    var logoMarca = document.getElementById('tc-marca-logo');
    var inputNom = document.getElementById('tc-nombre');
    var displayNom = document.getElementById('tc-nombre-display');
    var inputVence = document.getElementById('tc-vence');
    var displayVence = document.getElementById('tc-vence-display');

    if (inputNum && displayNum) {
      inputNum.addEventListener('input', function () {
        var raw = inputNum.value.replace(/\D/g, '').slice(0, 16);
        var formatted = raw.replace(/(\d{4})(?=\d)/g, '$1 ');
        inputNum.value = formatted;
        displayNum.textContent = formatted || '•••• •••• •••• ••••';

        // Detección de marca
        if (/^4/.test(raw)) logoMarca.textContent = 'VISA';
        else if (/^(5[1-5]|2[2-7])/.test(raw)) logoMarca.textContent = 'MASTERCARD';
        else if (/^3[47]/.test(raw)) logoMarca.textContent = 'AMEX';
        else if (/^(5896|6042)/.test(raw)) logoMarca.textContent = 'CABAL';
        else logoMarca.textContent = 'TARJETA';
      });
    }

    if (inputNom && displayNom) {
      inputNom.addEventListener('input', function () {
        displayNom.textContent = inputNom.value.trim().toUpperCase() || (usuario.nombre || 'CLIENTE').toUpperCase();
      });
    }

    if (inputVence && displayVence) {
      inputVence.addEventListener('input', function () {
        var raw = inputVence.value.replace(/\D/g, '').slice(0, 4);
        if (raw.length >= 2) raw = raw.slice(0, 2) + '/' + raw.slice(2);
        inputVence.value = raw;
        displayVence.textContent = raw || 'MM/AA';
      });
    }
  }

  function abrirModalComprobante() {
    var modalExistente = document.getElementById('modal-comprobante');
    if (modalExistente) modalExistente.remove();

    var fechaEmision = pago && pago.fecha_pago ? fechaHora(pago.fecha_pago) : fechaHora(new Date().toISOString());
    var numRecibo = 'HOG-2026-' + sol.id_solicitud + '-' + (pago ? pago.id_pago : '1');

    var overlay = document.createElement('div');
    overlay.id = 'modal-comprobante';
    overlay.className = 'comprobante-overlay';
    overlay.innerHTML =
      '<div class="comprobante-papel">' +
        '<div class="comprobante-acciones no-print">' +
          '<button class="btn btn-chico" id="btn-imprimir">🖨️ Imprimir / Guardar PDF</button>' +
          '<button class="btn btn-claro btn-chico" id="btn-cerrar-comprobante">Cerrar</button>' +
        '</div>' +

        '<div class="comprobante-header">' +
          '<div class="comprobante-marca">' +
            '<img src="' + RAIZ + 'assets/logo.png" alt="Hogaru Logo" class="comprobante-logo">' +
            '<div>' +
              '<h2 style="margin:0;font-size:1.4rem;color:var(--verde-oscuro)">Hogaru</h2>' +
              '<p class="muted" style="margin:0;font-size:0.82rem">Servicios de Limpieza de Confianza</p>' +
            '</div>' +
          '</div>' +
          '<div style="text-align:right">' +
            '<span class="comprobante-sello">TRANSACCIÓN CONFIRMADA</span>' +
            '<div class="muted" style="font-size:0.82rem;margin-top:6px">Comprobante Oficial Nº ' + numRecibo + '</div>' +
            '<div class="muted" style="font-size:0.82rem">' + fechaEmision + '</div>' +
          '</div>' +
        '</div>' +

        '<hr style="border:none;border-top:1.5px solid var(--gris-claro);margin:20px 0">' +

        '<div class="comprobante-datos-grid">' +
          '<div>' +
            '<div class="etiqueta" style="font-size:0.75rem;font-weight:700;color:var(--gris);text-transform:uppercase">CLIENTE</div>' +
            '<div class="valor" style="font-weight:700;font-size:1.05rem">' + esc(sol.cliente) + '</div>' +
            '<div class="muted" style="font-size:0.86rem;margin-top:2px">Lugar: ' + esc(sol.direccion_trabajo) + '</div>' +
          '</div>' +
          '<div>' +
            '<div class="etiqueta" style="font-size:0.75rem;font-weight:700;color:var(--gris);text-transform:uppercase">PRESTADOR VERIFICADO</div>' +
            '<div class="valor" style="font-weight:700;font-size:1.05rem">' + esc(sol.prestador) + '</div>' +
            '<div class="muted" style="font-size:0.86rem;margin-top:2px">🛡️ DNI y Antecedentes Penales Verificados</div>' +
          '</div>' +
        '</div>' +

        '<table class="comprobante-tabla">' +
          '<thead>' +
            '<tr>' +
              '<th>Concepto / Tarea</th>' +
              '<th style="text-align:center">Horas</th>' +
              '<th style="text-align:right">Tarifa / h</th>' +
              '<th style="text-align:right">Subtotal</th>' +
            '</tr>' +
          '</thead>' +
          '<tbody>' +
            '<tr>' +
              '<td>' +
                '<strong>' + esc(sol.servicio) + '</strong>' +
                '<div class="muted" style="font-size:0.82rem">Turno coordinado: ' + fechaHora(sol.fecha_hora_programada) + '</div>' +
              '</td>' +
              '<td style="text-align:center">' + sol.duracion_horas + ' hs</td>' +
              '<td style="text-align:right">' + peso(sol.tarifa) + '</td>' +
              '<td style="text-align:right"><strong>' + peso(sol.monto_estimado) + '</strong></td>' +
            '</tr>' +
          '</tbody>' +
          '<tfoot>' +
            '<tr>' +
              '<td colspan="3" style="text-align:right;padding-top:16px"><strong>Total Abonado:</strong></td>' +
              '<td style="text-align:right;padding-top:16px"><strong style="font-size:1.3rem;color:var(--verde)">' + peso(pago ? pago.monto : sol.monto_estimado) + '</strong></td>' +
            '</tr>' +
            '<tr>' +
              '<td colspan="4" class="muted" style="font-size:0.82rem;text-align:right;border:none">' +
                'Medio de pago: ' + (pago ? esc(pago.metodo_pago.replace('_', ' ').toUpperCase()) : 'TARJETA') + ' · Garantía Hogaru 100%' +
              '</td>' +
            '</tr>' +
          '</tfoot>' +
        '</table>' +

        '<div class="comprobante-pie">' +
          '<div style="font-size:0.78rem;color:var(--gris);line-height:1.5">' +
            '🛡️ <strong>Garantía de Satisfacción Hogaru:</strong> Pago custodiado bajo el protocolo de intermediación segura.<br>' +
            'Proyecto de Prácticas Profesionalizantes (7° Año) · E.E.S.T. N°6 "Chacabuco" · Morón, Buenos Aires.' +
          '</div>' +
        '</div>' +
      '</div>';

    document.body.appendChild(overlay);

    document.getElementById('btn-imprimir').addEventListener('click', function () {
      window.print();
    });

    document.getElementById('btn-cerrar-comprobante').addEventListener('click', function () {
      overlay.remove();
    });

    overlay.addEventListener('click', function (e) {
      if (e.target === overlay) overlay.remove();
    });
  }

  function panelCalificacion() {
    if (sol.estado !== 'finalizada') return '';
    var c = sol.calificacion;
    var cuerpo;
    if (c) {
      cuerpo = '<div class="datos">' + dato('Puntualidad', '★ ' + c.puntuacion_puntualidad + ' / 5') + dato('Prolijidad', '★ ' + c.puntuacion_prolijidad + ' / 5') +
        dato('Trato', '★ ' + c.puntuacion_trato + ' / 5') + '</div>' + (c.comentario ? '<p>“' + esc(c.comentario) + '”</p>' : '');
    } else if (esCliente) {
      var opciones = [5, 4, 3, 2, 1].map(function (n) { return '<option value="' + n + '">' + n + '</option>'; }).join('');
      cuerpo = '<form id="form-calif"><div class="grilla-2" style="grid-template-columns:repeat(3,1fr)">' +
        '<div class="campo"><label for="c-punt">Puntualidad</label><select id="c-punt">' + opciones + '</select></div>' +
        '<div class="campo"><label for="c-prol">Prolijidad</label><select id="c-prol">' + opciones + '</select></div>' +
        '<div class="campo"><label for="c-trato">Trato</label><select id="c-trato">' + opciones + '</select></div></div>' +
        '<div class="campo"><label for="c-coment">Comentario (opcional)</label><textarea id="c-coment" maxlength="1000"></textarea></div>' +
        '<button class="btn" type="submit">Enviar calificación</button></form>';
    } else {
      cuerpo = '<p class="muted">El cliente todavía no calificó este servicio.</p>';
    }
    return '<div class="panel"><h2>Calificación</h2>' + cuerpo + '</div>';
  }

  function panelDisputas() {
    var lista = disputas.length ? disputas.map(function (d) {
      return '<div style="padding:10px 0;border-bottom:1px solid var(--gris-claro)">' + badge(d.estado) + ' <span class="muted">' + fechaCorta(d.fecha_apertura) + '</span>' +
        '<p style="margin:6px 0 0">' + esc(d.motivo) + '</p>' +
        (d.resolucion ? '<p class="muted" style="margin:4px 0 0"><strong>Resolución:</strong> ' + esc(d.resolucion) + '</p>' : '') + '</div>';
    }).join('') : '';
    var puedeAbrir = (esCliente || esPrestador) && sol.estado !== 'pendiente';
    if (!lista && !puedeAbrir) return '';
    var form = puedeAbrir
      ? '<form id="form-disputa" style="margin-top:12px"><div class="campo"><label for="motivo">¿Hubo algún problema? Contanos qué pasó</label>' +
        '<textarea id="motivo" minlength="10" maxlength="2000" required></textarea><div class="ayuda">Un administrador va a revisar tu reclamo.</div></div>' +
        '<button class="btn btn-claro" type="submit">Abrir reclamo</button></form>' : '';
    return '<div class="panel"><h2>Reclamos</h2>' + (lista || '<p class="muted">No hay reclamos en esta solicitud.</p>') + form + '</div>';
  }

  function panelChat() {
    if (!(esCliente || esPrestador)) return '';
    return '<div class="panel"><h2>Mensajes</h2><div class="chat" id="chat-lista"></div>' +
      '<form id="form-chat"><div class="fila" style="flex-wrap:nowrap"><input id="chat-texto" maxlength="2000" placeholder="Escribí un mensaje…" autocomplete="off" required>' +
      '<button class="btn" type="submit">Enviar</button></div></form></div>';
  }

  // ---------- chat (se actualiza solo, sin redibujar toda la página) ----------
  async function cargarChat() {
    var lista = document.getElementById('chat-lista');
    if (!lista) return;
    try {
      var mensajes = await api('/solicitudes/' + id + '/mensajes');
      if (mensajes.length === mensajesMostrados) return;
      var alFinal = mensajesMostrados === -1 || lista.scrollHeight - lista.scrollTop - lista.clientHeight < 60;
      mensajesMostrados = mensajes.length;
      lista.innerHTML = mensajes.length ? mensajes.map(function (m) {
        var mia = m.id_emisor === usuario.id_usuario;
        return '<div class="burbuja' + (mia ? ' mia' : '') + '"><span class="quien">' + (mia ? 'Vos' : esc(m.emisor)) + ' · ' + fechaHora(m.fecha_envio) + '</span>' + esc(m.contenido) + '</div>';
      }).join('') : '<p class="muted" style="margin:auto">Todavía no hay mensajes. ¡Escribí el primero!</p>';
      if (alFinal) lista.scrollTop = lista.scrollHeight;
    } catch (e) { /* un fallo del chat no debe romper la página */ }
  }
  setInterval(function () { if (document.visibilityState === 'visible') cargarChat(); }, 8000);

  // ---------- eventos (delegados: el contenido se redibuja) ----------
  raiz.addEventListener('click', async function (ev) {
    if (ev.target.closest('#btn-comprobante')) {
      abrirModalComprobante();
      return;
    }

    var b = ev.target.closest('button[data-accion]');
    if (!b) return;
    var accion = b.dataset.accion;
    if (accion === 'cancelar' && !confirm('¿Seguro que querés cancelar la solicitud?' + (pago && pago.estado === 'completado' ? ' El pago se va a reembolsar.' : ''))) return;
    ocupado(b, true);
    try {
      await api('/solicitudes/' + id + '/' + accion, { metodo: 'POST' });
      toast(ICONO_NOTIF_ACCION[accion]);
      await cargar();
    } catch (e) {
      toast(e.message, true);
      ocupado(b, false);
    }
  });

  raiz.addEventListener('submit', async function (ev) {
    ev.preventDefault();
    var form = ev.target;
    var boton = form.querySelector('button[type=submit]');
    ocupado(boton, true);
    try {
      if (form.id === 'form-pago') {
        var metodo = document.getElementById('metodo').value;
        if (metodo === 'tarjeta') {
          var num = (document.getElementById('tc-numero').value || '').replace(/\D/g, '');
          if (num.length < 13) throw new Error('Por favor ingresá un número de tarjeta válido (16 dígitos).');
        }
        await api('/solicitudes/' + id + '/pago', { metodo: 'POST', cuerpo: {
          metodo_pago: metodo,
          simular_fallo: document.getElementById('simular-fallo').checked,
        } });
        toast('¡Pago realizado con éxito!');
      } else if (form.id === 'form-calif') {
        await api('/solicitudes/' + id + '/calificacion', { metodo: 'POST', cuerpo: {
          puntuacion_puntualidad: Number(document.getElementById('c-punt').value),
          puntuacion_prolijidad: Number(document.getElementById('c-prol').value),
          puntuacion_trato: Number(document.getElementById('c-trato').value),
          comentario: document.getElementById('c-coment').value.trim() || null,
        } });
        toast('¡Gracias por tu calificación!');
      } else if (form.id === 'form-disputa') {
        await api('/solicitudes/' + id + '/disputas', { metodo: 'POST', cuerpo: { motivo: document.getElementById('motivo').value.trim() } });
        toast('Reclamo enviado. Un administrador lo va a revisar.');
      } else if (form.id === 'form-chat') {
        var texto = document.getElementById('chat-texto');
        await api('/solicitudes/' + id + '/mensajes', { metodo: 'POST', cuerpo: { contenido: texto.value.trim() } });
        texto.value = '';
        ocupado(boton, false);
        await cargarChat();
        return;
      }
      await cargar();
    } catch (e) {
      toast(e.message, true);
      ocupado(boton, false);
    }
  });

  cargar();
})();
