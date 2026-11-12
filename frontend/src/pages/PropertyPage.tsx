import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import DeviceRegistry from "../components/DeviceRegistry";
import GatewaysPanel from "../components/GatewaysPanel";
import HotelOsTab from "../components/HotelOsTab";
import Field, { buttonClass, inputClass } from "../components/Field";
import RoomTypesTab from "../components/RoomTypesTab";
import RoomsTab from "../components/RoomsTab";
import { useAuthStore } from "../hooks/useAuthStore";
import { getCatalogue } from "../services/devices";
import { getProperty, patchProperty } from "../services/estate";
import type { ApiError, Catalogue, Property } from "../types";

const TABS = [
  { id: "zimmer", label: "Zimmer" },
  { id: "raumtypen", label: "Raumtypen" },
  { id: "geraete", label: "Geräte" },
  { id: "hotel-os", label: "Hotel OS" },
] as const;

export default function PropertyPage() {
  const { code = "" } = useParams();
  const [search, setSearch] = useSearchParams();
  const tab = TABS.find((t) => t.id === search.get("tab"))?.id ?? "zimmer";
  const [property, setProperty] = useState<Property | null>(null);
  const [catalogue, setCatalogue] = useState<Catalogue | null>(null);
  const [error, setError] = useState<string | null>(null);
  const isAdmin = useAuthStore((s) => s.user?.role === "admin");
  const [propertyDraft, setPropertyDraft] = useState<{
    name: string;
    street: string;
    postal_code: string;
    city: string;
  } | null>(null);

  useEffect(() => {
    Promise.all([getProperty(code), getCatalogue()])
      .then(([p, c]) => {
        setProperty(p);
        setCatalogue(c);
      })
      .catch((err: ApiError) => setError(err.message));
  }, [code]);

  async function run(action: () => Promise<unknown>) {
    setError(null);
    try {
      await action();
    } catch (err) {
      setError((err as ApiError).message);
      throw err;
    }
  }

  function editProperty() {
    if (property) {
      setPropertyDraft({
        name: property.name,
        street: property.street ?? "",
        postal_code: property.postal_code ?? "",
        city: property.city ?? "",
      });
    }
  }

  async function saveProperty(event: FormEvent) {
    event.preventDefault();
    if (!propertyDraft) {
      return;
    }
    await run(async () => {
      const updated = await patchProperty(code, {
        name: propertyDraft.name.trim(),
        street: propertyDraft.street.trim() || null,
        postal_code: propertyDraft.postal_code.trim() || null,
        city: propertyDraft.city.trim() || null,
      });
      setProperty(updated);
      setPropertyDraft(null);
    }).catch(() => undefined);
  }

  return (
    <section className="flex flex-col gap-6">
      {propertyDraft ? (
        <form
          aria-label="Haus bearbeiten"
          onSubmit={saveProperty}
          className="grid grid-cols-4 items-end gap-3 rounded-lg bg-white p-4 shadow-sm"
        >
          <Field label="Name">
            <input className={inputClass} value={propertyDraft.name} onChange={(e) => setPropertyDraft({ ...propertyDraft, name: e.target.value })} />
          </Field>
          <Field label="Straße">
            <input className={inputClass} value={propertyDraft.street} onChange={(e) => setPropertyDraft({ ...propertyDraft, street: e.target.value })} />
          </Field>
          <Field label="PLZ">
            <input className={inputClass} value={propertyDraft.postal_code} onChange={(e) => setPropertyDraft({ ...propertyDraft, postal_code: e.target.value })} />
          </Field>
          <Field label="Stadt">
            <input className={inputClass} value={propertyDraft.city} onChange={(e) => setPropertyDraft({ ...propertyDraft, city: e.target.value })} />
          </Field>
          <p className="col-span-2 text-xs text-ink/60">Code {code} bleibt; er steht in Links und Ereignissen.</p>
          <button type="button" className="rounded px-3 py-1.5 text-sm hover:bg-burgundy-light" onClick={() => setPropertyDraft(null)}>
            Abbrechen
          </button>
          <button type="submit" className={buttonClass} disabled={!propertyDraft.name.trim()}>
            Speichern
          </button>
        </form>
      ) : (
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-xl font-semibold">{property?.name ?? code}</h1>
            <p className="text-ink/60">
              {code}
              {property ? ` · ${property.tenant_code} · ${property.time_zone}` : ""}
              {property?.street || property?.city
                ? ` · ${[property.street, [property.postal_code, property.city].filter(Boolean).join(" ")].filter(Boolean).join(", ")}`
                : ""}
            </p>
          </div>
          {isAdmin && property && (
            <button type="button" className="rounded px-3 py-1.5 text-sm text-burgundy hover:bg-burgundy-light" onClick={editProperty}>
              Haus bearbeiten
            </button>
          )}
        </div>
      )}

      <nav role="tablist" aria-label="Bereiche des Hauses" className="flex gap-1 border-b border-ink/10">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            role="tab"
            aria-selected={tab === t.id}
            className={`-mb-px border-b-2 px-3 py-2 text-sm ${
              tab === t.id ? "border-burgundy font-medium text-burgundy" : "border-transparent text-ink/60 hover:text-ink"
            }`}
            onClick={() => setSearch({ tab: t.id }, { replace: true })}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {tab === "zimmer" && <RoomsTab propertyCode={code} />}
      {tab === "raumtypen" && (
        <RoomTypesTab propertyCode={code} catalogue={catalogue} />
      )}
      {tab === "geraete" && (
        <>
          <GatewaysPanel propertyCode={code} />
          <DeviceRegistry propertyCode={code} catalogue={catalogue} />
        </>
      )}
      {tab === "hotel-os" && <HotelOsTab propertyCode={code} />}
      {error && (
        <p role="alert" className="text-burgundy">
          {error}
        </p>
      )}
    </section>
  );
}
