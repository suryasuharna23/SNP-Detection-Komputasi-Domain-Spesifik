import { useState } from "react";
import type { Variant } from "../types";

const IMPACT_COLOR: Record<string, string> = {
  SILENT:            "#16a34a",
  MISSENSE:          "#dc2626",
  NONSENSE:          "#1e293b",
  STOP_LOST:         "#d97706",
  START_LOST:        "#0284c7",
  FRAMESHIFT:        "#7c3aed",
  INFRAME_INDEL:     "#6b7280",
  UTR_OR_OUTOFFRAME: "#374151",
  INCOMPLETE_CODON:  "#374151",
};

interface Props {
  variants: Variant[];
  refLength: number;
}

interface Tooltip {
  v: Variant;
  x: number;
  y: number;
}

export function SNPTrack({ variants, refLength }: Props) {
  const [tooltip, setTooltip] = useState<Tooltip | null>(null);

  const snps = variants.filter((v) => v.variant_type === "SNP");
  const trackW = 900;
  const trackH = 40;
  const pad = 16;
  const barH = 24;
  const barY = (trackH - barH) / 2;

  function xPos(pos: number) {
    return pad + ((pos - 1) / Math.max(refLength - 1, 1)) * (trackW - pad * 2);
  }

  return (
    <div className="relative">
      <div className="text-xs text-slate-500 mb-1 flex justify-between">
        <span>1</span>
        <span className="text-slate-400 font-medium">Distribusi Posisi SNP</span>
        <span>{refLength} bp</span>
      </div>
      <div className="overflow-x-auto">
        <svg
          width={trackW}
          height={trackH}
          className="block"
          style={{ minWidth: "100%" }}
        >
          {/* Background track */}
          <rect x={pad} y={barY} width={trackW - pad * 2} height={barH}
                rx={4} fill="#1e293b" />

          {/* SNP markers */}
          {snps.map((v, i) => {
            const cx = xPos(v.pos);
            const color = IMPACT_COLOR[v.impact] ?? "#6b7280";
            return (
              <line
                key={i}
                x1={cx} y1={barY + 2} x2={cx} y2={barY + barH - 2}
                stroke={color} strokeWidth={2.5} strokeLinecap="round"
                className="cursor-pointer opacity-90 hover:opacity-100"
                onMouseEnter={(e) =>
                  setTooltip({ v, x: e.clientX, y: e.clientY })
                }
                onMouseLeave={() => setTooltip(null)}
              />
            );
          })}
        </svg>
      </div>

      {/* Tooltip */}
      {tooltip && (
        <div
          className="fixed z-50 pointer-events-none bg-slate-800 border border-slate-600
                     rounded-lg px-3 py-2 text-xs shadow-xl"
          style={{ left: tooltip.x + 12, top: tooltip.y - 10 }}
        >
          <div className="font-bold text-slate-100 mb-0.5">
            Pos {tooltip.v.pos}: {tooltip.v.ref} → {tooltip.v.alt}
          </div>
          {tooltip.v.ref_codon && (
            <div className="text-slate-400">
              Kodon: <span className="text-red-400">{tooltip.v.ref_codon}</span>{" "}
              → <span className="text-blue-400">{tooltip.v.alt_codon}</span>
            </div>
          )}
          {tooltip.v.ref_aa_name && (
            <div className="text-slate-400">
              AA: {tooltip.v.ref_aa_name} → {tooltip.v.alt_aa_name}
            </div>
          )}
          <div className="mt-0.5">
            <span
              className="font-bold"
              style={{ color: IMPACT_COLOR[tooltip.v.impact] }}
            >
              {tooltip.v.impact}
            </span>
          </div>
        </div>
      )}

      {/* Legend */}
      <div className="flex flex-wrap gap-3 mt-2">
        {Object.entries(IMPACT_COLOR)
          .filter(([k]) => snps.some((v) => v.impact === k))
          .map(([impact, color]) => (
            <span key={impact} className="flex items-center gap-1 text-xs text-slate-400">
              <span
                className="inline-block w-3 h-3 rounded-sm"
                style={{ background: color }}
              />
              {impact}
            </span>
          ))}
      </div>
    </div>
  );
}
