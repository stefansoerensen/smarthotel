/** Parse room input such as "101-120, 201-210, Suite A" into room codes. */

const MAX_ROOMS = 500;

export interface ParsedRooms {
  codes: string[];
  error: string | null;
}

export function parseRoomCodes(input: string): ParsedRooms {
  const codes: string[] = [];
  for (const part of input.split(/[,;\n]+/)) {
    const item = part.trim();
    if (!item) {
      continue;
    }
    const range = item.match(/^(\d+)\s*-\s*(\d+)$/);
    if (!range) {
      codes.push(item);
      continue;
    }
    const [, from, to] = range;
    const start = Number(from);
    const end = Number(to);
    if (end < start) {
      return { codes: [], error: `Bereich ${item.replace(/\s/g, "")} ist rückwärts` };
    }
    if (end - start + 1 > MAX_ROOMS) {
      return { codes: [], error: `Höchstens ${MAX_ROOMS} Zimmer auf einmal` };
    }
    const width = from.length;
    for (let n = start; n <= end; n += 1) {
      codes.push(String(n).padStart(width, "0"));
    }
  }
  const unique = Array.from(new Set(codes));
  if (unique.length > MAX_ROOMS) {
    return { codes: [], error: `Höchstens ${MAX_ROOMS} Zimmer auf einmal` };
  }
  return { codes: unique, error: null };
}
