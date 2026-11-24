const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

function headers(includeAuth = true) {
  const values = { "Content-Type": "application/json" };
  const token = localStorage.getItem("ticketflow_token");
  if (includeAuth && token) {
    values.Authorization = `Bearer ${token}`;
  }
  return values;
}

async function request(path, options = {}) {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: { ...headers(options.auth !== false), ...options.headers },
  });
  if (response.status === 204) return null;
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const message =
      typeof data?.detail === "string"
        ? data.detail
        : data?.detail?.detail || "No fue posible completar la solicitud";
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }
  return { data, response };
}

export const api = {
  register: (data) =>
    request("/api/v1/auth/register", {
      method: "POST",
      auth: false,
      body: JSON.stringify(data),
    }),
  login: (correo, contrasena) =>
    request("/api/v1/auth/login", {
      method: "POST",
      auth: false,
      body: JSON.stringify({ correo, contrasena }),
    }),
  publicEvents: () => request("/api/v1/events?estado=publicado", { auth: false }),
  allEvents: () => request("/api/v1/events", { auth: false }),
  getUserOrders: (buyerId) =>
    request(`/api/v1/users/${buyerId}/orders`),
  availability: (showId) =>
    request(`/api/v1/shows/${showId}/availability`, { auth: false }),
  reserve: (funcionId, items) =>
    request("/api/v1/reservations", {
      method: "POST",
      body: JSON.stringify({ funcionId, items }),
    }),
  cancelReservation: (reservationId) =>
    request(`/api/v1/reservations/${reservationId}`, { method: "DELETE" }),
  pay: (reservaId, idempotencyKey) =>
    request("/api/v1/orders", {
      method: "POST",
      body: JSON.stringify({
        reservaId,
        idempotencyKey,
        metodoPago: "simulado",
      }),
  getReservation: (reservationId) =>
      request(`/api/v1/reservations/${reservationId}`),
    }),
  mineTickets: () => request("/api/v1/tickets/mine"),
  report: (name, filters = {}) => {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== "" && value !== null && value !== undefined) params.set(key, value);
    });
    const suffix = params.toString() ? `?${params}` : "";
    return request(`/api/v1/reports/${name}${suffix}`, { auth: true });
  },
  venues: {
    list: (ciudad = "", tipo = "") => {
      const params = new URLSearchParams();
      if (ciudad) params.set("ciudad", ciudad);
      if (tipo) params.set("tipo", tipo);
      const suffix = params.toString() ? `?${params}` : "";
      return request(`/api/v1/venues${suffix}`);
    },
    get: (id) => request(`/api/v1/venues/${id}`),
    create: (data) =>
      request("/api/v1/venues", { method: "POST", body: JSON.stringify(data) }),
    update: (id, data) =>
      request(`/api/v1/venues/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
    remove: (id) =>
      request(`/api/v1/venues/${id}`, { method: "DELETE" }),
  },
  organizers: {
    list: () => request("/api/v1/organizers"),
    get: (id) => request(`/api/v1/organizers/${id}`),
    create: (data) =>
      request("/api/v1/organizers", { method: "POST", body: JSON.stringify(data) }),
    update: (id, data) =>
      request(`/api/v1/organizers/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
    remove: (id) =>
      request(`/api/v1/organizers/${id}`, { method: "DELETE" }),
    events: (id) => request(`/api/v1/organizers/${id}/events`),
  },
  adminEvents: {
    list: (categoria = "", estado = "", ciudad = "") => {
      const params = new URLSearchParams();
      if (categoria) params.set("categoria", categoria);
      if (estado) params.set("estado", estado);
      if (ciudad) params.set("ciudad", ciudad);
      const suffix = params.toString() ? `?${params}` : "";
      return request(`/api/v1/events${suffix}`);
    },
    get: (id) => request(`/api/v1/events/${id}`),
    create: (data) =>
      request("/api/v1/events", { method: "POST", body: JSON.stringify(data) }),
    update: (id, data) =>
      request(`/api/v1/events/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
    cancel: (id) =>
      request(`/api/v1/events/${id}/cancel`, { method: "PATCH" }),
    publish: (id) =>
      request(`/api/v1/events/${id}/publish`, { method: "PATCH" }),
    addShows: (id, data) =>
      request(`/api/v1/events/${id}/shows`, { method: "POST", body: JSON.stringify(data) }),
  },
  batches: {
    create: (data) =>
      request("/api/v1/batches", { method: "POST", body: JSON.stringify(data) }),
    invoices: () => request("/api/v1/invoices"),
  },
  refunds: {
    create: (data) =>
      request("/api/v1/refunds", { method: "POST", body: JSON.stringify(data) }),
    get: (id) => request(`/api/v1/refunds/${id}`),
    approve: (id) =>
      request(`/api/v1/refunds/${id}/approve`, { method: "PATCH" }),
    reject: (id, motivo) =>
      request(`/api/v1/refunds/${id}/reject`, {
        method: "PATCH",
        body: JSON.stringify({ motivo }),
      }),
  },
  tickets: {
    all: () => request("/api/v1/tickets/all"),
    validate: (codigo, puerta) =>
      request("/api/v1/tickets/validate", {
        method: "POST",
        body: JSON.stringify({ codigo, puerta }),
      }),
  },
};
