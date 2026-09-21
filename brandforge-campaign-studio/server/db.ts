import { and, asc, desc, eq, gte, like, lte } from "drizzle-orm";
import { drizzle } from "drizzle-orm/mysql2";
import {
  assetVersions,
  appointments,
  assets,
  brandKits,
  InsertUser,
  nicheOptions,
  posTickets,
  projects,
  technicians,
  technicianAvailability,
  users,
} from "../drizzle/schema";
import { assessAppointmentAvailability, appointmentEnd, technicianInitials, validateAvailabilityWindow, type AvailabilityWindow } from "./scheduling";

let _db: ReturnType<typeof drizzle> | null = null;

export async function getDb() {
  if (!_db && process.env.DATABASE_URL) {
    try {
      _db = drizzle(process.env.DATABASE_URL);
    } catch (error) {
      console.warn("[Database] connection unavailable", error);
      _db = null;
    }
  }
  return _db;
}

export async function upsertUser(user: InsertUser): Promise<void> {
  if (!user.openId) throw new Error("User openId is required for upsert");
  const db = await getDb();
  if (!db) return;
  const values: InsertUser = { openId: user.openId, lastSignedIn: user.lastSignedIn ?? new Date() };
  const updateSet: Record<string, unknown> = { lastSignedIn: new Date() };
  (["name", "email", "loginMethod", "role"] as const).forEach((field) => {
    if (user[field] !== undefined) {
      values[field] = user[field] as never;
      updateSet[field] = user[field] as never;
    }
  });
  await db.insert(users).values(values).onDuplicateKeyUpdate({ set: updateSet });
}

export async function getUserByOpenId(openId: string) {
  const db = await getDb();
  if (!db) return undefined;
  const result = await db.select().from(users).where(eq(users.openId, openId)).limit(1);
  return result[0];
}

export async function createProject(input: {
  userId?: number;
  niche: string;
  market: string;
  budget?: string;
  audience?: string;
  tone?: string;
}) {
  const db = await getDb();
  if (!db) return null;
  const result = await db.insert(projects).values({
    userId: input.userId ?? null,
    name: `${input.niche} — ${input.market}`,
    niche: input.niche,
    market: input.market,
    budget: input.budget ?? null,
    audience: input.audience ?? null,
    tone: input.tone ?? null,
  });
  return result[0].insertId;
}

export async function saveNicheOptions(projectId: number, options: Array<Record<string, unknown>>) {
  const db = await getDb();
  if (!db) return;
  await db.insert(nicheOptions).values(options.map((option, index) => ({
    projectId,
    optionNumber: Number(option.id) || index + 1,
    positioning: String(option.positioning ?? ""),
    targetCustomer: String(option.target_customer ?? ""),
    coreOffer: String(option.core_offer ?? ""),
    payload: option,
  })));
}

export async function lockBrandKit(input: {
  projectId: number;
  strategyOptionId?: number;
  name: string;
  palette: string[];
  fonts: { heading: string; body: string };
  voice: string;
  tagline: string;
  offer: string;
}) {
  const db = await getDb();
  if (!db) return null;
  const result = await db.insert(brandKits).values(input);
  await db.update(projects).set({ status: "brand_locked" }).where(eq(projects.id, input.projectId));
  return result[0].insertId;
}

export async function saveAsset(input: {
  brandKitId: number;
  type: "deck" | "website" | "email" | "pos" | "logo" | "visual" | "voice" | "finance" | "video" | "animation" | "social";
  variant: number;
  provider: string;
  payload: Record<string, unknown>;
  previewUrl?: string;
}) {
  const db = await getDb();
  if (!db) return null;
  const result = await db.insert(assets).values({
    brandKitId: input.brandKitId,
    type: input.type,
    variant: input.variant,
    provider: input.provider,
    status: "ready",
    payload: input.payload,
    previewUrl: input.previewUrl ?? null,
  });
  const assetId = result[0].insertId;
  await db.insert(assetVersions).values({ assetId, version: 1, note: "Initial generation", payload: input.payload });
  return assetId;
}

