import { useMemo } from "react";
import type { AlnCol } from "../types";

const CHUNK = 40;

const BASE_COLORS: Record<string, string> = {
  A: "text-red-500",
  T: "text-blue-500",
  G: "text-emerald-600",
  C: "text-amber-500",
  N: "text-gray-400",
  "-": "text-gray-300",
};

function BaseCard({
  char, kind, role,
}: {
  char: string;
  kind: AlnCol["kind"];
  role: "ref" | "alt";
}) {
  const baseColor = BASE_COLORS[char] ?? "text-gray-500";

  if (kind === "match") {
    return (
      <span className={`inline-flex items-center justify-center w-[18px] h-[22px]
                        text-[11px] font-mono font-medium shrink-0
                        bg-gray-100 border border-gray-200 rounded
                        ${baseColor}`}>
        {char}
      </span>
    );
  }

  if (kind === "gap") {
    return (
      <span className="inline-flex items-center justify-center w-[18px] h-[22px]
                       text-[11px] font-mono shrink-0
                       bg-gray-50 border border-dashed border-gray-200 rounded text-gray-300">
        –
      </span>
    );
  }

  // mismatch
  return role === "ref" ? (
    <span className="inline-flex items-center justify-center w-[18px] h-[22px]
                     text-[11px] font-mono font-bold shrink-0
                     bg-red-50 border border-red-300 rounded text-red-600
                     ring-1 ring-red-200">
      {char}
    </span>
  ) : (
    <span className="inline-flex items-center justify-center w-[18px] h-[22px]
                     text-[11px] font-mono font-bold shrink-0
                     bg-blue-50 border border-blue-300 rounded text-blue-600
                     ring-1 ring-blue-200">
      {char}
    </span>
  );
}

function ConnectorRow({ slice }: { slice: AlnCol[] }) {
  return (
    <div className="flex gap-[1px] items-center my-0.5">
      {slice.map((c, i) => (
        <span key={i} className="inline-flex items-center justify-center w-[18px] text-[9px] text-gray-300">
          {c.kind === "match" ? "|" : c.kind === "gap" ? " " : "·"}
        </span>
      ))}
    </div>
  );
}

function PositionTick({ start, slice }: { start: number; slice: AlnCol[] }) {
  return (
    <div className="flex gap-[1px] mb-0.5">
      {slice.map((_, i) => {
        const pos = start + i;
        const show = pos === 1 || pos % 10 === 0;
        return (
          <span key={i} className="inline-flex items-end justify-center w-[18px]
                                   text-[8px] font-mono text-gray-300 leading-none h-3">
            {show ? pos : ""}
          </span>
        );
      })}
    </div>
  );
}

interface Props { cols: AlnCol[]; }

export function AlignmentViewer({ cols }: Props) {
  const chunks = useMemo(() => {
    const out = [];
    for (let i = 0; i < cols.length; i += CHUNK)
      out.push({ start: i + 1, slice: cols.slice(i, i + CHUNK) });
    return out;
  }, [cols]);

  const snpCount = cols.filter((c) => c.kind === "mismatch").length;
  const gapCount = cols.filter((c) => c.kind === "gap").length;

  return (
    <div>
      {/* Legend */}
      <div className="flex flex-wrap gap-3 mb-3 text-[11px] text-gray-500">
        <span className="flex items-center gap-1">
          <span className="inline-flex items-center justify-center w-[18px] h-[22px] bg-gray-100
                           border border-gray-200 rounded text-emerald-600 font-mono text-[11px]">G</span>
          match
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-flex items-center justify-center w-[18px] h-[22px] bg-red-50
                           border border-red-300 rounded text-red-600 font-mono text-[11px] font-bold">X</span>
          ref mismatch
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-flex items-center justify-center w-[18px] h-[22px] bg-blue-50
                           border border-blue-300 rounded text-blue-600 font-mono text-[11px] font-bold">X</span>
          alt mismatch
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-flex items-center justify-center w-[18px] h-[22px] bg-gray-50
                           border border-dashed border-gray-200 rounded text-gray-300 font-mono text-[11px]">–</span>
          gap
        </span>
        <span className="ml-auto text-gray-400">
          {snpCount} SNP · {gapCount} gap · {cols.length} kolom
        </span>
      </div>

      {/* Base color legend */}
      <div className="flex gap-3 mb-4 text-[11px]">
        {(["A","T","G","C"] as const).map((b) => (
          <span key={b} className={`font-mono font-semibold ${BASE_COLORS[b]}`}>
            {b}
          </span>
        ))}
      </div>

      {/* Alignment rows */}
      <div className="overflow-y-auto max-h-96 space-y-4 overflow-x-auto pr-1">
        {chunks.map(({ start, slice }) => (
          <div key={start}>
            {/* Position ticks */}
            <div className="flex items-center gap-1 mb-0.5">
              <span className="text-[9px] text-transparent select-none w-10 shrink-0">REF</span>
              <PositionTick start={start} slice={slice} />
            </div>

            {/* REF row */}
            <div className="flex items-center gap-1">
              <span className="text-[9px] font-semibold text-gray-400 uppercase w-10 shrink-0">REF</span>
              <div className="flex gap-[1px]">
                {slice.map((c, i) => (
                  <BaseCard key={i} char={c.ref} kind={c.kind} role="ref" />
                ))}
              </div>
            </div>

            {/* Connector */}
            <div className="flex items-center gap-1">
              <span className="w-10 shrink-0" />
              <ConnectorRow slice={slice} />
            </div>

            {/* SAMPLE row */}
            <div className="flex items-center gap-1">
              <span className="text-[9px] font-semibold text-gray-400 uppercase w-10 shrink-0">SMPL</span>
              <div className="flex gap-[1px]">
                {slice.map((c, i) => (
                  <BaseCard key={i} char={c.alt} kind={c.kind} role="alt" />
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
