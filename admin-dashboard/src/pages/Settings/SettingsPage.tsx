import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2, Save } from "lucide-react";
import { settingsAPI } from "../../api/client";
import {
  Card,
  CardHeader,
  CardTitle,
  Button,
  Input,
  Select,
  Tabs,
  Modal,
  LoadingSpinner,
} from "../../components/ui";
import type { Clinic, User, UserRole } from "../../types";

export function SettingsPage() {
  const [activeTab, setActiveTab] = useState("clinic");

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-900">Settings</h1>
      <Tabs
        tabs={[
          { id: "clinic", label: "Clinic Info" },
          { id: "hours", label: "Working Hours" },
          { id: "integrations", label: "Integrations" },
          { id: "users", label: "Users" },
        ]}
        activeTab={activeTab}
        onChange={setActiveTab}
      />

      {activeTab === "clinic" && <ClinicInfoSection />}
      {activeTab === "hours" && <WorkingHoursSection />}
      {activeTab === "integrations" && <IntegrationsSection />}
      {activeTab === "users" && <UsersSection />}
    </div>
  );
}

// === Clinic Info ===
function ClinicInfoSection() {
  const { data: clinic, isLoading } = useQuery<Clinic>({
    queryKey: ["clinic-settings"],
    queryFn: settingsAPI.getClinic,
  });

  const [name, setName] = useState("");
  const [address, setAddress] = useState("");
  const [phone, setPhone] = useState("");

  useEffect(() => {
    if (clinic) {
      setName(clinic.name);
      setAddress(clinic.address);
      setPhone(clinic.phone);
    }
  }, [clinic]);

  const mutation = useMutation({
    mutationFn: () => settingsAPI.updateClinic({ name, address, phone }),
  });

  if (isLoading) {
    return (
      <div className="flex justify-center py-10">
        <LoadingSpinner />
      </div>
    );
  }

  return (
    <Card>
      <form
        onSubmit={(e) => { e.preventDefault(); mutation.mutate(); }}
        className="space-y-4 max-w-lg"
      >
        <Input
          label="Clinic Name"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <Input
          label="Address"
          value={address}
          onChange={(e) => setAddress(e.target.value)}
        />
        <Input
          label="Phone"
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
        />
        {mutation.isSuccess && (
          <div className="rounded-lg bg-emerald-50 p-3 text-sm text-emerald-700">
            Settings saved successfully
          </div>
        )}
        {mutation.error && (
          <div className="rounded-lg bg-red-50 p-3 text-sm text-red-700">
            {(mutation.error as Error).message}
          </div>
        )}
        <Button
          type="submit"
          icon={<Save className="h-4 w-4" />}
          loading={mutation.isPending}
        >
          Save Changes
        </Button>
      </form>
    </Card>
  );
}

// === Working Hours ===
const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

function WorkingHoursSection() {
  const { data: clinic, isLoading } = useQuery<Clinic>({
    queryKey: ["clinic-settings"],
    queryFn: settingsAPI.getClinic,
  });

  const [hours, setHours] = useState<
    { day: string; open: string; close: string; enabled: boolean }[]
  >(
    DAYS.map((day) => ({ day, open: "09:00", close: "18:00", enabled: true })),
  );

  useEffect(() => {
    if (clinic?.working_hours) {
      setHours(
        DAYS.map((day) => {
          const wh = clinic.working_hours?.[day.toLowerCase()];
          return {
            day,
            open: wh?.open ?? "09:00",
            close: wh?.close ?? "18:00",
            enabled: !!wh,
          };
        }),
      );
    }
  }, [clinic]);

  const mutation = useMutation({
    mutationFn: () => {
      const working_hours: Record<string, { open: string; close: string }> = {};
      hours
        .filter((h) => h.enabled)
        .forEach((h) => {
          working_hours[h.day.toLowerCase()] = { open: h.open, close: h.close };
        });
      return settingsAPI.updateClinic({ working_hours });
    },
  });

  function update(idx: number, patch: Partial<(typeof hours)[0]>) {
    setHours((prev) => prev.map((h, i) => (i === idx ? { ...h, ...patch } : h)));
  }

  if (isLoading) {
    return (
      <div className="flex justify-center py-10">
        <LoadingSpinner />
      </div>
    );
  }

  return (
    <Card>
      <div className="space-y-3 max-w-xl">
        {hours.map((h, idx) => (
          <div key={h.day} className="flex items-center gap-4">
            <div className="w-24">
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={h.enabled}
                  onChange={(e) => update(idx, { enabled: e.target.checked })}
                  className="rounded border-slate-300 text-primary-600 focus:ring-primary-500"
                />
                {h.day.slice(0, 3)}
              </label>
            </div>
            <input
              type="time"
              value={h.open}
              onChange={(e) => update(idx, { open: e.target.value })}
              disabled={!h.enabled}
              className="rounded-lg border border-slate-300 px-2 py-1.5 text-sm disabled:opacity-40"
            />
            <span className="text-slate-400">to</span>
            <input
              type="time"
              value={h.close}
              onChange={(e) => update(idx, { close: e.target.value })}
              disabled={!h.enabled}
              className="rounded-lg border border-slate-300 px-2 py-1.5 text-sm disabled:opacity-40"
            />
          </div>
        ))}
        {mutation.isSuccess && (
          <div className="rounded-lg bg-emerald-50 p-3 text-sm text-emerald-700">
            Working hours saved
          </div>
        )}
        <Button
          icon={<Save className="h-4 w-4" />}
          onClick={() => mutation.mutate()}
          loading={mutation.isPending}
        >
          Save Hours
        </Button>
      </div>
    </Card>
  );
}