export async function listBrandAssets(brandKitId: number) {
  const db = await getDb();
  if (!db) return [];
  return db.select().from(assets).where(eq(assets.brandKitId, brandKitId)).orderBy(desc(assets.updatedAt));
}

export async function savePosTicket(input: {
  brandKitId: number;
  ticketNumber: string;
  currency: string;
  subtotalCents: number;
  taxCents: number;
  tipCents: number;
  totalCents: number;
  payload: Record<string, unknown>;
}) {
  const db = await getDb();
  if (!db) return null;
  const result = await db.insert(posTickets).values({
    brandKitId: input.brandKitId,
    ticketNumber: input.ticketNumber,
    currency: input.currency,
    subtotalCents: input.subtotalCents,
    taxCents: input.taxCents,
    tipCents: input.tipCents,
    totalCents: input.totalCents,
    payload: input.payload,
  });
  return result[0].insertId;
}

export async function listPosTickets(input: { brandKitId: number; search?: string; status?: "quote" | "exported" | "void"; from?: string; to?: string; limit?: number }) {
  const db = await getDb();
  if (!db) return [];
  const filters = [eq(posTickets.brandKitId, input.brandKitId)];
  const search = input.search?.trim();
  if (search) filters.push(like(posTickets.ticketNumber, `%${search}%`));
  if (input.status) filters.push(eq(posTickets.status, input.status));
  if (input.from) filters.push(gte(posTickets.createdAt, new Date(`${input.from}T00:00:00.000Z`)));
  if (input.to) filters.push(lte(posTickets.createdAt, new Date(`${input.to}T23:59:59.999Z`)));
  return db.select().from(posTickets).where(and(...filters)).orderBy(desc(posTickets.createdAt)).limit(Math.min(input.limit ?? 50, 100));
}

export async function createTechnician(input: { brandKitId: number; name: string; role?: string; color?: string }) {
  const db = await getDb();
  if (!db) return null;
  const name = input.name.trim();
  const result = await db.insert(technicians).values({
    brandKitId: input.brandKitId,
    name,
    role: input.role?.trim() || "Service technician",
    initials: technicianInitials(name),
    color: input.color ?? "#ddff51",
  });
  return result[0].insertId;
}

export async function listTechnicians(brandKitId: number) {
  const db = await getDb();
  if (!db) return [];
  return db.select().from(technicians).where(eq(technicians.brandKitId, brandKitId)).orderBy(asc(technicians.name)).limit(50);
}

export async function listTechnicianAvailability(brandKitId: number) {
  const db = await getDb();
  if (!db) return [];
  return db.select().from(technicianAvailability).where(eq(technicianAvailability.brandKitId, brandKitId)).orderBy(asc(technicianAvailability.technicianId), asc(technicianAvailability.weekday), asc(technicianAvailability.startMinutes)).limit(200);
}

export async function replaceTechnicianAvailability(input: { brandKitId: number; technicianId: number; windows: AvailabilityWindow[] }) {
  const db = await getDb();
  if (!db) return;
  if (!input.windows.length || input.windows.length > 14) throw new Error("Set between one and fourteen recurring availability windows.");
  const windows = input.windows.map(validateAvailabilityWindow);
  await db.transaction(async (tx) => {
    const technician = await tx.select({ id: technicians.id }).from(technicians).where(and(eq(technicians.id, input.technicianId), eq(technicians.brandKitId, input.brandKitId), eq(technicians.status, "active"))).for("update").limit(1);
    if (!technician[0]) throw new Error("Select an active technician from this brand kit.");
    await tx.delete(technicianAvailability).where(and(eq(technicianAvailability.brandKitId, input.brandKitId), eq(technicianAvailability.technicianId, input.technicianId)));
    await tx.insert(technicianAvailability).values(windows.map((window) => ({ brandKitId: input.brandKitId, technicianId: input.technicianId, ...window })));
  });
}

