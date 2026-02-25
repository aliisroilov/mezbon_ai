import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Phone, Check, Clock, Users } from "lucide-react";
import dayjs from "dayjs";
import clsx from "clsx";
import { queueAPI, departmentsAPI } from "../../api/client";
import { Card, Button, Badge, LoadingSpinner, Select } from "../../components/ui";
import { onQueueUpdate } from "../../services/socket";
import type { QueueTicket, Department, QueueTicketStatus } from "../../types";

const COLUMNS: { status: QueueTicketStatus; label: string; color: string }[] = [
  { status: "WAITING", label: "Waiting", color: "bg-amber-50 border-amber-200" },
  { status: "IN_PROGRESS", label: "In Progress", color: "bg-blue-50 border-blue-200" },
  { status: "COMPLETED", label: "Completed", color: "bg-emerald-50 border-emerald-200" },
];

export function QueuePage() {
  const queryClient = useQueryClient();
  const [deptFilter, setDeptFilter] = useState("");
  const [tickets, setTickets] = useState<QueueTicket[]>([]);

  const { data: departments } = useQuery<Department[]>({
    queryKey: ["departments"],
    queryFn: departmentsAPI.list,
  });

  const { data: queueData, isLoading } = useQuery<QueueTicket[]>({
    queryKey: ["queue", deptFilter],
    queryFn: () => queueAPI.list({ department_id: deptFilter || undefined }),
  });

  useEffect(() => {
    if (queueData) setTickets(queueData);
  }, [queueData]);

  // Real-time updates
  useEffect(() => {
    const unsub = onQueueUpdate((data) => {
      setTickets((prev) => {
        const otherDepts = prev.filter((t) => t.department_id !== data.department_id);
        const updated = deptFilter && data.department_id !== deptFilter
          ? prev
          : [...otherDepts, ...data.tickets];
        return updated;
      });
    });
    return unsub;
  }, [deptFilter]);

  const callNextMutation = useMutation({
    mutationFn: (departmentId: string) => queueAPI.callNext(departmentId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["queue"] }),
  });

  const completeMutation = useMutation({
    mutationFn: (ticketId: string) => queueAPI.complete(ticketId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["queue"] }),
  });

  const grouped = COLUMNS.map((col) => ({
    ...col,
    tickets: tickets.filter((t) => t.status === col.status),
  }));

  const stats = {
    waiting: tickets.filter((t) => t.status === "WAITING").length,
    inProgress: tickets.filter((t) => t.status === "IN_PROGRESS").length,
    completed: tickets.filter((t) => t.status === "COMPLETED").length,
    avgWait:
      tickets.filter((t) => t.status === "WAITING").length > 0
        ? Math.round(
            tickets
              .filter((t) => t.status === "WAITING")
              .reduce((sum, t) => sum + t.estimated_wait_minutes, 0) /
              tickets.filter((t) => t.status === "WAITING").length,
          )
        : 0,
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-slate-900">Queue</h1>
          <Badge variant="info" dot>Live</Badge>
        </div>
        <div className="flex items-center gap-3">
          <div className="w-48">
            <Select
              options={[
                { value: "", label: "All Departments" },
                ...(departments ?? []).map((d) => ({ value: d.id, label: d.name })),
              ]}
              value={deptFilter}
              onChange={(e) => setDeptFilter(e.target.value)}
            />
          </div>
          {deptFilter && (
            <Button
              icon={<Phone className="h-4 w-4" />}
              onClick={() => callNextMutation.mutate(deptFilter)}
              loading={callNextMutation.isPending}
            >
              Call Next
            </Button>
          )}
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-20">
          <LoadingSpinner size="lg" />
        </div>
      ) : (
        <>
          {/* Kanban Board */}
          <div className="grid gap-6 lg:grid-cols-3">
            {grouped.map((col) => (
              <div key={col.status}>
                <div className="mb-3 flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-slate-700">
                    {col.label}
                  </h3>
                  <Badge variant="default">{col.tickets.length}</Badge>
                </div>
                <div className={clsx("min-h-[200px] rounded-xl border-2 border-dashed p-3 space-y-2", col.color)}>
                  {col.tickets.length === 0 ? (
                    <p className="text-center text-sm text-slate-400 py-8">
                      No tickets
                    </p>
                  ) : (
                    col.tickets.map((ticket) => (
                      <div
                        key={ticket.id}
                        className="rounded-lg bg-white border border-slate-200 p-3 shadow-sm"
                      >
                        <div className="flex items-start justify-between">
                          <div>
                            <span className="text-lg font-bold text-primary-700">
                              #{ticket.ticket_number}
                            </span>
                            <p className="text-sm font-medium text-slate-900 mt-0.5">
                              {ticket.patient_name ?? "Patient"}
                            </p>
                            <p className="text-xs text-slate-500">
                              {ticket.department_name}
                            </p>
                          </div>
                          <div className="text-right">
                            <p className="text-xs text-slate-400">
                              {dayjs(ticket.created_at).format("HH:mm")}
                            </p>
                            {ticket.status === "WAITING" && (
                              <p className="text-xs text-amber-600 mt-1">
                                ~{ticket.estimated_wait_minutes} min
                              </p>
                            )}
                          </div>
                        </div>
                        {ticket.status === "IN_PROGRESS" && (
                          <div className="mt-2">
                            <Button
                              size="sm"
                              variant="secondary"
                              icon={<Check className="h-3.5 w-3.5" />}
                              onClick={() => completeMutation.mutate(ticket.id)}
                              loading={completeMutation.isPending}
                              className="w-full"
                            >
                              Complete
                            </Button>
                          </div>
                        )}
                      </div>
                    ))
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Stats */}
          <div className="grid gap-4 sm:grid-cols-4">
            <Card>
              <div className="flex items-center gap-3">
                <div className="rounded-lg bg-amber-50 p-2">
                  <Clock className="h-4 w-4 text-amber-600" />
                </div>
                <div>
                  <p className="text-xs text-slate-500">Waiting</p>
                  <p className="text-lg font-bold text-slate-900">{stats.waiting}</p>
                </div>
              </div>
            </Card>
            <Card>
              <div className="flex items-center gap-3">
                <div className="rounded-lg bg-blue-50 p-2">
                  <Users className="h-4 w-4 text-blue-600" />
                </div>
                <div>
                  <p className="text-xs text-slate-500">In Progress</p>
                  <p className="text-lg font-bold text-slate-900">{stats.inProgress}</p>
                </div>
              </div>
            </Card>
            <Card>
              <div className="flex items-center gap-3">
                <div className="rounded-lg bg-emerald-50 p-2">
                  <Check className="h-4 w-4 text-emerald-600" />
                </div>
                <div>
                  <p className="text-xs text-slate-500">Completed Today</p>
                  <p className="text-lg font-bold text-slate-900">{stats.completed}</p>
                </div>
              </div>
            </Card>
            <Card>
              <div className="flex items-center gap-3">
                <div className="rounded-lg bg-primary-50 p-2">
                  <Clock className="h-4 w-4 text-primary-600" />
                </div>
                <div>
                  <p className="text-xs text-slate-500">Avg Wait</p>
                  <p className="text-lg font-bold text-slate-900">{stats.avgWait} min</p>
                </div>
              </div>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
