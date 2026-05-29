import { useState } from "react";
import { ChevronDown, ChevronUp, Download } from "lucide-react";
import type { Variant } from "../types";
import { ImpactBadge } from "./ImpactBadge";

type SortKey = keyof Variant;

interface Props { variants: Variant[]; }

export function VariantTable({ variants }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>("pos");
  const [sortAsc, setSortAsc] = useState(true);
  const [filterImpact, setFilterImpact] = useState("ALL");
  const [filterType,   setFilterType]   = useState("ALL");

  const impacts = ["ALL", ...Array.from(new Set(variants.map((v) => v.impact)))];
  const types   = ["ALL", ...Array.from(new Set(variants.map((v) => v.variant_type)))];

  const sorted = [...variants]
    .filter((v) => filterImpact === "ALL" || v.impact === filterImpact)
    .filter((v) => filterType   === "ALL" || v.variant_type === filterType)
    .sort((a, b) => {
      const av = a[sortKey] as string | number | null;
      const bv = b[sortKey] as string | number | null;
      if (av === null) return 1;
      if (bv === null) return -1;
      const cmp = av < bv ? -1 : av > bv ? 1 : 0;
      return sortAsc ? cmp : -cmp;
    });

  function toggleSort(key: SortKey) {
    if (key === sortKey) setSortAsc(!sortAsc);
    else { setSortKey(key); setSortAsc(true); }
  }

  function SortIcon({ k }: { k: SortKey }) {
    if (k !== sortKey) return null;
    return sortAsc ? <ChevronUp size={12} /> : <ChevronDown size={12} />;
  }

  function downloadCsv() {
    const headers = [
      "Pos","Tipe","Ref","Alt","Kodon#","PosKodon","RefCodon","AltCodon","RefAA","AltAA","Dampak",
      "Conservation","Grantham","Region","RegionCriticality","Pathogenicity","Risk","Confidence",
      "ClinVar","ClinVarSource","ClinicalSignificance","Condition","Recommendation",
    ];
    const rows = sorted.map((v) => [
      v.pos, v.variant_type, v.ref, v.alt,
      v.codon_num ?? "", v.pos_in_codon ?? "",
      v.ref_codon ?? "", v.alt_codon ?? "",
      `${v.ref_aa ?? ""}(${v.ref_aa_name ?? ""})`,
      `${v.alt_aa ?? ""}(${v.alt_aa_name ?? ""})`,
      v.impact,
      v.conservation_score ?? "",
      v.grantham_distance ?? "",
      v.region_type ?? "",
      v.region_criticality ?? "",
      v.pathogenicity_score ?? "",
      v.risk_level ?? "",
      v.confidence ?? "",
      v.clinvar?.variant_id ?? "",
      v.clinvar?.source ?? "",
      v.clinvar?.clinical_significance ?? "",
      v.clinvar?.condition ?? "",
      v.recommendation ?? "",
    ]);
    const escapeCsv = (value: string | number) => {
      const text = String(value);
      return /[",\n\r]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
    };
    const csv = [headers, ...rows].map((r) => r.map(escapeCsv).join(",")).join("\n");
    const a = document.createElement("a");
    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
    a.href = url;
    a.download = "snp_variants.csv";
    a.click();
    URL.revokeObjectURL(url);
  }

  const Th = ({ children, k }: { children: React.ReactNode; k: SortKey }) => (
    <th
      className="px-3 py-2.5 text-left text-xs font-semibold text-gray-500
                 uppercase tracking-wider cursor-pointer hover:text-gray-700
                 whitespace-nowrap select-none bg-gray-50"
      onClick={() => toggleSort(k)}
    >
      <span className="flex items-center gap-1">{children}<SortIcon k={k} /></span>
    </th>
  );

  return (
    <div>
      <div className="flex flex-wrap gap-2 mb-3 items-center">
        <div className="flex items-center gap-1.5">
          <span className="label !mb-0">Dampak:</span>
          <select className="input !w-auto !py-1 !px-2 text-xs" value={filterImpact}
            onChange={(e) => setFilterImpact(e.target.value)}>
            {impacts.map((i) => <option key={i}>{i}</option>)}
          </select>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="label !mb-0">Tipe:</span>
          <select className="input !w-auto !py-1 !px-2 text-xs" value={filterType}
            onChange={(e) => setFilterType(e.target.value)}>
            {types.map((t) => <option key={t}>{t}</option>)}
          </select>
        </div>
        <span className="text-xs text-gray-400 ml-1">{sorted.length} varian</span>
        <button onClick={downloadCsv} className="btn-secondary !py-1 !px-3 text-xs ml-auto">
          <Download size={12} /> CSV
        </button>
      </div>

      <div className="overflow-auto max-h-80 rounded-lg border border-gray-200">
        <table className="w-full text-xs border-collapse">
          <thead className="sticky top-0 z-10">
            <tr className="border-b border-gray-200">
              <Th k="pos">Pos</Th>
              <Th k="variant_type">Tipe</Th>
              <Th k="ref">Ref</Th>
              <Th k="alt">Alt</Th>
              <Th k="codon_num">Kodon</Th>
              <Th k="ref_codon">Kodon Ref→Alt</Th>
              <Th k="ref_aa">AA Ref→Alt</Th>
              <Th k="impact">Dampak</Th>
              <Th k="pathogenicity_score">Risk</Th>
              <Th k="conservation_score">Scores</Th>
              <Th k="region_type">Region</Th>
              <Th k="clinvar">ClinVar</Th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((v, i) => (
              <tr key={i} className="border-b border-gray-100 hover:bg-gray-50 transition-colors">
                <td className="px-3 py-2 text-gray-700">{v.pos}</td>
                <td className="px-3 py-2 text-gray-500">{v.variant_type}</td>
                <td className="px-3 py-2 font-mono text-red-500 font-bold">{v.ref}</td>
                <td className="px-3 py-2 font-mono text-blue-500 font-bold">{v.alt}</td>
                <td className="px-3 py-2 text-gray-500">
                  {v.codon_num ? `#${v.codon_num} (pos ${v.pos_in_codon})` : "—"}
                </td>
                <td className="px-3 py-2 font-mono">
                  {v.ref_codon ? (
                    <>
                      <span className="text-red-500">{v.ref_codon}</span>
                      <span className="text-gray-300"> → </span>
                      <span className="text-blue-500">{v.alt_codon}</span>
                    </>
                  ) : "—"}
                </td>
                <td className="px-3 py-2">
                  {v.ref_aa ? (
                    <>
                      <span className="text-red-500">{v.ref_aa}</span>
                      <span className="text-gray-400 text-[10px]">·{v.ref_aa_name}</span>
                      <span className="text-gray-300"> → </span>
                      <span className="text-blue-500">{v.alt_aa}</span>
                      <span className="text-gray-400 text-[10px]">·{v.alt_aa_name}</span>
                    </>
                  ) : "—"}
                </td>
                <td className="px-3 py-2">
                  <ImpactBadge impact={v.impact as any} />
                </td>
                <td className="px-3 py-2">
                  {v.risk_level ? <RiskBadge risk={v.risk_level} /> : "â€”"}
                  {v.confidence && <div className="text-[10px] text-gray-400 mt-1">{v.confidence}</div>}
                </td>
                <td className="px-3 py-2 text-gray-600">
                  {v.pathogenicity_score !== null ? (
                    <div className="space-y-0.5">
                      <div>Path: <span className="font-mono">{v.pathogenicity_score.toFixed(4)}</span></div>
                      <div>Cons: <span className="font-mono">{v.conservation_score?.toFixed(4) ?? "â€”"}</span></div>
                      <div>G: <span className="font-mono">{v.grantham_distance ?? "â€”"}</span></div>
                    </div>
                  ) : "â€”"}
                </td>
                <td className="px-3 py-2 text-gray-600">
                  {v.region_type ? (
                    <>
                      <div className="font-semibold">{v.region_type}</div>
                      <div className="text-[10px] text-gray-400">{v.region_criticality?.toFixed(2)}</div>
                    </>
                  ) : "â€”"}
                </td>
                <td className="px-3 py-2 text-gray-600 min-w-44">
                  {v.clinvar ? (
                    <div>
                      <div className="flex items-center gap-2">
                        {v.clinvar.url ? (
                          <a
                            href={v.clinvar.url}
                            target="_blank"
                            rel="noreferrer"
                            className="font-mono text-emerald-700 font-semibold hover:underline"
                          >
                            {v.clinvar.variant_id}
                          </a>
                        ) : (
                          <div className="font-mono text-emerald-700 font-semibold">{v.clinvar.variant_id}</div>
                        )}
                        <span className="rounded bg-gray-100 px-1.5 py-0.5 text-[9px] uppercase text-gray-500">
                          {v.clinvar.source ?? "simulated"}
                        </span>
                      </div>
                      <div className="text-[11px]">{v.clinvar.clinical_significance}</div>
                      <div className="text-[10px] text-gray-400">{v.clinvar.condition}</div>
                    </div>
                  ) : (
                    <span className="text-gray-400">No ClinVar match</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {sorted.length === 0 && (
          <div className="text-center py-8 text-gray-400">
            Tidak ada varian yang cocok dengan filter.
          </div>
        )}
      </div>
    </div>
  );
}

function RiskBadge({ risk }: { risk: NonNullable<Variant["risk_level"]> }) {
  const cls = {
    "HIGH RISK": "bg-red-100 text-red-700 ring-red-300",
    "MODERATE RISK": "bg-amber-100 text-amber-700 ring-amber-300",
    "LOW RISK": "bg-blue-100 text-blue-700 ring-blue-300",
    BENIGN: "bg-emerald-100 text-emerald-700 ring-emerald-300",
  }[risk];
  return <span className={`impact-badge ring-1 ${cls}`}>{risk}</span>;
}
