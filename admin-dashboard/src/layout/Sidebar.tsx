import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Stethoscope,
  CalendarDays,
  Users,
  ListOrdered,
  Monitor,
  FileText,
  BarChart3,
  Settings,
  ChevronLeft,
  ChevronRight,
  X,
} from "lucide-react";
import clsx from "clsx";
import { useUIStore } from "../store/uiStore";

const navItems = [
  { to: "/", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/doctors", icon: Stethoscope, label: "Doctors" },
  { to: "/appointments", icon: CalendarDays, label: "Appointments" },
  { to: "/patients", icon: Users, label: "Patients" },
  { to: "/queue", icon: ListOrdered, label: "Queue" },
  { to: "/devices", icon: Monitor, label: "Devices" },
  { to: "/content", icon: FileText, label: "Content" },
  { to: "/analytics", icon: BarChart3, label: "Analytics" },
  { to: "/settings", icon: Settings, label: "Settings" },
];

export function Sidebar() {
  const { sidebarOpen, setSidebarOpen, sidebarCollapsed, toggleCollapsed } =
    useUIStore();

  return (
    <>
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <aside
        className={clsx(
          "fixed inset-y-0 left-0 z-50 flex flex-col border-r border-slate-200 bg-white transition-all duration-300 lg:static lg:z-auto",
          sidebarCollapsed ? "lg:w-20" : "lg:w-64",
          sidebarOpen ? "w-64 translate-x-0" : "-translate-x-full lg:translate-x-0",
        )}
      >
        {/* Logo */}
        <div className="flex h-16 items-center justify-between border-b border-slate-200 px-4">
          {!sidebarCollapsed && (
            <span className="text-xl font-bold text-primary-600">Mezbon</span>
          )}
          {sidebarCollapsed && (
            <span className="mx-auto text-xl font-bold text-primary-600">M</span>
          )}
          <button
            onClick={() => setSidebarOpen(false)}
            className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 lg:hidden"
          >
            <X className="h-5 w-5" />
          </button>
          <button
            onClick={toggleCollapsed}
            className="hidden rounded-lg p-1 text-slate-400 hover:bg-slate-100 lg:block"
          >
            {sidebarCollapsed ? (
              <ChevronRight className="h-4 w-4" />
            ) : (
              <ChevronLeft className="h-4 w-4" />
            )}
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto p-3">
          <ul className="space-y-1">
            {navItems.map((item) => (
              <li key={item.to}>
                <NavLink
                  to={item.to}
                  end={item.to === "/"}
                  onClick={() => setSidebarOpen(false)}
                  className={({ isActive }) =>
                    clsx(
                      "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                      isActive
                        ? "bg-primary-50 text-primary-700"
                        : "text-slate-600 hover:bg-slate-50 hover:text-slate-900",
                      sidebarCollapsed && "justify-center px-2",
                    )
                  }
                >
                  <item.icon className="h-5 w-5 flex-shrink-0" />
                  {!sidebarCollapsed && <span>{item.label}</span>}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>

        {/* Version */}
        <div className="border-t border-slate-200 p-3">
          {!sidebarCollapsed && (
            <p className="text-xs text-slate-400 text-center">Mezbon v0.1.0</p>
          )}
        </div>
      </aside>
    </>
  );
}
