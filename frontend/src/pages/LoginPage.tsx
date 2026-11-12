import { useState } from "react";
import type { FormEvent } from "react";
import Field, { buttonClass, inputClass } from "../components/Field";
import { useAuthStore } from "../hooks/useAuthStore";
import { login, me } from "../services/auth";
import type { ApiError } from "../types";

export default function LoginPage() {
  const setSession = useAuthStore((s) => s.setSession);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const token = await login(username, password);
      useAuthStore.setState({ token });
      setSession(token, await me());
    } catch (err) {
      const status = (err as ApiError).status;
      useAuthStore.setState({ token: null });
      setError(status === 429 ? "Zu viele Versuche, bitte eine Minute warten" : "Benutzer oder Passwort falsch");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-full items-center justify-center">
      <form onSubmit={submit} className="flex w-80 flex-col gap-4 rounded-lg bg-white p-6 shadow-sm">
        <h1 className="text-lg font-semibold text-burgundy">Smart Building</h1>
        <Field label="Benutzer">
          <input className={inputClass} value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" />
        </Field>
        <Field label="Passwort">
          <input className={inputClass} type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" />
        </Field>
        {error && (
          <p role="alert" className="text-sm text-burgundy">
            {error}
          </p>
        )}
        <button type="submit" className={buttonClass} disabled={busy || !username || !password}>
          Anmelden
        </button>
      </form>
    </div>
  );
}
