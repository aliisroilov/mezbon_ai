import { useQuery } from "@tanstack/react-query";
import {
  Users,
  CalendarDays,
  DollarSign,
  Clock,
  TrendingUp,
  TrendingDown,
} from "lucide-react";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import dayjs from "dayjs";
import clsx from "clsx";
import { analyticsAPI, queueAPI, devicesAPI } from "../../api/client";
import { Card, CardHeader, CardTitle, Badge, LoadingSpinner } from "../../components/ui";
import { useEffect, useState } from "react";
import { onQueueUpdate, onActivityNew } from "../../services/socket";
import type { QueueTicket, ActivityFeedItem, DashboardStats, ChartDataPoint, DepartmentStat, Device } from "../../types";

function StatCard({
  label,
  value,
  change,
  icon: Icon,
  format,
}: {
  label: string;
  value: number;
  change: number;
  icon: React.ElementType;
  format?: "currency" | "minutes";
}) {
  const formatted =
    format === "currency"
      ? `${(value / 1000).toFixed(0)}k UZS`
      : format === "minutes"
        ? `${value} min`
        : value.toLocaleString();

  return (
    <Card>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-slate-500">{label}</p>
          <p className="mt-1 text-2xl font-bold text-slate-900">{formatted}</p>
        </div>
        <div className="rounded-lg bg-primary-50 p-2.5">
          <Icon className="h-5 w-5 text-primary-600" />
        </div>
      </div>
      <div className="mt-3 flex items-center gap-1 text-xs">
        {change >= 0 ? (
          <TrendingUp className="h-3.5 w-3.5 text-emerald-500" />
        ) : (
          <TrendingDown className="h-3.5 w-3.5 text-red-500" />
        )}
        <span
          className={clsx(
            "font-medium",
            change >= 0 ? "text-emerald-600" : "text-red-600",
          )}
        >
          {change >= 0 ? "+" : ""}
          {change}%
        </span>
        <span className="text-slate-400">vs yesterday</span>
      </div>
    </Card>
  );
}

