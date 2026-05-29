import { useState } from "react";
import { Dna, FlaskConical, BookOpen, Activity, BarChart2 } from "lucide-react";
import { clsx } from "clsx";
import type { PipelineResult, SensitivityResult, TabType, RunParams } from "./types";
import { runPipeline, runSensitivity } from "./api";
import { InputPanel }        from "./components/InputPanel";
import { AlignmentViewer }   from "./components/AlignmentViewer";
import { SNPTrack }          from "./components/SNPTrack";
import { ImpactChart }       from "./components/ImpactChart";
import { SubstitutionMatrix } from "./components/SubstitutionMatrix";
import { VariantTable }      from "./components/VariantTable";
import { SensitivityChart }  from "./components/SensitivityChart";
import { ImpactBadge }       from "./components/ImpactBadge";

// ── Result sub-tab ─────────────────────────────────────────────────────────────
type ResultTab = "alignment" | "variants" | "charts" | "protein";

// ── App ────────────────────────────────────────────────────────────────────────
export default function App() {
  const [tab,     setTab]     = useState<TabType>("demo");
  const [result,  setResult]  = useState<PipelineResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState<string | null>(null);
  const [resTab,  setResTab]  = useState<ResultTab>("alignment");

  // Sensitivity
  const [sensLoading, setSensLoading] = useState(false);
  const [sensResult,  setSensResult]  = useState<SensitivityResult | null>(null);
  const [sensError,   setSensError]   = useState<string | null>(null);
  const [sensParams,  setSensParams]  = useState({
    ref_length: 600, max_snps: 120, n_points: 6, n_trials: 5,
  });

  async function handleRun(params: RunParams) {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await runPipeline(params);
      setResult(res);
      setResTab("alignment");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  async function handleSensitivity() {
    setSensLoading(true);
    setSensError(null);
    setSensResult(null);
    try {
      const res = await runSensitivity(sensParams);
      setSensResult(res);
    } catch (e) {
      setSensError(e instanceof Error ? e.message : String(e));
    } finally {
      setSensLoading(false);
    }
  }

  const TABS: { id: TabType; icon: React.ReactNode; label: string }[] = [
    { id: "demo",        icon: <Dna size={14} />,      label: "Demo Pipeline" },
    { id: "sensitivity", icon: <Activity size={14} />, label: "Sensitivitas" },
    { id: "about",       icon: <BookOpen size={14} />, label: "Tentang" },
  ];

  const RES_TABS: { id: ResultTab; label: string }[] = [
    { id: "alignment", label: "Alignment" },
    { id: "variants",  label: "Varian" },
    { id: "charts",    label: "Charts" },
    { id: "protein",   label: "Protein" },
  ];

  return (
    <div className="min-h-screen flex flex-col">
      {/* ── Header ── */}
      <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center gap-4">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-emerald-600 flex items-center justify-center">
              <Dna size={18} className="text-white" />
            </div>
            <div>
              <h1 className="text-sm font-bold text-slate-100 leading-none">SNP Detection</h1>
              <p className="text-[10px] text-slate-500 leading-none mt-0.5">IF3211 · Komputasi Domain Spesifik · ITB</p>
            </div>
          </div>

          <nav className="flex gap-1 ml-6">
            {TABS.map((t) => (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={clsx("tab flex items-center gap-1.5", tab === t.id ? "tab-active" : "tab-inactive")}
              >
                {t.icon}
                {t.label}
              </button>
            ))}
          </nav>

          <div className="ml-auto hidden sm:flex gap-2 text-xs text-slate-600">
            <span className="px-2 py-1 bg-slate-800 rounded font-mono">Needleman–Wunsch</span>
            <span className="px-2 py-1 bg-slate-800 rounded font-mono">Biopython</span>
          </div>
        </div>
      </header>

      <main className="flex-1 max-w-7xl mx-auto w-full px-4 py-6">

        {/* ══════════════════════════════════════════════════════════════════════
            TAB: DEMO
            ══════════════════════════════════════════════════════════════════════ */}
        {tab === "demo" && (
          <div className="grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-5">
            {/* Input */}
            <aside>
              <div className="card h-full">
                <h2 className="text-base font-semibold text-slate-200 mb-4 flex items-center gap-2">
                  <FlaskConical size={16} className="text-emerald-400" />
                  Parameter Input
                </h2>
                <InputPanel onRun={handleRun} loading={loading} />
              </div>
            </aside>

            {/* Results */}
            <div className="space-y-4">
              {error && (
                <div className="card border-red-900 bg-red-950/30 text-red-400 text-sm">
                  Error: {error}
                </div>
              )}

              {!result && !loading && !error && (
                <div className="card flex flex-col items-center justify-center min-h-64 gap-3 text-center">
                  <Dna size={40} className="text-slate-700" />
                  <p className="text-slate-500 text-sm">
                    Pilih dataset dan klik <strong className="text-emerald-400">Jalankan Pipeline</strong>
                  </p>
                  <div className="text-xs text-slate-700 space-y-1 mt-2">
                    <p>Alignment sekuens dengan Needleman–Wunsch</p>
                    <p>Deteksi SNP otomatis</p>
                    <p>Klasifikasi dampak mutasi terhadap protein</p>
                  </div>
                </div>
              )}

              {loading && (
                <div className="card flex flex-col items-center justify-center min-h-64 gap-4">
                  <div className="relative">
                    <div className="w-14 h-14 rounded-full border-4 border-slate-800 border-t-emerald-500 animate-spin" />
                    <Dna size={20} className="absolute inset-0 m-auto text-emerald-500" />
                  </div>
                  <p className="text-slate-400 text-sm animate-pulse">Menjalankan pipeline…</p>
                </div>
              )}

              {result && (
                <>
                  {/* Metrics row */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <MetricCard label="Panjang Ref"    value={`${result.stats.ref_len} bp`} />
                    <MetricCard label="Skor Alignment" value={result.alignment_score.toFixed(0)} />
                    <MetricCard label="Total Varian"   value={result.stats.total} color="text-amber-400" />
                    <MetricCard label="SNP Terdeteksi" value={result.stats.snps}  color="text-red-400" />
                  </div>

                  {/* Evaluation (synthetic only) */}
                  {result.evaluation && (
                    <div className="card border-emerald-900/50 bg-emerald-950/20">
                      <p className="section-title text-emerald-400">
                        <Activity size={14} /> Evaluasi vs Ground Truth
                      </p>
                      <div className="grid grid-cols-3 gap-3">
                        <EvalMetric label="Precision" value={result.evaluation.precision}
                          sub={`TP=${result.evaluation.tp} FP=${result.evaluation.fp}`} />
                        <EvalMetric label="Recall"    value={result.evaluation.recall}
                          sub={`FN=${result.evaluation.fn}`} />
                        <EvalMetric label="F1-Score"  value={result.evaluation.f1} />
                      </div>
                    </div>
                  )}

                  {/* Result sub-tabs */}
                  <div className="card !p-0 overflow-hidden">
                    <div className="flex border-b border-slate-800 px-2 pt-2 gap-1">
                      {RES_TABS.map((rt) => (
                        <button
                          key={rt.id}
                          onClick={() => setResTab(rt.id)}
                          className={clsx("tab text-xs", resTab === rt.id ? "tab-active" : "tab-inactive")}
                        >
                          {rt.label}
                        </button>
                      ))}
                    </div>

                    <div className="p-5">
                      {resTab === "alignment" && (
                        <>
                          <p className="section-title">
                            <BarChart2 size={14} className="text-emerald-400" />
                            Pratinjau Alignment
                          </p>
                          <AlignmentViewer cols={result.alignment_cols} />
                        </>
                      )}

                      {resTab === "variants" && (
                        <>
                          <p className="section-title">
                            <FlaskConical size={14} className="text-emerald-400" />
                            Tabel Varian ({result.variants.length})
                          </p>
                          {result.variants.length === 0 ? (
                            <p className="text-slate-500 text-sm text-center py-8">
                              Tidak ada varian terdeteksi — sekuens identik.
                            </p>
                          ) : (
                            <VariantTable variants={result.variants} />
                          )}
                        </>
                      )}

                      {resTab === "charts" && result.variants.length > 0 && (
                        <div className="space-y-6">
                          <div>
                            <p className="section-title">
                              <Activity size={14} className="text-emerald-400" /> Track Posisi SNP
                            </p>
                            <SNPTrack variants={result.variants} refLength={result.stats.ref_len} />
                          </div>
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                            <div>
                              <p className="section-title">Distribusi Dampak</p>
                              <ImpactChart variants={result.variants} />
                            </div>
                            <div>
                              <p className="section-title">Matriks Substitusi REF → ALT</p>
                              <SubstitutionMatrix variants={result.variants} />
                            </div>
                          </div>
                        </div>
                      )}

                      {resTab === "protein" && (
                        <div className="space-y-4">
                          <p className="section-title">
                            <Dna size={14} className="text-emerald-400" /> Translasi Protein
                          </p>
                          <ProteinCompare
                            refProtein={result.ref_protein}
                            smpProtein={result.sample_protein}
                          />
                        </div>
                      )}
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>
        )}

        {/* ══════════════════════════════════════════════════════════════════════
            TAB: SENSITIVITY
            ══════════════════════════════════════════════════════════════════════ */}
        {tab === "sensitivity" && (
          <div>
            <div className="mb-6">
              <h2 className="text-xl font-bold text-slate-100">Eksperimen Sensitivitas</h2>
              <p className="text-sm text-slate-500 mt-1">
                Ukur bagaimana akurasi deteksi SNP berubah ketika densitas mutasi meningkat.
              </p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr] gap-5">
              <div className="card space-y-4">
                <h3 className="text-sm font-semibold text-slate-300">Parameter Eksperimen</h3>
                <SensSlider
                  label={`Panjang referensi: ${sensParams.ref_length} bp`}
                  min={200} max={1000} step={100} value={sensParams.ref_length}
                  onChange={(v) => setSensParams((p) => ({ ...p, ref_length: v }))}
                />
                <SensSlider
                  label={`SNP maksimum: ${sensParams.max_snps}`}
                  min={10} max={Math.min(200, Math.floor(sensParams.ref_length / 3))} step={10}
                  value={sensParams.max_snps}
                  onChange={(v) => setSensParams((p) => ({ ...p, max_snps: v }))}
                />
                <SensSlider
                  label={`Titik densitas: ${sensParams.n_points}`}
                  min={3} max={8} value={sensParams.n_points}
                  onChange={(v) => setSensParams((p) => ({ ...p, n_points: v }))}
                />
                <SensSlider
                  label={`Trial per titik: ${sensParams.n_trials}`}
                  min={2} max={10} value={sensParams.n_trials}
                  onChange={(v) => setSensParams((p) => ({ ...p, n_trials: v }))}
                />
                <p className="text-xs text-slate-600">
                  {sensParams.n_points * sensParams.n_trials} alignment total
                </p>
                <button
                  className="btn-primary w-full justify-center"
                  onClick={handleSensitivity}
                  disabled={sensLoading}
                >
                  {sensLoading ? (
                    <span className="flex items-center gap-2">
                      <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
                      </svg>
                      Menghitung…
                    </span>
                  ) : (
                    <><Activity size={14} /> Jalankan Eksperimen</>
                  )}
                </button>
              </div>

              <div className="card">
                {sensError && (
                  <div className="text-red-400 text-sm mb-4">Error: {sensError}</div>
                )}
                {!sensResult && !sensLoading && (
                  <div className="flex flex-col items-center justify-center min-h-64 gap-3 text-slate-600">
                    <Activity size={36} />
                    <p className="text-sm">Atur parameter dan klik Jalankan Eksperimen</p>
                  </div>
                )}
                {sensLoading && (
                  <div className="flex flex-col items-center justify-center min-h-64 gap-4">
                    <div className="w-12 h-12 rounded-full border-4 border-slate-800 border-t-blue-500 animate-spin" />
                    <p className="text-slate-400 text-sm animate-pulse">
                      Menjalankan {sensParams.n_points * sensParams.n_trials} alignment…
                    </p>
                  </div>
                )}
                {sensResult && (
                  <SensitivityChart
                    data={sensResult.results}
                    refLength={sensResult.ref_length}
                    nTrials={sensResult.n_trials}
                  />
                )}
              </div>
            </div>
          </div>
        )}

        {/* ══════════════════════════════════════════════════════════════════════
            TAB: ABOUT
            ══════════════════════════════════════════════════════════════════════ */}
        {tab === "about" && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5 max-w-5xl">
            <div className="card space-y-5">
              <h2 className="text-lg font-bold text-slate-100">Tentang Proyek</h2>
              <p className="text-sm text-slate-400 leading-relaxed">
                Implementasi pipeline komputasi bioinformatika untuk mata kuliah{" "}
                <strong className="text-slate-200">IF3211 — Komputasi Domain Spesifik</strong>,
                Institut Teknologi Bandung.
              </p>

              <div>
                <p className="section-title">Pipeline</p>
                <div className="space-y-2 text-sm">
                  {[
                    ["1", "Load & Validasi", "Baca sekuens FASTA, validasi karakter DNA"],
                    ["2", "Sequence Alignment", "Needleman–Wunsch global alignment"],
                    ["3", "Deteksi Varian", "Identifikasi SNP, INS, DEL dari alignment"],
                    ["4", "Klasifikasi Dampak", "Silent / Missense / Nonsense / Frameshift"],
                    ["5", "Visualisasi", "Track posisi, distribusi, matriks substitusi"],
                  ].map(([num, title, desc]) => (
                    <div key={num} className="flex gap-3">
                      <span className="w-6 h-6 rounded-full bg-emerald-900 text-emerald-400
                                       text-xs font-bold flex items-center justify-center shrink-0 mt-0.5">
                        {num}
                      </span>
                      <div>
                        <p className="font-semibold text-slate-300 text-sm">{title}</p>
                        <p className="text-slate-500 text-xs">{desc}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <p className="section-title">Kasus Sickle-Cell Anemia</p>
                <div className="card !bg-slate-800/50 !p-3 text-xs space-y-2">
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <p className="text-emerald-400 font-semibold">Wild-type</p>
                      <p className="font-mono text-slate-400">GAG → Glu (Glutamat)</p>
                    </div>
                    <div>
                      <p className="text-red-400 font-semibold">Sickle-cell</p>
                      <p className="font-mono text-slate-400">GTG → Val (Valin)</p>
                    </div>
                  </div>
                  <p className="text-slate-500">
                    Satu mutasi A→T pada posisi 20 mengubah bentuk eritrosit menjadi bulan sabit.
                  </p>
                </div>
              </div>
            </div>

            <div className="space-y-5">
              <div className="card">
                <p className="section-title">Algoritma Needleman–Wunsch</p>
                <div className="font-mono text-xs text-slate-400 bg-slate-950 rounded-lg p-3 leading-relaxed">
                  <p className="text-slate-600 mb-1">{/* DP recurrence */}</p>
                  <p>F(i,j) = max &#123;</p>
                  <p className="ml-4">F(i-1,j-1) + s(xi,yj)  <span className="text-slate-600"># match/mismatch</span></p>
                  <p className="ml-4">F(i-1,j)   + g          <span className="text-slate-600"># gap di y</span></p>
                  <p className="ml-4">F(i,j-1)   + g          <span className="text-slate-600"># gap di x</span></p>
                  <p>&#125;</p>
                </div>
                <div className="grid grid-cols-2 gap-2 mt-3 text-xs">
                  {[["Match", "+2"], ["Mismatch", "−1"], ["Gap open", "−2"], ["Gap extend", "−1"]].map(([k, v]) => (
                    <div key={k} className="flex justify-between bg-slate-800 rounded px-3 py-1.5">
                      <span className="text-slate-400">{k}</span>
                      <span className="font-mono text-emerald-400 font-bold">{v}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="card">
                <p className="section-title">Kategori Dampak Mutasi</p>
                <div className="space-y-2">
                  {(["SILENT","MISSENSE","NONSENSE","STOP_LOST","FRAMESHIFT"] as const).map((imp) => (
                    <div key={imp} className="flex items-start gap-2 text-xs">
                      <ImpactBadge impact={imp} />
                      <span className="text-slate-500">
                        {{
                          SILENT:    "Asam amino tidak berubah (redundansi kode genetik)",
                          MISSENSE:  "Asam amino berbeda — dapat mengubah fungsi protein",
                          NONSENSE:  "Muncul kodon stop prematur (*) — protein terpotong",
                          STOP_LOST: "Kodon stop asli berubah menjadi asam amino",
                          FRAMESHIFT:"Indel bukan kelipatan 3 — semua kodon setelahnya bergeser",
                        }[imp]}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="card">
                <p className="section-title">Teknologi</p>
                <div className="flex flex-wrap gap-2 text-xs">
                  {["Python 3", "FastAPI", "Biopython", "NumPy",
                    "React 18", "TypeScript", "Tailwind CSS", "Recharts"].map((t) => (
                    <span key={t} className="px-2.5 py-1 bg-slate-800 rounded-full text-slate-400 border border-slate-700">
                      {t}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
      </main>

      <footer className="border-t border-slate-800 py-3 px-4 text-center text-xs text-slate-700">
        IF3211 — Komputasi Domain Spesifik · Institut Teknologi Bandung · 2025
      </footer>
    </div>
  );
}

// ── Helpers ────────────────────────────────────────────────────────────────────

function MetricCard({
  label, value, color = "text-emerald-400",
}: { label: string; value: string | number; color?: string }) {
  return (
    <div className="metric-card">
      <span className={`metric-value ${color}`}>{value}</span>
      <span className="metric-label">{label}</span>
    </div>
  );
}

function EvalMetric({
  label, value, sub,
}: { label: string; value: number; sub?: string }) {
  const pct = Math.round(value * 1000) / 10;
  const color = value >= 0.95 ? "text-emerald-400" : value >= 0.8 ? "text-amber-400" : "text-red-400";
  return (
    <div className="bg-slate-800/50 rounded-lg p-3 text-center">
      <div className={`text-xl font-bold font-mono ${color}`}>{value.toFixed(3)}</div>
      <div className="text-xs text-slate-400 font-medium">{label}</div>
      {sub && <div className="text-[10px] text-slate-600 mt-0.5">{sub}</div>}
      <div className="mt-2 h-1.5 bg-slate-700 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color.replace("text-","bg-")}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function ProteinCompare({
  refProtein, smpProtein,
}: { refProtein: string; smpProtein: string }) {
  const diffs = Array.from({ length: Math.max(refProtein.length, smpProtein.length) }, (_, i) => ({
    ref: refProtein[i] ?? " ",
    smp: smpProtein[i] ?? " ",
    diff: (refProtein[i] ?? " ") !== (smpProtein[i] ?? " "),
  }));
  const nDiff = diffs.filter((d) => d.diff).length;

  return (
    <div className="space-y-4">
      {nDiff === 0 ? (
        <div className="card !bg-emerald-950/30 border-emerald-900/50 text-emerald-400 text-sm text-center py-3">
          Protein identik — semua mutasi bersifat silent.
        </div>
      ) : (
        <div className="card !bg-red-950/20 border-red-900/30 text-red-400 text-sm text-center py-3">
          {nDiff} residu protein berubah.
        </div>
      )}

      <div className="space-y-3">
        {(["Referensi", "Sampel"] as const).map((role) => {
          const seq = role === "Referensi" ? refProtein : smpProtein;
          return (
            <div key={role}>
              <p className="text-xs text-slate-500 mb-1">{role}:</p>
              <div className="bg-slate-950 rounded-lg p-3 font-mono text-sm flex flex-wrap gap-0.5 max-h-32 overflow-y-auto">
                {seq.split("").map((aa, i) => {
                  const isDiff = diffs[i]?.diff;
                  return (
                    <span
                      key={i}
                      title={`${aa} (pos ${i + 1})`}
                      className={`px-0.5 rounded cursor-default ${
                        isDiff
                          ? role === "Referensi"
                            ? "text-red-400 bg-red-900/30"
                            : "text-blue-400 bg-blue-900/30"
                          : "text-slate-500"
                      }`}
                    >
                      {aa}
                    </span>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function SensSlider({
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
        className="w-full accent-blue-500 cursor-pointer"
      />
    </div>
  );
}
