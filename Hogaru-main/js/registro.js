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
      // se inicia sesión automáticamente
      var r = await api('/auth/login', { metodo: 'POST', cuerpo: { email: cuerpo.email, password: cuerpo.password } });
      Sesion.guardar(r.access_token, r.usuario);
      location.href = inicioSegunTipo(tipo);
    } catch (err) {
      mostrarAviso(aviso, 'error', err.message);
      ocupado(btn, false);
    }
  });
})();
