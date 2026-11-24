import * as React from "react";
import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "./services/api";
import AdminPanel from "./components/AdminPanel";
import { cartSummary, formatMoney, parseSeatLabel, secondsUntil } from "./utils/cart";
import { dedupePublishedEvents, REPORT_LABELS, resolveSaleEvent } from "./utils/ui";

const REPORTS = REPORT_LABELS;

const LABELS = {
  funcionId: "Función",
  seccion: "Sección",
  vendidas: "Boletas vendidas",
  reservadas: "Reservadas",
  bloqueadas: "Bloqueadas",
  disponibles: "Disponibles",
  ventas: "Ventas",
  ingresos: "Ingresos",
  compradores: "Compradores",
  asistentes: "Asistentes",
  inasistentes: "Inasistentes",
  intentos: "Intentos",
  cantidad: "Cantidad",
  monto: "Monto",
  ventasBrutas: "Ventas brutas",
  reembolsos: "Devoluciones",
  ingresoNeto: "Ingreso neto",
  rango: "Rango de edad",
  nombre: "Nombre",
  ciudad: "Ciudad",
  fechaHora: "Fecha",
  capacidad: "Capacidad",
  boletasVendidas: "Boletas vendidas",
  categoria: "Categoría",
};

function formatReportValue(key, value) {
  if (value == null) return "-";
  if (typeof value === "object") return Array.isArray(value) ? value.join(", ") : "-";
  if (["ingresos", "monto", "ventasBrutas", "reembolsos", "ingresoNeto", "precio"].includes(key)) {
    return new Intl.NumberFormat("es-CO", { style: "currency", currency: "COP", maximumFractionDigits: 0 }).format(value);
  }
  if (key === "fechaHora") {
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString("es-CO");
  }
  return String(value);
}

