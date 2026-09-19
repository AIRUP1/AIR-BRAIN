import { useMemo, useState } from "react";
import { BadgeDollarSign, Check, ClipboardCheck, CreditCard, Download, FileText, History, Loader2, Minus, Plus, ReceiptText, ShieldCheck, Store, TerminalSquare } from "lucide-react";
import { toast } from "sonner";
import { trpc } from "@/lib/trpc";

type Kit = { name: string; palette: string[]; fonts: { heading: string; body: string }; voice: string; tagline: string; offer: string };
type PosAsset = { type: string; variant: number; provider: string; payload: Record<string, unknown> };
type CatalogItem = { id: string; name: string; price: string; description: string; category: string };
type CartItem = CatalogItem & { quantity: number; unitPriceCents: number };
type Ticket = { ticketNumber: string; currency: "USD"; lines: Array<{ id: string; name: string; unitPriceCents: number; quantity: number; lineTotalCents: number }>; subtotalCents: number; taxRateBps: number; taxCents: number; tipRateBps: number; tipCents: number; totalCents: number; status: "quote"; paymentBoundary: string };
type TicketHistoryItem = { id: number; ticketNumber: string; totalCents: number; status: "quote" | "exported" | "void"; createdAt: Date | string };

function cents(value: number) { return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(value / 100); }
function priceToCents(value: string) { const parsed = Number(value.replace(/[^0-9.]/g, "")); return Number.isFinite(parsed) ? Math.round(parsed * 100) : 0; }
function download(name: string, content: Record<string, unknown>) { const blob = new Blob([JSON.stringify(content, null, 2)], { type: "application/json" }); const url = URL.createObjectURL(blob); const link = document.createElement("a"); link.href = url; link.download = name; link.click(); URL.revokeObjectURL(url); }

