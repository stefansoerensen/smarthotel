import { KeyRound } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { createGatewayToken, listGateways, registerGateway } from "../services/devices";
import type { ApiError, Gateway, GatewayToken } from "../types";
import { suggestCode } from "../utils/codes";
import Field, { buttonClass, inputClass } from "./Field";

interface GatewaysPanelProps {
  propertyCode: string;
}

const STATUS_LABEL: Record<Gateway["status"], string> = {
  provisioned: "noch nie verbunden",
  online: "online",
  offline: "offline",
  retired: "außer Betrieb",
};

const timeFormat = new Intl.DateTimeFormat("de-DE", { dateStyle: "short", timeStyle: "short" });

/** Edge gateways of a property: status, registration and tokens (ADR-0006). */
export default function GatewaysPanel({ propertyCode }: GatewaysPanelProps) {
  const [gateways, setGateways] = useState<Gateway[]>([]);
  const [form, setForm] = useState<{ name: string; code: string | null }>({ name: "", code: null });
  const [token, setToken] = useState<GatewayToken | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setGateways((await listGateways(propertyCode)).items);
  }, [propertyCode]);

  useEffect(() => {
    load().catch((err: ApiError) => setError(err.message));
  }, [load]);

  const code = form.code ?? suggestCode(form.name, { maxLength: 40, taken: gateways.map((g) => g.code) });

  async function register(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await registerGateway(propertyCode, { code, name: form.name.trim() });
      setForm({ name: "", code: null });
      await load();
    } catch (err) {
      setError((err as ApiError).message);
    }
  }

  async function newToken(gateway: Gateway) {
    if (gateway.has_token && !window.confirm(`Neuer Token für ${gateway.code}? Der bisherige funktioniert danach nicht mehr.`)) {
      return;
    }
    setError(null);
    try {
      setToken(await createGatewayToken(propertyCode, gateway.code));
      await load();
    } catch (err) {
      setError((err as ApiError).message);
    }
  }

  return (
    <section aria-label="Gateways" className="flex flex-col gap-3">
      <h2 className="text-base font-semibold">Gateways</h2>
      {gateways.length > 0 && (
        <ul className="divide-y divide-ink/10 rounded-lg bg-white shadow-sm">
          {gateways.map((g) => (
            <li key={g.code} aria-label={`Gateway ${g.code}`} className="flex items-center gap-3 p-3">
              <span className="font-mono text-xs">{g.code}</span>
              <span className="flex-1">{g.name}</span>
              <span
                className={`rounded px-2 py-0.5 text-xs ${
                  g.status === "online" ? "bg-ink text-white" : g.status === "offline" ? "bg-burgundy text-white" : "bg-bone"
                }`}
              >
                {STATUS_LABEL[g.status]}
              </span>
              <span className="w-28 text-right text-xs text-ink/50">{g.last_seen_at ? timeFormat.format(new Date(g.last_seen_at)) : "–"}</span>
              <button
                type="button"
                className="inline-flex items-center gap-1 rounded px-2 py-1 text-xs text-burgundy hover:bg-burgundy-light"
                onClick={() => void newToken(g)}
              >
                <KeyRound size={12} aria-hidden /> {g.has_token ? "Neuen Token erzeugen" : "Token erzeugen"}
              </button>
            </li>
          ))}
        </ul>
      )}
      {token && (
        <section aria-label={`Token für ${token.gateway_code}`} className="flex flex-col gap-2 rounded-lg border border-burgundy bg-white p-4">
          <p className="text-sm font-medium">Token für {token.gateway_code} – wird nur jetzt angezeigt.</p>
          <pre className="overflow-x-auto rounded bg-bone p-2 text-xs">
            {`docker run -d -v edge-${token.gateway_code.toLowerCase()}:/data \\\n  -e EDGE_CLOUD_URL=${window.location.origin} \\\n  -e EDGE_TOKEN=${token.token} \\\n  smarthotel-edge`}
          </pre>
          <button type="button" className="w-fit rounded px-2 py-1 text-xs hover:bg-burgundy-light" onClick={() => setToken(null)}>
            Ausblenden
          </button>
        </section>
      )}
      <form aria-label="Gateway registrieren" onSubmit={register} className="grid grid-cols-3 items-end gap-3 rounded-lg bg-white p-4 shadow-sm">
        <Field label="Name">
          <input className={inputClass} value={form.name} placeholder="z. B. Technik UG" onChange={(e) => setForm({ ...form, name: e.target.value })} />
        </Field>
        <Field label="Code">
          <input className={inputClass} value={code} onChange={(e) => setForm({ ...form, code: e.target.value || null })} />
        </Field>
        <button type="submit" className={buttonClass} disabled={!form.name.trim() || !code}>
          Gateway registrieren
        </button>
      </form>
      {error && (
        <p role="alert" className="text-burgundy">
          {error}
        </p>
      )}
    </section>
  );
}
