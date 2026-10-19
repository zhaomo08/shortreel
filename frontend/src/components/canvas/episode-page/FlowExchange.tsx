import { useState } from "react";
import { useTranslation } from "react-i18next";
import { FileDown, FileUp, Loader2 } from "lucide-react";

import { API } from "@/api";
import { Button } from "@/components/ui/button";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogBody,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { UnitTag } from "@/components/workflow/UnitTag";
import { useAppStore } from "@/stores/app-store";
import { useProjectsStore } from "@/stores/projects-store";
import { errMsg } from "@/utils/async";
import { downloadBlob } from "@/utils/download";
import { planFlowImport, type FlowImportPlan } from "@/utils/flow-import";

/**
 * 页头的 Google Flow 往返：导出一集的任务包，拿到 Flow 网页里用订阅额度出片，再把视频导回。
 *
 * Flow 没有 API，出片这一步只能人工。导回按目录名或文件名里的镜头 ID 匹配（见 utils/flow-import），
 * 逐个走既有的单镜头上传接口，所以版本记录、元数据回写与 SSE 推送都和手动上传一致。
 */
export function FlowExchange({
  projectName,
  episode,
  ids,
  busyIds,
  disabled = false,
  upload,
  onImported,
}: {
  projectName: string;
  episode: number;
  /** 这一集的镜头 / 视频单元 ID，按播放顺序。 */
  ids: string[];
  /** 正在生成的镜头，导入时跳过，免得和生成结果互相覆盖。 */
  busyIds: ReadonlySet<string>;
  disabled?: boolean;
  upload: (id: string, file: File) => Promise<{ asset_fingerprints: Record<string, number> }>;
  onImported: () => Promise<unknown> | void;
}) {
  const { t } = useTranslation(["dashboard", "common"]);
  const [exporting, setExporting] = useState(false);
  const [plan, setPlan] = useState<FlowImportPlan | null>(null);
  const [progress, setProgress] = useState<number | null>(null);

  const handleExport = async () => {
    setExporting(true);
    try {
      const { blob, filename } = await API.downloadFlowPackage(projectName, episode);
      downloadBlob(blob, filename);
    } catch (err) {
      useAppStore.getState().pushToast(t("flow_export_failed", { message: errMsg(err) }), "error");
    } finally {
      setExporting(false);
    }
  };

  // 选整个任务包目录（webkitdirectory），才拿得到「镜头目录/视频」的相对路径。输入框临时创建、
  // 不挂进 DOM：画布里已有按位置找文件输入框的单条上传，多一个隐藏输入框会挡在它们前面。
  const pickFolder = () => {
    const input = document.createElement("input");
    input.type = "file";
    input.multiple = true;
    input.setAttribute("webkitdirectory", "");
    input.addEventListener("change", () => {
      if (input.files && input.files.length > 0) setPlan(planFlowImport(Array.from(input.files), ids));
    });
    input.click();
  };

  const ready = plan?.matches.filter((m) => !busyIds.has(m.id)) ?? [];
  const busy = plan?.matches.filter((m) => busyIds.has(m.id)) ?? [];

  const handleImport = async () => {
    const failures: string[] = [];
    let imported = 0;
    for (const [index, { id, file }] of ready.entries()) {
      setProgress(index);
      try {
        const result = await upload(id, file);
        useProjectsStore.getState().updateAssetFingerprints(result.asset_fingerprints);
        imported += 1;
      } catch (err) {
        failures.push(`${id}（${errMsg(err)}）`);
      }
    }
    setProgress(null);
    setPlan(null);
    const toast = useAppStore.getState().pushToast;
    if (imported > 0) toast(t("flow_import_done", { count: imported }), "success");
    if (failures.length > 0) toast(t("flow_import_failed", { details: failures.join("；") }), "error");
    try {
      await onImported();
    } catch (err) {
      toast(t("media_refresh_failed", { message: errMsg(err) }), "error");
    }
  };

  const importing = progress !== null;
  const title = t("flow_import");
  return (
    <>
      <Tooltip>
        <TooltipTrigger
          render={<Button variant="outline" size="sm" disabled={disabled || exporting} onClick={() => void handleExport()} />}
        >
          {exporting ? <Loader2 aria-hidden data-icon="inline-start" className="animate-spin" /> : <FileDown aria-hidden data-icon="inline-start" />}
          {t("flow_export")}
        </TooltipTrigger>
        <TooltipContent>{t("flow_export_hint")}</TooltipContent>
      </Tooltip>
      <Tooltip>
        <TooltipTrigger
          render={<Button variant="outline" size="sm" disabled={disabled || importing} onClick={pickFolder} />}
        >
          <FileUp aria-hidden data-icon="inline-start" />
          {title}
        </TooltipTrigger>
        <TooltipContent>{t("flow_import_hint")}</TooltipContent>
      </Tooltip>

      {plan && (
        <AlertDialog
          open
          onOpenChange={(next) => {
            if (!next && !importing) setPlan(null);
          }}
        >
          <AlertDialogContent size="lg">
            <AlertDialogHeader>
              <AlertDialogTitle>{title}</AlertDialogTitle>
            </AlertDialogHeader>
            <AlertDialogBody tabIndex={0} role="region" aria-label={title}>
              <AlertDialogDescription render={<div />}>
                <div className="flex flex-col gap-3" data-testid="flow-import-plan">
                  {ready.length === 0 ? (
                    <p>{t("flow_import_nothing")}</p>
                  ) : (
                    <div className="flex flex-col gap-1">
                      <p className="font-medium text-subtle-foreground">
                        {t("flow_import_matched", { count: ready.length })}
                      </p>
                      <ul className="flex flex-col gap-1">
                        {ready.map(({ id, file }) => (
                          <li key={id} className="flex min-w-0 items-center gap-1.5">
                            <UnitTag unitId={id} />
                            <span className="truncate">{file.name}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {busy.length > 0 && <p>{t("flow_import_busy", { count: busy.length })}</p>}
                  {plan.superseded.length > 0 && (
                    <p>{t("flow_import_superseded", { count: plan.superseded.length })}</p>
                  )}
                  {plan.unmatched.length > 0 && (
                    <div>
                      <p>{t("flow_import_unmatched", { count: plan.unmatched.length })}</p>
                      <ul className="mt-1 flex flex-col gap-0.5 text-subtle-foreground">
                        {plan.unmatched.map((file) => (
                          <li key={file.webkitRelativePath || file.name} className="truncate">
                            {file.webkitRelativePath || file.name}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {ready.length > 0 && <p>{t("flow_import_replace_note")}</p>}
                </div>
              </AlertDialogDescription>
            </AlertDialogBody>
            <AlertDialogFooter>
              <AlertDialogCancel disabled={importing}>{t("common:cancel")}</AlertDialogCancel>
              <AlertDialogAction disabled={importing || ready.length === 0} onClick={() => void handleImport()}>
                {importing ? <Loader2 aria-hidden data-icon="inline-start" className="animate-spin" /> : null}
                {importing
                  ? t("flow_import_progress", { done: progress, total: ready.length })
                  : t("flow_import_confirm")}
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      )}
    </>
  );
}
