import { int, json, mysqlEnum, mysqlTable, text, timestamp, varchar } from "drizzle-orm/mysql-core";

/** Core identity table supplied by the web app template. */
export const users = mysqlTable("users", {
  id: int("id").autoincrement().primaryKey(),
  openId: varchar("openId", { length: 64 }).notNull().unique(),
  name: text("name"),
  email: varchar("email", { length: 320 }),
  loginMethod: varchar("loginMethod", { length: 64 }),
  role: mysqlEnum("role", ["user", "admin"]).default("user").notNull(),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
  lastSignedIn: timestamp("lastSignedIn").defaultNow().notNull(),
});

/** A single campaign workspace created from a niche intake. */
export const projects = mysqlTable("projects", {
  id: int("id").autoincrement().primaryKey(),
  userId: int("userId"),
  name: varchar("name", { length: 160 }).notNull(),
  niche: varchar("niche", { length: 240 }).notNull(),
  market: varchar("market", { length: 240 }).notNull(),
  budget: varchar("budget", { length: 80 }),
  audience: varchar("audience", { length: 320 }),
  tone: varchar("tone", { length: 120 }),
  status: mysqlEnum("status", ["draft", "brand_locked", "producing", "ready"]).default("draft").notNull(),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
});

/** The three strategic directions returned for every project. */
export const nicheOptions = mysqlTable("niche_options", {
  id: int("id").autoincrement().primaryKey(),
  projectId: int("projectId").notNull(),
  optionNumber: int("optionNumber").notNull(),
  positioning: text("positioning").notNull(),
  targetCustomer: text("targetCustomer").notNull(),
  coreOffer: text("coreOffer").notNull(),
  payload: json("payload").notNull(),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
});

/** Immutable brand system that each downstream asset must consume. */
export const brandKits = mysqlTable("brand_kits", {
  id: int("id").autoincrement().primaryKey(),
  projectId: int("projectId").notNull(),
  strategyOptionId: int("strategyOptionId"),
  name: varchar("name", { length: 160 }).notNull(),
  palette: json("palette").notNull(),
  fonts: json("fonts").notNull(),
  voice: text("voice").notNull(),
  tagline: text("tagline").notNull(),
  offer: text("offer").notNull(),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
});

/** Generated, structured content assets. Binary media is stored in object storage and referenced by URL. */
export const assets = mysqlTable("assets", {
  id: int("id").autoincrement().primaryKey(),
  brandKitId: int("brandKitId").notNull(),
  type: mysqlEnum("type", ["deck", "website", "email", "pos", "logo", "visual", "voice", "finance", "video", "animation", "social"]).notNull(),
  variant: int("variant").notNull(),
  schemaVersion: varchar("schemaVersion", { length: 32 }).notNull().default("1.0"),
  provider: varchar("provider", { length: 80 }).notNull().default("claude"),
  status: mysqlEnum("status", ["queued", "ready", "failed"]).default("queued").notNull(),
  payload: json("payload").notNull(),
  previewUrl: text("previewUrl"),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
});

/** Non-sensitive operational records for POS quotes. Payment credentials and card data are never stored here. */
export const posTickets = mysqlTable("pos_tickets", {
  id: int("id").autoincrement().primaryKey(),
  brandKitId: int("brandKitId").notNull(),
  ticketNumber: varchar("ticketNumber", { length: 64 }).notNull().unique(),
  status: mysqlEnum("status", ["quote", "exported", "void"]).default("quote").notNull(),
  currency: varchar("currency", { length: 8 }).notNull().default("USD"),
  subtotalCents: int("subtotalCents").notNull(),
  taxCents: int("taxCents").notNull(),
  tipCents: int("tipCents").notNull(),
  totalCents: int("totalCents").notNull(),
  payload: json("payload").notNull(),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
});

/** Brand-scoped service team members eligible for quote appointment assignments. */
export const technicians = mysqlTable("technicians", {
  id: int("id").autoincrement().primaryKey(),
  brandKitId: int("brandKitId").notNull(),
  name: varchar("name", { length: 160 }).notNull(),
  role: varchar("role", { length: 120 }).notNull().default("Service technician"),
  initials: varchar("initials", { length: 8 }).notNull(),
  color: varchar("color", { length: 16 }).notNull().default("#ddff51"),
  status: mysqlEnum("status", ["active", "inactive"]).default("active").notNull(),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
});

/** Scheduled operational work linked to a saved quote and an assigned technician. */
export const appointments = mysqlTable("appointments", {
  id: int("id").autoincrement().primaryKey(),
  brandKitId: int("brandKitId").notNull(),
  ticketId: int("ticketId").notNull(),
  technicianId: int("technicianId").notNull(),
  startsAt: timestamp("startsAt").notNull(),
  durationMinutes: int("durationMinutes").notNull(),
  status: mysqlEnum("status", ["scheduled", "confirmed", "completed", "cancelled"]).default("scheduled").notNull(),
  notes: varchar("notes", { length: 500 }),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
});

/** Append-only audit trail for edits and regenerated asset variants. */
export const assetVersions = mysqlTable("asset_versions", {
  id: int("id").autoincrement().primaryKey(),
  assetId: int("assetId").notNull(),
  version: int("version").notNull(),
  note: varchar("note", { length: 240 }),
  payload: json("payload").notNull(),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
});

export type User = typeof users.$inferSelect;
export type InsertUser = typeof users.$inferInsert;
export type Project = typeof projects.$inferSelect;
export type BrandKitRecord = typeof brandKits.$inferSelect;
export type AssetRecord = typeof assets.$inferSelect;
export type PosTicketRecord = typeof posTickets.$inferSelect;
export type TechnicianRecord = typeof technicians.$inferSelect;
export type AppointmentRecord = typeof appointments.$inferSelect;
