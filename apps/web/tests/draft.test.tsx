import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { useDraft } from "@/lib/draft";

afterEach(() => window.sessionStorage.clear());

describe("useDraft (autosave of unsaved edits)", () => {
  it("restores an unsaved edit after a reload of the same block version", () => {
    const first = renderHook(() => useDraft("block:b1:v3", { text: "gốc" }));
    expect(first.result.current.restored).toBe(false);
    act(() => first.result.current.setValue({ text: "đang sửa" }));
    first.unmount();

    const again = renderHook(() => useDraft("block:b1:v3", { text: "gốc" }));
    expect(again.result.current.value).toEqual({ text: "đang sửa" });
    expect(again.result.current.restored).toBe(true);
  });

  it("does not resurface a draft over a newer server version", () => {
    const first = renderHook(() => useDraft("block:b1:v3", { text: "gốc" }));
    act(() => first.result.current.setValue({ text: "đang sửa" }));
    first.unmount();

    const newer = renderHook(() => useDraft("block:b1:v4", { text: "bản mới" }));
    expect(newer.result.current.value).toEqual({ text: "bản mới" });
    expect(newer.result.current.restored).toBe(false);
  });

  it("forgets the draft once it is saved or cancelled", () => {
    const first = renderHook(() => useDraft("block:b2:v1", { text: "gốc" }));
    act(() => first.result.current.setValue({ text: "đang sửa" }));
    act(() => first.result.current.discard({ text: "gốc" }));
    first.unmount();

    const again = renderHook(() => useDraft("block:b2:v1", { text: "gốc" }));
    expect(again.result.current.restored).toBe(false);
    expect(again.result.current.value).toEqual({ text: "gốc" });
  });
});
