import { useMemo } from "react";
import type { Variant } from "../types";

const BASES = ["A", "C", "G", "T"] as const;

interface Props { variants: Variant[]; }

export function SubstitutionMatrix({ variants }: Props) {
  const matrix = useMemo(() => {
    const mat: Record<string, Record<string, number>> = {};
    for (const b of BASES) { mat[b] = {}; for (const b2 of BASES) mat[b][b2] = 0; }
    for (const v of variants) {
      if (
        v.variant_type === "SNP" &&
        BASES.includes(v.ref as (typeof BASES)[number]) &&
        BASES.includes(v.alt as (typeof BASES)[number])
      ) mat[v.ref][v.alt]++;
    }
    return mat;
  }, [variants]);

  const maxVal = Math.max(1, ...BASES.flatMap((r) => BASES.map((c) => matrix[r][c])));

  function cellClass(val: number) {
    if (val === 0) return "bg-gray-50 text-gray-300";
    const t = val / maxVal;
    if (t < 0.33) return "bg-emerald-50 text-emerald-600";
    if (t < 0.66) return "bg-emerald-100 text-emerald-700 font-semibold";
    return "bg-emerald-500 text-white font-bold";
  }

  return (
    <div>
      <div className="grid grid-cols-5 gap-1 mb-1">
        <div />
        {BASES.map((b) => (
          <div key={b} className="text-center text-xs font-bold text-gray-500 py-1">{b}</div>
        ))}
      </div>
      <div className="text-xs text-gray-400 text-center mb-1">→ ALT</div>
      {BASES.map((ref) => (
        <div key={ref} className="grid grid-cols-5 gap-1 mb-1">
          <div className="flex items-center justify-end pr-2 text-xs font-bold text-gray-500">{ref}</div>
          {BASES.map((alt) => {
            const val = matrix[ref][alt];
            const isDiag = ref === alt;
            return (
              <div
                key={alt}
                className={`rounded flex items-center justify-center h-10 text-sm border
                  ${isDiag ? "bg-gray-100 text-gray-300 border-gray-200" : `${cellClass(val)} border-transparent`}`}
              >
                {isDiag ? "—" : val}
              </div>
            );
          })}
        </div>
      ))}
      <div className="text-xs text-gray-400 text-center mt-1">REF ↓</div>
    </div>
  );
}
