import { useState } from "react";
import type { Tenant } from "../types";
import { inputClass } from "./Field";

interface TenantItemProps {
  tenant: Tenant;
  onRename: (name: string) => Promise<void>;
}

const smallButton = "rounded px-2 py-1 text-xs hover:bg-burgundy-light";

/** One tenant in the admin list, with in-place renaming. The code never changes. */
export default function TenantItem({ tenant, onRename }: TenantItemProps) {
  const [draft, setDraft] = useState<string | null>(null);

  async function save() {
    if (draft === null) {
      return;
    }
    try {
      await onRename(draft.trim());
      setDraft(null);
    } catch {
      /* the page shows the error; the item stays in edit mode */
    }
  }

  return (
    <li aria-label={`Mandant ${tenant.code}`} className="flex items-center justify-between gap-3 p-3">
      <span className="font-mono text-xs text-ink/60">{tenant.code}</span>
      {draft === null ? (
        <span className="flex-1">{tenant.name}</span>
      ) : (
        <input
          aria-label={`Name von ${tenant.code}`}
          className={`${inputClass} flex-1`}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
        />
      )}
      {draft === null ? (
        <button type="button" className={smallButton} onClick={() => setDraft(tenant.name)}>
          Umbenennen
        </button>
      ) : (
        <span className="whitespace-nowrap">
          <button type="button" className={`${smallButton} font-medium text-burgundy`} disabled={!draft.trim()} onClick={save}>
            Speichern
          </button>
          <button type="button" className={smallButton} onClick={() => setDraft(null)}>
            Abbrechen
          </button>
        </span>
      )}
    </li>
  );
}
