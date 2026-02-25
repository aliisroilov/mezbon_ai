import { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  CalendarDays,
  List,
  Search,
  ChevronLeft,
  ChevronRight,
  Filter,
} from "lucide-react";
import dayjs from "dayjs";
import clsx from "clsx";
import { appointmentsAPI, departmentsAPI, doctorsAPI } from "../../api/client";
import {
  Card,
  Button,
  Input,
  Badge,
  SlideOver,
  Select,
  LoadingSpinner,
} from "../../components/ui";
import type { Appointment, Department, Doctor, AppointmentStatus } from "../../types";

type ViewMode = "calendar" | "list";
type CalendarView = "day" | "week" | "month";

const STATUS_BADGES: Record<AppointmentStatus, { variant: "default" | "success" | "warning" | "danger" | "info"; label: string }> = {
  SCHEDULED: { variant: "info", label: "Scheduled" },
  CHECKED_IN: { variant: "warning", label: "Checked In" },
  IN_PROGRESS: { variant: "info", label: "In Progress" },
  COMPLETED: { variant: "success", label: "Completed" },
  CANCELLED: { variant: "danger", label: "Cancelled" },
  NO_SHOW: { variant: "default", label: "No Show" },
};

export function AppointmentsPage() {
  const queryClient = useQueryClient();
  const [viewMode, setViewMode] = useState<ViewMode>("list");
  const [calView, setCalView] = useState<CalendarView>("week");
  const [currentDate, setCurrentDate] = useState(dayjs());
  const [selectedAppt, setSelectedAppt] = useState<Appointment | null>(null);
  const [deptFilter, setDeptFilter] = useState("");
  const [doctorFilter, setDoctorFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [search, setSearch] = useState("");

  const dateFrom = calView === "day"
    ? currentDate.format("YYYY-MM-DD")
    : calView === "week"
      ? currentDate.startOf("week").format("YYYY-MM-DD")
      : currentDate.startOf("month").format("YYYY-MM-DD");

  const dateTo = calView === "day"
    ? currentDate.format("YYYY-MM-DD")
    : calView === "week"
      ? currentDate.endOf("week").format("YYYY-MM-DD")
      : currentDate.endOf("month").format("YYYY-MM-DD");

  const { data: appointmentsData, isLoading } = useQuery({
    queryKey: ["appointments", dateFrom, dateTo, deptFilter, doctorFilter, statusFilter],
    queryFn: () =>
      appointmentsAPI.list({
        date_from: dateFrom,
        date_to: dateTo,
        department_id: deptFilter || undefined,
        doctor_id: doctorFilter || undefined,
        status: statusFilter || undefined,
        limit: 200,
      }),
  });

  const appointments = appointmentsData?.data ?? [];

  const { data: departments } = useQuery<Department[]>({
    queryKey: ["departments"],
    queryFn: departmentsAPI.list,
  });

  const { data: doctors } = useQuery<Doctor[]>({
    queryKey: ["doctors-all"],
    queryFn: () => doctorsAPI.list(),
  });

  const statusMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: AppointmentStatus }) =>
      appointmentsAPI.updateStatus(id, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["appointments"] });
      setSelectedAppt(null);
    },
  });

  const filtered = useMemo(() => {
    if (!search) return appointments;
    const q = search.toLowerCase();
    return appointments.filter(
      (a) =>
        a.patient_name.toLowerCase().includes(q) ||
        a.doctor_name.toLowerCase().includes(q),
    );
  }, [appointments, search]);

  function navigateDate(dir: -1 | 1) {
    setCurrentDate((d) =>
      calView === "day"
        ? d.add(dir, "day")
        : calView === "week"
          ? d.add(dir, "week")
          : d.add(dir, "month"),
    );
  }

  // Calendar view helpers
  const calendarDays = useMemo(() => {
    if (calView === "day") return [currentDate];
    if (calView === "week") {
      const start = currentDate.startOf("week");
      return Array.from({ length: 7 }, (_, i) => start.add(i, "day"));
    }
    const start = currentDate.startOf("month").startOf("week");
    const end = currentDate.endOf("month").endOf("week");
    const days = [];
    let d = start;
    while (d.isBefore(end) || d.isSame(end, "day")) {
      days.push(d);
      d = d.add(1, "day");
    }
    return days;
  }, [currentDate, calView]);

  const hours = Array.from({ length: 12 }, (_, i) => i + 8); // 8:00 - 19:00

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-2xl font-bold text-slate-900">Appointments</h1>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setViewMode("calendar")}
            className={clsx(
              "rounded-lg p-2 transition-colors",
              viewMode === "calendar"
                ? "bg-primary-100 text-primary-700"
                : "text-slate-400 hover:bg-slate-100",
            )}
          >
            <CalendarDays className="h-4 w-4" />
          </button>
          <button
            onClick={() => setViewMode("list")}
            className={clsx(
              "rounded-lg p-2 transition-colors",
              viewMode === "list"
                ? "bg-primary-100 text-primary-700"
                : "text-slate-400 hover:bg-slate-100",
            )}
          >
            <List className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Filters */}
      <Card>
        <div className="flex flex-wrap items-center gap-3">
          <Filter className="h-4 w-4 text-slate-400" />
          <div className="w-40">
            <Select
              options={[
                { value: "", label: "All Departments" },
                ...(departments ?? []).map((d) => ({ value: d.id, label: d.name })),
              ]}
              value={deptFilter}
              onChange={(e) => setDeptFilter(e.target.value)}
            />
          </div>
          <div className="w-40">
            <Select
              options={[
                { value: "", label: "All Doctors" },
                ...(doctors ?? []).map((d) => ({ value: d.id, label: d.full_name })),
              ]}
              value={doctorFilter}
              onChange={(e) => setDoctorFilter(e.target.value)}
            />
          </div>
          <div className="w-36">
            <Select
              options={[
                { value: "", label: "All Status" },
                { value: "SCHEDULED", label: "Scheduled" },
                { value: "CHECKED_IN", label: "Checked In" },
                { value: "IN_PROGRESS", label: "In Progress" },
                { value: "COMPLETED", label: "Completed" },
                { value: "CANCELLED", label: "Cancelled" },
                { value: "NO_SHOW", label: "No Show" },
              ]}
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            />
          </div>
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <Input
              placeholder="Search patient or doctor..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9"
            />
          </div>
        </div>
      </Card>

      {/* Date Navigation */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <button
            onClick={() => navigateDate(-1)}
            className="rounded-lg p-1.5 text-slate-500 hover:bg-slate-100"
          >
            <ChevronLeft className="h-5 w-5" />
          </button>
          <span className="text-sm font-semibold text-slate-900 min-w-[180px] text-center">
            {calView === "day"
              ? currentDate.format("DD MMMM YYYY")
              : calView === "week"
                ? `${currentDate.startOf("week").format("DD MMM")} - ${currentDate.endOf("week").format("DD MMM YYYY")}`
                : currentDate.format("MMMM YYYY")}
          </span>
          <button
            onClick={() => navigateDate(1)}
            className="rounded-lg p-1.5 text-slate-500 hover:bg-slate-100"
          >
            <ChevronRight className="h-5 w-5" />
          </button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setCurrentDate(dayjs())}
          >
            Today
          </Button>
        </div>
        {viewMode === "calendar" && (
          <div className="flex items-center gap-1 rounded-lg border border-slate-200 p-0.5">
            {(["day", "week", "month"] as CalendarView[]).map((v) => (
              <button
                key={v}
                onClick={() => setCalView(v)}
                className={clsx(
                  "rounded-md px-3 py-1 text-xs font-medium capitalize transition-colors",
                  calView === v
                    ? "bg-primary-600 text-white"
                    : "text-slate-600 hover:bg-slate-100",
                )}
              >
                {v}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="flex justify-center py-20">
          <LoadingSpinner size="lg" />
        </div>
      ) : viewMode === "calendar" ? (
        <Card padding={false}>
          {calView === "month" ? (
            /* Month Grid */
            <div className="grid grid-cols-7">
              {["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((d) => (
                <div
                  key={d}
                  className="border-b border-r border-slate-200 px-2 py-2 text-center text-xs font-medium text-slate-500"
                >
                  {d}
                </div>
              ))}
              {calendarDays.map((day) => {
                const dayAppts = filtered.filter((a) =>
                  dayjs(a.scheduled_at).isSame(day, "day"),
                );
                const isCurrentMonth = day.month() === currentDate.month();
                return (
                  <div
                    key={day.format("YYYY-MM-DD")}
                    className={clsx(
                      "min-h-[100px] border-b border-r border-slate-200 p-2",
                      !isCurrentMonth && "bg-slate-50",
                    )}
                  >
                    <span
                      className={clsx(
                        "text-xs font-medium",
                        day.isSame(dayjs(), "day")
                          ? "text-primary-600"
                          : isCurrentMonth
                            ? "text-slate-700"
                            : "text-slate-400",
                      )}
                    >
                      {day.format("D")}
                    </span>
                    <div className="mt-1 space-y-0.5">
                      {dayAppts.slice(0, 3).map((a) => (
                        <button
                          key={a.id}
                          onClick={() => setSelectedAppt(a)}
                          className="block w-full truncate rounded bg-primary-50 px-1 py-0.5 text-left text-xs text-primary-700 hover:bg-primary-100"
                        >
                          {dayjs(a.scheduled_at).format("HH:mm")} {a.patient_name}
                        </button>
                      ))}
                      {dayAppts.length > 3 && (
                        <span className="text-xs text-slate-400">
                          +{dayAppts.length - 3} more
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            /* Day/Week Grid */
            <div className="overflow-x-auto">
              <div className="min-w-[600px]">
                {/* Header */}
                <div className="grid border-b border-slate-200" style={{ gridTemplateColumns: `80px repeat(${calendarDays.length}, 1fr)` }}>
                  <div className="border-r border-slate-200 p-2" />
                  {calendarDays.map((day) => (
                    <div
                      key={day.format("YYYY-MM-DD")}
                      className={clsx(
                        "border-r border-slate-200 p-2 text-center",
                        day.isSame(dayjs(), "day") && "bg-primary-50",
                      )}
                    >
                      <div className="text-xs text-slate-500">
                        {day.format("ddd")}
                      </div>
                      <div className="text-sm font-semibold text-slate-900">
                        {day.format("D")}
                      </div>
                    </div>
                  ))}
                </div>
                {/* Time slots */}
                {hours.map((hour) => (
                  <div
                    key={hour}
                    className="grid border-b border-slate-100"
                    style={{ gridTemplateColumns: `80px repeat(${calendarDays.length}, 1fr)` }}
                  >
                    <div className="border-r border-slate-200 p-2 text-xs text-slate-400">
                      {String(hour).padStart(2, "0")}:00
                    </div>
                    {calendarDays.map((day) => {
                      const hourAppts = filtered.filter((a) => {
                        const t = dayjs(a.scheduled_at);
                        return t.isSame(day, "day") && t.hour() === hour;
                      });
                      return (
                        <div
                          key={day.format("YYYY-MM-DD")}
                          className="min-h-[48px] border-r border-slate-100 p-0.5"
                        >
                          {hourAppts.map((a) => (
                            <button
                              key={a.id}
                              onClick={() => setSelectedAppt(a)}
                              className="mb-0.5 block w-full truncate rounded bg-primary-100 px-1.5 py-1 text-left text-xs font-medium text-primary-800 hover:bg-primary-200"
                            >
                              {a.patient_name}
                            </button>
                          ))}
                        </div>
                      );
                    })}
                  </div>
                ))}
              </div>
            </div>
          )}
        </Card>
      ) : (
        /* List View */
        <Card>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-left">
                  <th className="pb-3 pr-4 font-medium text-slate-500">Date/Time</th>
                  <th className="pb-3 pr-4 font-medium text-slate-500">Patient</th>
                  <th className="pb-3 pr-4 font-medium text-slate-500">Doctor</th>
                  <th className="pb-3 pr-4 font-medium text-slate-500">Service</th>
                  <th className="pb-3 pr-4 font-medium text-slate-500">Status</th>
                  <th className="pb-3 font-medium text-slate-500">Payment</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((appt) => {
                  const sb = STATUS_BADGES[appt.status];
                  return (
                    <tr
                      key={appt.id}
                      className="border-b border-slate-100 last:border-0 cursor-pointer hover:bg-slate-50"
                      onClick={() => setSelectedAppt(appt)}
                    >
                      <td className="py-3 pr-4">
                        <div className="font-medium text-slate-900">
                          {dayjs(appt.scheduled_at).format("DD MMM")}
                        </div>
                        <div className="text-xs text-slate-500">
                          {dayjs(appt.scheduled_at).format("HH:mm")} ({appt.duration_minutes} min)
                        </div>
                      </td>
                      <td className="py-3 pr-4 text-slate-700">
                        {appt.patient_name}
                      </td>
                      <td className="py-3 pr-4 text-slate-600">
                        {appt.doctor_name}
                      </td>
                      <td className="py-3 pr-4 text-slate-600">
                        {appt.service_name}
                      </td>
                      <td className="py-3 pr-4">
                        <Badge variant={sb.variant}>{sb.label}</Badge>
                      </td>
                      <td className="py-3">
                        <Badge
                          variant={
                            appt.payment_status === "PAID"
                              ? "success"
                              : appt.payment_status === "REFUNDED"
                                ? "danger"
                                : "warning"
                          }
                        >
                          {appt.payment_status}
                        </Badge>
                      </td>
                    </tr>
                  );
                })}
                {filtered.length === 0 && (
                  <tr>
                    <td colSpan={6} className="py-10 text-center text-slate-400">
                      No appointments found
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Detail SlideOver */}
      <SlideOver
        open={!!selectedAppt}
        onClose={() => setSelectedAppt(null)}
        title="Appointment Details"
      >
        {selectedAppt && (
          <div className="space-y-6">
            <div className="space-y-3">
              <div>
                <p className="text-xs text-slate-500">Patient</p>
                <p className="font-medium text-slate-900">{selectedAppt.patient_name}</p>
              </div>
              <div>
                <p className="text-xs text-slate-500">Doctor</p>
                <p className="font-medium text-slate-900">{selectedAppt.doctor_name}</p>
              </div>
              <div>
                <p className="text-xs text-slate-500">Service</p>
                <p className="font-medium text-slate-900">{selectedAppt.service_name}</p>
              </div>
              <div>
                <p className="text-xs text-slate-500">Date & Time</p>
                <p className="font-medium text-slate-900">
                  {dayjs(selectedAppt.scheduled_at).format("DD MMMM YYYY, HH:mm")}
                </p>
              </div>
              <div>
                <p className="text-xs text-slate-500">Duration</p>
                <p className="font-medium text-slate-900">{selectedAppt.duration_minutes} minutes</p>
              </div>
              <div>
                <p className="text-xs text-slate-500">Status</p>
                <Badge variant={STATUS_BADGES[selectedAppt.status].variant}>
                  {STATUS_BADGES[selectedAppt.status].label}
                </Badge>
              </div>
              <div>
                <p className="text-xs text-slate-500">Payment</p>
                <Badge
                  variant={
                    selectedAppt.payment_status === "PAID"
                      ? "success"
                      : "warning"
                  }
                >
                  {selectedAppt.payment_status}
                </Badge>
              </div>
              {selectedAppt.notes && (
                <div>
                  <p className="text-xs text-slate-500">Notes</p>
                  <p className="text-sm text-slate-700">{selectedAppt.notes}</p>
                </div>
              )}
            </div>

            <div className="border-t border-slate-200 pt-4">
              <p className="text-xs font-medium text-slate-500 mb-3">Change Status</p>
              <div className="flex flex-wrap gap-2">
                {selectedAppt.status === "SCHEDULED" && (
                  <>
                    <Button
                      size="sm"
                      onClick={() =>
                        statusMutation.mutate({ id: selectedAppt.id, status: "CHECKED_IN" })
                      }
                      loading={statusMutation.isPending}
                    >
                      Check In
                    </Button>
                    <Button
                      size="sm"
                      variant="danger"
                      onClick={() =>
                        statusMutation.mutate({ id: selectedAppt.id, status: "CANCELLED" })
                      }
                      loading={statusMutation.isPending}
                    >
                      Cancel
                    </Button>
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() =>
                        statusMutation.mutate({ id: selectedAppt.id, status: "NO_SHOW" })
                      }
                      loading={statusMutation.isPending}
                    >
                      No Show
                    </Button>
                  </>
                )}
                {selectedAppt.status === "CHECKED_IN" && (
                  <Button
                    size="sm"
                    onClick={() =>
                      statusMutation.mutate({ id: selectedAppt.id, status: "IN_PROGRESS" })
                    }
                    loading={statusMutation.isPending}
                  >
                    Start
                  </Button>
                )}
                {selectedAppt.status === "IN_PROGRESS" && (
                  <Button
                    size="sm"
                    onClick={() =>
                      statusMutation.mutate({ id: selectedAppt.id, status: "COMPLETED" })
                    }
                    loading={statusMutation.isPending}
                  >
                    Complete
                  </Button>
                )}
              </div>
            </div>
          </div>
        )}
      </SlideOver>
    </div>
  );
}
