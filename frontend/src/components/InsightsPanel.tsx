import { useMemo } from "react";
import { AlertTriangle, CheckCircle2, Info, Sparkles, TrendingDown, TrendingUp } from "lucide-react";
import type { AIGuide, PipelineResult } from "../types";
import { ImpactBadge } from "./ImpactBadge";

const IMPACT_COLOR: Record<string, string> = {
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

function countImpacts(variants: PipelineResult["variants"]) {
  const counts: Record<string, number> = {};
  for (const v of variants) counts[v.impact] = (counts[v.impact] ?? 0) + 1;
  return counts;
}

function proteinDiff(ref: string, smp: string) {
  return [...ref].filter((a, i) => a !== (smp[i] ?? "")).length;
}

interface Finding {
  level: "info" | "warn" | "ok";
  text: string;
}

function deriveFindings(result: PipelineResult): Finding[] {
  const { variants, stats, evaluation, ref_protein, sample_protein } = result;
  const findings: Finding[] = [];

  if (stats.total === 0) {
    findings.push({ level: "ok", text: "Tidak ada varian terdeteksi — kedua sekuens identik." });
    return findings;
  }

  const counts = countImpacts(variants);
  const dominant = Object.entries(counts).sort(([, a], [, b]) => b - a)[0];
  findings.push({
    level: "info",
    text: `Mutasi paling umum: ${dominant[0]} — ${dominant[1]} varian (${Math.round((dominant[1] / stats.total) * 100)}% dari total).`,
  });

  const nDiff = proteinDiff(ref_protein, sample_protein);
  if (nDiff === 0) {
    findings.push({ level: "ok", text: "Sekuens protein tidak berubah — semua mutasi bersifat sinonim (synonymous)." });
  } else {
    findings.push({
      level: counts.MISSENSE ? "warn" : "info",
      text: `${nDiff} dari ${ref_protein.length} residu asam amino berubah pada sekuens protein.`,
    });
  }

  if (counts.NONSENSE) {
    findings.push({
      level: "warn",
      text: `${counts.NONSENSE} mutasi nonsense terdeteksi — berpotensi menyebabkan protein terpotong sebelum waktunya.`,
    });
  }
  if (counts.STOP_LOST) {
    findings.push({
      level: "warn",
      text: `${counts.STOP_LOST} kodon stop hilang — protein dapat memanjang secara abnormal melewati ujung normal.`,
    });
  }
  if (counts.FRAMESHIFT) {
    findings.push({
      level: "warn",
      text: `Frameshift terdeteksi — seluruh urutan asam amino setelah titik mutasi bergeser, kemungkinan menghasilkan protein non-fungsional.`,
    });
  }
  if ((counts.SILENT ?? 0) === stats.total) {
    findings.push({ level: "ok", text: "Seluruh SNP bersifat silent — tidak ada dampak pada rangkaian asam amino." });
  }
  if (evaluation) {
    const { precision, recall, f1 } = evaluation;
    const level = f1 >= 0.95 ? "ok" : f1 >= 0.8 ? "info" : "warn";
    findings.push({
      level,
      text: `Akurasi deteksi (vs. ground truth): Precision ${precision.toFixed(3)}, Recall ${recall.toFixed(3)}, F1 ${f1.toFixed(3)}.`,
    });
  }

  return findings;
}

function deriveConclusion(result: PipelineResult): string {
  const { variants, stats, ref_protein, sample_protein } = result;

  if (stats.total === 0) {
    return "Kedua sekuens identik. Tidak ditemukan variasi genetik apa pun antara sekuens referensi dan sampel yang diberikan.";
  }

  const counts = countImpacts(variants);
  const missense  = counts.MISSENSE  ?? 0;
  const silent    = counts.SILENT    ?? 0;
  const nonsense  = counts.NONSENSE  ?? 0;
  const frameshift = counts.FRAMESHIFT ?? 0;
  const stopLost  = counts.STOP_LOST ?? 0;
  const nDiff     = proteinDiff(ref_protein, sample_protein);
  const hasHigh   = nonsense + frameshift + stopLost > 0;

  if (hasHigh) {
    return `Pipeline mendeteksi ${stats.total} varian termasuk mutasi berdampak tinggi ` +
      `(${[nonsense && `${nonsense} nonsense`, frameshift && `${frameshift} frameshift`, stopLost && `${stopLost} stop-lost`].filter(Boolean).join(", ")}). ` +
      `Jenis mutasi ini berpotensi menyebabkan disfungsi protein yang signifikan dan ` +
      `memerlukan investigasi lebih lanjut terkait konsekuensi fungsional maupun klinisnya.`;
  }

  if (stats.total > 0 && missense / stats.total > 0.6) {
    return `Dari ${stats.total} varian yang terdeteksi, ${missense} (${Math.round((missense / stats.total) * 100)}%) bersifat missense ` +
      `sehingga mengubah ${nDiff} residu asam amino. Perubahan ini dapat memengaruhi struktur tiga dimensi dan ` +
      `aktivitas biologis protein, tergantung pada posisi dan sifat kimia asam amino yang terlibat.`;
  }

  if (stats.total > 0 && silent / stats.total > 0.6) {
    return `Sebagian besar dari ${stats.total} varian bersifat silent (${Math.round((silent / stats.total) * 100)}%), ` +
      `menunjukkan bahwa variasi pada tingkat DNA tidak berdampak signifikan terhadap rangkaian asam amino. ` +
      `Sekuens protein relatif terjaga antara referensi dan sampel.`;
  }

  const parts = Object.entries(counts)
    .sort(([, a], [, b]) => b - a)
    .map(([k, v]) => `${k.toLowerCase().replace("_", " ")} (${v})`);

  return `Pipeline mendeteksi ${stats.total} varian dengan komposisi: ${parts.join(", ")}. ` +
    `Profil campuran ini mengindikasikan adanya tekanan selektif yang bervariasi sepanjang sekuens, ` +
    `dan analisis lebih lanjut diperlukan untuk menentukan relevansi fungsionalnya.`;
}

const GUIDE_STYLE: Record<AIGuide["severity"], string> = {
  ok: "border-emerald-200 bg-emerald-50",
  info: "border-blue-200 bg-blue-50",
  warning: "border-amber-200 bg-amber-50",
  critical: "border-red-200 bg-red-50",
};

interface SmartGuideProps {
  guide: AIGuide | null;
  loading: boolean;
  error: string | null;
}

function SmartGuide({ guide, loading, error }: SmartGuideProps) {
  if (loading) {
    return (
      <div className="border border-blue-200 bg-blue-50 rounded-xl p-4">
        <p className="section-title text-blue-700">
          <Sparkles size={14} /> Panduan AI
        </p>
        <p className="text-sm text-blue-700 animate-pulse">Gemini sedang menyusun panduan hasil...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="border border-gray-200 bg-gray-50 rounded-xl p-4">
        <p className="section-title">
          <Sparkles size={14} /> Panduan AI
        </p>
        <p className="text-sm text-gray-500">{error}</p>
      </div>
    );
  }

  if (!guide) return null;

  return (
    <div className={`border rounded-xl p-4 ${GUIDE_STYLE[guide.severity]}`}>
      <p className="section-title">
        <Sparkles size={14} /> Panduan AI
      </p>
      <h3 className="text-base font-semibold text-gray-900">{guide.headline}</h3>
      <p className="text-sm text-gray-700 leading-relaxed mt-2">{guide.summary}</p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
        <div>
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Temuan</p>
          <ul className="space-y-1.5 text-sm text-gray-700">
            {guide.key_findings.map((item, i) => <li key={i}>- {item}</li>)}
          </ul>
        </div>
        <div>
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Langkah Lanjut</p>
          <ul className="space-y-1.5 text-sm text-gray-700">
            {guide.next_steps.map((item, i) => <li key={i}>- {item}</li>)}
          </ul>
        </div>
      </div>
      {guide.limitations.length > 0 && (
        <p className="text-xs text-gray-500 mt-4">Batasan: {guide.limitations.join(" ")}</p>
      )}
      <p className="text-xs text-gray-500 mt-2">{guide.disclaimer}</p>
    </div>
  );
}

interface Props {
  result: PipelineResult;
  aiGuide: AIGuide | null;
  aiLoading: boolean;
  aiError: string | null;
}

export function InsightsPanel({ result, aiGuide, aiLoading, aiError }: Props) {
  const { variants, stats, ref_protein, sample_protein } = result;
  const counts  = useMemo(() => countImpacts(variants), [variants]);
  const findings = useMemo(() => deriveFindings(result), [result]);
  const conclusion = useMemo(() => deriveConclusion(result), [result]);
  const nDiff   = useMemo(() => proteinDiff(ref_protein, sample_protein), [ref_protein, sample_protein]);

  const sorted = Object.entries(counts).sort(([, a], [, b]) => b - a);
  const maxCount = sorted[0]?.[1] ?? 1;

  if (stats.total === 0) {
    return (
      <div className="space-y-5">
        <SmartGuide guide={aiGuide} loading={aiLoading} error={aiError} />
        <div className="flex flex-col items-center justify-center gap-3 py-12 text-center">
          <CheckCircle2 size={40} className="text-emerald-500" />
          <p className="text-gray-700 font-semibold">Tidak ada varian terdeteksi</p>
          <p className="text-sm text-gray-400">Kedua sekuens identik — tidak ada perbedaan nukleotida.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <SmartGuide guide={aiGuide} loading={aiLoading} error={aiError} />

      {/* ── Impact distribution ── */}
      <div>
        <p className="section-title">Distribusi Dampak Mutasi</p>
        <div className="space-y-2">
          {sorted.map(([impact, count]) => (
            <div key={impact} className="flex items-center gap-3">
              <div className="w-28 shrink-0">
                <ImpactBadge impact={impact as any} />
              </div>
              <div className="flex-1 bg-gray-100 rounded-full h-2 overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{
                    width: `${(count / maxCount) * 100}%`,
                    background: IMPACT_COLOR[impact] ?? "#9ca3af",
                  }}
                />
              </div>
              <div className="w-20 text-right text-sm text-gray-700">
                <span className="font-semibold">{count}</span>
                <span className="text-gray-400 text-xs ml-1">
                  ({Math.round((count / stats.total) * 100)}%)
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ── Findings + Protein side by side ── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

        {/* Temuan utama */}
        <div className="bg-gray-50 border border-gray-200 rounded-xl p-4">
          <p className="section-title">Temuan Utama</p>
          <ul className="space-y-2">
            {findings.map((f, i) => (
              <li key={i} className="flex gap-2 text-sm">
                {f.level === "ok"   && <CheckCircle2 size={15} className="text-emerald-500 shrink-0 mt-0.5" />}
                {f.level === "warn" && <AlertTriangle size={15} className="text-amber-500 shrink-0 mt-0.5" />}
                {f.level === "info" && <Info size={15} className="text-blue-400 shrink-0 mt-0.5" />}
                <span className="text-gray-600 leading-snug">{f.text}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Protein overview */}
        <div className="bg-gray-50 border border-gray-200 rounded-xl p-4">
          <p className="section-title">Dampak pada Protein</p>
          <div className="space-y-3">
            <div className="flex items-end gap-2">
              <span className="text-4xl font-bold text-gray-800">{nDiff}</span>
              <span className="text-sm text-gray-400 mb-1.5">
                / {ref_protein.length} residu berubah
              </span>
            </div>

            {/* Progress bar */}
            <div className="space-y-1">
              <div className="flex justify-between text-xs text-gray-400">
                <span>Identik</span>
                <span>Berubah</span>
              </div>
              <div className="bg-gray-200 rounded-full h-2.5 overflow-hidden">
                <div
                  className="h-full rounded-full bg-red-400 transition-all duration-500"
                  style={{ width: `${(nDiff / Math.max(ref_protein.length, 1)) * 100}%` }}
                />
              </div>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-3 gap-2 pt-1">
              {[
                { label: "SNP",      val: stats.snps, icon: <TrendingUp size={13} className="text-red-400" /> },
                { label: "Insersi",  val: stats.ins,  icon: <TrendingUp size={13} className="text-blue-400" /> },
                { label: "Delesi",   val: stats.dels, icon: <TrendingDown size={13} className="text-amber-400" /> },
              ].map(({ label, val, icon }) => (
                <div key={label} className="bg-white border border-gray-200 rounded-lg p-2 text-center">
                  <div className="flex justify-center mb-0.5">{icon}</div>
                  <div className="text-lg font-bold text-gray-800">{val}</div>
                  <div className="text-[10px] text-gray-400 uppercase tracking-wide">{label}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* ── Conclusion ── */}
      <div className="border border-emerald-200 bg-emerald-50 rounded-xl p-4">
        <p className="text-xs font-semibold text-emerald-700 uppercase tracking-wider mb-2 flex items-center gap-1.5">
          <CheckCircle2 size={13} /> Kesimpulan
        </p>
        <p className="text-sm text-gray-700 leading-relaxed">{conclusion}</p>
      </div>

    </div>
  );
}
