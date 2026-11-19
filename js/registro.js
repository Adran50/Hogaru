// ===== Registro =====
(function () {
  var tipo = 'cliente';
  var aviso = document.getElementById('aviso');
  var btn = document.getElementById('btn');

  function elegirTipo(nuevo) {
    tipo = nuevo;
    document.getElementById('tipo-cliente').classList.toggle('activo', nuevo === 'cliente');
    document.getElementById('tipo-prestador').classList.toggle('activo', nuevo === 'prestador');
    document.getElementById('campo-direccion').classList.toggle('oculto', nuevo !== 'cliente');
    document.getElementById('campo-descripcion').classList.toggle('oculto', nuevo !== 'prestador');
    document.getElementById('seccion-docs-prestador').classList.toggle('oculto', nuevo !== 'prestador');
    document.getElementById('info-prestador').classList.toggle('oculto', nuevo !== 'prestador');
  }
  document.getElementById('tipo-cliente').addEventListener('click', function () { elegirTipo('cliente'); });
  document.getElementById('tipo-prestador').addEventListener('click', function () { elegirTipo('prestador'); });
  if (param('tipo') === 'prestador') elegirTipo('prestador');

  function valor(id) { return document.getElementById(id).value.trim(); }

  document.getElementById('form-registro').addEventListener('submit', async function (e) {
    e.preventDefault();
    ocultarAviso(aviso);
    ocupado(btn, true);
    var cuerpo = {
      nombre: valor('nombre'), apellido: valor('apellido'), email: valor('email'),
      password: document.getElementById('password').value, telefono: valor('telefono') || null,
      tipo_cuenta: tipo,
    };
    if (tipo === 'cliente') cuerpo.direccion = valor('direccion') || null;
    else cuerpo.descripcion = valor('descripcion') || null;

    try {
      await api('/auth/registro', { metodo: 'POST', cuerpo: cuerpo });
      // Iniciar sesión automáticamente
      var r = await api('/auth/login', { metodo: 'POST', cuerpo: { email: cuerpo.email, password: cuerpo.password } });
      Sesion.guardar(r.access_token, r.usuario);

      // Si es prestador y adjuntó DNI (frente/dorso) y/o antecedentes, subirlos con el token recién obtenido
      if (tipo === 'prestador') {
        var fileFrente = document.getElementById('doc-dni-frente');
        var fileDorso = document.getElementById('doc-dni-dorso');
        var fileAnt = document.getElementById('doc-antecedentes');

        var tieneFrente = fileFrente && fileFrente.files && fileFrente.files[0];
        var tieneDorso = fileDorso && fileDorso.files && fileDorso.files[0];

        if (tieneFrente && tieneDorso) {
          try {
            var fdFrente = new FormData();
            fdFrente.append('tipo_documento', 'dni_frente');
            fdFrente.append('archivo', fileFrente.files[0]);
            await fetch(API_URL + '/verificacion/subir', {
              method: 'POST',
              headers: { 'Authorization': 'Bearer ' + r.access_token },
              body: fdFrente,
            });
          } catch (eFrente) { console.warn('Error subiendo DNI Frente:', eFrente); }

          try {
            var fdDorso = new FormData();
            fdDorso.append('tipo_documento', 'dni_dorso');
            fdDorso.append('archivo', fileDorso.files[0]);
            await fetch(API_URL + '/verificacion/subir', {
              method: 'POST',
              headers: { 'Authorization': 'Bearer ' + r.access_token },
              body: fdDorso,
            });
          } catch (eDorso) { console.warn('Error subiendo DNI Dorso:', eDorso); }
        } else if (tieneFrente && !tieneDorso) {
          try {
            var fdDni = new FormData();
            fdDni.append('tipo_documento', 'dni');
            fdDni.append('archivo', fileFrente.files[0]);
            await fetch(API_URL + '/verificacion/subir', {
              method: 'POST',
              headers: { 'Authorization': 'Bearer ' + r.access_token },
              body: fdDni,
            });
          } catch (eDni) { console.warn('Error subiendo DNI unificado:', eDni); }
        }

        if (fileAnt && fileAnt.files && fileAnt.files[0]) {
          try {
            var fdAnt = new FormData();
            fdAnt.append('tipo_documento', 'antecedentes_penales');
            fdAnt.append('archivo', fileAnt.files[0]);
            await fetch(API_URL + '/verificacion/subir', {
              method: 'POST',
              headers: { 'Authorization': 'Bearer ' + r.access_token },
              body: fdAnt,
            });
          } catch (eAnt) { console.warn('Error subiendo antecedentes:', eAnt); }
        }
      }

      location.href = inicioSegunTipo(tipo);
    } catch (err) {
      mostrarAviso(aviso, 'error', err.message);
      ocupado(btn, false);
    }
  });
})();
