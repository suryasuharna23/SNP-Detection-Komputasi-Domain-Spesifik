import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell,
} from "recharts";
import type { Variant } from "../types";

const COLORS: Record<string, string> = {
  SILENT:            "#16a34a",
  MISSENSE:          "#dc2626",
  NONSENSE:          "#334155",
  STOP_LOST:         "#d97706",
  START_LOST:        "#0284c7",
  FRAMESHIFT:        "#7c3aed",
  INFRAME_INDEL:     "#6b7280",
  UTR_OR_OUTOFFRAME: "#374151",
  INCOMPLETE_CODON:  "#374151",
};

interface Props {
  variants: Variant[];
}

export function ImpactChart({ variants }: Props) {
  const counts: Record<string, number> = {};
  for (const v of variants) {
    counts[v.impact] = (counts[v.impact] ?? 0) + 1;
  }
  const data = Object.entries(counts)
    .sort(([, a], [, b]) => b - a)
    .map(([impact, count]) => ({ impact, count }));

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data} margin={{ top: 10, right: 10, left: -10, bottom: 40 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
        <XAxis
          dataKey="impact"
          tick={{ fill: "#94a3b8", fontSize: 11 }}
          angle={-25}
          textAnchor="end"
          interval={0}
        />
        <YAxis tick={{ fill: "#64748b", fontSize: 11 }} allowDecimals={false} />
        <Tooltip
          contentStyle={{
            background: "#1e293b",
            border: "1px solid #334155",
            borderRadius: "8px",
            color: "#e2e8f0",
          }}
          cursor={{ fill: "#ffffff10" }}
          formatter={(val: number) => [val, "Jumlah"]}
        />
        <Bar dataKey="count" radius={[4, 4, 0, 0]} label={{ position: "top", fill: "#64748b", fontSize: 11 }}>
          {data.map((entry, i) => (
            <Cell key={i} fill={COLORS[entry.impact] ?? "#6b7280"} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
