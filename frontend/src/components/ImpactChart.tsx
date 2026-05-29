import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell,
} from "recharts";
import type { Variant } from "../types";

const COLORS: Record<string, string> = {
  SILENT:            "#16a34a",
  MISSENSE:          "#dc2626",
  NONSENSE:          "#374151",
  STOP_LOST:         "#d97706",
  START_LOST:        "#0284c7",
  FRAMESHIFT:        "#7c3aed",
  INFRAME_INDEL:     "#9ca3af",
  UTR_OR_OUTOFFRAME: "#d1d5db",
  INCOMPLETE_CODON:  "#d1d5db",
};

interface Props { variants: Variant[]; }

export function ImpactChart({ variants }: Props) {
  const counts: Record<string, number> = {};
  for (const v of variants) counts[v.impact] = (counts[v.impact] ?? 0) + 1;
  const data = Object.entries(counts)
    .sort(([, a], [, b]) => b - a)
    .map(([impact, count]) => ({ impact, count }));

  const FONT = { fontFamily: "Figtree, system-ui, sans-serif" };

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data} margin={{ top: 10, right: 10, left: -10, bottom: 40 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
        <XAxis
          dataKey="impact" tick={{ fill: "#6b7280", fontSize: 11, ...FONT }}
          angle={-25} textAnchor="end" interval={0}
        />
        <YAxis tick={{ fill: "#9ca3af", fontSize: 11, ...FONT }} allowDecimals={false} />
        <Tooltip
          contentStyle={{
            background: "#fff", border: "1px solid #e5e7eb",
            borderRadius: "8px", color: "#111827",
          }}
          cursor={{ fill: "#00000008" }}
          formatter={(val: number) => [val, "Jumlah"]}
        />
        <Bar dataKey="count" radius={[4, 4, 0, 0]}
          label={{ position: "top", fill: "#9ca3af", fontSize: 11 }}>
          {data.map((entry, i) => (
            <Cell key={i} fill={COLORS[entry.impact] ?? "#9ca3af"} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