// === Integrations ===
function IntegrationsSection() {
  const [crmEnabled, setCrmEnabled] = useState(false);
  const [crmProvider, setCrmProvider] = useState("bitrix24");
  const [crmWebhook, setCrmWebhook] = useState("");
  const [paymentMock, setPaymentMock] = useState(true);
  const [greeting, setGreeting] = useState("warm");
  const [defaultLang, setDefaultLang] = useState("uz");
  const [handoffThreshold, setHandoffThreshold] = useState("3");

  return (
    <div className="space-y-6">
      {/* CRM */}
      <Card>
        <CardHeader>
          <CardTitle>CRM Integration</CardTitle>
        </CardHeader>
        <div className="space-y-3 max-w-lg">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={crmEnabled}
              onChange={(e) => setCrmEnabled(e.target.checked)}
              className="rounded border-slate-300 text-primary-600 focus:ring-primary-500"
            />
            Enable CRM sync
          </label>
          {crmEnabled && (
            <>
              <Select
                label="Provider"
                value={crmProvider}
                onChange={(e) => setCrmProvider(e.target.value)}
                options={[
                  { value: "bitrix24", label: "Bitrix24" },
                  { value: "amocrm", label: "AmoCRM" },
                ]}
              />
              <Input
                label="Webhook URL"
                value={crmWebhook}
                onChange={(e) => setCrmWebhook(e.target.value)}
                placeholder="https://..."
              />
            </>
          )}
        </div>
      </Card>

      {/* Payment */}
      <Card>
        <CardHeader>
          <CardTitle>Payment Gateways</CardTitle>
        </CardHeader>
        <div className="space-y-3 max-w-lg">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={paymentMock}
              onChange={(e) => setPaymentMock(e.target.checked)}
              className="rounded border-slate-300 text-primary-600 focus:ring-primary-500"
            />
            Mock payments (dev mode)
          </label>
          <p className="text-xs text-slate-500">
            When enabled, all payments auto-confirm. Disable for production.
          </p>
          <div className="grid grid-cols-2 gap-3 mt-3">
            {["Uzcard", "Humo", "Click", "Payme"].map((gw) => (
              <label key={gw} className="flex items-center gap-2 text-sm rounded-lg border border-slate-200 p-3">
                <input
                  type="checkbox"
                  defaultChecked
                  className="rounded border-slate-300 text-primary-600 focus:ring-primary-500"
                />
                {gw}
              </label>
            ))}
          </div>
        </div>
      </Card>

      {/* AI Settings */}
      <Card>
        <CardHeader>
          <CardTitle>AI Settings</CardTitle>
        </CardHeader>
        <div className="space-y-4 max-w-lg">
          <Select
            label="Greeting Style"
            value={greeting}
            onChange={(e) => setGreeting(e.target.value)}
            options={[
              { value: "warm", label: "Warm & Friendly" },
              { value: "formal", label: "Formal & Professional" },
              { value: "brief", label: "Brief & Efficient" },
            ]}
          />
          <Select
            label="Default Language"
            value={defaultLang}
            onChange={(e) => setDefaultLang(e.target.value)}
            options={[
              { value: "uz", label: "Uzbek" },
              { value: "ru", label: "Russian" },
              { value: "en", label: "English" },
            ]}
          />
          <Input
            label="Hand-off Threshold (failed attempts before human)"
            type="number"
            value={handoffThreshold}
            onChange={(e) => setHandoffThreshold(e.target.value)}
            min={1}
            max={10}
          />
        </div>
      </Card>
    </div>
  );
}

