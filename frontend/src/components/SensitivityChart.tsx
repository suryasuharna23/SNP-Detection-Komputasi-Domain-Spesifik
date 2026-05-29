import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ResponsiveContainer, ErrorBar,
} from "recharts";
import type { SensitivityPoint } from "../types";

interface Props { data: SensitivityPoint[]; refLength: number; nTrials: number; }

export function SensitivityChart({ data, refLength, nTrials }: Props) {
  const chartData = data.map((d) => ({
    density:   d.density,
    precision: parseFloat(d.precision.mean.toFixed(4)),
    recall:    parseFloat(d.recall.mean.toFixed(4)),
    f1:        parseFloat(d.f1.mean.toFixed(4)),
    pErr:      parseFloat((d.precision.std * 2).toFixed(4)),
    rErr:      parseFloat((d.recall.std    * 2).toFixed(4)),
    fErr:      parseFloat((d.f1.std        * 2).toFixed(4)),
  }));

  return (
    <div>
      <p className="text-xs text-gray-400 mb-3">
        Ref={refLength} bp · {nTrials} trial/titik · Error bar = ±2σ
      </p>
      <ResponsiveContainer width="100%" height={360}>
        <LineChart data={chartData} margin={{ top: 5, right: 20, left: -5, bottom: 20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
          <XAxis
            dataKey="density"
            tickFormatter={(v) => `${v}%`}
            label={{ value: "Densitas SNP (%)", position: "insideBottom", offset: -10, fill: "#9ca3af", fontSize: 12 }}
            tick={{ fill: "#6b7280", fontSize: 11 }}
          />
          <YAxis
            domain={[0, 1.05]} tickFormatter={(v) => v.toFixed(2)}
            tick={{ fill: "#9ca3af", fontSize: 11 }}
          />
          <Tooltip
            contentStyle={{
              background: "#fff", border: "1px solid #e5e7eb",
              borderRadius: "8px", color: "#111827", fontSize: "12px",
            }}
            labelFormatter={(v) => `Densitas: ${v}%`}
            formatter={(val: number) => val.toFixed(4)}
          />
          <Legend wrapperStyle={{ paddingTop: "16px", fontSize: "12px", color: "#6b7280" }} />

          <Line dataKey="precision" name="Precision"
            stroke="#3b82f6" strokeWidth={2} dot={{ r: 4, fill: "#3b82f6" }}>
            <ErrorBar dataKey="pErr" width={4} strokeWidth={1} stroke="#3b82f680" direction="y" />
          </Line>
          <Line dataKey="recall" name="Recall"
            stroke="#f59e0b" strokeWidth={2} dot={{ r: 4, fill: "#f59e0b" }}>
            <ErrorBar dataKey="rErr" width={4} strokeWidth={1} stroke="#f59e0b80" direction="y" />
          </Line>
          <Line dataKey="f1" name="F1-Score"
            stroke="#16a34a" strokeWidth={2.5} dot={{ r: 5, fill: "#16a34a" }}>
            <ErrorBar dataKey="fErr" width={4} strokeWidth={1} stroke="#16a34a80" direction="y" />
          </Line>
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
