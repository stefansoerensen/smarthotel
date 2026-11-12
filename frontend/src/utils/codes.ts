/**
 * Code suggestions for tenants, properties and devices.
 *
 * Codes appear in URLs and event entity codes, so they stay short, upper case and ASCII. The user
 * can always overwrite a suggestion; the backend still checks uniqueness.
 */

const UMLAUTS: Record<string, string> = { Ä: "AE", Ö: "OE", Ü: "UE", ß: "SS" };

interface SuggestOptions {
  maxLength: number;
  /** Characters kept besides A–Z, 0–9 and the dash (devices also allow "." and "/"). */
  keep?: string;
  taken?: readonly string[];
}

function normalise(text: string, keep: string): string {
  const escaped = keep.replace(/[.*+?^${}()|[\]\\/-]/g, "\\$&");
  const outside = new RegExp(`[^A-Z0-9${escaped}]+`, "g");
  return text
    .toUpperCase()
    .replace(/[ÄÖÜß]/g, (ch) => UMLAUTS[ch] ?? ch)
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(outside, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "");
}

function cut(code: string, maxLength: number): string {
  return code.slice(0, maxLength).replace(/-+$/, "");
}

/** Suggest a code from free text; adds -2, -3 … when the code is already taken. */
export function suggestCode(text: string, { maxLength, keep = "", taken = [] }: SuggestOptions): string {
  const base = cut(normalise(text, keep), maxLength);
  if (!base) {
    return "";
  }
  const used = new Set(taken.map((code) => code.toUpperCase()));
  if (!used.has(base)) {
    return base;
  }
  for (let n = 2; n < 1000; n += 1) {
    const suffix = `-${n}`;
    const candidate = `${cut(base, maxLength - suffix.length)}${suffix}`;
    if (!used.has(candidate)) {
      return candidate;
    }
  }
  return base;
}

interface DeviceCodeInput {
  location: string;
  kind: string;
  name: string;
  taken?: readonly string[];
}

/** Suggest a device code: "<location>-<kind>" when a location is set, else from the name. */
export function suggestDeviceCode({ location, kind, name, taken = [] }: DeviceCodeInput): string {
  const text = location.trim() ? `${location} ${kind}` : name;
  return suggestCode(text, { maxLength: 60, keep: "./", taken });
}
