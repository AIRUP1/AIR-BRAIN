import { describe, expect, it } from "vitest";
import { assessAppointmentAvailability, appointmentEnd, appointmentWindow, technicianInitials, validateAvailabilityWindow, windowsOverlap } from "./scheduling";

const centralWeekday = { weekday: 1, startMinutes: 8 * 60, endMinutes: 17 * 60, timeZone: "America/Chicago" };

describe("appointment scheduling service", () => {
  it("calculates a bounded appointment window", () => {
    const start = new Date("2026-09-21T14:00:00.000Z");
    expect(appointmentEnd(start, 90).toISOString()).toBe("2026-09-21T15:30:00.000Z");
    expect(appointmentWindow(start, 90).endsAt.toISOString()).toBe("2026-09-21T15:30:00.000Z");
  });

  it("rejects unsafe scheduling durations and invalid availability windows", () => {
    expect(() => appointmentEnd(new Date("2026-09-21T14:00:00.000Z"), 10)).toThrow("between 15 minutes and 12 hours");
    expect(() => appointmentEnd(new Date("invalid"), 60)).toThrow("valid appointment start time");
    expect(() => validateAvailabilityWindow({ ...centralWeekday, endMinutes: 480 })).toThrow("valid start and end time");
    expect(() => validateAvailabilityWindow({ ...centralWeekday, timeZone: "Mars/Olympus" })).toThrow("valid IANA time zone");
  });

  it("detects a collision with a scheduled or confirmed appointment", () => {
    const start = new Date("2026-09-21T14:00:00.000Z");
    expect(windowsOverlap(start, appointmentEnd(start, 120), new Date("2026-09-21T15:00:00.000Z"), new Date("2026-09-21T16:00:00.000Z"))).toBe(true);
    const result = assessAppointmentAvailability({ startsAt: start, durationMinutes: 120, windows: [{ weekday: 1, startMinutes: 8 * 60, endMinutes: 17 * 60, timeZone: "UTC" }], appointments: [{ id: 42, startsAt: new Date("2026-09-21T15:00:00.000Z"), durationMinutes: 60, status: "confirmed" }] });
    expect(result).toMatchObject({ available: false, conflictAppointmentId: 42 });
  });

  it("accepts an open window and ignores completed appointments", () => {
    const result = assessAppointmentAvailability({ startsAt: new Date("2026-09-21T14:00:00.000Z"), durationMinutes: 60, windows: [{ weekday: 1, startMinutes: 8 * 60, endMinutes: 17 * 60, timeZone: "UTC" }], appointments: [{ id: 1, startsAt: new Date("2026-09-21T14:00:00.000Z"), durationMinutes: 60, status: "completed" }] });
    expect(result).toEqual({ available: true, reason: "Technician is available for this service window." });
  });

  it("derives concise technician initials", () => {
    expect(technicianInitials("Taylor Morgan")).toBe("TM");
    expect(technicianInitials("Avery")).toBe("A");
  });
});
