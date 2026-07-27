import { useEffect, useState } from "react";
import {
  BarChart3,
  LogOut,
  Menu,
  MessageSquareText,
  Newspaper,
  Radar,
  Settings,
  TimerReset,
  X,
} from "lucide-react";
import { api, clearSession, readSession } from "./api";
import { AuthPage } from "./pages/AuthPage";
import { CommentsPage } from "./pages/CommentsPage";
import { OverviewPage } from "./pages/OverviewPage";
import { PostsPage } from "./pages/PostsPage";
import { RunsPage } from "./pages/RunsPage";
import { SettingsPage } from "./pages/SettingsPage";
import type { User } from "./types";

type RouteName = "overview" | "posts" | "comments" | "runs" | "settings";

const navItems = [
  { route: "overview" as const, label: "Tổng quan", icon: BarChart3 },
  { route: "posts" as const, label: "Bài viết", icon: Newspaper },
  { route: "comments" as const, label: "Bình luận", icon: MessageSquareText },
  { route: "runs" as const, label: "Lượt thu thập", icon: TimerReset },
  { route: "settings" as const, label: "Cài đặt", icon: Settings },
];

function routeFromHash(): RouteName {
  const route = window.location.hash.replace(/^#\/?/, "");
  return navItems.some((item) => item.route === route)
    ? (route as RouteName)
    : "overview";
}

export default function App() {
  const initialSession = readSession();
  const [user, setUser] = useState<User | null>(initialSession?.user || null);
  const [route, setRoute] = useState<RouteName>(routeFromHash);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    const changeRoute = () => {
      setRoute(routeFromHash());
      setMenuOpen(false);
      window.scrollTo({ top: 0, behavior: "auto" });
    };
    const expireSession = () => setUser(null);
    window.addEventListener("hashchange", changeRoute);
    window.addEventListener("talent-radar:session-expired", expireSession);
    if (initialSession) {
      void api.me().then(setUser).catch(() => setUser(null));
    }
    if (!window.location.hash) window.location.hash = "/overview";
    return () => {
      window.removeEventListener("hashchange", changeRoute);
      window.removeEventListener("talent-radar:session-expired", expireSession);
    };
  }, []);

  async function logout() {
    try {
      await api.logout();
    } catch {
      // Local session still needs to be cleared if the API is unavailable.
    }
    clearSession();
    setUser(null);
  }

  if (!user) return <AuthPage onAuthenticated={setUser} />;

  return (
    <div className="app-shell">
      {menuOpen && (
        <button
          className="mobile-backdrop"
          type="button"
          onClick={() => setMenuOpen(false)}
          aria-label="Đóng menu"
        />
      )}
      <aside className={`sidebar ${menuOpen ? "sidebar-open" : ""}`}>
        <div className="sidebar-brand">
          <span>
            <Radar size={22} />
          </span>
          <strong>Talent Radar</strong>
          <button
            className="mobile-close"
            type="button"
            onClick={() => setMenuOpen(false)}
            aria-label="Đóng menu"
          >
            <X size={19} />
          </button>
        </div>
        <nav>
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <a
                href={`#/${item.route}`}
                key={item.route}
                className={route === item.route ? "active" : ""}
              >
                <Icon size={19} />
                <span>{item.label}</span>
              </a>
            );
          })}
        </nav>
        <div className="sidebar-account">
          <div className="avatar">{user.email.slice(0, 1).toUpperCase()}</div>
          <div>
            <strong>{user.email.split("@")[0]}</strong>
            <span>{user.email}</span>
          </div>
          <button
            type="button"
            onClick={logout}
            title="Đăng xuất"
            aria-label="Đăng xuất"
          >
            <LogOut size={18} />
          </button>
        </div>
      </aside>
      <div className="main-column">
        <header className="mobile-header">
          <button
            className="icon-button"
            type="button"
            onClick={() => setMenuOpen(true)}
            aria-label="Mở menu"
          >
            <Menu size={20} />
          </button>
          <div>
            <Radar size={19} />
            <strong>Talent Radar</strong>
          </div>
        </header>
        <main className="page-content">
          {route === "overview" && <OverviewPage />}
          {route === "posts" && <PostsPage />}
          {route === "comments" && <CommentsPage />}
          {route === "runs" && <RunsPage />}
          {route === "settings" && <SettingsPage />}
        </main>
      </div>
    </div>
  );
}
