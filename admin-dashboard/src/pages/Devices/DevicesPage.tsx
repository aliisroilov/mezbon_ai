import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Monitor,
  Wifi,
  WifiOff,
  Wrench,
  RotateCcw,
  ChevronLeft,
  Cpu,
  HardDrive,
} from "lucide-react";
import dayjs from "dayjs";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { devicesAPI } from "../../api/client";
import {
  Card,
  CardHeader,
  CardTitle,
  Button,
  Badge,
  LoadingSpinner,
} from "../../components/ui";
import type { Device, DeviceHeartbeat, DeviceStatus } from "../../types";
import { useEffect } from "react";
import { onDeviceStatusChange, onDeviceHeartbeat } from "../../services/socket";

const statusConfig: Record<DeviceStatus, { variant: "success" | "danger" | "warning"; icon: React.ElementType }> = {
  ONLINE: { variant: "success", icon: Wifi },
  OFFLINE: { variant: "danger", icon: WifiOff },
  MAINTENANCE: { variant: "warning", icon: Wrench },
};

export function DevicesPage() {
  const queryClient = useQueryClient();
  const [selectedDevice, setSelectedDevice] = useState<Device | null>(null);

  const { data: devices, isLoading } = useQuery<Device[]>({
    queryKey: ["devices"],
    queryFn: devicesAPI.list,
  });

  // Real-time status updates
  useEffect(() => {
    const unsub = onDeviceStatusChange(() => {
      queryClient.invalidateQueries({ queryKey: ["devices"] });
    });
    return unsub;
  }, [queryClient]);

  if (selectedDevice) {
    return (
      <DeviceDetail
        device={selectedDevice}
        onBack={() => setSelectedDevice(null)}
      />
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-900">Devices</h1>

      {isLoading ? (
        <div className="flex justify-center py-20">
          <LoadingSpinner size="lg" />
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {(devices ?? []).map((device) => {
            const cfg = statusConfig[device.status];
            const StatusIcon = cfg.icon;
            return (
              <Card
                key={device.id}
                className="cursor-pointer hover:shadow-md transition-shadow"
              >
                <div onClick={() => setSelectedDevice(device)}>
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div className="rounded-lg bg-slate-100 p-2.5">
                        <Monitor className="h-5 w-5 text-slate-600" />
                      </div>
                      <div>
                        <p className="font-semibold text-slate-900">{device.name}</p>
                        <p className="text-sm text-slate-500">{device.location}</p>
                      </div>
                    </div>
                    <Badge variant={cfg.variant} dot>
                      <StatusIcon className="h-3 w-3 mr-1" />
                      {device.status}
                    </Badge>
                  </div>
                  <div className="mt-4 flex items-center gap-4 text-xs text-slate-400">
                    <span>S/N: {device.serial_number}</span>
                    {device.last_heartbeat && (
                      <span>
                        Last seen: {dayjs(device.last_heartbeat).format("HH:mm")}
                      </span>
                    )}
                  </div>
                </div>
              </Card>
            );
          })}
          {(devices ?? []).length === 0 && (
            <div className="col-span-full text-center py-10 text-slate-400">
              No devices registered
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function DeviceDetail({ device, onBack }: { device: Device; onBack: () => void }) {
  const queryClient = useQueryClient();
  const [heartbeats, setHeartbeats] = useState<DeviceHeartbeat[]>([]);
  const [configJson, setConfigJson] = useState(
    JSON.stringify(device.config, null, 2),
  );
  const [configError, setConfigError] = useState("");

  const { data: hbData, isLoading: hbLoading } = useQuery<DeviceHeartbeat[]>({
    queryKey: ["device-heartbeats", device.id],
    queryFn: () => devicesAPI.getHeartbeats(device.id, 24),
  });

  useEffect(() => {
    if (hbData) setHeartbeats(hbData);
  }, [hbData]);

  // Live heartbeat updates
  useEffect(() => {
    const unsub = onDeviceHeartbeat((hb) => {
      if (hb.device_id === device.id) {
        setHeartbeats((prev) => [...prev, hb].slice(-100));
      }
    });
    return unsub;
  }, [device.id]);

  const restartMutation = useMutation({
    mutationFn: () => devicesAPI.restart(device.id),
  });

  const maintenanceMutation = useMutation({
    mutationFn: (enabled: boolean) => devicesAPI.setMaintenance(device.id, enabled),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["devices"] }),
  });

  const configMutation = useMutation({
    mutationFn: (config: Record<string, unknown>) =>
      devicesAPI.updateConfig(device.id, config),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["devices"] }),
  });

  function handleSaveConfig() {
    try {
      const parsed = JSON.parse(configJson);
      setConfigError("");
      configMutation.mutate(parsed);
    } catch {
      setConfigError("Invalid JSON");
    }
  }

  const chartData = heartbeats.map((hb) => ({
    time: dayjs(hb.timestamp).format("HH:mm"),
    cpu: hb.cpu_percent,
    memory: hb.memory_percent,
  }));

  const cfg = statusConfig[device.status];

  return (
    <div className="space-y-6">
      <button
        onClick={onBack}
        className="flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700"
      >
        <ChevronLeft className="h-4 w-4" /> Back to Devices
      </button>

      {/* Header */}
      <Card>
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-4">
            <div className="rounded-xl bg-slate-100 p-3">
              <Monitor className="h-8 w-8 text-slate-600" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-slate-900">{device.name}</h2>
              <p className="text-sm text-slate-500">{device.location}</p>
              <p className="text-xs text-slate-400 mt-1">S/N: {device.serial_number}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant={cfg.variant} dot>
              {device.status}
            </Badge>
            <Button
              variant="secondary"
              size="sm"
              icon={<RotateCcw className="h-3.5 w-3.5" />}
              onClick={() => restartMutation.mutate()}
              loading={restartMutation.isPending}
            >
              Restart
            </Button>
            <Button
              variant={device.status === "MAINTENANCE" ? "primary" : "secondary"}
              size="sm"
              icon={<Wrench className="h-3.5 w-3.5" />}
              onClick={() =>
                maintenanceMutation.mutate(device.status !== "MAINTENANCE")
              }
              loading={maintenanceMutation.isPending}
            >
              {device.status === "MAINTENANCE" ? "Exit Maintenance" : "Maintenance"}
            </Button>
          </div>
        </div>
      </Card>

      {/* CPU/Memory Chart */}
      <Card>
        <CardHeader>
          <CardTitle>System Resources (24h)</CardTitle>
        </CardHeader>
        {hbLoading ? (
          <div className="flex justify-center py-10">
            <LoadingSpinner />
          </div>
        ) : (
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="time" fontSize={11} stroke="#94a3b8" />
                <YAxis fontSize={11} stroke="#94a3b8" domain={[0, 100]} unit="%" />
                <Tooltip />
                <Line
                  type="monotone"
                  dataKey="cpu"
                  stroke="#0d9488"
                  strokeWidth={2}
                  dot={false}
                  name="CPU"
                />
                <Line
                  type="monotone"
                  dataKey="memory"
                  stroke="#f59e0b"
                  strokeWidth={2}
                  dot={false}
                  name="Memory"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Heartbeat History */}
        <Card>
          <CardHeader>
            <CardTitle>Recent Heartbeats</CardTitle>
          </CardHeader>
          <div className="max-h-64 overflow-y-auto space-y-2">
            {heartbeats.slice(-20).reverse().map((hb) => (
              <div
                key={hb.id}
                className="flex items-center justify-between rounded border border-slate-100 p-2 text-xs"
              >
                <span className="text-slate-500">
                  {dayjs(hb.timestamp).format("HH:mm:ss")}
                </span>
                <div className="flex items-center gap-3">
                  <span className="flex items-center gap-1 text-slate-600">
                    <Cpu className="h-3 w-3" /> {hb.cpu_percent}%
                  </span>
                  <span className="flex items-center gap-1 text-slate-600">
                    <HardDrive className="h-3 w-3" /> {hb.memory_percent}%
                  </span>
                </div>
                {hb.errors.length > 0 && (
                  <Badge variant="danger" className="text-xs">
                    {hb.errors.length} error{hb.errors.length > 1 ? "s" : ""}
                  </Badge>
                )}
              </div>
            ))}
            {heartbeats.length === 0 && (
              <p className="text-sm text-slate-400 text-center py-4">No heartbeats</p>
            )}
          </div>
        </Card>

        {/* Config Editor */}
        <Card>
          <CardHeader>
            <CardTitle>Configuration</CardTitle>
          </CardHeader>
          <textarea
            value={configJson}
            onChange={(e) => setConfigJson(e.target.value)}
            className="w-full rounded-lg border border-slate-300 bg-slate-50 p-3 font-mono text-xs text-slate-800 h-48 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
          />
          {configError && (
            <p className="mt-1 text-sm text-red-600">{configError}</p>
          )}
          <div className="mt-3 flex justify-end">
            <Button
              size="sm"
              onClick={handleSaveConfig}
              loading={configMutation.isPending}
            >
              Save Config
            </Button>
          </div>
        </Card>
      </div>
    </div>
  );
}
