import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import Field, { buttonClass, inputClass } from "../components/Field";
import { useAuthStore } from "../hooks/useAuthStore";
import { listTenants } from "../services/estate";
import { changeOwnPassword, createUser, listUsers, patchUser } from "../services/users";
import type { ApiError, Tenant, UserEntry } from "../types";

const small = "rounded px-2 py-1 text-xs hover:bg-burgundy-light";

/** Users: admins manage everyone, operators see their colleagues; everyone changes their password. */
export default function UsersPage() {
  const me = useAuthStore((s) => s.user);
  const isAdmin = me?.role === "admin";
  const [users, setUsers] = useState<UserEntry[]>([]);
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [form, setForm] = useState<{ username: string; password: string; role: "admin" | "operator"; tenant: string }>({
    username: "",
    password: "",
    role: "operator",
    tenant: "",
  });
  const [own, setOwn] = useState({ old: "", next: "" });
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);

  const load = useCallback(async () => {
    const [u, t] = await Promise.all([listUsers(), listTenants()]);
    setUsers(u.items);
    setTenants(t.items);
    setForm((f) => ({ ...f, tenant: f.tenant || t.items[0]?.code || "" }));
  }, []);

  useEffect(() => {
    load().catch((err: ApiError) => setError(err.message));
  }, [load]);

  async function run(action: () => Promise<void>, done?: string) {
    setError(null);
    setStatus(null);
    try {
      await action();
      if (done) {
        setStatus(done);
      }
    } catch (err) {
      setError((err as ApiError).message);
    }
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    void run(async () => {
      await createUser({
        username: form.username.trim(),
        password: form.password,
        role: form.role,
        ...(form.role === "operator" ? { tenant_code: form.tenant } : {}),
      });
      setForm((f) => ({ ...f, username: "", password: "" }));
      await load();
    }, "Benutzer angelegt");
  }

  function toggle(user: UserEntry) {
    const verb = user.is_active ? "deaktivieren" : "aktivieren";
    if (!window.confirm(`${user.username} ${verb}?`)) {
      return;
    }
    void run(async () => {
      await patchUser(user.username, { is_active: !user.is_active });
      await load();
    });
  }

  function reset(user: UserEntry) {
    const password = window.prompt(`Neues Passwort für ${user.username} (mindestens 10 Zeichen)`);
    if (password) {
      void run(() => patchUser(user.username, { password }).then(() => undefined), `Passwort von ${user.username} gesetzt`);
    }
  }

  function changeOwn(event: FormEvent) {
    event.preventDefault();
    void run(async () => {
      await changeOwnPassword(own.old, own.next);
      setOwn({ old: "", next: "" });
    }, "Passwort geändert");
  }

  return (
    <section className="flex flex-col gap-6">
      <h1 className="text-xl font-semibold">Benutzer</h1>
      <table className="w-full overflow-hidden rounded-lg bg-white text-left shadow-sm">
        <thead className="bg-burgundy-light text-xs text-ink/70">
          <tr>
            <th className="p-2">Benutzer</th>
            <th className="p-2">Rolle</th>
            <th className="p-2">Mandant</th>
            <th className="p-2">Status</th>
            {isAdmin && <th className="p-2"><span className="sr-only">Aktionen</span></th>}
          </tr>
        </thead>
        <tbody className="divide-y divide-ink/10">
          {users.map((u) => (
            <tr key={u.username} className={u.is_active ? "" : "text-ink/40"}>
              <td className="p-2">{u.username}</td>
              <td className="p-2">{u.role === "admin" ? "Admin" : "Betrieb"}</td>
              <td className="p-2">{u.tenant_code ?? "alle"}</td>
              <td className="p-2">{u.is_active ? "aktiv" : "deaktiviert"}</td>
              {isAdmin && (
                <td className="whitespace-nowrap p-2 text-right">
                  <button type="button" className={small} onClick={() => reset(u)}>
                    Passwort zurücksetzen
                  </button>
                  {u.username !== me?.username && (
                    <button type="button" className={small} onClick={() => toggle(u)}>
                      {u.is_active ? "Deaktivieren" : "Aktivieren"}
                    </button>
                  )}
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>

      {isAdmin && (
        <form aria-label="Benutzer anlegen" onSubmit={submit} className="grid grid-cols-5 items-end gap-3 rounded-lg bg-white p-4 shadow-sm">
          <Field label="Benutzername">
            <input className={inputClass} value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} />
          </Field>
          <Field label="Startpasswort">
            <input className={inputClass} type="password" value={form.password} autoComplete="new-password" onChange={(e) => setForm({ ...form, password: e.target.value })} />
          </Field>
          <Field label="Rolle">
            <select className={inputClass} value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value as "admin" | "operator" })}>
              <option value="operator">Betrieb (ein Mandant)</option>
              <option value="admin">Admin (alle)</option>
            </select>
          </Field>
          <Field label="Mandant">
            <select className={inputClass} value={form.tenant} disabled={form.role === "admin"} onChange={(e) => setForm({ ...form, tenant: e.target.value })}>
              {tenants.map((t) => (
                <option key={t.code} value={t.code}>
                  {t.code} – {t.name}
                </option>
              ))}
            </select>
          </Field>
          <button type="submit" className={buttonClass} disabled={!form.username.trim() || form.password.length < 10 || (form.role === "operator" && !form.tenant)}>
            Benutzer anlegen
          </button>
          <p className="col-span-5 text-xs text-ink/60">Passwörter haben mindestens 10 Zeichen. Der Benutzer kann sein Passwort danach selbst ändern.</p>
        </form>
      )}

      <form aria-label="Eigenes Passwort ändern" onSubmit={changeOwn} className="grid grid-cols-3 items-end gap-3 rounded-lg bg-white p-4 shadow-sm">
        <Field label="Aktuelles Passwort">
          <input className={inputClass} type="password" value={own.old} autoComplete="current-password" onChange={(e) => setOwn({ ...own, old: e.target.value })} />
        </Field>
        <Field label="Neues Passwort">
          <input className={inputClass} type="password" value={own.next} autoComplete="new-password" onChange={(e) => setOwn({ ...own, next: e.target.value })} />
        </Field>
        <button type="submit" className={buttonClass} disabled={!own.old || own.next.length < 10}>
          Passwort ändern
        </button>
      </form>

      {status && (
        <p role="status" className="text-sm">
          {status}
        </p>
      )}
      {error && (
        <p role="alert" className="text-burgundy">
          {error}
        </p>
      )}
    </section>
  );
}
