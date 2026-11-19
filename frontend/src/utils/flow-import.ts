/**
 * 把 Flow 下载回来的视频对回镜头。
 *
 * 任务包每个镜头一个目录「序号_镜头ID」（见 server/services/project/flow_package.py），用户把视频放进
 * 对应目录即可；放在别处时文件名里带上镜头 ID 也能对上。目录名优先，文件名其次。
 * 同一镜头有多个视频时取最后修改的那个——Flow 里重抽过几次，最后下载的通常是想要的。
 */

const VIDEO_FILE = /\.(mp4|mov|m4v|webm)$/i;
/** 与后端 _safe_name 同一套替换，目录名才对得上。 */
const UNSAFE_NAME = /[\\/:*?"<>|\s]+/g;

export interface FlowVideoMatch {
  id: string;
  file: File;
}

export interface FlowImportPlan {
  /** 按镜头顺序排列。 */
  matches: FlowVideoMatch[];
  /** 对不上任何镜头的视频。 */
  unmatched: File[];
  /** 因同一镜头已有更新的视频而没用上的。 */
  superseded: File[];
}

function escapeRegExp(text: string): string {
  return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function relativePath(file: File): string {
  return file.webkitRelativePath || file.name;
}

function matchId(file: File, ids: string[]): string | null {
  const segments = relativePath(file).split("/");
  const folders = segments.slice(0, -1);
  const byFolder = ids.find((id) => {
    const folderName = new RegExp(`^\\d+_${escapeRegExp(id.replace(UNSAFE_NAME, "_"))}$`, "i");
    return folders.some((folder) => folderName.test(folder));
  });
  if (byFolder) return byFolder;
  const stem = segments[segments.length - 1].replace(VIDEO_FILE, "");
  // 前后不能紧挨字母数字，E1S1 才不会认成 E1S10；多个命中取最长的那个
  const hits = ids.filter((id) => new RegExp(`(^|[^a-z0-9])${escapeRegExp(id)}($|[^a-z0-9])`, "i").test(stem));
  return hits.sort((a, b) => b.length - a.length)[0] ?? null;
}

export function planFlowImport(files: Iterable<File>, ids: string[]): FlowImportPlan {
  const byId = new Map<string, File>();
  const unmatched: File[] = [];
  const superseded: File[] = [];
  for (const file of files) {
    if (!VIDEO_FILE.test(file.name)) continue; // 任务包里的提示词与图片
    const id = matchId(file, ids);
    if (!id) {
      unmatched.push(file);
      continue;
    }
    const current = byId.get(id);
    if (!current) {
      byId.set(id, file);
    } else if (file.lastModified > current.lastModified) {
      superseded.push(current);
      byId.set(id, file);
    } else {
      superseded.push(file);
    }
  }
  const matches = ids.flatMap((id) => {
    const file = byId.get(id);
    return file ? [{ id, file }] : [];
  });
  return { matches, unmatched, superseded };
}
