import { clsx } from "clsx";
import type { ImpactType } from "../types";

const CONFIG: Record<ImpactType, { label: string; cls: string }> = {
  SILENT:            { label: "Silent",       cls: "bg-emerald-100 text-emerald-700 ring-1 ring-emerald-300" },
  MISSENSE:          { label: "Missense",     cls: "bg-red-100     text-red-700     ring-1 ring-red-300" },
  NONSENSE:          { label: "Nonsense",     cls: "bg-gray-200    text-gray-700    ring-1 ring-gray-400" },
  STOP_LOST:         { label: "Stop Lost",    cls: "bg-amber-100   text-amber-700   ring-1 ring-amber-300" },
  START_LOST:        { label: "Start Lost",   cls: "bg-sky-100     text-sky-700     ring-1 ring-sky-300" },
  FRAMESHIFT:        { label: "Frameshift",   cls: "bg-violet-100  text-violet-700  ring-1 ring-violet-300" },
  INFRAME_INDEL:     { label: "In-frame",     cls: "bg-gray-100    text-gray-500    ring-1 ring-gray-300" },
  UTR_OR_OUTOFFRAME: { label: "UTR",          cls: "bg-gray-100    text-gray-400    ring-1 ring-gray-300" },
  INCOMPLETE_CODON:  { label: "Incomplete",   cls: "bg-gray-100    text-gray-400    ring-1 ring-gray-300" },
};

interface Props {
  impact: ImpactType;
  size?: "sm" | "md";
}

export function ImpactBadge({ impact, size = "sm" }: Props) {
  const cfg = CONFIG[impact] ?? { label: impact, cls: "bg-slate-800 text-slate-400" };
  return (
    <span
      className={clsx(
        "impact-badge",
        cfg.cls,
        size === "sm" ? "text-xs px-2 py-0.5" : "text-sm px-3 py-1"
      )}
    >
      {cfg.label}
    </span>
  );
}

export { CONFIG as IMPACT_CONFIG };
