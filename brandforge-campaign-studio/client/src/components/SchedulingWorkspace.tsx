import { useMemo, useState } from "react";
import { CalendarClock, CheckCircle2, Clock3, FilterX, Loader2, Plus, Search, UserRoundPlus, UsersRound } from "lucide-react";
import { toast } from "sonner";
import { trpc } from "@/lib/trpc";

type Kit = { name: string };
type TicketRow = { id: number; ticketNumber: string; totalCents: number; status: "quote" | "exported" | "void"; createdAt: Date | string };
type Technician = { id: number; name: string; role: string; initials: string; color: string; status: "active" | "inactive" };
type Appointment = { id: number; ticketId: number; ticketNumber: string; totalCents: number; technicianId: number; technicianName: string; technicianInitials: string; technicianColor: string; startsAt: Date | string; durationMinutes: number; status: "scheduled" | "confirmed" | "completed" | "cancelled"; notes: string | null };

const formatMoney = (cents: number) => new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(cents / 100);
const formatDateTime = (value: Date | string) => new Date(value).toLocaleString([], { dateStyle: "medium", timeStyle: "short" });
const localDateTime = (value: Date) => { const shifted = new Date(value.getTime() - value.getTimezoneOffset() * 60_000); return shifted.toISOString().slice(0, 16); };

