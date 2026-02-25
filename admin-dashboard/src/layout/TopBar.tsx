import { Menu, LogOut, User as UserIcon } from "lucide-react";
import { useAuthStore } from "../store/authStore";
import { useUIStore } from "../store/uiStore";

export function TopBar() {
  const { user, logout } = useAuthStore();
  const { toggleSidebar } = useUIStore();

  return (
    <header className="flex h-16 items-center justify-between border-b border-slate-200 bg-white px-4 lg:px-6">
      <div className="flex items-center gap-3">
        <button
          onClick={toggleSidebar}
          className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 lg:hidden"
        >
          <Menu className="h-5 w-5" />
        </button>
      </div>

      <div className="flex items-center gap-4">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary-100 text-primary-700">
            <UserIcon className="h-4 w-4" />
          </div>
          <div className="hidden sm:block">
            <p className="text-sm font-medium text-slate-900">
              {user?.full_name ?? "Admin"}
            </p>
            <p className="text-xs text-slate-500">{user?.role ?? ""}</p>
          </div>
        </div>
        <button
          onClick={logout}
          className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
          title="Logout"
        >
          <LogOut className="h-4 w-4" />
        </button>
      </div>
    </header>
  );
}
