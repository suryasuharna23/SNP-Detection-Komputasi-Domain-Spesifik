import { useState, useCallback, useRef } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ResponsiveContainer, ErrorBar, ReferenceArea,
} from "recharts";
import { ZoomIn, ZoomOut, RotateCcw, MousePointer } from "lucide-react";
import type { SensitivityPoint } from "../types";

interface Props { data: SensitivityPoint[]; refLength: number; nTrials: number; }

export function SensitivityChart({ data, refLength, nTrials }: Props) {
  const chartData = data.map((d) => ({
    density:   parseFloat(d.density.toFixed(3)),
    precision: parseFloat(d.precision.mean.toFixed(4)),
    recall:    parseFloat(d.recall.mean.toFixed(4)),
    f1:        parseFloat(d.f1.mean.toFixed(4)),
    pErr:      parseFloat((d.precision.std * 2).toFixed(4)),
    rErr:      parseFloat((d.recall.std    * 2).toFixed(4)),
    fErr:      parseFloat((d.f1.std        * 2).toFixed(4)),
  }));

  const allDensities = chartData.map((d) => d.density);
  const FULL_X: [number, number] = [
    Math.min(...allDensities),
    Math.max(...allDensities),
  ];
  const FULL_Y: [number, number] = [0, 1.05];

  const [xDomain, setXDomain] = useState<[number, number]>([...FULL_X]);
  const [yDomain, setYDomain] = useState<[number, number]>([...FULL_Y]);

  // Drag-to-zoom state
  const [selLeft,  setSelLeft]  = useState<number | null>(null);
  const [selRight, setSelRight] = useState<number | null>(null);
  const dragging = useRef(false);

  const isZoomed =
    xDomain[0] !== FULL_X[0] || xDomain[1] !== FULL_X[1] ||
    yDomain[0] !== FULL_Y[0] || yDomain[1] !== FULL_Y[1];

  // ── Helpers ──────────────────────────────────────────────────────────────

  function yRangeFor(left: number, right: number): [number, number] {
    const visible = chartData.filter(
      (d) => d.density >= left && d.density <= right
    );
    if (visible.length === 0) return [...FULL_Y];
    const vals = visible.flatMap((d) => [d.precision, d.recall, d.f1]);
    const lo = Math.max(0,    Math.min(...vals) - 0.04);
    const hi = Math.min(1.05, Math.max(...vals) + 0.04);
    return [parseFloat(lo.toFixed(3)), parseFloat(hi.toFixed(3))];
  }

  // ── Drag-to-zoom handlers ────────────────────────────────────────────────

  const onMouseDown = useCallback((e: any) => {
    if (!e?.activeLabel) return;
    dragging.current = true;
    setSelLeft(parseFloat(e.activeLabel));
    setSelRight(null);
  }, []);

  const onMouseMove = useCallback((e: any) => {
    if (!dragging.current || !e?.activeLabel) return;
    setSelRight(parseFloat(e.activeLabel));
  }, []);

  const onMouseUp = useCallback(() => {
    dragging.current = false;
    if (selLeft !== null && selRight !== null && selLeft !== selRight) {
      const left  = Math.min(selLeft, selRight);
      const right = Math.max(selLeft, selRight);
      setXDomain([left, right]);
      setYDomain(yRangeFor(left, right));
    }
    setSelLeft(null);
    setSelRight(null);
  }, [selLeft, selRight, chartData]);

  // ── Button zoom ──────────────────────────────────────────────────────────

  function stepZoom(factor: number) {
    const cx = (xDomain[0] + xDomain[1]) / 2;
    const half = ((xDomain[1] - xDomain[0]) / 2) * factor;
    const left  = Math.max(FULL_X[0], cx - half);
    const right = Math.min(FULL_X[1], cx + half);
    setXDomain([left, right]);
    setYDomain(factor < 1 ? yRangeFor(left, right) : [...FULL_Y]);
  }

  function reset() {
    setXDomain([...FULL_X]);
    setYDomain([...FULL_Y]);
  }

  // ── Render ───────────────────────────────────────────────────────────────

  const FONT = { fontFamily: "Figtree, system-ui, sans-serif" };

  return (
    <div>
      {/* Toolbar */}
      <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
        <p className="text-xs text-gray-400">
          Ref={refLength} bp · {nTrials} trial/titik · error bar = ±2σ
        </p>

        <div className="flex items-center gap-1.5">
          {isZoomed && (
            <span className="text-[10px] text-emerald-600 bg-emerald-50 border border-emerald-200
                             rounded px-2 py-0.5 font-mono">
              {xDomain[0].toFixed(2)}% – {xDomain[1].toFixed(2)}%
            </span>
          )}

          <button
            onClick={() => stepZoom(0.6)}
            className="btn-secondary !py-1 !px-2"
            title="Zoom In"
          >
            <ZoomIn size={14} />
          </button>
          <button
            onClick={() => stepZoom(1.7)}
            className="btn-secondary !py-1 !px-2"
            title="Zoom Out"
          >
            <ZoomOut size={14} />
          </button>
          {isZoomed && (
            <button
              onClick={reset}
              className="btn-secondary !py-1 !px-2 text-xs"
              title="Reset zoom"
            >
              <RotateCcw size={14} />
            </button>
          )}

          <span className="text-[10px] text-gray-400 flex items-center gap-1 ml-1 select-none">
            <MousePointer size={11} /> drag to zoom
          </span>
        </div>
      </div>

      {/* Chart */}
      <div
        className="select-none"
        style={{ cursor: dragging.current ? "col-resize" : "crosshair" }}
      >
        <ResponsiveContainer width="100%" height={380}>
          <LineChart
            data={chartData}
            margin={{ top: 8, right: 20, left: -5, bottom: 24 }}
            onMouseDown={onMouseDown}
            onMouseMove={onMouseMove}
            onMouseUp={onMouseUp}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />

            <XAxis
              dataKey="density"
              type="number"
              domain={xDomain}
              tickFormatter={(v) => `${v}%`}
              tick={{ fill: "#6b7280", fontSize: 11, ...FONT }}
              label={{
                value: "Densitas SNP (%)",
                position: "insideBottom",
                offset: -12,
                fill: "#9ca3af",
                fontSize: 12,
                ...FONT,
              }}
              allowDataOverflow
            />

            <YAxis
              domain={yDomain}
              tickFormatter={(v) => v.toFixed(2)}
              tick={{ fill: "#9ca3af", fontSize: 11, ...FONT }}
              allowDataOverflow
            />

            <Tooltip
              contentStyle={{
                background: "#fff",
                border: "1px solid #e5e7eb",
                borderRadius: "8px",
                color: "#111827",
                fontSize: "12px",
              }}
              labelFormatter={(v) => `Densitas: ${v}%`}
              formatter={(val: number) => val.toFixed(4)}
            />
            <Legend
              wrapperStyle={{ paddingTop: "14px", fontSize: "12px", color: "#6b7280" }}
            />

            <Line
              dataKey="precision" name="Precision"
              stroke="#3b82f6" strokeWidth={2}
              dot={{ r: 4, fill: "#3b82f6", strokeWidth: 0 }}
              activeDot={{ r: 6 }}
              isAnimationActive={false}
            >
              <ErrorBar dataKey="pErr" width={4} strokeWidth={1} stroke="#3b82f660" direction="y" />
            </Line>

            <Line
              dataKey="recall" name="Recall"
              stroke="#f59e0b" strokeWidth={2}
              dot={{ r: 4, fill: "#f59e0b", strokeWidth: 0 }}
              activeDot={{ r: 6 }}
              isAnimationActive={false}
            >
              <ErrorBar dataKey="rErr" width={4} strokeWidth={1} stroke="#f59e0b60" direction="y" />
            </Line>

            <Line
              dataKey="f1" name="F1-Score"
              stroke="#16a34a" strokeWidth={2.5}
              dot={{ r: 5, fill: "#16a34a", strokeWidth: 0 }}
              activeDot={{ r: 7 }}
              isAnimationActive={false}
            >
              <ErrorBar dataKey="fErr" width={4} strokeWidth={1} stroke="#16a34a60" direction="y" />
            </Line>

            {/* Selection overlay while dragging */}
            {selLeft !== null && selRight !== null && (
              <ReferenceArea
                x1={Math.min(selLeft, selRight)}
                x2={Math.max(selLeft, selRight)}
                fill="#3b82f6"
                fillOpacity={0.08}
                stroke="#3b82f6"
                strokeOpacity={0.4}
                strokeWidth={1}
              />
            )}
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Y-axis range indicator when zoomed */}
      {isZoomed && (
        <p className="text-[10px] text-gray-400 text-center mt-1">
          Y: {yDomain[0].toFixed(2)} – {yDomain[1].toFixed(2)} &nbsp;·&nbsp;
          X: {xDomain[0].toFixed(2)}% – {xDomain[1].toFixed(2)}%
          &nbsp;·&nbsp;
          <button onClick={reset} className="text-emerald-600 hover:underline">
            reset
          </button>
        </p>
      )}
    </div>
  );
}
