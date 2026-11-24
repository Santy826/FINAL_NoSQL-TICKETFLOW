export const REPORT_LABELS = [
  ["occupancy", "Ocupación"],
  ["inventory-value", "Valor del inventario"],
  ["sales", "Ventas"],
  ["organizers", "Organizadores"],
  ["show-availability", "Disponibilidad"],
  ["buyers-by-age", "Compradores por edad"],
  ["sales-by-type", "Ventas por tipo de evento"],
  ["top-seats", "Sillas más vendidas"],
  ["revenue", "Ingresos"],
  ["low-sales", "Eventos con bajas ventas"],
  ["refunds", "Devoluciones"],
  ["fraud-attempts", "Intentos de fraude"],
  ["attendance", "Asistencia"],
];

export function dedupePublishedEvents(events) {
  if (!Array.isArray(events)) return [];
  return [...new Map(
    events
      .filter((event) => event.estado === "publicado")
      .map((event) => [event._id, event]),
  ).values()];
}

export function resolveSaleEvent(order, events) {
  for (const event of Array.isArray(events) ? events : []) {
    const show = (event.funciones || []).find((item) => item.funcionId === order.funcionId);
    if (show) return { event, show };
  }
  return null;
}
