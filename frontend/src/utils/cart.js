export function formatMoney(value) {
  return new Intl.NumberFormat("es-CO", {
    style: "currency",
    currency: "COP",
    maximumFractionDigits: 0,
  }).format(Number(value || 0));
}

export function parseSeatLabel(seatId, sectionCode) {
  const fallback = seatId ? String(seatId) : "";
  if (!fallback) return { seccion: sectionCode || "", fila: "-", numero: "-", mesa: "-" };
  const parts = fallback.split("-");
  if (parts.length >= 3) {
    return {
      seccion: parts[0] || sectionCode || "",
      fila: parts[1] || "-",
      numero: parts.slice(2).join("-"),
      mesa: "-",
    };
  }
  if (fallback.startsWith(`${sectionCode}-`)) {
    return {
      seccion: sectionCode || parts[0] || "",
      fila: "-",
      numero: "-",
      mesa: fallback.slice(sectionCode.length + 1),
    };
  }
  return { seccion: sectionCode || "", fila: "-", numero: "-", mesa: fallback };
}

export function cartSummary(items) {
  const quantity = items.reduce(
    (sum, item) => sum + (item.silla ? 1 : Number(item.cantidad || 0)),
    0,
  );
  const subtotal = items.reduce(
    (sum, item) => sum + (Number(item.precioUnitario || 0) * (item.silla ? 1 : Number(item.cantidad || 0))),
    0,
  );
  return { quantity, subtotal };
}

export function secondsUntil(expiration, now = Date.now()) {
  if (!expiration) return 0;
  const target = new Date(expiration).getTime();
  if (Number.isNaN(target)) return 0;
  return Math.max(0, Math.floor((target - now) / 1000));
}

