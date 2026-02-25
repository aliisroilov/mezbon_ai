import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Search, Pencil, Trash2 } from "lucide-react";
import { doctorsAPI, departmentsAPI } from "../../api/client";
import { Card, Button, Input, Badge, Modal, LoadingSpinner, Select } from "../../components/ui";
import type { Doctor, Department } from "../../types";
import { DoctorForm } from "./DoctorForm";
import { ScheduleEditor } from "./ScheduleEditor";
import { ServiceAssignment } from "./ServiceAssignment";

export function DoctorsPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [deptFilter, setDeptFilter] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [editingDoctor, setEditingDoctor] = useState<Doctor | null>(null);
  const [scheduleDoctor, setScheduleDoctor] = useState<Doctor | null>(null);
  const [serviceDoctor, setServiceDoctor] = useState<Doctor | null>(null);

  const { data: doctors, isLoading } = useQuery<Doctor[]>({
    queryKey: ["doctors", deptFilter],
    queryFn: () => doctorsAPI.list({ department_id: deptFilter || undefined }),
  });

  const { data: departments } = useQuery<Department[]>({
    queryKey: ["departments"],
    queryFn: departmentsAPI.list,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => doctorsAPI.delete(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["doctors"] }),
  });

  const filtered = (doctors ?? []).filter((d) =>
    d.full_name.toLowerCase().includes(search.toLowerCase()) ||
    d.specialty.toLowerCase().includes(search.toLowerCase()),
  );

  const deptOptions = [
    { value: "", label: "All Departments" },
    ...(departments ?? []).map((d) => ({ value: d.id, label: d.name })),
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-900">Doctors</h1>
        <Button icon={<Plus className="h-4 w-4" />} onClick={() => { setEditingDoctor(null); setShowForm(true); }}>
          Add Doctor
        </Button>
      </div>

      <Card>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center mb-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <Input
              placeholder="Search doctors..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9"
            />
          </div>
          <div className="w-48">
            <Select
              options={deptOptions}
              value={deptFilter}
              onChange={(e) => setDeptFilter(e.target.value)}
            />
          </div>
        </div>

        {isLoading ? (
          <div className="flex justify-center py-10">
            <LoadingSpinner />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-left">
                  <th className="pb-3 pr-4 font-medium text-slate-500">Doctor</th>
                  <th className="pb-3 pr-4 font-medium text-slate-500">Department</th>
                  <th className="pb-3 pr-4 font-medium text-slate-500">Specialty</th>
                  <th className="pb-3 pr-4 font-medium text-slate-500">Status</th>
                  <th className="pb-3 font-medium text-slate-500">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((doctor) => (
                  <tr
                    key={doctor.id}
                    className="border-b border-slate-100 last:border-0"
                  >
                    <td className="py-3 pr-4">
                      <div className="flex items-center gap-3">
                        <div className="flex h-9 w-9 items-center justify-center rounded-full bg-primary-100 text-sm font-medium text-primary-700">
                          {doctor.full_name.charAt(0)}
                        </div>
                        <span className="font-medium text-slate-900">
                          {doctor.full_name}
                        </span>
                      </div>
                    </td>
                    <td className="py-3 pr-4 text-slate-600">
                      {doctor.department_name}
                    </td>
                    <td className="py-3 pr-4 text-slate-600">
                      {doctor.specialty}
                    </td>
                    <td className="py-3 pr-4">
                      <Badge
                        variant={doctor.is_active ? "success" : "default"}
                        dot
                      >
                        {doctor.is_active ? "Active" : "Inactive"}
                      </Badge>
                    </td>
                    <td className="py-3">
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => { setEditingDoctor(doctor); setShowForm(true); }}
                          className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
                          title="Edit"
                        >
                          <Pencil className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => setScheduleDoctor(doctor)}
                          className="rounded-lg px-2 py-1 text-xs font-medium text-primary-600 hover:bg-primary-50"
                        >
                          Schedule
                        </button>
                        <button
                          onClick={() => setServiceDoctor(doctor)}
                          className="rounded-lg px-2 py-1 text-xs font-medium text-primary-600 hover:bg-primary-50"
                        >
                          Services
                        </button>
                        <button
                          onClick={() => {
                            if (confirm("Delete this doctor?")) {
                              deleteMutation.mutate(doctor.id);
                            }
                          }}
                          className="rounded-lg p-1.5 text-slate-400 hover:bg-red-50 hover:text-red-600"
                          title="Delete"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                {filtered.length === 0 && (
                  <tr>
                    <td colSpan={5} className="py-10 text-center text-slate-400">
                      No doctors found
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Doctor Form Modal */}
      <Modal
        open={showForm}
        onClose={() => setShowForm(false)}
        title={editingDoctor ? "Edit Doctor" : "Add Doctor"}
        size="lg"
      >
        <DoctorForm
          doctor={editingDoctor}
          departments={departments ?? []}
          onSuccess={() => {
            setShowForm(false);
            queryClient.invalidateQueries({ queryKey: ["doctors"] });
          }}
        />
      </Modal>

      {/* Schedule Editor Modal */}
      <Modal
        open={!!scheduleDoctor}
        onClose={() => setScheduleDoctor(null)}
        title={`Schedule — ${scheduleDoctor?.full_name ?? ""}`}
        size="xl"
      >
        {scheduleDoctor && (
          <ScheduleEditor
            doctor={scheduleDoctor}
            onSuccess={() => {
              setScheduleDoctor(null);
              queryClient.invalidateQueries({ queryKey: ["doctors"] });
            }}
          />
        )}
      </Modal>

      {/* Service Assignment Modal */}
      <Modal
        open={!!serviceDoctor}
        onClose={() => setServiceDoctor(null)}
        title={`Services — ${serviceDoctor?.full_name ?? ""}`}
        size="lg"
      >
        {serviceDoctor && (
          <ServiceAssignment
            doctor={serviceDoctor}
            onSuccess={() => {
              setServiceDoctor(null);
              queryClient.invalidateQueries({ queryKey: ["doctors"] });
            }}
          />
        )}
      </Modal>
    </div>
  );
}
