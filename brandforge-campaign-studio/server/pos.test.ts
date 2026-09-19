import { describe, expect, it } from "vitest";
import { buildDeluxeCatalogPayload, buildQuoteReceipt, catalogItemsFromAsset, createPosTicket, dollarsToCents } from "./pos";

describe("POS service", () => {
  const catalog = {
    categories: [{ name: "Signature services", layout_id: "cinema-split", items: [{ name: "The Essential", price: "$149", description: "A clear service." }, { name: "The Complete", price: "$249.50", description: "The full reset." }] }],
    receipt_layout: "minimal-brand-receipt",
  };

  it("normalizes generated POS catalog prices into cents", () => {
    expect(dollarsToCents("$249.50")).toBe(24950);
    expect(catalogItemsFromAsset(catalog)).toHaveLength(2);
    expect(catalogItemsFromAsset(catalog)[1]?.category).toBe("Signature services");
  });

  it("creates a deterministic quote without treating it as a payment", () => {
    const ticket = createPosTicket({ lines: [{ id: "1", name: "The Essential", unitPriceCents: 14900, quantity: 2 }], taxRateBps: 825, tipRateBps: 1500 });
    expect(ticket.subtotalCents).toBe(29800);
    expect(ticket.taxCents).toBe(2459);
    expect(ticket.tipCents).toBe(4470);
    expect(ticket.totalCents).toBe(36729);
    expect(ticket.status).toBe("quote");
    expect(ticket.paymentBoundary).toContain("never collects card data");
  });

  it("builds a non-sensitive Deluxe catalog mapping", () => {
    const payload = buildDeluxeCatalogPayload({ brandName: "Detail Reserve", catalog, taxRateBps: 825, locationName: "DFW", receiptFooter: "Thank you" });
    expect(payload.catalog.items[0]).toMatchObject({ name: "The Essential", price_cents: 14900, taxable: true });
    expect(JSON.stringify(payload)).not.toMatch(/\bpan\b|\bcvv\b|card_number/i);
  });

  it("renders a quote receipt without presenting it as a payment receipt", () => {
    const ticket = createPosTicket({ lines: [{ id: "1", name: "The Essential", unitPriceCents: 14900, quantity: 1 }], taxRateBps: 825, tipRateBps: 0 });
    const receipt = buildQuoteReceipt({ brandName: "Detail Reserve", locationName: "DFW", receiptFooter: "Thank you", ticket });
    expect(receipt).toContain("QUOTE RECEIPT — NOT A PAYMENT RECEIPT");
    expect(receipt).toContain("The Essential");
    expect(receipt).toContain("$161.29");
    expect(receipt).not.toMatch(/card number|cvv|emv/i);
  });
});
