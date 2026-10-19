import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { FlowExchange } from "./FlowExchange";

function video(path: string): File {
  const f = new File(["x"], path.split("/").pop()!, { type: "video/mp4" });
  Object.defineProperty(f, "webkitRelativePath", { value: path });
  return f;
}

describe("FlowExchange 导入", () => {
  it("只上传对上且未在生成中的镜头，完成后刷新一次", async () => {
    const upload = vi.fn().mockResolvedValue({ asset_fingerprints: {} });
    const onImported = vi.fn();
    render(
      <FlowExchange
        projectName="demo"
        episode={1}
        ids={["E1S01", "E1S02", "E1S03"]}
        busyIds={new Set(["E1S02"])}
        upload={upload}
        onImported={onImported}
      />,
    );

    const click = vi.spyOn(HTMLInputElement.prototype, "click").mockImplementation(() => {});
    fireEvent.click(screen.getByRole("button", { name: "导入 Flow 视频" }));
    const input = click.mock.contexts[0] as HTMLInputElement;
    click.mockRestore();
    expect(input).toHaveAttribute("webkitdirectory");
    fireEvent.change(input, {
      target: {
        files: [
          video("pkg/01_E1S01/flow.mp4"),
          video("pkg/02_E1S02/flow.mp4"),
          video("pkg/stray.mp4"),
        ],
      },
    });

    expect(screen.getByText("将导入 1 个视频")).toBeInTheDocument();
    expect(screen.getByText("1 个镜头正在生成，已跳过")).toBeInTheDocument();
    expect(screen.getByText("pkg/stray.mp4")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "导入" }));

    await waitFor(() => expect(onImported).toHaveBeenCalledTimes(1));
    expect(upload).toHaveBeenCalledTimes(1);
    expect(upload.mock.calls[0][0]).toBe("E1S01");
  });
});
