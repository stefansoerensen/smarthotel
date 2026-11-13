import { useEffect, useState } from "react";
import { listCommands } from "../services/devices";
import type { ApiError, Command } from "../types";

const STATUS: Record<Command["status"], string> = {
  pending: "offen",
  sent: "gesendet",
  done: "erledigt",
  failed: "fehlgeschlagen",
  refused: "abgelehnt",
};
const time = new Intl.DateTimeFormat("de-DE", { dateStyle: "short", timeStyle: "short" });
const num = new Intl.NumberFormat("de-DE", { maximumFractionDigits: 2 });

/** The last commands sent to the gateways of a property. */
export default function CommandsPanel({ propertyCode }: { propertyCode: string }) {
  const [items, setItems] = useState<Command[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listCommands(propertyCode)
      .then((page) => setItems(page.items))
      .catch((err: ApiError) => setError(err.message));
  }, [propertyCode]);

  if (items.length === 0 && !error) {
    return null;
  }
  return (
    <section className="flex flex-col gap-2">
      <h2 className="text-base font-semibold">Letzte Befehle</h2>
      <table aria-label="Befehle" className="w-full overflow-hidden rounded-lg bg-white text-left text-sm shadow-sm">
        <thead className="bg-burgundy-light text-xs text-ink/70">
          <tr>
            <th className="p-2">Zeit</th>
            <th className="p-2">Gerät</th>
            <th className="p-2">Wert</th>
            <th className="p-2">Status</th>
            <th className="p-2">Hinweis</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-ink/10">
          {items.map((c) => (
            <tr key={c.id}>
              <td className="p-2 text-xs text-ink/60">{time.format(new Date(c.created_at))}</td>
              <td className="p-2 font-mono text-xs">{c.device_code}</td>
              <td className="p-2">{num.format(c.value)}</td>
              <td className="p-2">
                <span className={`rounded px-1.5 py-0.5 text-xs ${c.status === "done" ? "bg-bone" : c.status === "refused" || c.status === "failed" ? "bg-burgundy text-white" : "bg-burgundy-light text-burgundy"}`}>
                  {STATUS[c.status]}
                </span>
              </td>
              <td className="p-2 text-xs text-ink/60">{c.detail ?? ""}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {error && (
        <p role="alert" className="text-burgundy">
          {error}
        </p>
      )}
    </section>
  );
}
