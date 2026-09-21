import { useMemo, useState } from "react";
import { CalendarRange, CheckCircle2, Clock3, Loader2, ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import { trpc } from "@/lib/trpc";

type Technician = { id: number; name: string; role: string; initials: string; color: string; status: "active" | "inactive" };
type AvailabilityRecord = { id: number; technicianId: number; weekday: number; startMinutes: number; endMinutes: number; timeZone: string };

const days = [{ id: 0, label: "S" }, { id: 1, label: "M" }, { id: 2, label: "T" }, { id: 3, label: "W" }, { id: 4, label: "T" }, { id: 5, label: "F" }, { id: 6, label: "S" }];
const dayNames = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
const clockToMinutes = (value: string) => { const [hours, minutes] = value.split(":").map(Number); return hours * 60 + minutes; };
const minutesToClock = (value: number) => `${String(Math.floor(value / 60)).padStart(2, "0")}:${String(value % 60).padStart(2, "0")}`;
const formatClock = (value: number) => new Intl.DateTimeFormat("en-US", { hour: "numeric", minute: "2-digit" }).format(new Date(Date.UTC(2026, 0, 1, 0, value)));

export default function TechnicianAvailabilityEditor({ brandKitId, technicians, onAvailabilitySaved }: { brandKitId: number; technicians: Technician[]; onAvailabilitySaved: () => void }) {
  const activeTechnicians = technicians.filter((technician) => technician.status === "active");
  const [technicianId, setTechnicianId] = useState(0);
  const [selectedDays, setSelectedDays] = useState<number[]>([1, 2, 3, 4, 5]);
  const [startTime, setStartTime] = useState("08:00");
  const [endTime, setEndTime] = useState("17:00");
  const [timeZone, setTimeZone] = useState("America/Chicago");
  const utils = trpc.useUtils();
  const availability = trpc.studio.pos.listTechnicianAvailability.useQuery({ brandKitId }, { enabled: Boolean(brandKitId) });
  const saveAvailability = trpc.studio.pos.setTechnicianAvailability.useMutation({
    onSuccess: () => { void utils.studio.pos.listTechnicianAvailability.invalidate(); onAvailabilitySaved(); toast.success("Recurring technician availability saved."); },
    onError: (error) => toast.error(error.message || "Availability could not be saved."),
  });
  const records = (availability.data ?? []) as AvailabilityRecord[];
  const selectedTechnician = useMemo(() => activeTechnicians.find((technician) => technician.id === technicianId), [activeTechnicians, technicianId]);
  const windowsForSelection = useMemo(() => records.filter((record) => record.technicianId === technicianId), [records, technicianId]);
  const toggleDay = (day: number) => setSelectedDays((current) => current.includes(day) ? current.filter((item) => item !== day) : [...current, day].sort((a, b) => a - b));
  const save = () => {
    if (!technicianId || !selectedDays.length) return;
    const startMinutes = clockToMinutes(startTime); const endMinutes = clockToMinutes(endTime);
    if (startMinutes >= endMinutes) { toast.error("Availability end time must be after the start time."); return; }
    saveAvailability.mutate({ brandKitId, technicianId, windows: selectedDays.map((weekday) => ({ weekday, startMinutes, endMinutes, timeZone })) });
  };

  return <article className="availability-panel">
    <header><div><span><ShieldCheck size={14} /> AVAILABILITY GUARDRAILS</span><h3>Recurring working windows</h3></div><CalendarRange size={20} /></header>
    <p>Set the local hours a technician can be assigned. The server will reject requests outside these windows and prevent overlapping active appointments.</p>
    <div className="availability-editor">
      <label><span>TECHNICIAN</span><select value={technicianId ? String(technicianId) : "none"} onChange={(event) => setTechnicianId(event.target.value === "none" ? 0 : Number(event.target.value))}><option value="none">Choose an active technician</option>{activeTechnicians.map((technician) => <option key={technician.id} value={String(technician.id)}>{technician.name} · {technician.role}</option>)}</select></label>
      <label><span>TIME ZONE</span><select value={timeZone} onChange={(event) => setTimeZone(event.target.value)}><option value="America/Chicago">Central Time</option><option value="America/New_York">Eastern Time</option><option value="America/Denver">Mountain Time</option><option value="America/Los_Angeles">Pacific Time</option></select></label>
      <div className="availability-days"><span>REPEAT ON</span><div>{days.map((day) => <button key={day.id} className={selectedDays.includes(day.id) ? "selected" : ""} onClick={() => toggleDay(day.id)} title={dayNames[day.id]}>{day.label}</button>)}</div></div>
      <div className="availability-times"><label><span>START</span><input type="time" value={startTime} onChange={(event) => setStartTime(event.target.value)} /></label><label><span>END</span><input type="time" value={endTime} onChange={(event) => setEndTime(event.target.value)} /></label></div>
      <button className="command-action" onClick={save} disabled={!selectedTechnician || !selectedDays.length || saveAvailability.isPending}>{saveAvailability.isPending ? <Loader2 className="spin" size={15} /> : <CheckCircle2 size={15} />}{saveAvailability.isPending ? "Saving..." : "Save recurring availability"}</button>
    </div>
    <div className="availability-summary">{availability.isLoading ? <div className="schedule-loading"><Loader2 className="spin" size={14} /> Loading availability...</div> : selectedTechnician ? windowsForSelection.length ? <><b>{selectedTechnician.name}'s current coverage</b>{windowsForSelection.map((window) => <span key={window.id}><Clock3 size={12} />{dayNames[window.weekday]} · {formatClock(window.startMinutes)}–{formatClock(window.endMinutes)} · {window.timeZone.replace("America/", "")}</span>)}</> : <div className="schedule-empty">No coverage saved for {selectedTechnician.name}. Save a window before attempting an appointment.</div> : <div className="schedule-empty">Choose a technician to review or set their working window.</div>}</div>
  </article>;
}
