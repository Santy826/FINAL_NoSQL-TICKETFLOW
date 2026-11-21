import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: 20,
  duration: '30s',
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

export function setup() {
  const response = http.post(`${BASE_URL}/api/v1/auth/login`, JSON.stringify({
    correo: 'admin@ticketflow.com',
    contrasena: 'Admin123!',
  }), { headers: { 'Content-Type': 'application/json' } });
  check(response, { 'login 200': (r) => r.status === 200 });
  return { token: response.json('access_token') };
}

export default function (data) {
  const headers = {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${data.token}`,
  };
  const body = JSON.stringify({
    funcionId: 'fn_rock_01',
    items: [{ seccion: 'NORTE', silla: 'NORTE-1-99', cantidad: 1 }],
  });

  const response = http.post(`${BASE_URL}/api/v1/reservations`, body, { headers });
  check(response, {
    '201 or 409': (r) => r.status === 201 || r.status === 409,
  });
  sleep(0.1);
}
