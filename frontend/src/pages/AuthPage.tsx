import { useState, type FormEvent } from "react";
import { LoaderCircle, Radar } from "lucide-react";
import { api, storeSession } from "../api";
import type { User } from "../types";

export function AuthPage({
  onAuthenticated,
}: {
  onAuthenticated: (user: User) => void;
}) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      const result =
        mode === "login"
          ? await api.login(email, password)
          : await api.register(email, password);
      storeSession(result);
      onAuthenticated(result.user);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Không thể đăng nhập.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="auth-shell">
      <section className="auth-panel">
        <div className="brand-mark">
          <Radar size={26} />
        </div>
        <h1>Talent Radar</h1>
        <p>Không gian theo dõi thảo luận mạng xã hội.</p>
        <div className="segmented-control" role="tablist">
          <button
            type="button"
            className={mode === "login" ? "active" : ""}
            onClick={() => setMode("login")}
          >
            Đăng nhập
          </button>
          <button
            type="button"
            className={mode === "register" ? "active" : ""}
            onClick={() => setMode("register")}
          >
            Tạo tài khoản
          </button>
        </div>
        <form onSubmit={submit}>
          <label>
            Email
            <input
              type="email"
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
          </label>
          <label>
            Mật khẩu
            <input
              type="password"
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              minLength={8}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </label>
          {error && <div className="form-error">{error}</div>}
          <button className="primary-button auth-submit" disabled={submitting}>
            {submitting && <LoaderCircle className="spin" size={18} />}
            {mode === "login" ? "Đăng nhập" : "Tạo tài khoản"}
          </button>
        </form>
      </section>
    </main>
  );
}
