import { useState } from "react";
import { importAddresses } from "../services/devices";
import type { AddressImport, ApiError } from "../types";
import { buttonClass, inputClass } from "./Field";

interface AddressImportDialogProps {
  propertyCode: string;
  onDone: () => void;
}

/** Paste or load a list of bus addresses, check it, then apply it. */
export default function AddressImportDialog({ propertyCode, onDone }: AddressImportDialogProps) {
  const [text, setText] = useState("");
  const [preview, setPreview] = useState<AddressImport | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function run(apply: boolean) {
    setError(null);
    try {
      const result = await importAddresses(propertyCode, text, apply);
      if (apply) {
        setText("");
        setPreview(null);
        onDone();
      } else {
        setPreview(result);
      }
    } catch (err) {
      setError((err as ApiError).message);
    }
  }

  async function loadFile(file: File) {
    setText(await file.text());
    setPreview(null);
  }

  const count = preview?.changes.length ?? 0;
  return (
    <section aria-label="Busadressen importieren" className="flex flex-col gap-3 rounded-lg bg-white p-4 shadow-sm">
      <h3 className="text-sm font-semibold">Busadressen importieren</h3>
      <p className="text-xs text-ink/60">
        Eine Zeile je Gerät: <code>Code;Adresse</code>, z. B. <code>101-VALVE;1/2/3</code>. Ein Gruppenadressen-Export aus der ETS (CSV) geht
        auch, wenn die Gruppenadressen wie die Geräte heißen.
      </p>
      <label className="flex flex-col gap-1 text-xs font-medium text-ink/70">
        Adressliste
        <textarea
          className={`${inputClass} h-28 font-mono text-xs`}
          value={text}
          onChange={(e) => {
            setText(e.target.value);
            setPreview(null);
          }}
        />
      </label>
      <div className="flex flex-wrap items-center gap-2">
        <input
          type="file"
          accept=".csv,.txt,text/csv,text/plain"
          aria-label="Datei laden"
          className="text-xs"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) {
              void loadFile(file);
            }
          }}
        />
        <button type="button" className="rounded border border-burgundy px-3 py-1.5 text-sm text-burgundy hover:bg-burgundy-light disabled:opacity-50" disabled={!text.trim()} onClick={() => void run(false)}>
          Prüfen
        </button>
        {preview && count > 0 && (
          <button type="button" className={buttonClass} onClick={() => void run(true)}>
            {count === 1 ? "1 Adresse übernehmen" : `${count} Adressen übernehmen`}
          </button>
        )}
      </div>
      {preview && (
        <div className="flex flex-col gap-1 text-xs">
          {count === 0 && <p className="text-ink/60">Keine Änderungen.</p>}
          {preview.changes.map((c) => (
            <p key={c.line}>
              <span className="font-mono">{c.device_code}</span>: {c.old ?? "–"} → <span className="font-mono">{c.new}</span>
            </p>
          ))}
          {preview.errors.map((e) => (
            <p key={`e${e.line}`} className="text-burgundy">{`Zeile ${e.line}: ${e.message}`}</p>
          ))}
        </div>
      )}
      {error && (
        <p role="alert" className="text-burgundy">
          {error}
        </p>
      )}
    </section>
  );
}