export default function PosCommandCenter({ kit, brandKitId, posAsset }: { kit: Kit; brandKitId: number; posAsset?: PosAsset }) {
  const [cart, setCart] = useState<CartItem[]>([]);
  const [taxRateBps, setTaxRateBps] = useState(825);
  const [tipRateBps, setTipRateBps] = useState(1500);
  const [locationName, setLocationName] = useState("Primary location");
  const [receiptFooter, setReceiptFooter] = useState("Thank you for choosing a higher standard.");
  const [ticket, setTicket] = useState<Ticket | null>(null);
  const utils = trpc.useUtils();
  const catalog = trpc.studio.pos.catalog.useQuery({ payload: posAsset?.payload ?? {} }, { enabled: Boolean(posAsset) });
  const readiness = trpc.studio.pos.deluxeReadiness.useQuery();
  const quoteHistory = trpc.studio.pos.listTickets.useQuery({ brandKitId }, { enabled: Boolean(brandKitId) });
  const quote = trpc.studio.pos.createTicket.useMutation({
    onSuccess: (data) => { setTicket(data as Ticket); void utils.studio.pos.listTickets.invalidate(); toast.success("Quote saved to the POS ledger. Choose an approved Deluxe checkout path to capture payment."); },
    onError: () => toast.error("Ticket needs at least one valid line item."),
  });
  const deluxePackage = trpc.studio.pos.buildDeluxeCatalog.useMutation({
    onSuccess: (data) => { download(`${kit.name.toLowerCase().replace(/\s+/g, "-")}-deluxe-catalog-mapping.json`, data.payload as Record<string, unknown>); toast.success("Deluxe catalog mapping downloaded for merchant onboarding."); },
    onError: () => toast.error("Catalog mapping could not be prepared."),
  });
  const receipt = trpc.studio.pos.buildReceipt.useMutation({
    onSuccess: (data) => { const blob = new Blob([data.receipt], { type: "text/plain;charset=utf-8" }); const url = URL.createObjectURL(blob); const link = document.createElement("a"); link.href = url; link.download = `${kit.name.toLowerCase().replace(/\s+/g, "-")}-quote-receipt.txt`; link.click(); URL.revokeObjectURL(url); toast.success("Quote receipt downloaded. It is not a payment receipt."); },
    onError: () => toast.error("Quote receipt could not be prepared."),
  });
  const grouped = useMemo<Record<string, CatalogItem[]>>(() => {
    const items = (catalog.data?.items ?? []) as CatalogItem[];
    return items.reduce<Record<string, CatalogItem[]>>((groups, item) => { (groups[item.category] ??= []).push(item); return groups; }, {});
  }, [catalog.data]);
  const subtotal = cart.reduce((sum, item) => sum + item.unitPriceCents * item.quantity, 0);
  const add = (item: CatalogItem) => setCart((current) => { const found = current.find((line) => line.id === item.id); return found ? current.map((line) => line.id === item.id ? { ...line, quantity: line.quantity + 1 } : line) : [...current, { ...item, quantity: 1, unitPriceCents: priceToCents(item.price) }]; });
  const changeQuantity = (id: string, next: number) => setCart((current) => next < 1 ? current.filter((line) => line.id !== id) : current.map((line) => line.id === id ? { ...line, quantity: next } : line));
  const createQuote = () => quote.mutate({ brandKitId, lines: cart.map(({ id, name, quantity, unitPriceCents }) => ({ id, name, quantity, unitPriceCents })), taxRateBps, tipRateBps });
  const exportReceipt = () => ticket && receipt.mutate({ brandName: kit.name, locationName, receiptFooter, ticket });
  const status = readiness.data as { configured: boolean; provider: string; safety: string; requirements: string[] } | undefined;

  return <section className="pos-command section-card">
    <div className="section-kicker compact"><span>05</span><div><small>POS OPERATIONS / ELIOT BY DELUXE READY</small><h2>Turn your offer into a working register.</h2></div><div className="line" /><p>Build the sellable catalog, make transparent tickets, and package the merchant mapping for Deluxe activation—without accepting payment data in BrandForge.</p></div>
    {!posAsset ? <div className="pos-empty"><TerminalSquare size={25} /><div><b>Generate the POS Menu asset first.</b><p>Your brand-locked service grid will appear here as a category-aware register catalog.</p></div></div> : <div className="pos-grid">
      <article className="pos-panel pos-catalog"><header><div><span>01 / CATALOG</span><h3>{kit.name} service menu</h3></div><Store size={20} /></header><p>Built from variant 0{posAsset.variant} / {posAsset.provider}. Add services to a quote before sending the catalog mapping to the merchant implementation team.</p>
      {catalog.isLoading ? <div className="pos-loading"><Loader2 className="spin" size={16} /> Loading catalog...</div> : Object.entries(grouped).map(([category, items]) => <div className="pos-category" key={category}><b>{category}</b>{items.map((item) => <button key={item.id} onClick={() => add(item)}><span><strong>{item.name}</strong><small>{item.description}</small></span><em>{item.price}</em><Plus size={14} /></button>)}</div>)}
      </article>
      <article className="pos-panel pos-register"><header><div><span>02 / QUOTE REGISTER</span><h3>{cart.length ? `${cart.reduce((count, line) => count + line.quantity, 0)} item${cart.reduce((count, line) => count + line.quantity, 0) === 1 ? "" : "s"} in ticket` : "New ticket"}</h3></div><ReceiptText size={20} /></header>
      <div className="cart-lines">{cart.length === 0 ? <div className="cart-empty"><CreditCard size={20} /><p>Choose a service from the catalog to build a payment-ready quote.</p></div> : cart.map((line) => <div className="cart-line" key={line.id}><div><b>{line.name}</b><span>{cents(line.unitPriceCents)} each</span></div><div className="quantity"><button onClick={() => changeQuantity(line.id, line.quantity - 1)} aria-label={`Reduce ${line.name}`}><Minus size={12} /></button><span>{line.quantity}</span><button onClick={() => changeQuantity(line.id, line.quantity + 1)} aria-label={`Add ${line.name}`}><Plus size={12} /></button></div><strong>{cents(line.unitPriceCents * line.quantity)}</strong></div>)}</div>
      <div className="pos-input-grid"><label><span>SALES TAX %</span><input type="number" min="0" max="20" step="0.01" value={(taxRateBps / 100).toFixed(2)} onChange={(event) => setTaxRateBps(Math.round(Number(event.target.value) * 100) || 0)} /></label><label><span>TIP %</span><input type="number" min="0" max="50" step="1" value={tipRateBps / 100} onChange={(event) => setTipRateBps(Math.round(Number(event.target.value) * 100) || 0)} /></label></div>
      <div className="pos-summary"><span><i>SUBTOTAL</i><b>{cents(subtotal)}</b></span><span><i>EST. TAX</i><b>{cents(Math.round(subtotal * taxRateBps / 10_000))}</b></span><span><i>EST. TIP</i><b>{cents(Math.round(subtotal * tipRateBps / 10_000))}</b></span><strong><i>QUOTE TOTAL</i><b>{cents(subtotal + Math.round(subtotal * taxRateBps / 10_000) + Math.round(subtotal * tipRateBps / 10_000))}</b></strong></div>
      <button className="command-action" onClick={createQuote} disabled={!cart.length || quote.isPending || !brandKitId}>{quote.isPending ? <Loader2 className="spin" size={15} /> : <ClipboardCheck size={15} />}{quote.isPending ? "Calculating..." : "Create payment-ready quote"}</button>
      {ticket && <div className="ticket-result"><div><span>{ticket.ticketNumber}</span><Check size={14} /></div><p><b>{cents(ticket.totalCents)}</b> saved to the quote ledger and ready for an approved Deluxe payment handoff.</p><small>{ticket.paymentBoundary}</small><button onClick={exportReceipt} disabled={receipt.isPending}>{receipt.isPending ? <Loader2 className="spin" size={13} /> : <FileText size={13} />}{receipt.isPending ? "Preparing receipt..." : "Export quote receipt"}</button></div>}
      </article>
      <article className="pos-panel pos-deluxe"><header><div><span>03 / DELUXE ACTIVATION</span><h3>Eliot merchant handoff</h3></div><BadgeDollarSign size={20} /></header><div className={`deluxe-status ${status?.configured ? "ready" : "pending"}`}><span><i />{status?.configured ? "SERVER CREDENTIALS DETECTED" : "ACTIVATION REQUIRED"}</span><b>{status?.provider ?? "Eliot by Deluxe / Deluxe Payments"}</b><p>{status?.safety}</p></div>
      <label className="pos-text-input"><span>STORE / SERVICE LOCATION</span><input value={locationName} onChange={(event) => setLocationName(event.target.value)} /></label><label className="pos-text-input"><span>RECEIPT FOOTER</span><textarea value={receiptFooter} onChange={(event) => setReceiptFooter(event.target.value)} /></label>
      <div className="activation-list">{status?.requirements.map((item) => <div key={item}><ShieldCheck size={14} /><span>{item}</span></div>)}</div>
      <button className="command-action" onClick={() => posAsset && deluxePackage.mutate({ brandName: kit.name, catalog: posAsset.payload, taxRateBps, locationName, receiptFooter })} disabled={deluxePackage.isPending}>{deluxePackage.isPending ? <Loader2 className="spin" size={15} /> : <Download size={15} />}{deluxePackage.isPending ? "Packaging..." : "Export Deluxe catalog mapping"}</button>
      <small className="deluxe-note">Use this package for catalog/onboarding review. Payment capture must be configured with the approved Deluxe Hosted Payment Form or native Mobile POS SDK.</small>
      </article>
    </div>}
    {posAsset && <div className="pos-ledger"><div><span><History size={14} /> QUOTE LEDGER</span><p>Quotes are operational records only; they do not represent card authorization, settlement, or payment completion.</p></div><div className="ledger-list">{quoteHistory.isLoading ? <span className="ledger-loading"><Loader2 className="spin" size={13} /> Loading quote history...</span> : (quoteHistory.data as TicketHistoryItem[] | undefined)?.length ? (quoteHistory.data as TicketHistoryItem[]).slice(0, 4).map((row) => <div key={row.id}><span><b>{row.ticketNumber}</b><small>{new Date(row.createdAt).toLocaleDateString()}</small></span><em>{cents(row.totalCents)}</em><i>{row.status.toUpperCase()}</i></div>) : <span className="ledger-empty">No saved quotes yet. Create a payment-ready quote to begin the operational history.</span>}</div></div>}
  </section>;
}
