export type ImpactType =
  | "SILENT"
  | "MISSENSE"
  | "NONSENSE"
  | "STOP_LOST"
  | "START_LOST"
  | "FRAMESHIFT"
  | "INFRAME_INDEL"
  | "UTR_OR_OUTOFFRAME"
  | "INCOMPLETE_CODON";

export interface Variant {
  pos: number;
  variant_type: "SNP" | "INS" | "DEL";
  ref: string;
  alt: string;
  codon_num: number | null;
  pos_in_codon: number | null;
  ref_codon: string | null;
  alt_codon: string | null;
  ref_aa: string | null;
  alt_aa: string | null;
  ref_aa_name: string | null;
  alt_aa_name: string | null;
  impact: ImpactType;
}

export interface AlnCol {
  ref: string;
  alt: string;
  kind: "match" | "mismatch" | "gap";
}

export interface Evaluation {
  tp: number;
  fp: number;
  fn: number;
  precision: number;
  recall: number;
  f1: number;
}

export interface PipelineStats {
  total: number;
  snps: number;
  ins: number;
  dels: number;
  ref_len: number;
}

export interface PipelineResult {
  ref_seq: string;
  sample_seq: string;
  ref_aligned: string;
  sample_aligned: string;
  alignment_score: number;
  alignment_cols: AlnCol[];
  variants: Variant[];
  ref_protein: string;
  sample_protein: string;
  evaluation: Evaluation | null;
  stats: PipelineStats;
}

export interface SensitivityPoint {
  n_snp: number;
  density: number;
  precision: { mean: number; std: number };
  recall:    { mean: number; std: number };
  f1:        { mean: number; std: number };
}

export interface SensitivityResult {
  ref_length: number;
  n_trials: number;
  results: SensitivityPoint[];
}

export type DatasetType = "synthetic" | "hbb" | "custom";
export type TabType = "demo" | "sensitivity" | "about";

export interface RunParams {
  dataset: DatasetType;
  ref_seq?: string;
  sample_seq?: string;
  seq_length: number;
  n_snps: number;
  gc_content: number;
  seed: number;
  frame: number;
}
