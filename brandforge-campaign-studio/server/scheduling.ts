export const appointmentStatuses = ["scheduled", "confirmed", "completed", "cancelled"] as const;
export type AppointmentStatus = (typeof appointmentStatuses)[number];

export function appointmentEnd(startsAt: Date, durationMinutes: number): Date {
  if (Number.isNaN(startsAt.getTime())) throw new Error("A valid appointment start time is required.");
  if (!Number.isInteger(durationMinutes) || durationMinutes < 15 || durationMinutes > 720) {
    throw new Error("Appointment duration must be between 15 minutes and 12 hours.");
  }
  return new Date(startsAt.getTime() + durationMinutes * 60_000);
}

export function technicianInitials(name: string): string {
  const initials = name.trim().split(/\s+/).filter(Boolean).slice(0, 2).map((part) => part[0]?.toUpperCase() ?? "").join("");
  return initials || "TM";
}

export function appointmentWindow(startsAt: Date, durationMinutes: number): { startsAt: Date; endsAt: Date } {
  return { startsAt, endsAt: appointmentEnd(startsAt, durationMinutes) };
}
