import { useMemo } from "react";
import type { Variant } from "../types";

const BASES = ["A", "C", "G", "T"] as const;

interface Props {
  variants: Variant[];
}

export function SubstitutionMatrix({ variants }: Props) {
  const matrix = useMemo(() => {
    const mat: Record<string, Record<string, number>> = {};
    for (const b of BASES) {
      mat[b] = {};
      for (const b2 of BASES) mat[b][b2] = 0;
    }
    for (const v of variants) {
      if (
        v.variant_type === "SNP" &&
        BASES.includes(v.ref as (typeof BASES)[number]) &&
        BASES.includes(v.alt as (typeof BASES)[number])
      ) {
        mat[v.ref][v.alt]++;
      }
    }
    return mat;
  }, [variants]);

  const maxVal = Math.max(
    1,
    ...BASES.flatMap((r) => BASES.map((c) => matrix[r][c]))
  );

  function cellColor(val: number) {
    if (val === 0) return "bg-slate-900 text-slate-700";
    const t = val / maxVal;
    if (t < 0.33) return "bg-amber-900/30 text-amber-400";
    if (t < 0.66) return "bg-amber-700/50 text-amber-200";
    return "bg-amber-500/70 text-white font-bold";
  }

  return (
    <div>
      {/* Column headers */}
      <div className="grid grid-cols-5 gap-1 mb-1">
        <div className="text-center" />
        {BASES.map((b) => (
          <div key={b} className="text-center text-xs font-bold text-slate-400 py-1">
            {b}
          </div>
        ))}
      </div>
      <div className="text-xs text-slate-600 text-center mb-1">→ ALT</div>

      {/* Rows */}
      {BASES.map((ref) => (
        <div key={ref} className="grid grid-cols-5 gap-1 mb-1">
          <div className="flex items-center justify-end pr-2 text-xs font-bold text-slate-400">
            {ref}
          </div>
          {BASES.map((alt) => {
            const val = matrix[ref][alt];
            const isDiag = ref === alt;
            return (
              <div
                key={alt}
                className={`rounded flex items-center justify-center h-10 text-sm
                  ${isDiag ? "bg-slate-800/50 text-slate-600" : cellColor(val)}`}
              >
                {isDiag ? "—" : val}
              </div>
            );
          })}
        </div>
      ))}
      <div className="text-xs text-slate-600 text-center mt-1">REF ↓</div>
    </div>
  );
}
