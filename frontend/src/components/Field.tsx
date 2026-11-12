import type { ReactNode } from "react";

interface FieldProps {
  label: string;
  children: ReactNode;
}

/** A label wrapping its control, so the control gets the label as its accessible name. */
export default function Field({ label, children }: FieldProps) {
  return (
    <label className="flex flex-col gap-1 text-xs font-medium text-ink/70">
      {label}
      {children}
    </label>
  );
}

export const inputClass =
  "rounded border border-ink/20 bg-white px-2 py-1.5 text-sm text-ink focus:border-burgundy focus:outline-none";
export const buttonClass =
  "rounded bg-burgundy px-3 py-1.5 text-sm font-medium text-white hover:bg-burgundy/90 disabled:opacity-50";