export function DashboardPage() {
  const [liveQueue, setLiveQueue] = useState<QueueTicket[]>([]);
  const [activityFeed, setActivityFeed] = useState<ActivityFeedItem[]>([]);

  const from = dayjs().subtract(7, "day").format("YYYY-MM-DD");
  const to = dayjs().format("YYYY-MM-DD");

  const { data: stats, isLoading: statsLoading } = useQuery<DashboardStats>({
    queryKey: ["dashboard-stats"],
    queryFn: analyticsAPI.dashboard,
  });

  const { data: visitorsChart } = useQuery<ChartDataPoint[]>({
    queryKey: ["visitors-chart", from, to],
    queryFn: () => analyticsAPI.visitors({ from, to }),
  });

  const { data: deptStats } = useQuery<DepartmentStat[]>({
    queryKey: ["dept-stats", from, to],
    queryFn: () => analyticsAPI.appointmentsByDepartment({ from, to }),
  });

  const { data: devices } = useQuery<Device[]>({
    queryKey: ["devices"],
    queryFn: devicesAPI.list,
  });

  const { data: queueData } = useQuery<QueueTicket[]>({
    queryKey: ["queue-waiting"],
    queryFn: () => queueAPI.list({ status: "WAITING" }),
  });

  const { data: feedData } = useQuery<ActivityFeedItem[]>({
    queryKey: ["activity-feed"],
    queryFn: analyticsAPI.activityFeed,
  });

  useEffect(() => {
    if (queueData) setLiveQueue(queueData.slice(0, 5));
  }, [queueData]);

  useEffect(() => {
    if (feedData) setActivityFeed(feedData.slice(0, 10));
  }, [feedData]);

  useEffect(() => {
    const unsubQueue = onQueueUpdate((data) => {
      setLiveQueue((prev) => {
        const updated = [...prev.filter((t) => t.department_id !== data.department_id), ...data.tickets.filter((t) => t.status === "WAITING")];
        return updated.slice(0, 5);
      });
    });

    const unsubActivity = onActivityNew((item) => {
      setActivityFeed((prev) => [item, ...prev].slice(0, 10));
    });

    return () => {
      unsubQueue();
      unsubActivity();
    };
  }, []);

  if (statsLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-900">Dashboard</h1>

      {/* Stats Cards */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Today's Visitors"
          value={stats?.today_visitors ?? 0}
          change={stats?.visitors_change ?? 0}
          icon={Users}
        />
        <StatCard
          label="Appointments"
          value={stats?.today_appointments ?? 0}
          change={stats?.appointments_change ?? 0}
          icon={CalendarDays}
        />
        <StatCard
          label="Revenue"
          value={stats?.today_revenue ?? 0}
          change={stats?.revenue_change ?? 0}
          icon={DollarSign}
          format="currency"
        />
        <StatCard
          label="Avg Wait Time"
          value={stats?.avg_wait_minutes ?? 0}
          change={stats?.wait_change ?? 0}
          icon={Clock}
          format="minutes"
        />
      </div>

      {/* Charts Row */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Visitors Chart */}
        <Card>
          <CardHeader>
            <CardTitle>Visitors (Last 7 Days)</CardTitle>
          </CardHeader>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={visitorsChart ?? []}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis
                  dataKey="date"
                  tickFormatter={(d) => dayjs(d).format("DD MMM")}
                  fontSize={12}
                  stroke="#94a3b8"
                />
                <YAxis fontSize={12} stroke="#94a3b8" />
                <Tooltip
                  labelFormatter={(d) => dayjs(d).format("DD MMMM, YYYY")}
                />
                <Line
                  type="monotone"
                  dataKey="value"
                  stroke="#0d9488"
                  strokeWidth={2}
                  dot={{ fill: "#0d9488", r: 3 }}
                  name="Visitors"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>

        {/* Appointments by Department */}
        <Card>
          <CardHeader>
            <CardTitle>Appointments by Department</CardTitle>
          </CardHeader>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={deptStats ?? []}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="department_name" fontSize={12} stroke="#94a3b8" />
                <YAxis fontSize={12} stroke="#94a3b8" />
                <Tooltip />
                <Bar
                  dataKey="appointments"
                  fill="#0d9488"
                  radius={[4, 4, 0, 0]}
                  name="Appointments"
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      {/* Bottom Row */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Live Queue */}
        <Card>
          <CardHeader>
            <CardTitle>Live Queue</CardTitle>
            <Badge variant="info" dot>
              Real-time
            </Badge>
          </CardHeader>
          {liveQueue.length === 0 ? (
            <p className="text-sm text-slate-400 py-4 text-center">
              No patients waiting
            </p>
          ) : (
            <ul className="space-y-3">
              {liveQueue.map((ticket) => (
                <li
                  key={ticket.id}
                  className="flex items-center justify-between rounded-lg border border-slate-100 p-3"
                >
                  <div>
                    <span className="text-sm font-semibold text-primary-700">
                      #{ticket.ticket_number}
                    </span>
                    <p className="text-xs text-slate-500">
                      {ticket.patient_name ?? "Patient"}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-slate-500">
                      {ticket.department_name}
                    </p>
                    <p className="text-xs text-slate-400">
                      ~{ticket.estimated_wait_minutes} min
                    </p>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>

        {/* Device Status */}
        <Card>
          <CardHeader>
            <CardTitle>Devices</CardTitle>
          </CardHeader>
          {!devices || devices.length === 0 ? (
            <p className="text-sm text-slate-400 py-4 text-center">
              No devices registered
            </p>
          ) : (
            <ul className="space-y-3">
              {devices.map((device) => (
                <li
                  key={device.id}
                  className="flex items-center justify-between rounded-lg border border-slate-100 p-3"
                >
                  <div>
                    <p className="text-sm font-medium text-slate-900">
                      {device.name}
                    </p>
                    <p className="text-xs text-slate-500">{device.location}</p>
                  </div>
                  <Badge
                    variant={
                      device.status === "ONLINE"
                        ? "success"
                        : device.status === "MAINTENANCE"
                          ? "warning"
                          : "danger"
                    }
                    dot
                  >
                    {device.status}
                  </Badge>
                </li>
              ))}
            </ul>
          )}
        </Card>

        {/* Recent Activity */}
        <Card>
          <CardHeader>
            <CardTitle>Recent Activity</CardTitle>
          </CardHeader>
          {activityFeed.length === 0 ? (
            <p className="text-sm text-slate-400 py-4 text-center">
              No recent activity
            </p>
          ) : (
            <ul className="space-y-3">
              {activityFeed.map((item) => (
                <li key={item.id} className="flex items-start gap-3">
                  <div className="mt-0.5 h-2 w-2 flex-shrink-0 rounded-full bg-primary-400" />
                  <div className="min-w-0">
                    <p className="text-sm text-slate-700 truncate">
                      {item.message}
                    </p>
                    <p className="text-xs text-slate-400">
                      {dayjs(item.timestamp).format("HH:mm")}
                    </p>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </div>
  );
}
