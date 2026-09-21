export const appointmentStatuses = ["scheduled", "confirmed", "completed", "cancelled"] as const;
export type AppointmentStatus = (typeof appointmentStatuses)[number];
export const busyAppointmentStatuses: AppointmentStatus[] = ["scheduled", "confirmed"];

export type AvailabilityWindow = { weekday: number; startMinutes: number; endMinutes: number; timeZone: string };
export type ExistingAppointment = { id: number; startsAt: Date; durationMinutes: number; status: AppointmentStatus };
export type AvailabilityAssessment = { available: boolean; reason: string; conflictAppointmentId?: number };

const weekdayLookup: Record<string, number> = { Sun: 0, Mon: 1, Tue: 2, Wed: 3, Thu: 4, Fri: 5, Sat: 6 };

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

export function validateAvailabilityWindow(window: AvailabilityWindow): AvailabilityWindow {
  if (!Number.isInteger(window.weekday) || window.weekday < 0 || window.weekday > 6) throw new Error("Availability weekday must be between Sunday and Saturday.");
  if (!Number.isInteger(window.startMinutes) || !Number.isInteger(window.endMinutes) || window.startMinutes < 0 || window.endMinutes > 1_440 || window.startMinutes >= window.endMinutes) {
    throw new Error("Availability window must have a valid start and end time.");
  }
  try { new Intl.DateTimeFormat("en-US", { timeZone: window.timeZone }).format(); } catch { throw new Error("Choose a valid IANA time zone for technician availability."); }
  return window;
}

function zonedTime(date: Date, timeZone: string): { weekday: number; minutes: number } {
  const parts = new Intl.DateTimeFormat("en-US", { timeZone, weekday: "short", hour: "2-digit", minute: "2-digit", hourCycle: "h23" }).formatToParts(date);
  const values = Object.fromEntries(parts.filter((part) => part.type !== "literal").map((part) => [part.type, part.value]));
  return { weekday: weekdayLookup[values.weekday] ?? -1, minutes: Number(values.hour) * 60 + Number(values.minute) };
}

export function windowsOverlap(firstStart: Date, firstEnd: Date, secondStart: Date, secondEnd: Date): boolean {
  return firstStart < secondEnd && secondStart < firstEnd;
}

export function assessAppointmentAvailability(input: { startsAt: Date; durationMinutes: number; windows: AvailabilityWindow[]; appointments: ExistingAppointment[] }): AvailabilityAssessment {
  const { startsAt, durationMinutes, windows, appointments } = input;
  const endsAt = appointmentEnd(startsAt, durationMinutes);
  if (!windows.length) return { available: false, reason: "Set a recurring availability window before scheduling this technician." };
  const isWithinWindow = windows.some((window) => {
    const validWindow = validateAvailabilityWindow(window);
    const start = zonedTime(startsAt, validWindow.timeZone);
    const end = zonedTime(endsAt, validWindow.timeZone);
    return start.weekday === validWindow.weekday && end.weekday === start.weekday && start.minutes >= validWindow.startMinutes && end.minutes <= validWindow.endMinutes;
  });
  if (!isWithinWindow) return { available: false, reason: "This appointment falls outside the technician's recurring availability." };
  const conflict = appointments.find((appointment) => busyAppointmentStatuses.includes(appointment.status) && windowsOverlap(startsAt, endsAt, appointment.startsAt, appointmentEnd(appointment.startsAt, appointment.durationMinutes)));
  if (conflict) return { available: false, reason: "This technician already has a scheduled or confirmed appointment in that time window.", conflictAppointmentId: conflict.id };
  return { available: true, reason: "Technician is available for this service window." };
}
