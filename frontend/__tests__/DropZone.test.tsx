import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import DropZone, { MAX_BYTES, MAX_FILES, validateFiles } from "@/components/DropZone";

function makeFile(name: string, sizeBytes: number, type = "text/plain"): File {
  const file = new File(["x".repeat(Math.min(sizeBytes, 10))], name, { type });
  Object.defineProperty(file, "size", { value: sizeBytes });
  return file;
}

describe("validateFiles", () => {
  it("rejects more than the max file count", () => {
    const existing = Array.from({ length: MAX_FILES }, (_, i) => makeFile(`a${i}.txt`, 10));
    const { error, files } = validateFiles(existing, [makeFile("one-too-many.txt", 10)]);
    expect(error).toMatch(/up to 5 files/i);
    expect(files).toHaveLength(MAX_FILES);
  });

  it("rejects a disallowed file type", () => {
    const { error } = validateFiles([], [makeFile("virus.exe", 10, "application/octet-stream")]);
    expect(error).toMatch(/not an allowed file type/i);
  });

  it("rejects an oversized file", () => {
    const { error } = validateFiles([], [makeFile("big.pdf", MAX_BYTES + 1, "application/pdf")]);
    expect(error).toMatch(/larger than 5 mb/i);
  });

  it("accepts a valid file within limits", () => {
    const { error, files } = validateFiles([], [makeFile("ok.pdf", 100, "application/pdf")]);
    expect(error).toBeNull();
    expect(files).toHaveLength(1);
  });
});

describe("DropZone component", () => {
  it("shows an error and does not add the file when the type is disallowed", async () => {
    const user = userEvent.setup();
    const onChange = jest.fn();
    render(<DropZone id="attachments" files={[]} onChange={onChange} />);

    const input = document.getElementById("attachments") as HTMLInputElement;
    await user.upload(input, makeFile("virus.exe", 10, "application/octet-stream"));

    expect(await screen.findByRole("alert")).toHaveTextContent(/not an allowed file type/i);
    expect(onChange).not.toHaveBeenCalled();
  });

  it("shows an error before upload when the file is oversized", async () => {
    const user = userEvent.setup();
    const onChange = jest.fn();
    render(<DropZone id="attachments" files={[]} onChange={onChange} />);

    const input = document.getElementById("attachments") as HTMLInputElement;
    await user.upload(input, makeFile("big.pdf", MAX_BYTES + 1, "application/pdf"));

    expect(await screen.findByRole("alert")).toHaveTextContent(/larger than 5 mb/i);
    expect(onChange).not.toHaveBeenCalled();
  });

  it("adds a valid file and lists it", async () => {
    const user = userEvent.setup();
    const onChange = jest.fn();
    render(<DropZone id="attachments" files={[]} onChange={onChange} />);

    const input = document.getElementById("attachments") as HTMLInputElement;
    await user.upload(input, makeFile("evidence.pdf", 100, "application/pdf"));

    expect(onChange).toHaveBeenCalledWith([expect.objectContaining({ name: "evidence.pdf" })]);
  });
});
