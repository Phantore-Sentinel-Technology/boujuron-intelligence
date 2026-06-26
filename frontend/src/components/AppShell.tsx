import { NavLink } from "react-router-dom";
import { Activity, BarChart3, Bell, BriefcaseBusiness, Code2, FlaskConical, Gauge, History, LayoutDashboard, LogOut, Moon, Network, Settings, ShieldCheck, Sun, Users, X } from "lucide-react";
import type { PropsWithChildren } from "react";
import { useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";
import type { NotificationItem } from "../types";
import { getIntelligenceActivity } from "../services/api";

const links = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/activity", label: "Live Feed", icon: Activity },
  { to: "/history", label: "History", icon: History },
  { to: "/executive", label: "Executive", icon: BarChart3 },
  { to: "/analytics", label: "Analytics", icon: Activity },
  { to: "/decision-lab", label: "Decision Lab", icon: FlaskConical },
  { to: "/consortium", label: "Consortium", icon: Network },
  { to: "/developer-api", label: "API", icon: Code2 },
  { to: "/alerts", label: "Alerts", icon: Bell },
  { to: "/cases", label: "Cases", icon: BriefcaseBusiness },
  { to: "/users", label: "Users", icon: Users },
  { to: "/settings", label: "Settings", icon: Settings }
];

const dismissedNotificationsKey = "boujuron.dismissed.notifications";

interface AppShellProps extends PropsWithChildren {
  connection: "live" | "polling" | "offline";
}

export function AppShell({ children, connection }: AppShellProps) {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [dismissed, setDismissed] = useState<string[]>(() => {
    try {
      return JSON.parse(localStorage.getItem(dismissedNotificationsKey) || "[]") as string[];
    } catch {
      return [];
    }
  });
  const ThemeIcon = theme === "dark" ? Moon : Sun;

  useEffect(() => {
    let mounted = true;
    const load = () => {
      getIntelligenceActivity(12)
        .then((data) => mounted && setNotifications(data.notifications.filter((item) => !dismissed.includes(item.id))))
        .catch(() => mounted && setNotifications([]));
    };
    load();
    const timer = window.setInterval(load, 8000);
    return () => {
      mounted = false;
      window.clearInterval(timer);
    };
  }, [dismissed]);

  function dismissNotification(id: string) {
    setDismissed((current) => {
      const next = Array.from(new Set([...current, id])).slice(-80);
      localStorage.setItem(dismissedNotificationsKey, JSON.stringify(next));
      return next;
    });
    setNotifications((current) => current.filter((item) => item.id !== id));
  }

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

        <button className="sidebar-action" onClick={toggleTheme}>
          <ThemeIcon size={16} />
          {theme === "dark" ? "Dark mode" : "Light mode"}
        </button>

        <div className="user-chip">
          <div>
            <strong>{user?.name}</strong>
            <span>{user?.role}</span>
          </div>
          <button className="signout-button" onClick={logout}>
            <LogOut size={16} />
            Sign out
          </button>
        </div>
      </aside>

      <main className="main-panel">
        <header className="topbar">
          <div>
            <p className="eyebrow">Fraud intelligence command center</p>
            <h1>Boujuron Risk Operations</h1>
          </div>
          <div className="topbar-actions">
            <div className="notification-wrap">
              <button className="notification-button" onClick={() => setNotificationsOpen((open) => !open)} aria-label="Open notifications">
                <Bell size={18} />
                {notifications.length > 0 && <span>{notifications.length}</span>}
              </button>
              {notificationsOpen && (
                <div className="notification-popover">
                  <div className="section-header compact">
                    <div>
                      <p className="eyebrow">Notifications</p>
                      <h3>Live Signals</h3>
                    </div>
                  </div>
                  <div className="notification-list">
                    {notifications.map((item) => (
                      <DismissibleNotification key={item.id} item={item} onDismiss={dismissNotification} onOpen={() => setNotificationsOpen(false)} />
                    ))}
                    {notifications.length === 0 && <div className="empty-state slim">No live notifications yet.</div>}
                  </div>
                </div>
              )}
            </div>
            <div className="operator-chip">
              <span className="pulse" />
              Analyst console
            </div>
          </div>
        </header>
        {children}
      </main>
    </div>
  );
}

function DismissibleNotification({ item, onDismiss, onOpen }: { item: NotificationItem; onDismiss: (id: string) => void; onOpen: () => void }) {
  const [startX, setStartX] = useState<number | null>(null);
  const to = item.case_id ? `/cases/${item.case_id}` : "/history";

  return (
    <div
      className={`notification-item-row ${item.severity.toLowerCase()}`}
      onPointerDown={(event) => setStartX(event.clientX)}
      onPointerUp={(event) => {
        if (startX !== null && Math.abs(event.clientX - startX) > 70) onDismiss(item.id);
        setStartX(null);
      }}
    >
      <NavLink to={to} className="notification-item-content" onClick={onOpen}>
        <strong>{item.title}</strong>
        <span>{item.message}</span>
      </NavLink>
      <button className="notification-dismiss" onClick={() => onDismiss(item.id)} aria-label="Dismiss notification">
        <X size={15} />
      </button>
    </div>
  );
}
