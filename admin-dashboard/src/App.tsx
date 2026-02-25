import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect } from "react";
import { useAuthStore } from "./store/authStore";
import { AppLayout } from "./layout/AppLayout";
import { LoginPage } from "./pages/Login/LoginPage";
import { DashboardPage } from "./pages/Dashboard/DashboardPage";
import { DoctorsPage } from "./pages/Doctors/DoctorsPage";
import { AppointmentsPage } from "./pages/Appointments/AppointmentsPage";
import { PatientsPage } from "./pages/Patients/PatientsPage";
import { QueuePage } from "./pages/Queue/QueuePage";
import { DevicesPage } from "./pages/Devices/DevicesPage";
import { ContentPage } from "./pages/Content/ContentPage";
import { AnalyticsPage } from "./pages/Analytics/AnalyticsPage";
import { SettingsPage } from "./pages/Settings/SettingsPage";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

function AuthInit({ children }: { children: React.ReactNode }) {
  const { checkAuth } = useAuthStore();

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  return <>{children}</>;
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthInit>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route element={<AppLayout />}>
              <Route index element={<DashboardPage />} />
              <Route path="doctors" element={<DoctorsPage />} />
              <Route path="appointments" element={<AppointmentsPage />} />
              <Route path="patients" element={<PatientsPage />} />
              <Route path="queue" element={<QueuePage />} />
              <Route path="devices" element={<DevicesPage />} />
              <Route path="content" element={<ContentPage />} />
              <Route path="analytics" element={<AnalyticsPage />} />
              <Route path="settings" element={<SettingsPage />} />
            </Route>
          </Routes>
        </AuthInit>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
