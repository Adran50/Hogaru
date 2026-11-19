// ===== Cliente de la API de Hogaru + manejo de sesión =====
const API_URL = window.HOGARU_API_URL || 'http://localhost:8000';
const CLAVE_TOKEN = 'hogaru_token';
const CLAVE_USUARIO = 'hogaru_usuario';

const Sesion = {
  token() { return localStorage.getItem(CLAVE_TOKEN); },
  usuario() {
    try { return JSON.parse(localStorage.getItem(CLAVE_USUARIO)); } catch (e) { return null; }
  },
  logueado() { return !!localStorage.getItem(CLAVE_TOKEN); },
  guardar(token, usuario) {
    localStorage.setItem(CLAVE_TOKEN, token);
    localStorage.setItem(CLAVE_USUARIO, JSON.stringify(usuario));
  },
  cerrar() {
    localStorage.removeItem(CLAVE_TOKEN);
    localStorage.removeItem(CLAVE_USUARIO);
  },
};

class ErrorApi extends Error {
  constructor(status, mensaje) {
    super(mensaje);
    this.status = status;
  }
}

// Convierte el cuerpo de error de FastAPI en un texto legible
function mensajeDeError(datos, status) {
  if (!datos || !datos.detail) return 'Ocurrió un error (' + status + ')';
  if (typeof datos.detail === 'string') return datos.detail;
  if (Array.isArray(datos.detail)) {
    return datos.detail.map(function (d) {
      var campo = (d.loc || []).filter(function (x) { return x !== 'body' && x !== 'query'; }).join('.');
      return campo ? campo + ': ' + d.msg : d.msg;
    }).join(' · ');
  }
  return 'Ocurrió un error (' + status + ')';
}

// api('/ruta', { metodo: 'POST', cuerpo: {...}, params: {...} })  ->  datos JSON
async function api(ruta, opciones) {
  opciones = opciones || {};
  var url = new URL(API_URL + ruta);
  var params = opciones.params || {};
  Object.keys(params).forEach(function (k) {
    var v = params[k];
    if (v !== undefined && v !== null && v !== '') url.searchParams.set(k, v);
  });

  var headers = {};
  var tieneCuerpo = opciones.cuerpo !== undefined;
  if (tieneCuerpo) headers['Content-Type'] = 'application/json';
  if (Sesion.token()) headers['Authorization'] = 'Bearer ' + Sesion.token();

  var resp;
  try {
    resp = await fetch(url.toString(), {
      method: opciones.metodo || 'GET',
      headers: headers,
      body: tieneCuerpo ? JSON.stringify(opciones.cuerpo) : undefined,
    });
  } catch (e) {
    throw new ErrorApi(0, 'No se pudo conectar con el servidor. ¿Está levantada la API?');
  }

  var datos = null;
  try { datos = await resp.json(); } catch (e) { /* respuesta sin cuerpo */ }

  if (!resp.ok) {
    // Token vencido o inválido: se cierra la sesión y se vuelve al login
    if (resp.status === 401 && Sesion.token()) {
      Sesion.cerrar();
      irALogin();
    }
    throw new ErrorApi(resp.status, mensajeDeError(datos, resp.status));
  }
  return datos;
}
