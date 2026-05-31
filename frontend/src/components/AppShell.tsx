import { NavLink } from "react-router-dom";
import { Activity, Bell, Gauge, LayoutDashboard, LogOut, Settings, ShieldCheck, Users } from "lucide-react";
import type { PropsWithChildren } from "react";
import { useAuth } from "../context/AuthContext";

const links = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/analytics", label: "Analytics", icon: Activity },
  { to: "/alerts", label: "Alerts", icon: Bell },
  { to: "/users", label: "Users", icon: Users },
  { to: "/settings", label: "Settings", icon: Settings }
];

interface AppShellProps extends PropsWithChildren {
  connection: "live" | "polling" | "offline";
}

export function AppShell({ children, connection }: AppShellProps) {
  const { user, logout } = useAuth();

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">
            <ShieldCheck size={22} />
          </div>
          <div>
            <strong>Boujuron</strong>
            <span>Intelligence</span>
          </div>
        </div>

        <nav className="nav-list">
          {links.map((link) => {
            const Icon = link.icon;
            return (
              <NavLink key={link.to} to={link.to} className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}>
                <Icon size={18} />
                <span>{link.label}</span>
              </NavLink>
            );
          })}
        </nav>

        <div className="sidebar-status">
          <Gauge size={18} />
          <div>
            <span>Stream</span>
            <strong className={`connection ${connection}`}>{connection}</strong>
          </div>
        </div>

        <div className="user-chip">
          <div>
            <strong>{user?.name}</strong>
            <span>{user?.role}</span>
          </div>
          <button className="icon-button" onClick={logout} aria-label="Sign out">
            <LogOut size={16} />
          </button>
        </div>
      </aside>

      <main className="main-panel">
        <header className="topbar">
          <div>
            <p className="eyebrow">Fraud intelligence command center</p>
            <h1>Boujuron Risk Operations</h1>
          </div>
          <div className="operator-chip">
            <span className="pulse" />
            Analyst console
          </div>
        </header>
        {children}
      </main>
    </div>
  );
}
