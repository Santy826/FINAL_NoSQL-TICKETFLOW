import * as React from "react";
import { useEffect, useState } from "react";
import { api } from "../services/api";

function errorMessage(error) {
  if (error.status === 401) return "La sesión expiró. Inicia sesión nuevamente.";
  if (error.status === 403) return "No tienes permisos para realizar esta acción.";
  return error.message;
}

function money(value) {
  return new Intl.NumberFormat("es-CO", { style: "currency", currency: "COP", maximumFractionDigits: 0 }).format(value || 0);
}

export default function AdminPanel({ role, onMessage, onAuthExpired }) {
  const [section, setSection] = useState("venues");
  const [venues, setVenues] = useState([]);
  const [organizers, setOrganizers] = useState([]);
  const [events, setEvents] = useState([]);
  const [invoices, setInvoices] = useState([]);
  const [busy, setBusy] = useState(false);

  const [venue, setVenue] = useState({ nombre: "", tipo: "teatro", ciudad: "", direccion: "" });
  const [venueSections, setVenueSections] = useState([]);
  const [sectionDraft, setSectionDraft] = useState({
    codigo: "",
    tipo: "general",
    capacidad: 100,
  });
  const [sectionRows, setSectionRows] = useState([]);
  const [rowDraft, setRowDraft] = useState({ fila: "A", sillas: 20 });
  const [sectionTables, setSectionTables] = useState([]);
  const [tableDraft, setTableDraft] = useState({ mesa: "M1", capacidad: 6 });
  const [organizer, setOrganizer] = useState({
    razonSocial: "", nit: "", contacto: "", telefono: "", comision: 10, politicaDevolucion: "hasta_48h_antes",
  });
  const [eventData, setEventData] = useState({
    nombre: "", categoria: "musica", organizadorId: "", restriccionEdad: 0,
    artista: "", duracionMin: 120,
  });
  const [shows, setShows] = useState([]);
  const [showDraft, setShowDraft] = useState({ recintoId: "", fechaHora: "", precios: {} });
  const [batch, setBatch] = useState({ tipo: "preventa", funcionId: "", eventId: "", seccion: "", cantidad: 100, precio: 50000 });
  const [refund, setRefund] = useState({ boletaId: "", tipo: "reembolso", motivo: "", nuevaFuncionId: "" });
  const [refundAction, setRefundAction] = useState({ id: "", motivo: "Solicitud rechazada por el organizador" });
  const [ticket, setTicket] = useState({ codigo: "", puerta: "PUERTA-1" });
  const [tickets, setTickets] = useState([]);

  async function safeCall(action) {
    try {
      return await action();
    } catch (error) {
      onMessage(errorMessage(error));
      if (error.status === 401 && onAuthExpired) onAuthExpired();
      return null;
    }
  }

  async function loadSection() {
    setBusy(true);
    if (section === "venues") {
      const result = await safeCall(() => api.venues.list());
      if (result) setVenues(result.data);
    } else if (section === "organizers") {
      const result = await safeCall(() => api.organizers.list());
      if (result) setOrganizers(result.data);
    } else if (section === "events") {
      const [eventResult, venueResult, organizerResult] = await Promise.all([
        safeCall(() => api.adminEvents.list()),
        safeCall(() => api.venues.list()),
        safeCall(() => api.organizers.list()),
      ]);
      if (eventResult) setEvents(eventResult.data);
      if (venueResult) setVenues(venueResult.data);
      if (organizerResult) setOrganizers(organizerResult.data);
    } else if (section === "batches") {
      const result = await safeCall(() => api.batches.invoices());
      if (result) setInvoices(result.data);
      const eventResult = await safeCall(() => api.adminEvents.list());
      if (eventResult) setEvents(eventResult.data);
    } else if (section === "refunds") {
      const result = await safeCall(() => api.tickets.all());
      if (result) setTickets(result.data);
    } else if (section === "tickets") {
      const result = await safeCall(() => api.tickets.all());
      if (result) setTickets(result.data);
    }
    setBusy(false);
  }

  useEffect(() => {
    loadSection();
  }, [section]);

  function addSectionRow() {
    if (!rowDraft.fila.trim()) return;
    setSectionRows((current) => [
      ...current.filter((row) => row.fila !== rowDraft.fila),
      { fila: rowDraft.fila.trim(), sillas: Number(rowDraft.sillas) },
    ]);
  }

  function addSectionTable() {
    if (!tableDraft.mesa.trim()) return;
    setSectionTables((current) => [
      ...current.filter((table) => table.mesa !== tableDraft.mesa),
      { mesa: tableDraft.mesa.trim(), capacidad: Number(tableDraft.capacidad) },
    ]);
  }

  function addVenueSection() {
    const code = sectionDraft.codigo.trim().toUpperCase();
    if (!code) {
      onMessage("Escribe el nombre o código de la sección.");
      return;
    }
    let section;
    if (sectionDraft.tipo === "general") {
      section = {
        codigo: code,
        tipo: "general",
        capacidad: Number(sectionDraft.capacidad),
      };
    } else if (sectionDraft.tipo === "numerada") {
      if (!sectionRows.length) {
        onMessage("Agrega al menos una fila con sus sillas.");
        return;
      }
      section = { codigo: code, tipo: "numerada", filas: sectionRows };
    } else {
      if (!sectionTables.length) {
        onMessage("Agrega al menos una mesa.");
        return;
      }
      section = { codigo: code, tipo: "mesa", mesas: sectionTables };
    }
    setVenueSections((current) => [
      ...current.filter((item) => item.codigo !== code),
      section,
    ]);
    setSectionDraft({ codigo: "", tipo: "general", capacidad: 100 });
    setSectionRows([]);
    setSectionTables([]);
  }

  async function createVenue(e) {
    e.preventDefault();
    if (!venueSections.length) {
      onMessage("Agrega al menos una sección al recinto.");
      return;
    }
    const result = await safeCall(() => api.venues.create({
      nombre: venue.nombre,
      tipo: venue.tipo,
      ciudad: venue.ciudad,
      direccion: venue.direccion,
      secciones: venueSections,
    }));
    if (result) {
      onMessage("Recinto creado correctamente.");
      setVenue({ nombre: "", tipo: "teatro", ciudad: "", direccion: "" });
      setVenueSections([]);
      setSectionRows([]);
      setSectionTables([]);
      await loadSection();
    }
  }

  async function removeVenue(id) {
    const result = await safeCall(() => api.venues.remove(id));
    if (result !== null) {
      onMessage("Recinto eliminado.");
      await loadSection();
    }
  }

  async function createOrganizer(e) {
    e.preventDefault();
    const result = await safeCall(() => api.organizers.create({
      ...organizer,
      comision: Number(organizer.comision),
    }));
    if (result) {
      onMessage("Organizador registrado correctamente.");
      setOrganizer({ razonSocial: "", nit: "", contacto: "", telefono: "", comision: 10, politicaDevolucion: "hasta_48h_antes" });
      await loadSection();
    }
  }

  async function removeOrganizer(id) {
    const result = await safeCall(() => api.organizers.remove(id));
    if (result !== null) {
      onMessage("Organizador eliminado.");
      await loadSection();
    }
  }

  function chooseVenueForShow(recintoId) {
    const selected = venues.find((item) => item._id === recintoId);
    const prices = {};
    (selected?.secciones || []).forEach((section) => { prices[section.codigo] = 50000; });
    setShowDraft({ recintoId, fechaHora: "", precios: prices });
  }

  function setShowPrice(code, value) {
    setShowDraft((current) => ({
      ...current,
      precios: { ...current.precios, [code]: Number(value) },
    }));
  }

  function addShow() {
    const selected = venues.find((item) => item._id === showDraft.recintoId);
    if (!selected || !showDraft.fechaHora) {
      onMessage("Selecciona el recinto y la fecha de la función.");
      return;
    }
    setShows((current) => [
      ...current,
      {
        fechaHora: new Date(showDraft.fechaHora).toISOString(),
        recintoId: showDraft.recintoId,
        ciudad: selected.ciudad,
        estado: "abierta",
        precios: showDraft.precios,
      },
    ]);
    setShowDraft({ recintoId: "", fechaHora: "", precios: {} });
  }

  async function createEvent(e) {
    e.preventDefault();
    if (!shows.length) {
      onMessage("Agrega al menos una función al evento.");
      return;
    }
    const result = await safeCall(() => api.adminEvents.create({
      nombre: eventData.nombre,
      categoria: eventData.categoria,
      organizadorId: eventData.organizadorId,
      restriccionEdad: Number(eventData.restriccionEdad),
      atributos: {
        artistas: eventData.artista ? [eventData.artista] : [],
        duracionMin: Number(eventData.duracionMin),
      },
      funciones: shows,
    }));
    if (result) {
      await safeCall(() => api.adminEvents.publish(result.data._id));
      onMessage("Evento creado y publicado con todas sus funciones.");
      setEventData({ nombre: "", categoria: "musica", organizadorId: "", restriccionEdad: 0, artista: "", duracionMin: 120 });
      setShows([]);
      await loadSection();
    }
  }

  async function cancelEvent(id) {
    const result = await safeCall(() => api.adminEvents.cancel(id));
    if (result) {
      onMessage("Evento cancelado.");
      await loadSection();
    }
  }

  async function publishEvent(id) {
    const result = await safeCall(() => api.adminEvents.publish(id));
    if (result) {
      onMessage("Evento publicado.");
      await loadSection();
    }
  }

  async function createBatch(e) {
    e.preventDefault();
    if (batch.tipo !== "nueva_funcion" && !batch.funcionId) {
      onMessage("Selecciona la función que recibirá el lote.");
      return;
    }
    if (batch.tipo === "nueva_funcion" && (!batch.eventId || !batch.seccion)) {
      onMessage("Selecciona el evento y la sección de la nueva función.");
      return;
    }
    if (batch.tipo === "nueva_seccion" && !batch.seccion) {
      onMessage("Escribe el código de la nueva sección.");
      return;
    }
    if ((batch.tipo === "preventa" || batch.tipo === "ampliacion") && !batch.seccion) {
      onMessage("Selecciona la zona general del lote.");
      return;
    }
    const payload = {
      tipo: batch.tipo,
      cantidad: Number(batch.cantidad),
      precio: Number(batch.precio),
    };
    if (batch.tipo === "nueva_funcion") {
      payload.eventId = batch.eventId;
      payload.seccion = batch.seccion;
    } else {
      payload.funcionId = batch.funcionId;
    }
    if (batch.tipo === "preventa" || batch.tipo === "ampliacion" || batch.tipo === "nueva_seccion") {
      payload.seccion = batch.seccion;
    }
    const result = await safeCall(() => api.batches.create(payload));
    if (result) {
      onMessage("Lote creado y factura generada.");
      await loadSection();
    }
  }

  async function createRefund(e) {
    e.preventDefault();
    const payload = {
      boletaId: refund.boletaId,
      tipo: refund.tipo,
      motivo: refund.motivo,
    };
    if (refund.tipo === "cambio_funcion") payload.nuevaFuncionId = refund.nuevaFuncionId;
    const result = await safeCall(() => api.refunds.create(payload));
    if (result) onMessage(`Solicitud creada con número ${result.data._id}.`);
  }

  async function approveRefund() {
    if (!refundAction.id) return onMessage("Ingresa el número de la devolución.");
    const result = await safeCall(() => api.refunds.approve(refundAction.id));
    if (result) onMessage("Devolución aprobada: la boleta quedó devuelta y se liberó el cupo.");
  }

  async function rejectRefund() {
    if (!refundAction.id) return onMessage("Ingresa el número de la devolución.");
    const result = await safeCall(() => api.refunds.reject(refundAction.id, refundAction.motivo));
    if (result) onMessage("Devolución rechazada.");
  }

  async function validateTicket(e) {
    e.preventDefault();
    const result = await safeCall(() => api.tickets.validate(ticket.codigo, ticket.puerta));
    if (result) onMessage(`Boleta aceptada en ${ticket.puerta}.`);
  }

  const adminOnly = role === "administrador";
  if (role !== "administrador" && role !== "organizador" && role !== "validador") {
    return <section className="panel"><h2>Administración</h2><p>Tu usuario no tiene permisos para operar este módulo.</p></section>;
  }

  const draftVenue = venues.find((item) => item._id === showDraft.recintoId);
  const batchShows = events.flatMap((eventItem) =>
    (eventItem.funciones || []).map((showItem) => ({
      ...showItem,
      eventName: eventItem.nombre,
      eventId: eventItem._id,
    })),
  );
  const selectedBatchEvent = events.find((item) => item._id === batch.eventId);
  const batchEventBaseShow = selectedBatchEvent?.funciones?.[0];
  const batchEventVenue = venues.find((item) => item._id === batchEventBaseShow?.recintoId);
  const selectedBatchShow = batchShows.find((item) => item.funcionId === batch.funcionId);
  const selectedBatchVenue = venues.find((item) => item._id === selectedBatchShow?.recintoId);

  return (
    <section className="panel administration">
      <div className="admin-heading">
        <div>
          <span className="eyebrow">Panel administrativo</span>
          <h2>Gestionar TicketFlow</h2>
        </div>
        <span className="role-badge">{role}</span>
      </div>

      <nav className="admin-tabs" aria-label="Módulos administrativos">
        {[
          ["venues", "1. Recintos"],
          ["organizers", "2. Organizadores"],
          ["events", "3. Eventos"],
          ["batches", "4. Lotes y facturas"],
          ["refunds", "5. Devoluciones"],
          ["tickets", "6. Acceso en puertas"],
        ].map(([id, label]) => (
          <button type="button" className={section === id ? "active" : ""} key={id} onClick={() => setSection(id)}>{label}</button>
        ))}
      </nav>

      {section === "venues" && adminOnly && (
        <div className="admin-grid">
          <form className="admin-form card" onSubmit={createVenue}>
            <div className="form-title">
              <span>Paso 1</span>
              <h3>Crear un recinto</h3>
              <p>Define libremente las secciones, filas, sillas, mesas o zonas generales de este escenario.</p>
            </div>
            <label>Tipo de escenario
              <select value={venue.tipo} onChange={(e) => setVenue({ ...venue, tipo: e.target.value })}>
                <option value="teatro">Teatro</option>
                <option value="estadio">Estadio</option>
                <option value="sala_comedia">Sala de comedia</option>
              </select>
            </label>
            <label>Nombre del recinto<input required value={venue.nombre} onChange={(e) => setVenue({ ...venue, nombre: e.target.value })} /></label>
            <label>Ciudad<input required value={venue.ciudad} onChange={(e) => setVenue({ ...venue, ciudad: e.target.value })} /></label>
            <label>Dirección<input value={venue.direccion} onChange={(e) => setVenue({ ...venue, direccion: e.target.value })} /></label>
            <div className="section-builder">
              <h4>Agregar una localidad o sección</h4>
              <label>Código visible
                <input value={sectionDraft.codigo} onChange={(e) => setSectionDraft({ ...sectionDraft, codigo: e.target.value })} placeholder="Ej. NORTE, PLATEA, VIP" />
              </label>
              <label>Tipo de localidad
                <select value={sectionDraft.tipo} onChange={(e) => setSectionDraft({ ...sectionDraft, tipo: e.target.value })}>
                  <option value="general">Zona general por cupos</option>
                  <option value="numerada">Sillas numeradas por filas</option>
                  <option value="mesa">Mesas</option>
                </select>
              </label>
              {sectionDraft.tipo === "general" && (
                <label>Capacidad de la zona
                  <input type="number" min="1" value={sectionDraft.capacidad} onChange={(e) => setSectionDraft({ ...sectionDraft, capacidad: e.target.value })} />
                </label>
              )}
              {sectionDraft.tipo === "numerada" && (
                <div className="mini-builder">
                  <div className="two-columns">
                    <label>Nombre de fila<input value={rowDraft.fila} onChange={(e) => setRowDraft({ ...rowDraft, fila: e.target.value })} /></label>
                    <label>Cantidad de sillas<input type="number" min="1" value={rowDraft.sillas} onChange={(e) => setRowDraft({ ...rowDraft, sillas: e.target.value })} /></label>
                  </div>
                  <button type="button" className="secondary" onClick={addSectionRow}>Agregar fila</button>
                  {sectionRows.map((row) => <span className="chip" key={row.fila}>Fila {row.fila}: {row.sillas} sillas</span>)}
                </div>
              )}
              {sectionDraft.tipo === "mesa" && (
                <div className="mini-builder">
                  <div className="two-columns">
                    <label>Nombre de mesa<input value={tableDraft.mesa} onChange={(e) => setTableDraft({ ...tableDraft, mesa: e.target.value })} /></label>
                    <label>Personas por mesa<input type="number" min="1" value={tableDraft.capacidad} onChange={(e) => setTableDraft({ ...tableDraft, capacidad: e.target.value })} /></label>
                  </div>
                  <button type="button" className="secondary" onClick={addSectionTable}>Agregar mesa</button>
                  {sectionTables.map((table) => <span className="chip" key={table.mesa}>{table.mesa}: {table.capacidad} personas</span>)}
                </div>
              )}
              <button type="button" className="secondary" onClick={addVenueSection}>Agregar sección al recinto</button>
            </div>
            {venueSections.length > 0 && (
              <div className="venue-sections">
                {venueSections.map((item) => (
                  <div className="show-row" key={item.codigo}>
                    <div><strong>{item.codigo}</strong><span>{item.tipo === "general" ? `${item.capacidad} cupos` : item.tipo === "numerada" ? `${item.filas.length} filas` : `${item.mesas.length} mesas`}</span></div>
                    <button type="button" className="danger" onClick={() => setVenueSections((current) => current.filter((row) => row.codigo !== item.codigo))}>Quitar</button>
                  </div>
                ))}
              </div>
            )}
            <button className="primary">Guardar recinto</button>
          </form>

          <div className="records card">
            <div className="form-title"><span>Recursos registrados</span><h3>Recintos</h3></div>
            {busy ? <p className="empty">Cargando recintos...</p> : venues.map((item) => (
              <article className="record" key={item._id}>
                <div className="record-icon">{item.tipo === "estadio" ? "E" : item.tipo === "teatro" ? "T" : "C"}</div>
                <div className="record-main"><strong>{item.nombre}</strong><span>{item.ciudad} · {item.tipo}</span></div>
                <div className="record-meta">{item.secciones?.length || 0} secciones</div>
                <button type="button" className="danger" onClick={() => removeVenue(item._id)}>Eliminar</button>
              </article>
            ))}
          </div>
        </div>
      )}

      {section === "organizers" && adminOnly && (
        <div className="admin-grid">
          <form className="admin-form card" onSubmit={createOrganizer}>
            <div className="form-title"><span>Paso 2</span><h3>Registrar organizador</h3><p>Datos comerciales, comisión y política de devoluciones.</p></div>
            <label>Razón social<input required value={organizer.razonSocial} onChange={(e) => setOrganizer({ ...organizer, razonSocial: e.target.value })} /></label>
            <label>NIT<input required value={organizer.nit} onChange={(e) => setOrganizer({ ...organizer, nit: e.target.value })} /></label>
            <label>Correo comercial<input required type="email" value={organizer.contacto} onChange={(e) => setOrganizer({ ...organizer, contacto: e.target.value })} /></label>
            <label>Teléfono<input value={organizer.telefono} onChange={(e) => setOrganizer({ ...organizer, telefono: e.target.value })} /></label>
            <label>Comisión (%)<input type="number" min="0" max="100" step="0.1" value={organizer.comision} onChange={(e) => setOrganizer({ ...organizer, comision: e.target.value })} /></label>
            <label>Política de devolución
              <select value={organizer.politicaDevolucion} onChange={(e) => setOrganizer({ ...organizer, politicaDevolucion: e.target.value })}>
                <option value="hasta_48h_antes">Permitir hasta 48 horas antes</option>
                <option value="sin_devolucion">No permitir devoluciones</option>
              </select>
            </label>
            <button className="primary">Guardar organizador</button>
          </form>
          <div className="records card">
            <div className="form-title"><span>Organizadores</span><h3>Registro activo</h3></div>
            {busy ? <p>Cargando...</p> : organizers.map((item) => (
              <article className="record" key={item._id}>
                <div className="record-icon">O</div>
                <div className="record-main"><strong>{item.razonSocial}</strong><span>NIT {item.nit}</span></div>
                <div className="record-meta">{item.comision}% comisión</div>
                <button type="button" className="danger" onClick={() => removeOrganizer(item._id)}>Eliminar</button>
              </article>
            ))}
          </div>
        </div>
      )}

      {section === "events" && adminOnly && (
        <div className="event-builder">
          <form className="admin-form card" onSubmit={createEvent}>
            <div className="form-title"><span>Paso 3</span><h3>Crear evento y funciones</h3><p>Primero los datos generales y después cada fecha, recinto y precio.</p></div>
            <div className="two-columns">
              <label>Nombre del evento<input required value={eventData.nombre} onChange={(e) => setEventData({ ...eventData, nombre: e.target.value })} /></label>
              <label>Categoría
                <select value={eventData.categoria} onChange={(e) => setEventData({ ...eventData, categoria: e.target.value })}>
                  <option value="musica">Música</option><option value="comedia">Comedia</option><option value="teatro">Teatro</option>
                  <option value="deportivo">Deportivo</option><option value="conferencia">Conferencia</option><option value="festival">Festival</option>
                </select>
              </label>
            </div>
            <div className="two-columns">
              <label>Organizador
                <select required value={eventData.organizadorId} onChange={(e) => setEventData({ ...eventData, organizadorId: e.target.value })}>
                  <option value="">Seleccionar organizador</option>
                  {organizers.map((item) => <option value={item._id} key={item._id}>{item.razonSocial}</option>)}
                </select>
              </label>
              <label>Edad mínima<input type="number" min="0" value={eventData.restriccionEdad} onChange={(e) => setEventData({ ...eventData, restriccionEdad: e.target.value })} /></label>
            </div>
            <div className="two-columns">
              <label>Artista principal<input value={eventData.artista} onChange={(e) => setEventData({ ...eventData, artista: e.target.value })} /></label>
              <label>Duración en minutos<input type="number" min="1" value={eventData.duracionMin} onChange={(e) => setEventData({ ...eventData, duracionMin: e.target.value })} /></label>
            </div>

            <div className="show-builder">
              <h4>Agregar una función</h4>
              <label>Fecha y hora<input type="datetime-local" value={showDraft.fechaHora} onChange={(e) => setShowDraft({ ...showDraft, fechaHora: e.target.value })} /></label>
              <label>Recinto
                <select value={showDraft.recintoId} onChange={(e) => chooseVenueForShow(e.target.value)}>
                  <option value="">Seleccionar recinto</option>
                  {venues.map((item) => <option value={item._id} key={item._id}>{item.nombre} — {item.ciudad}</option>)}
                </select>
              </label>
              {draftVenue && (
                <>
                  <p className="helper">Ciudad asignada: <strong>{draftVenue.ciudad}</strong></p>
                  <div className="price-grid">
                    {(draftVenue.secciones || []).map((item) => (
                      <label key={item.codigo}>Precio {item.codigo}
                        <input type="number" min="0" value={showDraft.precios[item.codigo] ?? 50000} onChange={(e) => setShowPrice(item.codigo, e.target.value)} />
                      </label>
                    ))}
                  </div>
                </>
              )}
              <button type="button" className="secondary" onClick={addShow}>Agregar esta función</button>
            </div>

            {shows.length > 0 && (
              <div className="show-list">
                <h4>Funciones del evento ({shows.length})</h4>
                {shows.map((item, index) => {
                  const venueItem = venues.find((candidate) => candidate._id === item.recintoId);
                  return (
                    <div className="show-row" key={`${item.fechaHora}-${index}`}>
                      <div><strong>{venueItem?.nombre}</strong><span>{item.ciudad} · {new Date(item.fechaHora).toLocaleString("es-CO")}</span></div>
                      <button type="button" className="danger" onClick={() => setShows((current) => current.filter((_, rowIndex) => rowIndex !== index))}>Quitar</button>
                    </div>
                  );
                })}
              </div>
            )}
            <button className="primary">Publicar evento</button>
          </form>

          <div className="records card">
            <div className="form-title"><span>Eventos</span><h3>Agenda registrada</h3></div>
            {busy ? <p>Cargando...</p> : events.map((item) => (
              <article className="record" key={item._id}>
                <div className="record-main"><strong>{item.nombre}</strong><span>{item.categoria} · {item.funciones?.length || 0} función(es)</span></div>
                <div className="record-meta">{item.estado}</div>
                {item.estado === "borrador" && <button type="button" className="primary" onClick={() => publishEvent(item._id)}>Publicar</button>}
                {item.estado !== "cancelado" && item.estado !== "cancelada" && <button type="button" className="danger" onClick={() => cancelEvent(item._id)}>Cancelar</button>}
              </article>
            ))}
          </div>
        </div>
      )}

      {section === "batches" && (
        <div className="admin-grid">
          <form className="admin-form card" onSubmit={createBatch}>
            <div className="form-title"><span>Paso 4</span><h3>Agregar inventario</h3><p>Se crea el lote y la factura automáticamente.</p></div>
            <label>Tipo de lote
              <select value={batch.tipo} onChange={(e) => setBatch({ ...batch, tipo: e.target.value })}>
                <option value="preventa">Preventa</option><option value="ampliacion">Ampliación de cupos</option>
                <option value="nueva_seccion">Nueva sección</option><option value="nueva_funcion">Nueva función</option>
              </select>
            </label>
            {batch.tipo === "nueva_funcion" ? (
              <>
                <label>Evento
                  <select value={batch.eventId} onChange={(e) => setBatch({ ...batch, eventId: e.target.value, seccion: "" })}>
                    <option value="">Seleccionar evento</option>
                    {events.map((item) => <option value={item._id} key={item._id}>{item.nombre}</option>)}
                  </select>
                </label>
                {batchEventVenue && (
                  <label>Sección de la nueva función
                    <select value={batch.seccion} onChange={(e) => setBatch({ ...batch, seccion: e.target.value })}>
                      <option value="">Seleccionar sección</option>
                      {(batchEventVenue.secciones || []).map((item) => <option value={item.codigo} key={item.codigo}>{item.codigo} · {item.tipo}</option>)}
                    </select>
                  </label>
                )}
              </>
            ) : (
              <label>Función
                <select value={batch.funcionId} onChange={(e) => setBatch({ ...batch, funcionId: e.target.value, seccion: "" })}>
                  <option value="">Seleccionar función</option>
                  {batchShows.map((item) => <option value={item.funcionId} key={item.funcionId}>{item.eventName} · {item.funcionId} · {item.ciudad}</option>)}
                </select>
              </label>
            )}
            {batch.tipo === "nueva_seccion" && <label>Código de la nueva sección<input placeholder="Ej. VIP" value={batch.seccion} onChange={(e) => setBatch({ ...batch, seccion: e.target.value })} /></label>}
            {(batch.tipo === "preventa" || batch.tipo === "ampliacion") && (
              <label>Zona general
                <select value={batch.seccion} onChange={(e) => setBatch({ ...batch, seccion: e.target.value })}>
                  <option value="">Seleccionar zona general</option>
                  {(selectedBatchVenue?.secciones || [])
                    .filter((item) => item.tipo === "general")
                    .map((item) => <option value={item.codigo} key={item.codigo}>{item.codigo} · {item.capacidad} cupos</option>)}
                </select>
              </label>
            )}
            <label>Cantidad<input type="number" min="1" value={batch.cantidad} onChange={(e) => setBatch({ ...batch, cantidad: e.target.value })} /></label>
            <label>Precio por unidad<input type="number" min="1" value={batch.precio} onChange={(e) => setBatch({ ...batch, precio: e.target.value })} /></label>
            <button className="primary">Crear lote y factura</button>
          </form>
          <div className="records card">
            <div className="form-title"><span>Facturación</span><h3>Facturas generadas</h3></div>
            {busy ? <p>Cargando...</p> : invoices.length ? invoices.map((item) => (
              <article className="record" key={item._id}>
                <div className="record-main"><strong>Factura {item._id}</strong><span>Lote {item.loteId}</span></div>
                <div className="record-meta">{money(item.monto ?? item.total)}</div>
              </article>
            )) : <p className="empty">Aún no hay facturas.</p>}
          </div>
        </div>
      )}

      {section === "refunds" && (
        <div className="admin-grid">
          <form className="admin-form card" onSubmit={createRefund}>
            <div className="form-title"><span>Paso 5</span><h3>Solicitar devolución</h3><p>La solicitud se vincula a una boleta existente.</p></div>
            <label>Boleta
              <select required value={refund.boletaId} onChange={(e) => setRefund({ ...refund, boletaId: e.target.value })}>
                <option value="">Seleccionar boleta vigente</option>
                {tickets.filter((item) => item.estado === "valida").map((item) => (
                  <option value={item._id} key={item._id}>
                    {item._id} · {item.seccion}{item.silla ? ` ${item.silla}` : ""}
                  </option>
                ))}
              </select>
            </label>
            <label>Tipo de solicitud
              <select value={refund.tipo} onChange={(e) => setRefund({ ...refund, tipo: e.target.value })}>
                <option value="reembolso">Reembolso</option><option value="cambio_funcion">Cambio de función</option>
              </select>
            </label>
            {refund.tipo === "cambio_funcion" && <label>Nueva función<input required placeholder="Ej. fn_rock_02" value={refund.nuevaFuncionId} onChange={(e) => setRefund({ ...refund, nuevaFuncionId: e.target.value })} /></label>}
            <label>Motivo<textarea required rows="4" value={refund.motivo} onChange={(e) => setRefund({ ...refund, motivo: e.target.value })} /></label>
            <button className="primary">Crear solicitud</button>
          </form>

          <form className="admin-form card" onSubmit={(e) => e.preventDefault()}>
            <div className="form-title"><span>Respuesta del organizador</span><h3>Aprobar o rechazar</h3><p>Ingresa el número mostrado al crear la solicitud.</p></div>
            <label>Número de devolución<input placeholder="Ej. dev_123" value={refundAction.id} onChange={(e) => setRefundAction({ ...refundAction, id: e.target.value })} /></label>
            <label>Motivo del rechazo<textarea rows="3" value={refundAction.motivo} onChange={(e) => setRefundAction({ ...refundAction, motivo: e.target.value })} /></label>
            <div className="action-buttons"><button type="button" className="primary" onClick={approveRefund}>Aprobar devolución</button><button type="button" className="danger" onClick={rejectRefund}>Rechazar</button></div>
          </form>
        </div>
      )}

      {section === "tickets" && (
        <form className="admin-form card narrow" onSubmit={validateTicket}>
          <div className="form-title"><span>Paso 6</span><h3>Validar entrada</h3><p>Escanea o escribe el código completo impreso en la boleta.</p></div>
          <label>Boleta encontrada
            <select value={ticket.codigo} onChange={(e) => setTicket({ ...ticket, codigo: e.target.value })}>
              <option value="">Seleccionar boleta emitida</option>
              {tickets.map((item) => (
                <option value={item.codigo} key={item._id}>
                  {item._id} · {item.estado} · {item.seccion}{item.silla ? ` ${item.silla}` : ""}
                </option>
              ))}
            </select>
          </label>
          <label>O pegar el código completo<textarea required={!ticket.codigo} rows="3" placeholder="bol_xxxxxxxx.firma" value={ticket.codigo} onChange={(e) => setTicket({ ...ticket, codigo: e.target.value })} /></label>
          <label>Puerta de ingreso
            <select value={ticket.puerta} onChange={(e) => setTicket({ ...ticket, puerta: e.target.value })}>
              <option value="PUERTA-1">Puerta 1</option><option value="PUERTA-2">Puerta 2</option><option value="PUERTA-3">Puerta 3</option>
            </select>
          </label>
          <button className="primary">Validar ahora</button>
        </form>
      )}
    </section>
  );
}
