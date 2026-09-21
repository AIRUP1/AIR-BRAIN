import { describe, expect, it } from "vitest";
import { appointmentEnd, appointmentWindow, technicianInitials } from "./scheduling";

describe("appointment scheduling service", () => {
  it("calculates a bounded appointment window", () => {
    const start = new Date("2026-09-21T14:00:00.000Z");
    expect(appointmentEnd(start, 90).toISOString()).toBe("2026-09-21T15:30:00.000Z");
    expect(appointmentWindow(start, 90).endsAt.toISOString()).toBe("2026-09-21T15:30:00.000Z");
  });

  it("rejects unsafe scheduling durations", () => {
    expect(() => appointmentEnd(new Date("2026-09-21T14:00:00.000Z"), 10)).toThrow("between 15 minutes and 12 hours");
    expect(() => appointmentEnd(new Date("invalid"), 60)).toThrow("valid appointment start time");
  });

  it("derives concise technician initials", () => {
    expect(technicianInitials("Taylor Morgan")).toBe("TM");
    expect(technicianInitials("Avery")).toBe("A");
  });
});
