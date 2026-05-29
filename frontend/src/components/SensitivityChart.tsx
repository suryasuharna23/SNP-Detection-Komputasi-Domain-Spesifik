import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ResponsiveContainer, ErrorBar,
} from "recharts";
import type { SensitivityPoint } from "../types";

interface Props {
  data: SensitivityPoint[];
  refLength: number;
  nTrials: number;
}

export function SensitivityChart({ data, refLength, nTrials }: Props) {
  const chartData = data.map((d) => ({
    density:   d.density,
    precision: parseFloat(d.precision.mean.toFixed(4)),
    recall:    parseFloat(d.recall.mean.toFixed(4)),
    f1:        parseFloat(d.f1.mean.toFixed(4)),
    pErr:      parseFloat((d.precision.std * 2).toFixed(4)),
    rErr:      parseFloat((d.recall.std * 2).toFixed(4)),
    fErr:      parseFloat((d.f1.std * 2).toFixed(4)),
  }));

  return (
    <div>
      <p className="text-xs text-slate-500 mb-3">
        Ref={refLength} bp · {nTrials} trial/titik · Error bar = ±2σ
      </p>
      <ResponsiveContainer width="100%" height={360}>
        <LineChart data={chartData} margin={{ top: 5, right: 20, left: -5, bottom: 20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis
            dataKey="density"
            tickFormatter={(v) => `${v}%`}
            label={{ value: "Densitas SNP (%)", position: "insideBottom", offset: -10, fill: "#64748b", fontSize: 12 }}
            tick={{ fill: "#94a3b8", fontSize: 11 }}
          />
          <YAxis
            domain={[0, 1.05]}
            tickFormatter={(v) => v.toFixed(2)}
            tick={{ fill: "#64748b", fontSize: 11 }}
          />
          <Tooltip
            contentStyle={{
              background: "#1e293b",
              border: "1px solid #334155",
              borderRadius: "8px",
              color: "#e2e8f0",
              fontSize: "12px",
            }}
            labelFormatter={(v) => `Densitas: ${v}%`}
            formatter={(val: number) => val.toFixed(4)}
          />
          <Legend
            wrapperStyle={{ paddingTop: "16px", fontSize: "12px", color: "#94a3b8" }}
          />

          <Line
            dataKey="precision" name="Precision"
            stroke="#3b82f6" strokeWidth={2} dot={{ r: 4, fill: "#3b82f6" }}
          >
            <ErrorBar dataKey="pErr" width={4} strokeWidth={1} stroke="#3b82f670" direction="y" />
          </Line>

          <Line
            dataKey="recall" name="Recall"
            stroke="#f59e0b" strokeWidth={2} dot={{ r: 4, fill: "#f59e0b" }}
          >
            <ErrorBar dataKey="rErr" width={4} strokeWidth={1} stroke="#f59e0b70" direction="y" />
          </Line>

          <Line
            dataKey="f1" name="F1-Score"
            stroke="#22c55e" strokeWidth={2.5} dot={{ r: 5, fill: "#22c55e" }}
          >
            <ErrorBar dataKey="fErr" width={4} strokeWidth={1} stroke="#22c55e70" direction="y" />
          </Line>
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