function formatTicketDate(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString("es-CO", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function userIdFromToken(token) {
  if (!token) return null;
  try {
    const payload = token.split(".")[1];
    const normalized = payload.replace(/-/g, "+").replace(/_/g, "/");
    const decoded = JSON.parse(atob(normalized));
    return decoded.sub || null;
  } catch {
    return null;
  }
}

function ReportTable({ report }) {
  const data = report.data;
  if (!Array.isArray(data)) {
    return (
      <dl className="report-summary">
        {Object.entries(data || {}).map(([key, value]) => (
          <div key={key}><dt>{LABELS[key] || key}</dt><dd>{formatReportValue(key, value)}</dd></div>
        ))}
      </dl>
    );
  }
  if (!data.length) {
    return <p className="empty">No hay resultados para mostrar.</p>;
  }

  const flat = data.map((row) => (
    typeof row === "object" && row !== null
      ? Object.fromEntries(Object.entries(row).filter(([key]) => !["_id", "organizador", "porEdad"].includes(key)))
      : { resultado: row }
  ));
  const columns = [...new Set(flat.flatMap((row) => Object.keys(row)))].slice(0, 7);

  return (
    <div className="table-wrap">
      <table>
        <thead><tr>{columns.map((column) => <th key={column}>{LABELS[column] || column}</th>)}</tr></thead>
        <tbody>
          {flat.slice(0, 20).map((row, index) => (
            <tr key={index}>{columns.map((column) => <td key={column}>{formatReportValue(column, row[column])}</td>)}</tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function App() {
  const [tab, setTab] = useState("eventos");
  const [events, setEvents] = useState([]);
  const [selectedShow, setSelectedShow] = useState("");
  const [availability, setAvailability] = useState(null);
  const [availabilityLoading, setAvailabilityLoading] = useState(false);
  const [cart, setCart] = useState([]);
  const [reservation, setReservation] = useState(null);
  const [remaining, setRemaining] = useState(0);
  const expirationCheckStarted = useRef(false);
  const [tickets, setTickets] = useState([]);
  const [sales, setSales] = useState([]);
  const [salesLoading, setSalesLoading] = useState(false);
  const [reports, setReports] = useState({});
  const [reportFilters, setReportFilters] = useState({});
  const [activeReport, setActiveReport] = useState("");
  const [message, setMessage] = useState("");
  const [login, setLogin] = useState({ correo: "", contrasena: "" });
  const [register, setRegister] = useState({
    nombre: "",
    correo: "",
    contrasena: "",
    fechaNacimiento: "",
    rol: "comprador",
  });
  const [authMode, setAuthMode] = useState("login");
  const [token, setToken] = useState(() => localStorage.getItem("ticketflow_token"));
  const [role, setRole] = useState(() => localStorage.getItem("ticketflow_role"));
  const [userId, setUserId] = useState(() => {
    const stored = localStorage.getItem("ticketflow_userId");
    if (stored) return stored;
    return userIdFromToken(localStorage.getItem("ticketflow_token"));
  });
  const [authLoading, setAuthLoading] = useState(false);
  const availabilityRequest = useRef(0);

  useEffect(() => {
    api.publicEvents()
        .then(({ data }) => {
          setEvents(dedupePublishedEvents(data));
        })
      .catch((error) => setMessage(error.message));
  }, []);

  useEffect(() => {
    if (!reservation?.expiraEn) return;
    expirationCheckStarted.current = false;
    const update = () => {
      const seconds = secondsUntil(reservation.expiraEn);
      setRemaining(seconds);
      if (seconds === 0 && !expirationCheckStarted.current) {
        expirationCheckStarted.current = true;
        api.getReservation(reservation._id)
          .then(({ data }) => {
            if (data.estado !== "activa" || secondsUntil(data.expiraEn) === 0) {
              setReservation(null);
              setCart([]);
              setRemaining(0);
              setMessage("La reserva venció y las entradas fueron liberadas.");
              chooseShow(selectedShow);
            } else {
              setReservation(data);
            }
          })
          .catch((error) => {
            setReservation(null);
            setCart([]);
            setRemaining(0);
            setMessage(requestError(error));
            chooseShow(selectedShow);
          });
      }
    };
    update();
    const timer = window.setInterval(update, 1000);
    return () => window.clearInterval(timer);
  }, [reservation]);

  const shows = useMemo(
    () =>
      events.flatMap((event) =>
        (event.funciones || []).map((show) => ({
          ...show,
          eventoNombre: event.nombre,
          eventoId: event._id,
        })),
      ),
    [events],
  );

  const selectedShowData = useMemo(
    () => shows.find((show) => show.funcionId === selectedShow) || null,
    [shows, selectedShow],
  );

  async function chooseShow(showId) {
    const requestId = ++availabilityRequest.current;
    setSelectedShow(showId);
    setCart([]);
    setReservation(null);
    setRemaining(0);
    setAvailability(null);
    setAvailabilityLoading(true);
    setMessage("Cargando la distribución de esta función...");
    try {
      const { data } = await api.availability(showId);
      if (requestId !== availabilityRequest.current) return;
      setAvailability(data);
      setAvailabilityLoading(false);
      setMessage("");
    } catch (error) {
      if (requestId !== availabilityRequest.current) return;
      setAvailability(null);
      setAvailabilityLoading(false);
      setMessage(requestError(error));
      if (error.status === 401) setTab("boletas");
    }
  }

  function toggleSeat(section, seat) {
    if (seat.estado !== "libre") return;
    const unitPrice = Number(selectedShowData?.precios?.[section] || 0);
    setCart((current) =>
      current.some((item) => item.silla === seat.silla)
        ? current.filter((item) => item.silla !== seat.silla)
        : [...current, {
          seccion: section,
          silla: seat.silla,
          cantidad: 1,
          precioUnitario: unitPrice,
          etiqueta: seat.silla,
        }],
    );
  }

  function setGeneralQuantity(section, quantity) {
    const amount = Math.max(0, Number(quantity || 0));
    const unitPrice = Number(selectedShowData?.precios?.[section] || 0);
    setCart((current) => {
      const others = current.filter((item) => item.seccion !== section || item.silla);
      if (amount === 0) return others;
      return [
        ...others,
        {
          seccion: section,
          silla: null,
          cantidad: amount,
          precioUnitario: unitPrice,
          etiqueta: `Zona ${section}`,
        },
      ];
    });
  }

  async function reserve() {
    if (!selectedShow || !cart.length) {
      setMessage("Selecciona al menos una silla disponible.");
      return;
    }
    if (!token) {
      setTab("boletas");
      setMessage("Inicia sesión antes de crear una reserva.");
      return;
    }
    try {
      const reservationItems = cart.map((item) => ({
        seccion: item.seccion,
        silla: item.silla,
        cantidad: item.silla ? 1 : item.cantidad,
      }));
      const { data } = await api.reserve(selectedShow, reservationItems);
      setReservation(data);
      setMessage("Reserva creada durante 10 minutos.");
    } catch (error) {
      setMessage(requestError(error));
      if (error.status === 401) setTab("boletas");
    }
  }

  async function cancelReservation() {
    if (!reservation) return;
    try {
      await api.cancelReservation(reservation._id);
      setReservation(null);
      setCart([]);
      await chooseShow(selectedShow);
      setMessage("Reserva cancelada.");
    } catch (error) {
      setMessage(requestError(error));
    }
  }

  async function pay() {
    if (!reservation) return;
    const key = `front-${crypto.randomUUID()}`;
    try {
      await api.pay(reservation._id, key);
      setReservation(null);
      setCart([]);
      setMessage("Pago simulado completado.");
      await loadTickets();
    } catch (error) {
      setMessage(requestError(error));
    }
  }

  async function signIn(event) {
    event.preventDefault();
    setAuthLoading(true);
    try {
      const { data } = await api.login(login.correo, login.contrasena);
      localStorage.setItem("ticketflow_token", data.access_token);
      localStorage.setItem("ticketflow_role", data.usuario?.rol || "");
      localStorage.setItem("ticketflow_userId", data.usuario?._id || "");
      setToken(data.access_token);
      setRole(data.usuario?.rol || "");
      setUserId(data.usuario?._id || "");
      setMessage(`Sesión iniciada como ${data.usuario?.correo || login.correo}`);
      setTab("eventos");
    } catch (error) {
      setMessage(requestError(error));
    } finally {
      setAuthLoading(false);
    }
  }

  async function signUp(event) {
    event.preventDefault();
    try {
      await api.register(register);
      setLogin({ correo: register.correo, contrasena: register.contrasena });
      setAuthMode("login");
      setMessage("Cuenta creada. Ahora inicia sesión.");
    } catch (error) {
      setMessage(requestError(error));
    }
  }

  async function loadTickets() {
    try {
      const { data } = await api.mineTickets();
      setTickets(data);
    } catch (error) {
      setMessage(requestError(error));
    }
  }

  async function loadSales() {
    if (!userId) return;
    setSalesLoading(true);
    try {
      const [ordersResult, eventsResult] = await Promise.all([
        api.getUserOrders(userId),
        api.allEvents(),
      ]);
      const allEvents = Array.isArray(eventsResult.data) ? eventsResult.data : [];
      const venueCache = new Map();
      const resolved = await Promise.all((Array.isArray(ordersResult.data) ? ordersResult.data : []).map(async (order) => {
        const eventInfo = resolveSaleEvent(order, allEvents);
        let venueName = "";
        const venueId = eventInfo?.show?.recintoId;
        if (venueId) {
          if (!venueCache.has(venueId)) {
            try {
              venueCache.set(venueId, (await api.venues.get(venueId)).data);
            } catch {
              venueCache.set(venueId, null);
            }
          }
          venueName = venueCache.get(venueId)?.nombre || "";
        }
        const ticketsCount = (order.items || []).reduce(
          (sum, item) => sum + (item.silla ? 1 : Number(item.cantidad || 0)),
          0,
        );
        return {
          ...order,
          eventoNombre: eventInfo?.event?.nombre || "Evento no disponible",
          funcionId: order.funcionId,
          fechaHora: eventInfo?.show?.fechaHora || null,
          recintoNombre: venueName,
          ciudad: eventInfo?.show?.ciudad || "",
          ticketsCount,
        };
      }));
      setSales(resolved);
    } catch (error) {
      setMessage(requestError(error));
      setSales([]);
    } finally {
      setSalesLoading(false);
    }
  }

  async function loadReport(name) {
    setActiveReport(name);
    if (!token) {
      setAuthMode("login");
      setTab("boletas");
      setMessage("Inicia sesión antes de consultar reportes.");
      return;
    }
    if (!["administrador", "organizador"].includes(role)) {
      setMessage("Tu rol no tiene permiso para consultar reportes.");
      return;
    }
    try {
      const { data, response } = await api.report(name, reportFilters);
      setReports((current) => ({
        ...current,
        [name]: { data, cache: response.headers.get("X-Cache") },
      }));
    } catch (error) {
      setMessage(requestError(error));
      if (error.status === 401) setTab("boletas");
    }
  }

  useEffect(() => {
    if (tab === "boletas" && token) loadTickets();
  }, [tab, token]);

  useEffect(() => {
    if (tab === "ventas" && token && userId) loadSales();
  }, [tab, token, userId]);

  function logout() {
    localStorage.removeItem("ticketflow_token");
    localStorage.removeItem("ticketflow_role");
    localStorage.removeItem("ticketflow_userId");
    setToken(null);
    setRole(null);
    setUserId(null);
    setTickets([]);
    setSales([]);
    setReports({});
    setMessage("Sesión cerrada.");
  }

  function requestError(error) {
    if (error.status === 401) {
      localStorage.removeItem("ticketflow_token");
      localStorage.removeItem("ticketflow_role");
      localStorage.removeItem("ticketflow_userId");
      setToken(null);
      setRole(null);
      setUserId(null);
      return "Tu sesión expiró o no has iniciado sesión.";
    }
    if (error.status === 403) {
      return "No tienes permiso para realizar esta acción.";
    }
    return error.message;
  }

  const timer = `${String(Math.floor(remaining / 60)).padStart(2, "0")}:${String(remaining % 60).padStart(2, "0")}`;
  const cartTotals = cartSummary(cart);

  return (
    <main className="app">
      <header>
        <div>
          <strong>TicketFlow</strong>
          <span>Compra y administración de eventos</span>
        </div>
        <nav>
          {[
            ["eventos", "Eventos"],
            ["boletas", "Mis boletas"],
            ...(token ? [["ventas", "Ventas"]] : []),
            ["reportes", "Reportes"],
            ...(token ? [["administracion", "Administración"]] : []),
          ].map(([id, label]) => (
            <button className={tab === id ? "active" : ""} key={id} onClick={() => setTab(id)}>
              {label}
            </button>
          ))}
          {token && <button className="logout-button" onClick={logout}>Cerrar sesión</button>}
        </nav>
      </header>

      {message && <div className="notice" role="status">{message}</div>}

      {tab === "eventos" && (
        <section className="grid">
          <aside className="panel">
            <h2>Eventos publicados</h2>
            {events.map((event) => (
              <article className="event-card" key={event._id}>
                <strong>{event.nombre}</strong>
                {event.atributos?.descripcion && <p>{event.atributos.descripcion}</p>}
                {(event.funciones || []).map((show) => (
                  <button
                    className={`show ${selectedShow === show.funcionId ? "active" : ""}`}
                    key={show.funcionId}
                    onClick={() => chooseShow(show.funcionId)}
                  >
                    <strong>{show.ciudad}</strong>
                    <small>{formatTicketDate(show.fechaHora)}</small>
                  </button>
                ))}
              </article>
            ))}
          </aside>

          <div className="panel map">
            <h2>Mapa de sillas y zonas</h2>
            {!availability ? (
              <p className="empty">{availabilityLoading ? "Cargando disponibilidad..." : "Selecciona una función."}</p>
            ) : (
              availability.secciones.map((section) => (
                <div className="section" key={section.seccion}>
                  <h3>{section.seccion} · {section.tipo}</h3>
                  {section.sillas ? (
                    <div className="seats">
                      {section.sillas.map((seat) => (
                        (() => {
                          const label = parseSeatLabel(seat.silla, section.seccion);
                          return (
                            <button
                              key={seat.silla}
                              className={`seat ${seat.estado} ${cart.some((item) => item.silla === seat.silla) ? "selected" : ""}`}
                              title={`${label.seccion} · fila ${label.fila} · silla ${label.numero} · ${seat.estado}`}
                              onClick={() => toggleSeat(section.seccion, seat)}
                            >
                              <span>{label.fila}</span>
                              <strong>{label.numero}</strong>
                            </button>
                          );
                        })()
                      ))}
                    </div>
                  ) : (
                    <div className="general-zone">
                      <p>Zona general: {section.disponibles} disponibles</p>
                      <label>
                        Cantidad
                        <input
                          type="number"
                          min="0"
                          max={section.disponibles}
                          value={cart.find((item) => item.seccion === section.seccion && !item.silla)?.cantidad || 0}
                          onChange={(event) => setGeneralQuantity(section.seccion, event.target.value)}
                        />
                      </label>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>

          <aside className="panel cart">
            <h2>Carrito</h2>
            {reservation ? (
              <>
                <div className="timer">{timer}</div>
                <p>Reserva {reservation._id}</p>
                <button onClick={pay} disabled={remaining <= 0}>Confirmar pago simulado</button>
                <button className="secondary" onClick={cancelReservation}>Cancelar reserva</button>
              </>
            ) : (
              <>
                {cart.map((item) => (
                  <div className="cart-row" key={item.silla || `${item.seccion}-general`}>
                    <div>
                      <strong>{item.etiqueta || item.silla}</strong>
                      {item.silla && (() => {
                        const label = parseSeatLabel(item.silla, item.seccion);
                        return <small>Sección {label.seccion} · fila {label.fila} · silla {label.numero}</small>;
                      })()}
                      {!item.silla && <small>{item.cantidad} cupo(s) · {formatMoney(item.precioUnitario)} c/u</small>}
                      {item.silla && <small>{formatMoney(item.precioUnitario)} c/u</small>}
                    </div>
                    <div className="cart-line-total">{formatMoney(item.precioUnitario * (item.silla ? 1 : item.cantidad))}</div>
                    <button onClick={() => setCart((current) =>
                      item.silla
                        ? current.filter((row) => row.silla !== item.silla)
                        : current.filter((row) => row.seccion !== item.seccion || row.silla)
                    )}>×</button>
                  </div>
                ))}
                {!cart.length && <p className="empty">El carrito está vacío.</p>}
                {!!cart.length && (
                  <div className="cart-summary">
                    <span>{cartTotals.quantity} entrada(s)</span>
                    <strong>{formatMoney(cartTotals.subtotal)}</strong>
                  </div>
                )}
                <button disabled={!cart.length} onClick={reserve}>Reservar</button>
              </>
            )}
          </aside>
        </section>
      )}

      {tab === "boletas" && (
        <section className="panel">
          <div className="section-heading">
            <h2>Mis boletas</h2>
            {token && <button className="logout" onClick={logout}>Cerrar sesión</button>}
          </div>
          {!token ? (
            <div className="auth-panel">
              <div className="auth-tabs">
                {authMode === "login" ? (
                  <button type="button" onClick={() => setAuthMode("register")}>Crear cuenta</button>
                ) : (
                  <button type="button" onClick={() => setAuthMode("login")}>Iniciar sesión</button>
                )}
              </div>
              {authMode === "login" ? (
                <form className="login" onSubmit={signIn}>
                  <label>Correo electrónico<input type="email" required value={login.correo} onChange={(event) => setLogin({ ...login, correo: event.target.value })} /></label>
                  <label>Contraseña<input type="password" required value={login.contrasena} onChange={(event) => setLogin({ ...login, contrasena: event.target.value })} /></label>
                  <button disabled={authLoading}>{authLoading ? "Iniciando sesión..." : "Iniciar sesión"}</button>
                </form>
              ) : (
                <form className="login" onSubmit={signUp}>
                  <label>Nombre completo<input required value={register.nombre} onChange={(e) => setRegister({ ...register, nombre: e.target.value })} /></label>
                  <label>Correo electrónico<input required type="email" value={register.correo} onChange={(e) => setRegister({ ...register, correo: e.target.value })} /></label>
                  <label>Contraseña (mínimo 6 caracteres)<input required minLength="6" type="password" value={register.contrasena} onChange={(e) => setRegister({ ...register, contrasena: e.target.value })} /></label>
                  <label>Fecha de nacimiento<input required type="date" value={register.fechaNacimiento} onChange={(e) => setRegister({ ...register, fechaNacimiento: e.target.value })} /></label>
                  <label>Tipo de cuenta
                    <select value={register.rol} onChange={(e) => setRegister({ ...register, rol: e.target.value })}>
                      <option value="comprador">Comprador</option>
                      <option value="validador">Validador</option>
                    </select>
                  </label>
                  <button>Crear cuenta</button>
                </form>
              )}
            </div>
          ) : (
            <>
              <button onClick={loadTickets}>Actualizar boletas</button>
              <div className="tickets">
                {tickets.map((ticket) => (
                  <article key={ticket._id}>
                    {ticket.qr?.startsWith("data:image") && (
                      <img className="ticket-qr" src={ticket.qr} alt={`Código QR de la boleta ${ticket._id}`} />
                    )}
                    <h3>{ticket._id}</h3>
                    {ticket.eventoDisponible ? (
                      <>
                        <p className="ticket-event">{ticket.eventoNombre}</p>
                        {ticket.eventoFechaHora && (
                          <p>{formatTicketDate(ticket.eventoFechaHora)}</p>
                        )}
                        {ticket.recintoNombre && (
                          <p>{ticket.recintoNombre}{ticket.recintoCiudad ? ` · ${ticket.recintoCiudad}` : ""}</p>
                        )}
                      </>
                    ) : (
                      <p className="ticket-event unavailable">Información del evento no disponible</p>
                    )}
                    {ticket.qr && !ticket.qr.startsWith("data:image") && (
                      <code className="ticket-code">{ticket.codigo || ticket.qr}</code>
                    )}
                    <p>
                      <strong>{ticket.seccion}</strong>
                      {ticket.silla
                        ? ` · ${ticket.silla}`
                        : ` · ${ticket.cantidad} cupo(s)`}
                    </p>
                    <p>Precio: {formatMoney(ticket.precio)}</p>
                    <span className={`status ${ticket.estado}`}>{ticket.estado}</span>
                  </article>
                ))}
                {!tickets.length && <p className="empty">No hay boletas disponibles.</p>}
              </div>
            </>
          )}
        </section>
      )}

      {tab === "ventas" && (
        <section className="panel">
          <div className="section-heading">
            <h2>Mis ventas</h2>
            <button type="button" onClick={loadSales}>Actualizar ventas</button>
          </div>
          {salesLoading ? (
            <p className="empty">Cargando ventas...</p>
          ) : (
            <div className="sales-grid">
              {sales.map((sale) => (
                <article className="sale-card" key={sale._id}>
                  <div className="sale-heading">
                    <div>
                      <span>Venta {sale._id}</span>
                      <h3>{sale.eventoNombre}</h3>
                    </div>
                    <span className={`status ${sale.estado}`}>{sale.estado}</span>
                  </div>
                  {sale.fechaHora && <p>{formatTicketDate(sale.fechaHora)}</p>}
                  {sale.recintoNombre && (
                    <p>{sale.recintoNombre}{sale.ciudad ? ` · ${sale.ciudad}` : ""}</p>
                  )}
                  <p>Función: {sale.funcionId}</p>
                  <div className="sale-items">
                    {(sale.items || []).map((item, index) => (
                      <span key={`${item.seccion}-${item.silla || index}`}>
                        {item.seccion}
                        {item.silla ? ` · ${item.silla}` : ` · ${item.cantidad || 0} cupo(s)`}
                      </span>
                    ))}
                  </div>
                  <div className="sale-totals">
                    <span>{sale.ticketsCount} boleta(s)</span>
                    <strong>{formatMoney(sale.subtotal)}</strong>
                  </div>
                </article>
              ))}
              {!sales.length && <p className="empty">No hay ventas registradas.</p>}
            </div>
          )}
        </section>
      )}

      {tab === "reportes" && (
        <section className="panel">
          <h2>Panel de reportes</h2>
          {!token || !["administrador", "organizador"].includes(role) ? (
            <div className="login-required">
              <h3>{token ? "Tu rol no puede consultar reportes" : "Necesitas iniciar sesión"}</h3>
              <p>Los reportes están disponibles para cuentas administradoras y organizadoras.</p>
              {!token && (
                <button
                  type="button"
                  className="primary"
                  onClick={() => {
                    setAuthMode("login");
                    setTab("boletas");
                  }}
                >
                  Ir a iniciar sesión
                </button>
              )}
            </div>
          ) : (
            <>
              <div className="report-buttons">
                {REPORTS.map(([name, label]) => (
                  <button key={name} onClick={() => loadReport(name)}>{label}</button>
                ))}
              </div>
              {["occupancy", "inventory-value", "sales", "show-availability", "buyers-by-age", "top-seats", "low-sales", "refunds", "attendance"].includes(activeReport) && (
                <div className="report-filters">
                  {["occupancy", "inventory-value", "show-availability", "sales", "buyers-by-age", "attendance"].includes(activeReport) && (
                    <label>
                      ID de función o evento
                      <input
                        value={reportFilters.funcion_id || reportFilters.evento_id || ""}
                        onChange={(event) => setReportFilters((current) => ({
                          ...current,
                          ...(activeReport === "show-availability" || activeReport === "sales" || activeReport === "buyers-by-age"
                            ? { evento_id: event.target.value }
                            : { funcion_id: event.target.value }),
                        }))}
                        placeholder="Ej. fn_rock_01"
                      />
                    </label>
                  )}
                  {activeReport === "occupancy" && (
                    <label>
                      Sección
                      <input value={reportFilters.seccion || ""} onChange={(event) => setReportFilters((current) => ({ ...current, seccion: event.target.value }))} placeholder="Ej. NORTE" />
                    </label>
                  )}
                  {["sales", "buyers-by-age", "refunds"].includes(activeReport) && (
                    <>
                      <label>
                        Desde
                        <input type="datetime-local" value={reportFilters.desde || ""} onChange={(event) => setReportFilters((current) => ({ ...current, desde: event.target.value }))} />
                      </label>
                      <label>
                        Hasta
                        <input type="datetime-local" value={reportFilters.hasta || ""} onChange={(event) => setReportFilters((current) => ({ ...current, hasta: event.target.value }))} />
                      </label>
                    </>
                  )}
                  {activeReport === "top-seats" && (
                    <label>
                      Límite
                      <input type="number" min="1" max="100" value={reportFilters.limite || 10} onChange={(event) => setReportFilters((current) => ({ ...current, limite: event.target.value }))} />
                    </label>
                  )}
                  {activeReport === "low-sales" && (
                    <label>
                      Próximos días
                      <input type="number" min="1" max="365" value={reportFilters.dias || 15} onChange={(event) => setReportFilters((current) => ({ ...current, dias: event.target.value }))} />
                    </label>
                  )}
                  <button type="button" className="primary" onClick={() => loadReport(activeReport)}>Aplicar filtros</button>
                </div>
              )}
            </>
          )}
          <div className="reports">
            {REPORTS.map(([name, label]) => {
              const report = reports[name];
              return report ? (
                <article key={name}>
                  <h3>{label}</h3>
                  <span className={`cache-badge ${report.cache === "hit" ? "hit" : ""}`}>
                    {report.cache === "hit" ? "Datos actualizados desde caché" : "Datos consultados en MongoDB"}
                  </span>
                  <ReportTable report={report} />
                </article>
              ) : null;
            })}
          </div>
        </section>
      )}

      {tab === "administracion" && token && (
        <AdminPanel
          role={role}
          onMessage={setMessage}
          onAuthExpired={() => {
            localStorage.removeItem("ticketflow_token");
            localStorage.removeItem("ticketflow_role");
            localStorage.removeItem("ticketflow_userId");
            setToken(null);
            setRole(null);
            setUserId(null);
            setTab("boletas");
            setMessage("La sesión expiró. Inicia sesión nuevamente.");
          }}
        />
      )}
    </main>
  );
}
