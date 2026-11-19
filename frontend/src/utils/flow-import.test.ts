import { describe, expect, it } from "vitest";
import { planFlowImport } from "./flow-import";

function file(path: string, lastModified = 0): File {
  const name = path.split("/").pop()!;
  const f = new File(["x"], name, { lastModified });
  Object.defineProperty(f, "webkitRelativePath", { value: path.includes("/") ? path : "" });
  return f;
}

const IDS = ["E1S1", "E1S10", "E1S02"];

describe("planFlowImport", () => {
  it("matches by package folder first, whatever the video is called", () => {
    const plan = planFlowImport([file("pkg/02_E1S10/flow_video_8f3a.mp4")], IDS);
    expect(plan.matches.map((m) => m.id)).toEqual(["E1S10"]);
  });

  it("falls back to an id in the file name without confusing E1S1 and E1S10", () => {
    const plan = planFlowImport([file("e1s1.mp4"), file("take-E1S10-final.MOV")], IDS);
    expect(plan.matches.map((m) => [m.id, m.file.name])).toEqual([
      ["E1S1", "e1s1.mp4"],
      ["E1S10", "take-E1S10-final.MOV"],
    ]);
  });

  it("keeps the newest video per shot and reports the rest", () => {
    const older = file("pkg/03_E1S02/a.mp4", 1);
    const newer = file("pkg/03_E1S02/b.mp4", 2);
    const plan = planFlowImport([newer, older], IDS);
    expect(plan.matches[0].file).toBe(newer);
    expect(plan.superseded).toEqual([older]);
  });

  it("ignores package images and prompts, reports videos it cannot place", () => {
    const stray = file("pkg/random.mp4");
    const plan = planFlowImport([file("pkg/01_E1S1/start_frame.png"), file("pkg/01_E1S1/prompt.txt"), stray], IDS);
    expect(plan.matches).toEqual([]);
    expect(plan.unmatched).toEqual([stray]);
  });

  it("orders matches by shot order, not by file order", () => {
    const plan = planFlowImport([file("E1S02.mp4"), file("E1S1.mp4")], IDS);
    expect(plan.matches.map((m) => m.id)).toEqual(["E1S1", "E1S02"]);
  });
});
