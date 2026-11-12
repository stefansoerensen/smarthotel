import { Building2, LogOut } from "lucide-react";
import { Link, Outlet } from "react-router-dom";
import { useAuthStore } from "../hooks/useAuthStore";

export default function Layout() {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  return (
    <div className="flex min-h-full flex-col">
      <header className="flex items-center justify-between border-b border-ink/10 bg-white px-6 py-3">
        <Link to="/properties" className="flex items-center gap-2 font-semibold text-burgundy">
          <Building2 size={18} aria-hidden /> Smart Building
        </Link>
        <div className="flex items-center gap-4 text-ink/70">
          <span>
            {user?.username}
            {user?.tenant_code ? ` · ${user.tenant_code}` : ""}
          </span>
          <button type="button" onClick={logout} className="flex items-center gap-1 hover:text-burgundy">
            <LogOut size={16} aria-hidden /> Abmelden
          </button>
        </div>
      </header>
      <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-6">
        <Outlet />
      </main>
    </div>
  );
}
