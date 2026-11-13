import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import * as devices from "../services/devices";
import AddressImportDialog from "./AddressImportDialog";

describe("AddressImportDialog", () => {
  it("previews, then applies the import", async () => {
    const run = vi
      .spyOn(devices, "importAddresses")
      .mockResolvedValueOnce({
        applied: false,
        changes: [{ line: 2, device_code: "101-VALVE", old: null, new: "1/2/3" }],
        errors: [{ line: 3, message: "Gerät NOPE gibt es in diesem Haus nicht" }],
      })
      .mockResolvedValueOnce({ applied: true, changes: [{ line: 2, device_code: "101-VALVE", old: null, new: "1/2/3" }], errors: [] });
    const done = vi.fn();
    render(<AddressImportDialog propertyCode="HAM1" onDone={done} />);
    await userEvent.type(screen.getByLabelText("Adressliste"), "101-VALVE;1/2/3");
    await userEvent.click(screen.getByRole("button", { name: "Prüfen" }));
    expect(run).toHaveBeenNthCalledWith(1, "HAM1", "101-VALVE;1/2/3", false);
    expect(await screen.findByText("Zeile 3: Gerät NOPE gibt es in diesem Haus nicht")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "1 Adresse übernehmen" }));
    expect(run).toHaveBeenNthCalledWith(2, "HAM1", "101-VALVE;1/2/3", true);
    expect(done).toHaveBeenCalled();
  });
});
