import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Search, Plus, ChevronLeft } from "lucide-react";
import dayjs from "dayjs";
import { patientsAPI } from "../../api/client";
import {
  Card,
  CardHeader,
  CardTitle,
  Button,
  Input,
  Badge,
  Modal,
  LoadingSpinner,
} from "../../components/ui";
import type { Patient, Appointment, Payment, VisitLog, ConsentRecord } from "../../types";
import { PatientForm } from "./PatientForm";

export function PatientsPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null);
  const [showForm, setShowForm] = useState(false);

  const { data: patientsData, isLoading } = useQuery({
    queryKey: ["patients", search, page],
    queryFn: () =>
      patientsAPI.list({ search: search || undefined, page, limit: 20 }),
  });

  const patients = patientsData?.data ?? [];
  const total = patientsData?.meta?.total ?? 0;
  const totalPages = Math.ceil(total / 20);

  return (
    <div className="space-y-6">
      {selectedPatient ? (
        <PatientDetail
          patient={selectedPatient}
          onBack={() => setSelectedPatient(null)}
        />
      ) : (
        <>
          <div className="flex items-center justify-between">
            <h1 className="text-2xl font-bold text-slate-900">Patients</h1>
            <Button
              icon={<Plus className="h-4 w-4" />}
              onClick={() => setShowForm(true)}
            >
              Register Patient
            </Button>
          </div>

          <Card>
            <div className="mb-4">
              <div className="relative max-w-md">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                <Input
                  placeholder="Search by name or phone..."
                  value={search}
                  onChange={(e) => {
                    setSearch(e.target.value);
                    setPage(1);
                  }}
                  className="pl-9"
                />
              </div>
            </div>

            {isLoading ? (
              <div className="flex justify-center py-10">
                <LoadingSpinner />
              </div>
            ) : (
              <>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-slate-200 text-left">
                        <th className="pb-3 pr-4 font-medium text-slate-500">Name</th>
                        <th className="pb-3 pr-4 font-medium text-slate-500">Phone</th>
                        <th className="pb-3 pr-4 font-medium text-slate-500">DOB</th>
                        <th className="pb-3 pr-4 font-medium text-slate-500">Language</th>
                        <th className="pb-3 font-medium text-slate-500">Face ID</th>
                      </tr>
                    </thead>
                    <tbody>
                      {patients.map((p) => (
                        <tr
                          key={p.id}
                          className="border-b border-slate-100 last:border-0 cursor-pointer hover:bg-slate-50"
                          onClick={() => setSelectedPatient(p)}
                        >
                          <td className="py-3 pr-4 font-medium text-slate-900">
                            {p.full_name}
                          </td>
                          <td className="py-3 pr-4 text-slate-600">{p.phone}</td>
                          <td className="py-3 pr-4 text-slate-600">
                            {p.date_of_birth
                              ? dayjs(p.date_of_birth).format("DD/MM/YYYY")
                              : "—"}
                          </td>
                          <td className="py-3 pr-4">
                            <Badge>{p.language_preference.toUpperCase()}</Badge>
                          </td>
                          <td className="py-3">
                            <Badge
                              variant={p.has_face_embedding ? "success" : "default"}
                              dot
                            >
                              {p.has_face_embedding ? "Enrolled" : "None"}
                            </Badge>
                          </td>
                        </tr>
                      ))}
                      {patients.length === 0 && (
                        <tr>
                          <td colSpan={5} className="py-10 text-center text-slate-400">
                            No patients found
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>

                {totalPages > 1 && (
                  <div className="mt-4 flex items-center justify-between">
                    <p className="text-sm text-slate-500">
                      {total} patient{total !== 1 ? "s" : ""} total
                    </p>
                    <div className="flex items-center gap-2">
                      <Button
                        variant="secondary"
                        size="sm"
                        disabled={page <= 1}
                        onClick={() => setPage((p) => p - 1)}
                      >
                        Previous
                      </Button>
                      <span className="text-sm text-slate-600">
                        {page} / {totalPages}
                      </span>
                      <Button
                        variant="secondary"
                        size="sm"
                        disabled={page >= totalPages}
                        onClick={() => setPage((p) => p + 1)}
                      >
                        Next
                      </Button>
                    </div>
                  </div>
                )}
              </>
            )}
          </Card>

          <Modal
            open={showForm}
            onClose={() => setShowForm(false)}
            title="Register Patient"
          >
            <PatientForm
              onSuccess={() => {
                setShowForm(false);
                queryClient.invalidateQueries({ queryKey: ["patients"] });
              }}
            />
          </Modal>
        </>
      )}
    </div>
  );
}

function PatientDetail({ patient, onBack }: { patient: Patient; onBack: () => void }) {
  const { data: appointments } = useQuery<Appointment[]>({
    queryKey: ["patient-appointments", patient.id],
    queryFn: () => patientsAPI.getAppointments(patient.id),
  });

  const { data: payments } = useQuery<Payment[]>({
    queryKey: ["patient-payments", patient.id],
    queryFn: () => patientsAPI.getPayments(patient.id),
  });

  const { data: visits } = useQuery<VisitLog[]>({
    queryKey: ["patient-visits", patient.id],
    queryFn: () => patientsAPI.getVisits(patient.id),
  });

  const { data: consents } = useQuery<ConsentRecord[]>({
    queryKey: ["patient-consents", patient.id],
    queryFn: () => patientsAPI.getConsents(patient.id),
  });

  return (
    <div className="space-y-6">
      <button
        onClick={onBack}
        className="flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700"
      >
        <ChevronLeft className="h-4 w-4" /> Back to Patients
      </button>

      {/* Patient Info */}
      <Card>
        <div className="flex items-start gap-4">
          <div className="flex h-14 w-14 items-center justify-center rounded-full bg-primary-100 text-lg font-bold text-primary-700">
            {patient.full_name.charAt(0)}
          </div>
          <div>
            <h2 className="text-xl font-bold text-slate-900">{patient.full_name}</h2>
            <p className="text-sm text-slate-500">{patient.phone}</p>
            <div className="mt-2 flex items-center gap-2">
              <Badge>{patient.language_preference.toUpperCase()}</Badge>
              {patient.date_of_birth && (
                <Badge variant="default">
                  DOB: {dayjs(patient.date_of_birth).format("DD/MM/YYYY")}
                </Badge>
              )}
              <Badge variant={patient.has_face_embedding ? "success" : "default"} dot>
                {patient.has_face_embedding ? "Face enrolled" : "No face"}
              </Badge>
            </div>
          </div>
        </div>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Upcoming Appointments */}
        <Card>
          <CardHeader>
            <CardTitle>Appointments</CardTitle>
          </CardHeader>
          {!appointments || appointments.length === 0 ? (
            <p className="text-sm text-slate-400">No appointments</p>
          ) : (
            <div className="space-y-2">
              {appointments.map((a) => (
                <div
                  key={a.id}
                  className="flex items-center justify-between rounded-lg border border-slate-100 p-3"
                >
                  <div>
                    <p className="text-sm font-medium text-slate-900">
                      {a.doctor_name} — {a.service_name}
                    </p>
                    <p className="text-xs text-slate-500">
                      {dayjs(a.scheduled_at).format("DD MMM YYYY, HH:mm")}
                    </p>
                  </div>
                  <Badge
                    variant={
                      a.status === "COMPLETED"
                        ? "success"
                        : a.status === "CANCELLED"
                          ? "danger"
                          : "info"
                    }
                  >
                    {a.status}
                  </Badge>
                </div>
              ))}
            </div>
          )}
        </Card>

        {/* Payment History */}
        <Card>
          <CardHeader>
            <CardTitle>Payments</CardTitle>
          </CardHeader>
          {!payments || payments.length === 0 ? (
            <p className="text-sm text-slate-400">No payments</p>
          ) : (
            <div className="space-y-2">
              {payments.map((p) => (
                <div
                  key={p.id}
                  className="flex items-center justify-between rounded-lg border border-slate-100 p-3"
                >
                  <div>
                    <p className="text-sm font-medium text-slate-900">
                      {p.amount.toLocaleString()} UZS
                    </p>
                    <p className="text-xs text-slate-500">
                      {p.method} — {dayjs(p.created_at).format("DD MMM YYYY")}
                    </p>
                  </div>
                  <Badge
                    variant={
                      p.status === "COMPLETED"
                        ? "success"
                        : p.status === "FAILED"
                          ? "danger"
                          : "warning"
                    }
                  >
                    {p.status}
                  </Badge>
                </div>
              ))}
            </div>
          )}
        </Card>

        {/* Visit History */}
        <Card>
          <CardHeader>
            <CardTitle>Visit History</CardTitle>
          </CardHeader>
          {!visits || visits.length === 0 ? (
            <p className="text-sm text-slate-400">No visits</p>
          ) : (
            <div className="space-y-2">
              {visits.map((v) => (
                <div
                  key={v.id}
                  className="flex items-center justify-between rounded-lg border border-slate-100 p-3"
                >
                  <div>
                    <p className="text-sm font-medium text-slate-900">
                      {v.intent}
                    </p>
                    <p className="text-xs text-slate-500">
                      {v.language.toUpperCase()} — {dayjs(v.created_at).format("DD MMM, HH:mm")}
                    </p>
                  </div>
                  <Badge variant={v.success ? "success" : "danger"} dot>
                    {v.success ? "Success" : "Failed"}
                  </Badge>
                </div>
              ))}
            </div>
          )}
        </Card>

        {/* Consents */}
        <Card>
          <CardHeader>
            <CardTitle>Consent Records</CardTitle>
          </CardHeader>
          {!consents || consents.length === 0 ? (
            <p className="text-sm text-slate-400">No consent records</p>
          ) : (
            <div className="space-y-2">
              {consents.map((c) => (
                <div
                  key={c.id}
                  className="flex items-center justify-between rounded-lg border border-slate-100 p-3"
                >
                  <div>
                    <p className="text-sm font-medium text-slate-900">
                      {c.consent_type}
                    </p>
                    <p className="text-xs text-slate-500">
                      Granted: {dayjs(c.granted_at).format("DD MMM YYYY")}
                    </p>
                  </div>
                  <Badge variant={c.revoked_at ? "danger" : "success"}>
                    {c.revoked_at ? "Revoked" : "Active"}
                  </Badge>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
