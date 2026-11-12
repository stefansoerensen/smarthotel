import { describe, expect, it } from "vitest";
import { suggestCode, suggestDeviceCode } from "./codes";

describe("suggestCode", () => {
  it("turns a name into an upper-case code with umlauts spelled out", () => {
    expect(suggestCode("Hotelgruppe Nord", { maxLength: 20 })).toBe("HOTELGRUPPE-NORD");
    expect(suggestCode("Neubau Düsseldorf-Süd", { maxLength: 20 })).toBe("NEUBAU-DUESSELDORF-S");
    expect(suggestCode("  Straße & Co. ", { maxLength: 20 })).toBe("STRASSE-CO");
  });

  it("returns an empty string when nothing usable is left", () => {
    expect(suggestCode("  !!  ", { maxLength: 20 })).toBe("");
  });

  it("does not end on a dash after cutting", () => {
    expect(suggestCode("Hotelgruppe Nordsee Ost", { maxLength: 12 })).toBe("HOTELGRUPPE");
  });

  it("adds a number when the code is taken, case-insensitively", () => {
    expect(suggestCode("Nord", { maxLength: 20, taken: ["NORD", "nord-2"] })).toBe("NORD-3");
  });

  it("keeps the numbered code within the maximum length", () => {
    expect(suggestCode("Hotelgruppe Nordsee", { maxLength: 12, taken: ["HOTELGRUPPE"] })).toBe(
      "HOTELGRUPP-2",
    );
  });
});

describe("suggestDeviceCode", () => {
  it("combines location and kind", () => {
    expect(suggestDeviceCode({ location: "101", kind: "smoke_detector", name: "Rauchmelder" })).toBe(
      "101-SMOKE-DETECTOR",
    );
  });

  it("falls back to the name without a location", () => {
    expect(suggestDeviceCode({ location: "", kind: "meter", name: "Hauptzähler Strom" })).toBe(
      "HAUPTZAEHLER-STROM",
    );
  });

  it("keeps dots and slashes of a location", () => {
    expect(suggestDeviceCode({ location: "EG/Lobby", kind: "light", name: "" })).toBe("EG/LOBBY-LIGHT");
  });

  it("avoids codes already in the registry", () => {
    expect(
      suggestDeviceCode({ location: "101", kind: "valve", name: "", taken: ["101-VALVE"] }),
    ).toBe("101-VALVE-2");
  });
});