export async function checkAppointmentAvailability(input: { brandKitId: number; technicianId: number; startsAt: Date; durationMinutes: number }) {
  const db = await getDb();
  if (!db) return { available: false, reason: "Scheduling storage is unavailable. Try again shortly." };
  const [windows, existing] = await Promise.all([
    db.select().from(technicianAvailability).where(and(eq(technicianAvailability.brandKitId, input.brandKitId), eq(technicianAvailability.technicianId, input.technicianId))).limit(14),
    db.select({ id: appointments.id, startsAt: appointments.startsAt, durationMinutes: appointments.durationMinutes, status: appointments.status }).from(appointments).where(and(eq(appointments.brandKitId, input.brandKitId), eq(appointments.technicianId, input.technicianId))).limit(100),
  ]);
  return assessAppointmentAvailability({ startsAt: input.startsAt, durationMinutes: input.durationMinutes, windows, appointments: existing });
}

export async function createAppointment(input: { brandKitId: number; ticketId: number; technicianId: number; startsAt: Date; durationMinutes: number; notes?: string }) {
  const db = await getDb();
  if (!db) return null;
  appointmentEnd(input.startsAt, input.durationMinutes);
  return db.transaction(async (tx) => {
    const technician = await tx.select({ id: technicians.id }).from(technicians).where(and(eq(technicians.id, input.technicianId), eq(technicians.brandKitId, input.brandKitId), eq(technicians.status, "active"))).for("update").limit(1);
    const ticket = await tx.select({ id: posTickets.id }).from(posTickets).where(and(eq(posTickets.id, input.ticketId), eq(posTickets.brandKitId, input.brandKitId))).limit(1);
    if (!ticket[0] || !technician[0]) throw new Error("Select an active technician and a saved quote from this brand kit.");
    const [windows, existing] = await Promise.all([
      tx.select().from(technicianAvailability).where(and(eq(technicianAvailability.brandKitId, input.brandKitId), eq(technicianAvailability.technicianId, input.technicianId))).limit(14),
      tx.select({ id: appointments.id, startsAt: appointments.startsAt, durationMinutes: appointments.durationMinutes, status: appointments.status }).from(appointments).where(and(eq(appointments.brandKitId, input.brandKitId), eq(appointments.technicianId, input.technicianId))).limit(100),
    ]);
    const availability = assessAppointmentAvailability({ startsAt: input.startsAt, durationMinutes: input.durationMinutes, windows, appointments: existing });
    if (!availability.available) throw new Error(availability.reason);
    const result = await tx.insert(appointments).values({
      brandKitId: input.brandKitId,
      ticketId: input.ticketId,
      technicianId: input.technicianId,
      startsAt: input.startsAt,
      durationMinutes: input.durationMinutes,
      notes: input.notes?.trim() || null,
    });
    return result[0].insertId;
  });
}

export async function listAppointments(brandKitId: number) {
  const db = await getDb();
  if (!db) return [];
  return db.select({
    id: appointments.id,
    ticketId: appointments.ticketId,
    ticketNumber: posTickets.ticketNumber,
    totalCents: posTickets.totalCents,
    technicianId: appointments.technicianId,
    technicianName: technicians.name,
    technicianInitials: technicians.initials,
    technicianColor: technicians.color,
    startsAt: appointments.startsAt,
    durationMinutes: appointments.durationMinutes,
    status: appointments.status,
    notes: appointments.notes,
  }).from(appointments).innerJoin(posTickets, eq(appointments.ticketId, posTickets.id)).innerJoin(technicians, eq(appointments.technicianId, technicians.id)).where(eq(appointments.brandKitId, brandKitId)).orderBy(asc(appointments.startsAt)).limit(20);
}

export async function updateAppointmentStatus(input: { appointmentId: number; brandKitId: number; status: "scheduled" | "confirmed" | "completed" | "cancelled" }) {
  const db = await getDb();
  if (!db) return;
  await db.update(appointments).set({ status: input.status }).where(and(eq(appointments.id, input.appointmentId), eq(appointments.brandKitId, input.brandKitId)));
}
