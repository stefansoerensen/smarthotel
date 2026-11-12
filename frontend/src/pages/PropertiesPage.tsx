import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Link } from "react-router-dom";
import Field, { buttonClass, inputClass } from "../components/Field";
import { useAuthStore } from "../hooks/useAuthStore";
import { createProperty, createTenant, listProperties, listTenants } from "../services/estate";
import type { ApiError, Property, Tenant } from "../types";

export default function PropertiesPage() {
  const isAdmin = useAuthStore((s) => s.user?.role === "admin");
  const [properties, setProperties] = useState<Property[]>([]);
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({ tenant_code: "", code: "", name: "", city: "" });
  const [tenantForm, setTenantForm] = useState({ code: "", name: "" });

  const load = useCallback(async () => {
    const [props, tens] = await Promise.all([listProperties(), listTenants()]);
    setProperties(props.items);
    setTenants(tens.items);
    setForm((f) => ({ ...f, tenant_code: f.tenant_code || tens.items[0]?.code || "" }));
  }, []);

  useEffect(() => {
    load().catch((err: ApiError) => setError(err.message));
  }, [load]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await createProperty({ ...form, city: form.city || undefined });
      setForm((f) => ({ ...f, code: "", name: "", city: "" }));
      await load();
    } catch (err) {
      setError((err as ApiError).message);
    }
  }

  async function submitTenant(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      const tenant = await createTenant({ code: tenantForm.code, name: tenantForm.name });
      setTenantForm({ code: "", name: "" });
      setForm((f) => ({ ...f, tenant_code: tenant.code }));
      await load();
    } catch (err) {
      const apiError = err as ApiError;
      setError(
        apiError.code === "tenant.code_taken" ? "Mandanten-Code ist schon vergeben" : apiError.message,
      );
    }
  }

  return (
    <section className="flex flex-col gap-6">
      <h1 className="text-xl font-semibold">Häuser</h1>
      <ul className="divide-y divide-ink/10 rounded-lg bg-white shadow-sm">
        {properties.length === 0 && <li className="p-4 text-ink/60">Noch kein Haus angelegt.</li>}
        {properties.map((p) => (
          <li key={p.code}>
            <Link to={`/properties/${p.code}`} className="flex justify-between p-4 hover:bg-burgundy-light">
              <span className="font-medium">{p.name}</span>
              <span className="text-ink/60">
                {p.code} · {p.tenant_code}
                {p.city ? ` · ${p.city}` : ""}
              </span>
            </Link>
          </li>
        ))}
      </ul>
      {isAdmin && (
        <form
          aria-label="Mandant anlegen"
          onSubmit={submitTenant}
          className="grid grid-cols-5 items-end gap-3 rounded-lg bg-white p-4 shadow-sm"
        >
          <Field label="Mandanten-Code">
            <input className={inputClass} value={tenantForm.code} onChange={(e) => setTenantForm({ ...tenantForm, code: e.target.value })} />
          </Field>
          <div className="col-span-3">
            <Field label="Mandanten-Name">
              <input className={inputClass} value={tenantForm.name} onChange={(e) => setTenantForm({ ...tenantForm, name: e.target.value })} />
            </Field>
          </div>
          <button type="submit" className={buttonClass} disabled={!tenantForm.code || !tenantForm.name}>
            Mandant anlegen
          </button>
        </form>
      )}
      {isAdmin && tenants.length === 0 && (
        <p className="text-ink/60">Zuerst einen Mandanten anlegen, dann ein Haus.</p>
      )}
      {isAdmin && tenants.length > 0 && (
        <form aria-label="Haus anlegen" onSubmit={submit} className="grid grid-cols-5 items-end gap-3 rounded-lg bg-white p-4 shadow-sm">
          <Field label="Mandant">
            <select className={inputClass} value={form.tenant_code} onChange={(e) => setForm({ ...form, tenant_code: e.target.value })}>
              {tenants.map((t) => (
                <option key={t.code} value={t.code}>
                  {t.code} – {t.name}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Code">
            <input className={inputClass} value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} />
          </Field>
          <Field label="Name">
            <input className={inputClass} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </Field>
          <Field label="Ort">
            <input className={inputClass} value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })} />
          </Field>
          <button type="submit" className={buttonClass} disabled={!form.tenant_code || !form.code || !form.name}>
            Haus anlegen
          </button>
        </form>
      )}
      {error && (
        <p role="alert" className="text-burgundy">
          {error}
        </p>
      )}
    </section>
  );
}
