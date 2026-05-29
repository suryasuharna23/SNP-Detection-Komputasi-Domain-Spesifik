import { useState } from "react";
import { Play, FlaskConical, Dna, PenLine } from "lucide-react";
import type { DatasetType, RunParams } from "../types";

const HBB_WT = "ATGGTGCATCTGACTCCTGAGGAGAAGTCTGCCGTTACTGCCCTGTGGGGCAAGGTGAAC";
const HBB_SC = "ATGGTGCATCTGACTCCTGTGGAGAAGTCTGCCGTTACTGCCCTGTGGGGCAAGGTGAAC";

interface Props {
  onRun: (p: RunParams) => void;
  loading: boolean;
}

export function InputPanel({ onRun, loading }: Props) {
  const [dataset, setDataset] = useState<DatasetType>("synthetic");
  const [seqLen,  setSeqLen]  = useState(300);
  const [nSnps,   setNSnps]   = useState(12);
  const [gc,      setGc]      = useState(50);
  const [seed,    setSeed]    = useState(42);
  const [frame,   setFrame]   = useState(0);
  const [refSeq,  setRefSeq]  = useState("");
  const [smpSeq,  setSmpSeq]  = useState("");

  const canRun =
    !loading &&
    (dataset !== "custom" || (refSeq.trim().length >= 3 && smpSeq.trim().length >= 3));

  function handleRun() {
    onRun({
      dataset,
      ref_seq:    dataset === "custom" ? refSeq : undefined,
      sample_seq: dataset === "custom" ? smpSeq : undefined,
      seq_length: seqLen,
      n_snps:     nSnps,
      gc_content: gc / 100,
      seed,
      frame,
    });
  }

  const DATASETS: { id: DatasetType; icon: React.ReactNode; label: string; desc: string }[] = [
    { id: "synthetic", icon: <FlaskConical size={14} />, label: "Sintetik", desc: "Kontrol ground truth" },
    { id: "hbb",       icon: <Dna size={14} />,          label: "HBB Sickle-Cell", desc: "Kasus biologis nyata" },
    { id: "custom",    icon: <PenLine size={14} />,       label: "Custom", desc: "Masukkan sendiri" },
  ];

  return (
    <div className="space-y-5">
      {/* Dataset selector */}
      <div>
        <p className="label">Dataset</p>
        <div className="grid grid-cols-3 gap-2">
          {DATASETS.map((d) => (
            <button
              key={d.id}
              onClick={() => setDataset(d.id)}
              className={`flex flex-col items-center gap-1.5 p-3 rounded-xl border text-xs
                transition-all duration-150 text-center
                ${dataset === d.id
                  ? "border-emerald-500 bg-emerald-950/50 text-emerald-300"
                  : "border-slate-700 bg-slate-800/50 text-slate-400 hover:border-slate-600"
                }`}
            >
              <span className="text-base">{d.icon}</span>
              <span className="font-semibold">{d.label}</span>
              <span className="text-slate-500 text-[10px]">{d.desc}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Dataset-specific inputs */}
      {dataset === "synthetic" && (
        <div className="space-y-3">
          <Slider
            label={`Panjang sekuens: ${seqLen} bp`}
            min={60} max={900} step={30} value={seqLen}
            onChange={setSeqLen}
          />
          <Slider
            label={`Jumlah SNP: ${nSnps}`}
            min={1} max={Math.max(1, Math.floor(seqLen / 6))} value={nSnps}
            onChange={setNSnps}
          />
          <Slider
            label={`GC content: ${gc}%`}
            min={30} max={70} value={gc}
            onChange={setGc}
          />
          <div>
            <p className="label">Random Seed</p>
            <input
              type="number" className="input" value={seed}
              onChange={(e) => setSeed(Number(e.target.value))}
            />
          </div>
        </div>
      )}

      {dataset === "hbb" && (
        <div className="space-y-2 text-xs">
          <div className="card !p-3 space-y-1.5">
            <p className="text-emerald-400 font-semibold text-[11px] uppercase tracking-wider">Wild-type HBB</p>
            <p className="font-mono text-[11px] text-slate-400 break-all">{HBB_WT}</p>
          </div>
          <div className="card !p-3 space-y-1.5">
            <p className="text-red-400 font-semibold text-[11px] uppercase tracking-wider">Sickle-Cell HBB</p>
            <p className="font-mono text-[11px] text-slate-400 break-all">{HBB_SC}</p>
            <p className="text-slate-600">Mutasi A→T pos.20 menyebabkan Glu→Val (kodon GAG→GTG)</p>
          </div>
        </div>
      )}

      {dataset === "custom" && (
        <div className="space-y-3">
          <div>
            <p className="label">Sekuens Referensi (DNA)</p>
            <textarea
              className="textarea h-20" placeholder="ATGGTGCATCTG…"
              value={refSeq} onChange={(e) => setRefSeq(e.target.value)}
            />
          </div>
          <div>
            <p className="label">Sekuens Sampel (DNA)</p>
            <textarea
              className="textarea h-20" placeholder="ATGGTGCATCTG…"
              value={smpSeq} onChange={(e) => setSmpSeq(e.target.value)}
            />
          </div>
        </div>
      )}

      {/* Frame */}
      <div>
        <p className="label">Reading Frame</p>
        <div className="flex gap-2">
          {[0, 1, 2].map((f) => (
            <button
              key={f}
              onClick={() => setFrame(f)}
              className={`flex-1 py-1.5 rounded-lg text-sm font-mono transition-colors
                ${frame === f
                  ? "bg-emerald-700 text-white"
                  : "bg-slate-800 text-slate-400 hover:bg-slate-700"
                }`}
            >
              +{f}
            </button>
          ))}
        </div>
      </div>

      {/* Run button */}
      <button
        className="btn-primary w-full justify-center text-base py-3"
        onClick={handleRun}
        disabled={!canRun}
      >
        {loading ? (
          <span className="flex items-center gap-2">
            <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
            </svg>
            Menjalankan…
          </span>
        ) : (
          <><Play size={16} /> Jalankan Pipeline</>
        )}
      </button>
    </div>
  );
}

function Slider({
  label, min, max, step = 1, value, onChange,
}: {
  label: string; min: number; max: number; step?: number; value: number;
  onChange: (v: number) => void;
}) {
  return (
    <div>
      <p className="label">{label}</p>
      <input
        type="range" min={min} max={max} step={step} value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full accent-emerald-500 cursor-pointer"
      />
      <div className="flex justify-between text-[10px] text-slate-600 mt-0.5">
        <span>{min}</span><span>{max}</span>
      </div>
    </div>
  );
}