// === Users ===
function UsersSection() {
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);

  const { data: users, isLoading } = useQuery<User[]>({
    queryKey: ["settings-users"],
    queryFn: settingsAPI.getUsers,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => settingsAPI.deleteUser(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["settings-users"] }),
  });

  const roleMutation = useMutation({
    mutationFn: ({ id, role }: { id: string; role: UserRole }) =>
      settingsAPI.updateUserRole(id, role),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["settings-users"] }),
  });

  return (
    <>
      <Card>
        <div className="flex items-center justify-between mb-4">
          <p className="text-sm text-slate-500">
            {(users ?? []).length} user(s)
          </p>
          <Button
            icon={<Plus className="h-4 w-4" />}
            size="sm"
            onClick={() => setShowForm(true)}
          >
            Add User
          </Button>
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
                  <th className="pb-3 pr-4 font-medium text-slate-500">Name</th>
                  <th className="pb-3 pr-4 font-medium text-slate-500">Email</th>
                  <th className="pb-3 pr-4 font-medium text-slate-500">Role</th>
                  <th className="pb-3 font-medium text-slate-500">Actions</th>
                </tr>
              </thead>
              <tbody>
                {(users ?? []).map((user) => (
                  <tr key={user.id} className="border-b border-slate-100 last:border-0">
                    <td className="py-3 pr-4 font-medium text-slate-900">
                      {user.full_name}
                    </td>
                    <td className="py-3 pr-4 text-slate-600">{user.email}</td>
                    <td className="py-3 pr-4">
                      <select
                        value={user.role}
                        onChange={(e) =>
                          roleMutation.mutate({
                            id: user.id,
                            role: e.target.value as UserRole,
                          })
                        }
                        className="rounded-lg border border-slate-300 px-2 py-1 text-xs"
                      >
                        <option value="SUPER_ADMIN">Super Admin</option>
                        <option value="CLINIC_ADMIN">Clinic Admin</option>
                        <option value="STAFF">Staff</option>
                      </select>
                    </td>
                    <td className="py-3">
                      <button
                        onClick={() => {
                          if (confirm("Remove this user?"))
                            deleteMutation.mutate(user.id);
                        }}
                        className="rounded-lg p-1.5 text-slate-400 hover:bg-red-50 hover:text-red-600"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Modal
        open={showForm}
        onClose={() => setShowForm(false)}
        title="Add User"
      >
        <AddUserForm
          onSuccess={() => {
            setShowForm(false);
            queryClient.invalidateQueries({ queryKey: ["settings-users"] });
          }}
        />
      </Modal>
    </>
  );
}

function AddUserForm({ onSuccess }: { onSuccess: () => void }) {
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<UserRole>("STAFF");

  const mutation = useMutation({
    mutationFn: () =>
      settingsAPI.createUser({
        full_name: fullName,
        email,
        password,
        role,
      }),
    onSuccess,
  });

  return (
    <form
      onSubmit={(e) => { e.preventDefault(); mutation.mutate(); }}
      className="space-y-4"
    >
      <Input
        label="Full Name"
        value={fullName}
        onChange={(e) => setFullName(e.target.value)}
        required
      />
      <Input
        label="Email"
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        required
      />
      <Input
        label="Password"
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        required
        minLength={8}
      />
      <Select
        label="Role"
        value={role}
        onChange={(e) => setRole(e.target.value as UserRole)}
        options={[
          { value: "SUPER_ADMIN", label: "Super Admin" },
          { value: "CLINIC_ADMIN", label: "Clinic Admin" },
          { value: "STAFF", label: "Staff" },
        ]}
      />
      {mutation.error && (
        <div className="rounded-lg bg-red-50 p-3 text-sm text-red-700">
          {(mutation.error as Error).message}
        </div>
      )}
      <div className="flex justify-end">
        <Button type="submit" loading={mutation.isPending}>
          Create User
        </Button>
      </div>
    </form>
  );
}
