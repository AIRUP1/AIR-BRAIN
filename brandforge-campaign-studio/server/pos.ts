export type PosCatalogItem = {
  id: string;
  name: string;
  price: string;
  description: string;
  category: string;
};

export type PosTicketLine = {
  id: string;
  name: string;
  unitPriceCents: number;
  quantity: number;
};

export type PosTicket = {
  ticketNumber: string;
  currency: "USD";
  lines: Array<PosTicketLine & { lineTotalCents: number }>;
  subtotalCents: number;
  taxRateBps: number;
  taxCents: number;
  tipRateBps: number;
  tipCents: number;
  totalCents: number;
  status: "quote";
  paymentBoundary: string;
};

function money(cents: number): string {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(cents / 100);
}

type UnknownRecord = Record<string, unknown>;

function record(value: unknown): UnknownRecord {
  return typeof value === "object" && value !== null && !Array.isArray(value) ? value as UnknownRecord : {};
}

function text(value: unknown, fallback = ""): string {
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}

export function dollarsToCents(value: string): number {
  const normalized = value.replace(/[^0-9.]/g, "");
  const amount = Number(normalized);
  return Number.isFinite(amount) && amount >= 0 ? Math.round(amount * 100) : 0;
}

export function catalogItemsFromAsset(payload: UnknownRecord): PosCatalogItem[] {
  const categories = Array.isArray(payload.categories) ? payload.categories : [];
  return categories.flatMap((category, categoryIndex) => {
    const categoryRecord = record(category);
    const categoryName = text(categoryRecord.name, `Category ${categoryIndex + 1}`);
    const items = Array.isArray(categoryRecord.items) ? categoryRecord.items : [];
    return items.map((item, itemIndex) => {
      const itemRecord = record(item);
      const name = text(itemRecord.name, `Item ${itemIndex + 1}`);
      return {
        id: `${categoryIndex + 1}-${itemIndex + 1}-${name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "")}`,
        name,
        price: text(itemRecord.price, "$0"),
        description: text(itemRecord.description, "Brand-aligned service."),
        category: categoryName,
      };
    });
  });
}

export function createPosTicket(input: { lines: PosTicketLine[]; taxRateBps: number; tipRateBps: number }): PosTicket {
  const lines = input.lines
    .filter((line) => Number.isFinite(line.unitPriceCents) && line.unitPriceCents >= 0 && Number.isInteger(line.quantity) && line.quantity > 0)
    .map((line) => ({ ...line, unitPriceCents: Math.round(line.unitPriceCents), lineTotalCents: Math.round(line.unitPriceCents) * line.quantity }));
  const subtotalCents = lines.reduce((sum, line) => sum + line.lineTotalCents, 0);
  const taxRateBps = Math.min(2_000, Math.max(0, Math.round(input.taxRateBps)));
  const tipRateBps = Math.min(5_000, Math.max(0, Math.round(input.tipRateBps)));
  const taxCents = Math.round(subtotalCents * (taxRateBps / 10_000));
  const tipCents = Math.round(subtotalCents * (tipRateBps / 10_000));
  return {
    ticketNumber: `BF-${new Date().toISOString().slice(0, 10).replace(/-/g, "")}-${Math.random().toString(36).slice(2, 6).toUpperCase()}`,
    currency: "USD",
    lines,
    subtotalCents,
    taxRateBps,
    taxCents,
    tipRateBps,
    tipCents,
    totalCents: subtotalCents + taxCents + tipCents,
    status: "quote",
    paymentBoundary: "Quote only. BrandForge never collects card data. Complete a live charge in an approved Deluxe hosted-payment or mobile-POS flow after merchant activation.",
  };
}

export function buildQuoteReceipt(input: { brandName: string; locationName: string; receiptFooter: string; ticket: PosTicket }) {
  const lines = input.ticket.lines.map((line) => `${line.quantity} × ${line.name}\n${money(line.lineTotalCents)}`).join("\n\n");
  return [
    input.brandName.toUpperCase(),
    input.locationName,
    "QUOTE RECEIPT — NOT A PAYMENT RECEIPT",
    `Ticket: ${input.ticket.ticketNumber}`,
    `Created: ${new Date().toLocaleString("en-US", { dateStyle: "medium", timeStyle: "short" })}`,
    "",
    lines,
    "",
    `SUBTOTAL  ${money(input.ticket.subtotalCents)}`,
    `EST. TAX  ${money(input.ticket.taxCents)}`,
    `EST. TIP  ${money(input.ticket.tipCents)}`,
    `QUOTE TOTAL  ${money(input.ticket.totalCents)}`,
    "",
    input.ticket.paymentBoundary,
    input.receiptFooter,
  ].join("\n");
}

export function deluxeReadiness() {
  const configured = Boolean(process.env.DELUXE_CLIENT_ID && process.env.DELUXE_CLIENT_SECRET && process.env.DELUXE_PARTNER_TOKEN);
  return {
    provider: "Eliot by Deluxe / Deluxe Payments",
    state: configured ? "credentialed" : "activation_required",
    configured,
    apiBaseUrl: "https://api.deluxe.com",
    supports: ["Catalog mapping", "Quote and receipt payloads", "Hosted-payment handoff", "Mobile POS SDK activation", "Webhook-ready event boundary"],
    requirements: configured
      ? ["Merchant account and server credentials detected. Confirm the approved Deluxe API product and production endpoint with the Deluxe Implementations Team before enabling payment capture."]
      : ["Active Deluxe Merchant Account configured for API access", "Client ID, Client Secret, and Partner Token issued by Deluxe Implementations", "Approved Hosted Payment Form or Mobile POS SDK integration for card-present or card-not-present capture", "Merchant-controlled webhook URL and event contract"],
    safety: "Card numbers, EMV data, and wallet credentials are not accepted or stored by BrandForge.",
  };
}

export function buildDeluxeCatalogPayload(input: { brandName: string; catalog: UnknownRecord; taxRateBps: number; locationName: string; receiptFooter: string }) {
  const items = catalogItemsFromAsset(input.catalog).map((item) => ({
    external_item_ref: item.id,
    name: item.name,
    description: item.description,
    price_cents: dollarsToCents(item.price),
    currency: "USD",
    category: item.category,
    taxable: input.taxRateBps > 0,
  }));
  return {
    provider: "Eliot by Deluxe / Deluxe Payments",
    package_type: "catalog-and-receipt-mapping",
    schema_version: "1.0",
    generated_at: new Date().toISOString(),
    merchant_profile: {
      display_name: input.brandName,
      location_name: input.locationName,
      tax_rate_bps: input.taxRateBps,
      receipt_footer: input.receiptFooter,
    },
    catalog: { items },
    implementation_note: "Mapping payload only. Submit only after Deluxe validates the merchant-specific catalog, API product, and required fields.",
  };
}
