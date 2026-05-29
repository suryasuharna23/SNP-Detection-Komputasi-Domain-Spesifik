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
  conservation_score: number | null;
  grantham_distance: number | null;
  region_type: RegionType | null;
  region_criticality: number | null;
  rarity_bonus: number | null;
  clinvar_severity: number | null;
  pathogenicity_score: number | null;
  risk_level: RiskLevel | null;
  confidence: ConfidenceLevel | null;
  recommendation: string | null;
  clinvar: ClinVarEntry | null;
}

export type RegionType =
  | "SPLICE_SITE"
  | "EXON_CODING"
  | "5_UTR"
  | "3_UTR"
  | "INTRON"
  | "PROMOTER"
  | "INTERGENIC";

export type RiskLevel = "HIGH RISK" | "MODERATE RISK" | "LOW RISK" | "BENIGN";
export type ConfidenceLevel = "HIGH" | "MEDIUM" | "LOW";
export type FrameMode = "manual" | "automatic";
export type CodonTableType = "standard" | "vertebrate_mitochondrial";
export type ClinVarSource = "simulated" | "real" | "both";

export interface ClinVarEntry {
  variant_id: string;
  gene: string;
  hgvs_c: string;
  hgvs_p: string;
  clinical_significance: string;
  condition: string;
  review_status: string;
  allele_frequency: number;
  evidence_count: number;
  source?: "simulated" | "real";
  url?: string | null;
}

export interface ORF {
  start: number;
  end: number;
  frame: number;
  strand: "+" | "-";
  length_bp: number;
  length_aa: number;
  protein?: string;
}

export interface GeneAnnotation {
  gene_name?: string;
  strand: "+" | "-";
  total_length?: number;
  exons: Array<[number, number]>;
  cds_start: number;
  cds_end: number;
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
  gene_name: string;
  frame_mode: FrameMode;
  codon_table: CodonTableType;
  clinvar_source: ClinVarSource;
  clinvar_lookup: {
    requested: boolean;
    source: string;
    queried: number;
    matches: number;
    elapsed_ms?: number;
    message: string;
  };
  selected_frame: number;
  selected_strand: "+" | "-";
  orf_detected: boolean;
  selected_orf: ORF | null;
  orfs: Array<ORF | null>;
  annotation: Required<Omit<GeneAnnotation, "gene_name">> & { gene_name: string };
  clinical_report: string;
  stats: PipelineStats;
}

export interface AIGuide {
  headline: string;
  severity: "ok" | "info" | "warning" | "critical";
  summary: string;
  key_findings: string[];
  next_steps: string[];
  limitations: string[];
  disclaimer: string;
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
  frame_mode?: FrameMode;
  codon_table?: CodonTableType;
  clinvar_source?: ClinVarSource;
  gene_name?: string;
  annotation?: GeneAnnotation;
}
