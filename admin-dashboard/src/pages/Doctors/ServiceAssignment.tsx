import { useState, useEffect } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { request, doctorsAPI } from "../../api/client";
import { Button, LoadingSpinner } from "../../components/ui";
import type { Doctor, MedicalService } from "../../types";

interface ServiceRow {
  service_id: string;
  name: string;
  selected: boolean;
  price_uzs: number;
}

interface Props {
  doctor: Doctor;
  onSuccess: () => void;
}

export function ServiceAssignment({ doctor, onSuccess }: Props) {
  const [rows, setRows] = useState<ServiceRow[]>([]);

  const { data: allServices, isLoading } = useQuery<MedicalService[]>({
    queryKey: ["services", doctor.department_id],
    queryFn: () =>
      request<MedicalService[]>(
        `/services?department_id=${doctor.department_id}`,
      ),
  });

  useEffect(() => {
    if (allServices) {
      const existing = doctor.services ?? [];
      setRows(
        allServices.map((s) => {
          const assigned = existing.find((a) => a.service_id === s.id);
          return {
            service_id: s.id,
            name: s.name,
            selected: !!assigned,
            price_uzs: assigned?.price_uzs ?? s.price_uzs,
          };
        }),
      );
    }
  }, [allServices, doctor.services]);

  const mutation = useMutation({
    mutationFn: (services: { service_id: string; price_uzs: number }[]) =>
      doctorsAPI.updateServices(doctor.id, services),
    onSuccess,
  });

  function toggle(idx: number) {
    setRows((prev) =>
      prev.map((r, i) =>
        i === idx ? { ...r, selected: !r.selected } : r,
      ),
    );
  }

  function setPrice(idx: number, price: number) {
    setRows((prev) =>
      prev.map((r, i) => (i === idx ? { ...r, price_uzs: price } : r)),
    );
  }

  function handleSave() {
    const selected = rows
      .filter((r) => r.selected)
      .map((r) => ({ service_id: r.service_id, price_uzs: r.price_uzs }));
    mutation.mutate(selected);
  }

  if (isLoading) {
    return (
      <div className="flex justify-center py-10">
        <LoadingSpinner />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {rows.length === 0 ? (
        <p className="text-sm text-slate-400 text-center py-6">
          No services available for this department
        </p>
      ) : (
        <div className="space-y-2">
          {rows.map((row, idx) => (
            <div
              key={row.service_id}
              className="flex items-center gap-4 rounded-lg border border-slate-200 p-3"
            >
              <input
                type="checkbox"
                checked={row.selected}
                onChange={() => toggle(idx)}
                className="rounded border-slate-300 text-primary-600 focus:ring-primary-500"
              />
              <span className="flex-1 text-sm font-medium text-slate-700">
                {row.name}
              </span>
              <div className="flex items-center gap-1">
                <input
                  type="number"
                  value={row.price_uzs}
                  onChange={(e) =>
                    setPrice(idx, parseInt(e.target.value) || 0)
                  }
                  disabled={!row.selected}
                  className="w-28 rounded-lg border border-slate-300 px-2 py-1 text-sm text-right disabled:opacity-40"
                />
                <span className="text-xs text-slate-400">UZS</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {mutation.error && (
        <div className="rounded-lg bg-red-50 p-3 text-sm text-red-700">
          {(mutation.error as Error).message}
        </div>
      )}

      <div className="flex justify-end">
        <Button onClick={handleSave} loading={mutation.isPending}>
          Save Services
        </Button>
      </div>
    </div>
  );
}
