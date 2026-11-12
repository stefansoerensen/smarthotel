import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Link } from "react-router-dom";
import Field, { buttonClass, inputClass } from "../components/Field";
import TenantItem from "../components/TenantItem";
import { useAuthStore } from "../hooks/useAuthStore";
import { createProperty, createTenant, listProperties, listTenants, patchTenant } from "../services/estate";
import type { ApiError, Property, Tenant } from "../types";
import { suggestCode } from "../utils/codes";

export default function PropertiesPage() {
  const isAdmin = useAuthStore((s) => s.user?.role === "admin");
  const [properties, setProperties] = useState<Property[]>([]);
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [error, setError] = useState<string | null>(null);
  // A code is null while it follows the suggestion and holds the user's text once they edit it.
  const [form, setForm] = useState<{ tenant_code: string; code: string | null; name: string; city: string }>({
    tenant_code: "",
    code: null,
    name: "",
    city: "",
  });
  const [tenantForm, setTenantForm] = useState<{ code: string | null; name: string }>({ code: null, name: "" });
  const tenantCode =
    tenantForm.code ?? suggestCode(tenantForm.name, { maxLength: 20, taken: tenants.map((t) => t.code) });
  const propertyCode =
    form.code ?? suggestCode(form.name, { maxLength: 20, taken: properties.map((p) => p.code) });

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
      await createProperty({
        tenant_code: form.tenant_code,
        code: propertyCode,
        name: form.name,
        city: form.city || undefined,
      });
      setForm((f) => ({ ...f, code: null, name: "", city: "" }));
      await load();
    } catch (err) {
      setError((err as ApiError).message);
    }
  }

  async function submitTenant(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      const tenant = await createTenant({ code: tenantCode, name: tenantForm.name });
      setTenantForm({ code: null, name: "" });
      setForm((f) => ({ ...f, tenant_code: tenant.code }));
      await load();
    } catch (err) {
      const apiError = err as ApiError;
      setError(
        apiError.code === "tenant.code_taken" ? "Mandanten-Code ist schon vergeben" : apiError.message,
      );
    }
  }

  async function renameTenant(tenantCode: string, name: string) {
    setError(null);
    try {
      await patchTenant(tenantCode, { name });
      await load();
    } catch (err) {
      setError((err as ApiError).message);
      throw err;
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
      {isAdmin && tenants.length > 0 && (
        <div className="flex flex-col gap-2">
          <h2 className="text-base font-semibold">Mandanten</h2>
          <ul className="divide-y divide-ink/10 rounded-lg bg-white shadow-sm">
            {tenants.map((t) => (
              <TenantItem key={t.code} tenant={t} onRename={(name) => renameTenant(t.code, name)} />
            ))}
          </ul>
        </div>
      )}
      {isAdmin && (
        <form
          aria-label="Mandant anlegen"
          onSubmit={submitTenant}
          className="grid grid-cols-5 items-end gap-3 rounded-lg bg-white p-4 shadow-sm"
        >
          <Field label="Mandanten-Code">
            <input className={inputClass} value={tenantCode} onChange={(e) => setTenantForm({ ...tenantForm, code: e.target.value || null })} />
          </Field>
          <div className="col-span-3">
            <Field label="Mandanten-Name">
              <input className={inputClass} value={tenantForm.name} onChange={(e) => setTenantForm({ ...tenantForm, name: e.target.value })} />
            </Field>
          </div>
          <button type="submit" className={buttonClass} disabled={!tenantCode || !tenantForm.name}>
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
            <input className={inputClass} value={propertyCode} onChange={(e) => setForm({ ...form, code: e.target.value || null })} />
          </Field>
          <Field label="Name">
            <input className={inputClass} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </Field>
          <Field label="Ort">
            <input className={inputClass} value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })} />
          </Field>
          <button type="submit" className={buttonClass} disabled={!form.tenant_code || !propertyCode || !form.name}>
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
