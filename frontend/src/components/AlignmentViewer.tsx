import { useMemo } from "react";
import type { AlnCol } from "../types";

const CHUNK = 60;

function Base({ char, kind, role }: { char: string; kind: AlnCol["kind"]; role: "ref" | "alt" }) {
  if (kind === "match") return <span className="aln-match">{char}</span>;
  if (kind === "gap")   return <span className="aln-gap">{char}</span>;
  return role === "ref"
    ? <span className="aln-mismatch-ref">{char}</span>
    : <span className="aln-mismatch-alt">{char}</span>;
}

interface Props {
  cols: AlnCol[];
}

export function AlignmentViewer({ cols }: Props) {
  const chunks = useMemo(() => {
    const out = [];
    for (let i = 0; i < cols.length; i += CHUNK) {
      out.push({ start: i + 1, slice: cols.slice(i, i + CHUNK) });
    }
    return out;
  }, [cols]);

  const snpCount = cols.filter((c) => c.kind === "mismatch").length;
  const gapCount = cols.filter((c) => c.kind === "gap").length;

  return (
    <div>
      <div className="flex gap-4 mb-3 text-xs text-slate-500">
        <span><span className="aln-mismatch-ref font-bold">X</span> Ref · <span className="aln-mismatch-alt font-bold">X</span> Alt</span>
        <span className="aln-match">| match</span>
        <span className="text-slate-600">– gap</span>
        <span className="ml-auto">
          {snpCount} SNP · {gapCount} gap · {cols.length} kolom
        </span>
      </div>
      <div className="overflow-y-auto max-h-72 bg-slate-950 rounded-lg p-3 border border-slate-800">
        <pre className="font-mono text-xs leading-6 whitespace-pre">
          {chunks.map(({ start, slice }) => {
            const end = start + slice.length - 1;
            const mid = slice.map((c) =>
              c.kind === "match" ? "|" : c.kind === "gap" ? " " : "·"
            ).join("");
            return (
              <div key={start}>
                <span className="text-slate-600 select-none mr-2">
                  REF  [{String(start).padStart(5)}–{String(end).padEnd(5)}]
                </span>
                {slice.map((c, i) => (
                  <Base key={i} char={c.ref} kind={c.kind} role="ref" />
                ))}
                {"\n"}
                <span className="text-transparent select-none mr-2">{"             "}</span>
                <span className="aln-match">{mid}</span>
                {"\n"}
                <span className="text-slate-600 select-none mr-2">
                  SMPL [{String(start).padStart(5)}–{String(end).padEnd(5)}]
                </span>
                {slice.map((c, i) => (
                  <Base key={i} char={c.alt} kind={c.kind} role="alt" />
                ))}
                {"\n\n"}
              </div>
            );
          })}
        </pre>
      </div>
    </div>
  );
}
