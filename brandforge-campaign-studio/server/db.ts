import { desc, eq } from "drizzle-orm";
import { drizzle } from "drizzle-orm/mysql2";
import {
  assetVersions,
  assets,
  brandKits,
  InsertUser,
  nicheOptions,
  projects,
  users,
} from "../drizzle/schema";

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
