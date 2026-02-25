import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { doctorsAPI } from "../../api/client";
import { Button } from "../../components/ui";
import type { Doctor, DoctorSchedule } from "../../types";

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

interface ScheduleRow {
  day_of_week: number;
  enabled: boolean;
  start_time: string;
  end_time: string;
  break_start: string;
  break_end: string;
}

function initSchedule(existing: DoctorSchedule[]): ScheduleRow[] {
  return DAYS.map((_, i) => {
    const found = existing.find((s) => s.day_of_week === i);
    return {
      day_of_week: i,
      enabled: !!found?.is_active,
      start_time: found?.start_time ?? "09:00",
      end_time: found?.end_time ?? "18:00",
      break_start: found?.break_start ?? "13:00",
      break_end: found?.break_end ?? "14:00",
    };
  });
}

interface Props {
  doctor: Doctor;
  onSuccess: () => void;
}

export function ScheduleEditor({ doctor, onSuccess }: Props) {
  const [rows, setRows] = useState<ScheduleRow[]>(() =>
    initSchedule(doctor.schedules),
  );

  const mutation = useMutation({
    mutationFn: (schedules: DoctorSchedule[]) =>
      doctorsAPI.updateSchedule(doctor.id, schedules),
    onSuccess,
  });

  function updateRow(idx: number, patch: Partial<ScheduleRow>) {
    setRows((prev) =>
      prev.map((r, i) => (i === idx ? { ...r, ...patch } : r)),
    );
  }

  function handleSave() {
    const schedules = rows.map((r) => ({
      id: "",
      day_of_week: r.day_of_week,
      start_time: r.start_time,
      end_time: r.end_time,
      break_start: r.enabled ? r.break_start : null,
      break_end: r.enabled ? r.break_end : null,
      is_active: r.enabled,
    }));
    mutation.mutate(schedules);
  }

  return (
    <div className="space-y-4">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200 text-left">
              <th className="pb-2 pr-4 font-medium text-slate-500 w-28">Day</th>
              <th className="pb-2 pr-4 font-medium text-slate-500 w-12">Active</th>
              <th className="pb-2 pr-2 font-medium text-slate-500">Start</th>
              <th className="pb-2 pr-2 font-medium text-slate-500">End</th>
              <th className="pb-2 pr-2 font-medium text-slate-500">Break Start</th>
              <th className="pb-2 font-medium text-slate-500">Break End</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, idx) => (
              <tr key={row.day_of_week} className="border-b border-slate-100">
                <td className="py-2 pr-4 font-medium text-slate-700">
                  {DAYS[row.day_of_week]}
                </td>
                <td className="py-2 pr-4">
                  <input
                    type="checkbox"
                    checked={row.enabled}
                    onChange={(e) =>
                      updateRow(idx, { enabled: e.target.checked })
                    }
                    className="rounded border-slate-300 text-primary-600 focus:ring-primary-500"
                  />
                </td>
                <td className="py-2 pr-2">
                  <input
                    type="time"
                    value={row.start_time}
                    onChange={(e) =>
                      updateRow(idx, { start_time: e.target.value })
                    }
                    disabled={!row.enabled}
                    className="rounded-lg border border-slate-300 px-2 py-1 text-sm disabled:opacity-40"
                  />
                </td>
                <td className="py-2 pr-2">
                  <input
                    type="time"
                    value={row.end_time}
                    onChange={(e) =>
                      updateRow(idx, { end_time: e.target.value })
                    }
                    disabled={!row.enabled}
                    className="rounded-lg border border-slate-300 px-2 py-1 text-sm disabled:opacity-40"
                  />
                </td>
                <td className="py-2 pr-2">
                  <input
                    type="time"
                    value={row.break_start}
                    onChange={(e) =>
                      updateRow(idx, { break_start: e.target.value })
                    }
                    disabled={!row.enabled}
                    className="rounded-lg border border-slate-300 px-2 py-1 text-sm disabled:opacity-40"
                  />
                </td>
                <td className="py-2">
                  <input
                    type="time"
                    value={row.break_end}
                    onChange={(e) =>
                      updateRow(idx, { break_end: e.target.value })
                    }
                    disabled={!row.enabled}
                    className="rounded-lg border border-slate-300 px-2 py-1 text-sm disabled:opacity-40"
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {mutation.error && (
        <div className="rounded-lg bg-red-50 p-3 text-sm text-red-700">
          {(mutation.error as Error).message}
        </div>
      )}

      <div className="flex justify-end">
        <Button onClick={handleSave} loading={mutation.isPending}>
          Save Schedule
        </Button>
      </div>
    </div>
  );
}
