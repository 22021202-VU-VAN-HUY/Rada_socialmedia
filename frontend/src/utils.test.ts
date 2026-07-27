import { describe, expect, it } from "vitest";
import { startForRange, statusLabel } from "./utils";

describe("UI formatting", () => {
  it("keeps the all-time filter open ended", () => {
    expect(startForRange("all")).toBeUndefined();
  });

  it("translates collection states", () => {
    expect(statusLabel("running")).toBe("Đang lấy dữ liệu");
    expect(statusLabel("completed")).toBe("Hoàn tất");
  });
});