export default function SchedulingWorkspace({ kit, brandKitId }: { kit: Kit; brandKitId: number }) {
  const [technicianName, setTechnicianName] = useState("");
  const [technicianRole, setTechnicianRole] = useState("Service technician");
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [selectedTicketId, setSelectedTicketId] = useState(0);
  const [selectedTechnicianId, setSelectedTechnicianId] = useState(0);
  const [startsAt, setStartsAt] = useState(() => localDateTime(new Date(Date.now() + 86_400_000)));
  const [durationMinutes, setDurationMinutes] = useState(120);
  const [notes, setNotes] = useState("");
  const utils = trpc.useUtils();
  const technicians = trpc.studio.pos.listTechnicians.useQuery({ brandKitId }, { enabled: Boolean(brandKitId) });
  const ledger = trpc.studio.pos.listTickets.useQuery({ brandKitId, search: search || undefined, status: statusFilter === "all" ? undefined : statusFilter as "quote" | "exported" | "void", from: from || undefined, to: to || undefined, limit: 100 }, { enabled: Boolean(brandKitId) });
  const appointments = trpc.studio.pos.listAppointments.useQuery({ brandKitId }, { enabled: Boolean(brandKitId) });
  const addTechnician = trpc.studio.pos.addTechnician.useMutation({
    onSuccess: () => { setTechnicianName(""); setTechnicianRole("Service technician"); void utils.studio.pos.listTechnicians.invalidate(); toast.success("Technician added to the assignment roster."); },
    onError: () => toast.error("Technician could not be added."),
  });
  const createAppointment = trpc.studio.pos.createAppointment.useMutation({
    onSuccess: () => { setNotes(""); setSelectedTicketId(0); void utils.studio.pos.listAppointments.invalidate(); toast.success("Appointment scheduled and technician assigned."); },
    onError: (error) => toast.error(error.message || "Appointment could not be scheduled."),
  });
  const updateAppointment = trpc.studio.pos.updateAppointmentStatus.useMutation({
    onSuccess: () => { void utils.studio.pos.listAppointments.invalidate(); toast.success("Appointment status updated."); },
    onError: () => toast.error("Appointment status could not be updated."),
  });
  const ticketRows = (ledger.data ?? []) as TicketRow[];
  const technicianRows = (technicians.data ?? []) as Technician[];
  const appointmentRows = (appointments.data ?? []) as Appointment[];
  const selectedTicket = useMemo(() => ticketRows.find((ticket) => ticket.id === selectedTicketId), [ticketRows, selectedTicketId]);
  const selectedTechnician = useMemo(() => technicianRows.find((technician) => technician.id === selectedTechnicianId), [technicianRows, selectedTechnicianId]);
  const canSchedule = Boolean(selectedTicket && selectedTechnician && startsAt && brandKitId);
  const resetFilters = () => { setSearch(""); setStatusFilter("all"); setFrom(""); setTo(""); };
  const schedule = () => {
    if (!canSchedule || !selectedTicket || !selectedTechnician) return;
    createAppointment.mutate({ brandKitId, ticketId: selectedTicket.id, technicianId: selectedTechnician.id, startsAt: new Date(startsAt).toISOString(), durationMinutes, notes: notes || undefined });
  };

  if (!brandKitId) return <section className="schedule-command section-card"><div className="section-kicker compact"><span>06</span><div><small>SERVICE OPS / SCHEDULING</small><h2>Route a signed-off quote to the right technician.</h2></div><div className="line" /><p>Build a brand-specific team roster, search historical quotes, and turn a quote into an accountable service appointment.</p></div><div className="schedule-empty schedule-lock-empty"><CalendarClock size={20} />Lock the Brand Kit first to activate technician assignments, quote search, and service scheduling.</div></section>;

  return <section className="schedule-command section-card">
    <div className="section-kicker compact"><span>06</span><div><small>SERVICE OPS / SCHEDULING</small><h2>Route a signed-off quote to the right technician.</h2></div><div className="line" /><p>Build a brand-specific team roster, search historical quotes, and turn a quote into an accountable service appointment.</p></div>
    <div className="schedule-grid">
      <article className="schedule-panel roster-panel"><header><div><span>01 / TEAM ROSTER</span><h3>Technician assignments</h3></div><UsersRound size={20} /></header><p>Add the people who can be assigned to service appointments for {kit.name}.</p>
        <div className="technician-form"><label><span>TECHNICIAN NAME</span><input value={technicianName} onChange={(event) => setTechnicianName(event.target.value)} placeholder="e.g. Taylor Morgan" /></label><label><span>ROLE</span><input value={technicianRole} onChange={(event) => setTechnicianRole(event.target.value)} placeholder="Service technician" /></label><button className="command-action" onClick={() => addTechnician.mutate({ brandKitId, name: technicianName, role: technicianRole })} disabled={technicianName.trim().length < 2 || addTechnician.isPending}>{addTechnician.isPending ? <Loader2 className="spin" size={15} /> : <UserRoundPlus size={15} />}{addTechnician.isPending ? "Adding..." : "Add technician"}</button></div>
        <div className="technician-list">{technicians.isLoading ? <div className="schedule-loading"><Loader2 className="spin" size={14} /> Loading roster...</div> : technicianRows.length ? technicianRows.map((technician) => <div key={technician.id} className="technician-row"><span className="avatar" style={{ backgroundColor: technician.color, color: "#101410" }}>{technician.initials}</span><div><b>{technician.name}</b><small>{technician.role}</small></div><i>{technician.status}</i></div>) : <div className="schedule-empty">No technicians yet. Add a team member to unlock quote assignment.</div>}</div>
      </article>
      <article className="schedule-panel appointment-panel"><header><div><span>02 / APPOINTMENT ROUTING</span><h3>Assign service work</h3></div><CalendarClock size={20} /></header><p>Choose a saved quote, select an active technician, and set a service window. This is operational scheduling—not payment capture.</p>
        <div className="schedule-selects"><label><span>SELECTED QUOTE</span><select value={selectedTicketId ? String(selectedTicketId) : "none"} onChange={(event) => setSelectedTicketId(event.target.value === "none" ? 0 : Number(event.target.value))}><option value="none">Choose a quote from search results</option>{ticketRows.map((ticket) => <option key={ticket.id} value={String(ticket.id)}>{ticket.ticketNumber} · {formatMoney(ticket.totalCents)}</option>)}</select></label><label><span>ASSIGNED TECHNICIAN</span><select value={selectedTechnicianId ? String(selectedTechnicianId) : "none"} onChange={(event) => setSelectedTechnicianId(event.target.value === "none" ? 0 : Number(event.target.value))}><option value="none">Choose an active technician</option>{technicianRows.filter((technician) => technician.status === "active").map((technician) => <option key={technician.id} value={String(technician.id)}>{technician.name} · {technician.role}</option>)}</select></label></div>
        <div className="schedule-selects"><label><span>SERVICE START</span><input type="datetime-local" value={startsAt} onChange={(event) => setStartsAt(event.target.value)} /></label><label><span>DURATION</span><select value={String(durationMinutes)} onChange={(event) => setDurationMinutes(Number(event.target.value))}><option value="60">60 minutes</option><option value="90">90 minutes</option><option value="120">2 hours</option><option value="180">3 hours</option><option value="240">4 hours</option></select></label></div>
        <label className="schedule-notes"><span>ASSIGNMENT NOTES</span><textarea value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="Access instructions, vehicle notes, or service context." maxLength={500} /></label>
        <div className="schedule-confirmation"><span><Clock3 size={14} />{startsAt ? formatDateTime(new Date(startsAt)) : "Choose a start time"}</span><b>{selectedTechnician ? `${selectedTechnician.name} will own the appointment.` : "Choose a technician to continue."}</b></div>
        <button className="command-action" onClick={schedule} disabled={!canSchedule || createAppointment.isPending}>{createAppointment.isPending ? <Loader2 className="spin" size={15} /> : <CheckCircle2 size={15} />}{createAppointment.isPending ? "Scheduling..." : "Schedule selected quote"}</button>
      </article>
    </div>
    <article className="schedule-ledger"><header><div><span><Search size={14} /> QUOTE LEDGER / SEARCH + FILTER</span><h3>Find a past quote, then schedule it.</h3></div><button onClick={resetFilters}><FilterX size={13} /> Clear filters</button></header><div className="ledger-filters"><label><span>QUOTE NUMBER</span><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search BF-..." /></label><label><span>STATUS</span><select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}><option value="all">All statuses</option><option value="quote">Quote</option><option value="exported">Exported</option><option value="void">Void</option></select></label><label><span>FROM</span><input type="date" value={from} onChange={(event) => setFrom(event.target.value)} /></label><label><span>TO</span><input type="date" value={to} onChange={(event) => setTo(event.target.value)} /></label></div>
      <div className="search-results">{ledger.isLoading ? <div className="schedule-loading"><Loader2 className="spin" size={14} /> Searching the quote ledger...</div> : ticketRows.length ? ticketRows.map((ticket) => <button key={ticket.id} className={selectedTicketId === ticket.id ? "ledger-ticket selected" : "ledger-ticket"} onClick={() => setSelectedTicketId(ticket.id)}><span><b>{ticket.ticketNumber}</b><small>{formatDateTime(ticket.createdAt)}</small></span><em>{formatMoney(ticket.totalCents)}</em><i>{ticket.status}</i></button>) : <div className="schedule-empty">No saved quotes match these filters. Clear the filters or create a new quote in the register.</div>}</div>
    </article>
    <article className="appointments-board"><header><div><span><CalendarClock size={14} /> UPCOMING SERVICE BOARD</span><h3>Appointments by technician</h3></div><small>{appointmentRows.length} scheduled record{appointmentRows.length === 1 ? "" : "s"}</small></header><div className="appointment-list">{appointments.isLoading ? <div className="schedule-loading"><Loader2 className="spin" size={14} /> Loading appointments...</div> : appointmentRows.length ? appointmentRows.map((appointment) => <div className="appointment-row" key={appointment.id}><span className="avatar" style={{ backgroundColor: appointment.technicianColor, color: "#101410" }}>{appointment.technicianInitials}</span><div><b>{appointment.ticketNumber} · {formatMoney(appointment.totalCents)}</b><small>{appointment.technicianName} · {formatDateTime(appointment.startsAt)} · {appointment.durationMinutes} min</small>{appointment.notes && <p>{appointment.notes}</p>}</div><select value={appointment.status} onChange={(event) => updateAppointment.mutate({ appointmentId: appointment.id, brandKitId, status: event.target.value as Appointment["status"] })} disabled={updateAppointment.isPending}><option value="scheduled">Scheduled</option><option value="confirmed">Confirmed</option><option value="completed">Completed</option><option value="cancelled">Cancelled</option></select></div>) : <div className="schedule-empty">No appointments have been scheduled yet. Select a quote and technician above to create the first assignment.</div>}</div>
    </article>
  </section>;
}
