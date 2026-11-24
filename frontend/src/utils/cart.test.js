import { describe, expect, it } from "vitest";
import { cartSummary, parseSeatLabel, secondsUntil } from "./cart";
import { dedupePublishedEvents, REPORT_LABELS, resolveSaleEvent } from "./ui";

describe("cart helpers", () => {
  it("calcula cantidad y subtotal para sillas y zona general", () => {
    const summary = cartSummary([
      { silla: "NORTE-A-1", cantidad: 1, precioUnitario: 250000 },
      { silla: null, cantidad: 3, precioUnitario: 80000 },
    ]);
    expect(summary.quantity).toBe(4);
    expect(summary.subtotal).toBe(490000);
  });

  it("extrae sección, fila y número de una silla", () => {
    expect(parseSeatLabel("PLATEA-B-12", "PLATEA")).toEqual({
      seccion: "PLATEA",
      fila: "B",
      numero: "12",
      mesa: "-",
    });
  });

  it("calcula segundos restantes sin aceptar fechas vencidas", () => {
    const now = new Date("2027-01-01T20:00:00Z").getTime();
    expect(secondsUntil("2027-01-01T20:10:00Z", now)).toBe(600);
    expect(secondsUntil("2027-01-01T19:59:00Z", now)).toBe(0);
  });

  it("deduplica eventos publicados y excluye estados no publicados", () => {
    const events = [
      {_id: "evt_1", nombre: "Evento 1", estado: "publicado"},
      {_id: "evt_1", nombre: "Evento 1 duplicado", estado: "publicado"},
      {_id: "evt_2", nombre: "Evento cancelado", estado: "cancelado"},
      {_id: "evt_3", nombre: "Evento 3", estado: "publicado"},
    ];
    expect(dedupePublishedEvents(events).map((event) => event._id)).toEqual(["evt_1", "evt_3"]);
  });

  it("usa nombres visibles amigables sin cambiar identificadores", () => {
    expect(REPORT_LABELS).toContainEqual(["occupancy", "Ocupación"]);
    expect(REPORT_LABELS).toContainEqual(["low-sales", "Eventos con bajas ventas"]);
    expect(REPORT_LABELS).toContainEqual(["sales-by-type", "Ventas por tipo de evento"]);
  });

  it("relaciona una venta con el evento de su funcion", () => {
    const result = resolveSaleEvent(
      { funcionId: "fn_rock" },
      [
        {_id: "evt_rock", nombre: "Rock", funciones: [{ funcionId: "fn_rock", fechaHora: "2027-01-01T20:00:00Z" }]},
        {_id: "evt_theater", nombre: "Teatro", funciones: [{ funcionId: "fn_theater" }]},
      ],
    );
    expect(result.event._id).toBe("evt_rock");
    expect(result.show.funcionId).toBe("fn_rock");
  });
});
