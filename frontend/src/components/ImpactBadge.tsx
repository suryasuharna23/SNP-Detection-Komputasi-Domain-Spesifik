import { clsx } from "clsx";
import type { ImpactType } from "../types";

const CONFIG: Record<ImpactType, { label: string; cls: string }> = {
  SILENT:            { label: "Silent",       cls: "bg-emerald-900/60 text-emerald-300 ring-1 ring-emerald-700" },
  MISSENSE:          { label: "Missense",     cls: "bg-red-900/60    text-red-300    ring-1 ring-red-700" },
  NONSENSE:          { label: "Nonsense",     cls: "bg-slate-700     text-slate-100  ring-1 ring-slate-600" },
  STOP_LOST:         { label: "Stop Lost",    cls: "bg-amber-900/60  text-amber-300  ring-1 ring-amber-700" },
  START_LOST:        { label: "Start Lost",   cls: "bg-sky-900/60    text-sky-300    ring-1 ring-sky-700" },
  FRAMESHIFT:        { label: "Frameshift",   cls: "bg-violet-900/60 text-violet-300 ring-1 ring-violet-700" },
  INFRAME_INDEL:     { label: "In-frame",     cls: "bg-slate-800     text-slate-400  ring-1 ring-slate-700" },
  UTR_OR_OUTOFFRAME: { label: "UTR",          cls: "bg-slate-800     text-slate-500  ring-1 ring-slate-700" },
  INCOMPLETE_CODON:  { label: "Incomplete",   cls: "bg-slate-800     text-slate-500  ring-1 ring-slate-700" },
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
