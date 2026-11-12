import { describe, expect, it } from "vitest";
import { parseRoomCodes } from "./rooms";

describe("parseRoomCodes", () => {
  it("expands ranges and single rooms", () => {
    expect(parseRoomCodes("101-103, 201, 301-302")).toEqual({
      codes: ["101", "102", "103", "201", "301", "302"],
      error: null,
    });
  });

  it("keeps leading zeros and removes duplicates", () => {
    expect(parseRoomCodes("009-011; 010").codes).toEqual(["009", "010", "011"]);
  });

  it("accepts free room names", () => {
    expect(parseRoomCodes("Suite A, Suite B").codes).toEqual(["Suite A", "Suite B"]);
  });

  it("rejects reversed or oversized ranges", () => {
    expect(parseRoomCodes("120-101").error).toBe("Bereich 120-101 ist rückwärts");
    expect(parseRoomCodes("1-600").error).toBe("Höchstens 500 Zimmer auf einmal");
  });

  it("returns nothing for empty input", () => {
    expect(parseRoomCodes("  ")).toEqual({ codes: [], error: null });
  });
});
