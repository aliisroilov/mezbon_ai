import { Link, useLocation } from "react-router-dom";
import { ChevronRight, Home } from "lucide-react";

const labelMap: Record<string, string> = {
  doctors: "Doctors",
  appointments: "Appointments",
  patients: "Patients",
  queue: "Queue",
  devices: "Devices",
  content: "Content",
  analytics: "Analytics",
  settings: "Settings",
};

export function Breadcrumbs() {
  const { pathname } = useLocation();
  const segments = pathname.split("/").filter(Boolean);

  if (segments.length === 0) return null;

  return (
    <nav className="flex items-center gap-1.5 text-sm text-slate-500 mb-4">
      <Link
        to="/"
        className="flex items-center gap-1 hover:text-slate-700 transition-colors"
      >
        <Home className="h-3.5 w-3.5" />
      </Link>
      {segments.map((segment, index) => {
        const path = "/" + segments.slice(0, index + 1).join("/");
        const isLast = index === segments.length - 1;
        const label = labelMap[segment] || segment;

        return (
          <span key={path} className="flex items-center gap-1.5">
            <ChevronRight className="h-3.5 w-3.5 text-slate-300" />
            {isLast ? (
              <span className="font-medium text-slate-900">{label}</span>
            ) : (
              <Link to={path} className="hover:text-slate-700 transition-colors">
                {label}
              </Link>
            )}
          </span>
        );
      })}
    </nav>
  );
}
