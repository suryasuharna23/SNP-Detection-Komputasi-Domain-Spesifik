import json
import os
import time
from pathlib import Path
from enum import Enum
from typing import Any, Literal, Optional
from urllib import error, parse, request

import numpy as np
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from pipeline import (
    AA_NAMES,
    ClinVarEntry,
    GeneAnnotation,
    HBB_SICKLE,
    HBB_WILDTYPE,
    assess_impacts,
    align_sequences,
    classify_all,
    find_orfs,
    generate_clinical_report,
    get_codon_table,
    detect_variants,
    evaluate,
    generate_random_dna,
    impacts_to_dicts,
    introduce_point_mutations,
    lookup_clinvar,
    map_impact_to_original_coordinates,
    orf_to_dict,
    reverse_complement,
    translate_dna,
    validate_dna,
)


def load_project_env() -> None:
    candidates = [
        Path.cwd() / ".env",
        Path(__file__).resolve().parent / ".env",
        Path(__file__).resolve().parent.parent / ".env",
    ]
    for env_path in candidates:
        if not env_path.exists():
            continue
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)
        break


load_project_env()


MAX_SEQUENCE_LENGTH = int(os.getenv("SNP_MAX_SEQUENCE_LENGTH", "5000"))
MAX_SENSITIVITY_RUNS = int(os.getenv("SNP_MAX_SENSITIVITY_RUNS", "150"))
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest")
AI_TIMEOUT_SECONDS = float(os.getenv("SNP_AI_TIMEOUT_SECONDS", "20"))
NCBI_API_KEY = os.getenv("NCBI_API_KEY", "")
NCBI_EMAIL = os.getenv("NCBI_EMAIL", "")
CLINVAR_TIMEOUT_SECONDS = float(os.getenv("SNP_CLINVAR_TIMEOUT_SECONDS", "8"))
CORS_ORIGINS = [
    item.strip()
    for item in os.getenv(
        "SNP_CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if item.strip()
]

app = FastAPI(title="SNP Detection API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


class DatasetType(str, Enum):
    synthetic = "synthetic"
    hbb = "hbb"
    custom = "custom"


class FrameMode(str, Enum):
    manual = "manual"
    automatic = "automatic"


class CodonTableType(str, Enum):
    standard = "standard"
    vertebrate_mitochondrial = "vertebrate_mitochondrial"


class ClinVarSource(str, Enum):
    simulated = "simulated"
    real = "real"
    both = "both"


class GeneAnnotationRequest(BaseModel):
    gene_name: Optional[str] = None
    strand: Literal["+", "-"] = "+"
    total_length: Optional[int] = None
    exons: list[tuple[int, int]]
    cds_start: int
    cds_end: int


class RunPipelineRequest(BaseModel):
    dataset: DatasetType = DatasetType.synthetic
    ref_seq: Optional[str] = None
    sample_seq: Optional[str] = None
    seq_length: int = Field(300, ge=3, le=MAX_SEQUENCE_LENGTH)
    n_snps: int = Field(12, ge=0, le=MAX_SEQUENCE_LENGTH)
    gc_content: float = Field(0.5, ge=0.0, le=1.0)
    seed: int = 42
    frame: int = Field(0, ge=0, le=2)
    frame_mode: FrameMode = FrameMode.manual
    codon_table: CodonTableType = CodonTableType.standard
    gene_name: Optional[str] = None
    annotation: Optional[GeneAnnotationRequest] = None
    clinvar_source: ClinVarSource = ClinVarSource.simulated


class SensitivityRequest(BaseModel):
    ref_length: int = Field(600, ge=100, le=MAX_SEQUENCE_LENGTH)
    max_snps: int = Field(120, ge=5, le=MAX_SEQUENCE_LENGTH)
    n_points: int = Field(6, ge=3, le=10)
    n_trials: int = Field(5, ge=2, le=15)


class AIGuideRequest(BaseModel):
    result: dict[str, Any]


class ClinicalReportRequest(BaseModel):
    result: Optional[dict[str, Any]] = None
    analysis: Optional[RunPipelineRequest] = None


class AIGuideResponse(BaseModel):
    headline: str
    severity: Literal["ok", "info", "warning", "critical"]
    summary: str
    key_findings: list[str]
    next_steps: list[str]
    limitations: list[str]
    disclaimer: str


def api_error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code, detail={"code": code, "message": message})


_REAL_CLINVAR_CACHE: dict[str, Optional[ClinVarEntry]] = {}


def eutils_json(endpoint: str, params: dict[str, str]) -> dict[str, Any]:
    query = {
        "retmode": "json",
        "tool": "snp-detection-demo",
        **params,
    }
    if NCBI_API_KEY:
        query["api_key"] = NCBI_API_KEY
    if NCBI_EMAIL:
        query["email"] = NCBI_EMAIL
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/{endpoint}.fcgi?{parse.urlencode(query)}"
    req = request.Request(url, headers={"User-Agent": "snp-detection-demo/1.0"})
    with request.urlopen(req, timeout=CLINVAR_TIMEOUT_SECONDS) as resp:
        return json.loads(resp.read().decode("utf-8"))


def protein_hgvs_from_impact(impact: Any) -> str:
    if not impact.ref_aa or not impact.alt_aa or impact.codon_index < 0:
        return ""
    ref = "Ter" if impact.ref_aa == "*" else AA_NAMES.get(impact.ref_aa, impact.ref_aa)
    alt = "Ter" if impact.alt_aa == "*" else AA_NAMES.get(impact.alt_aa, impact.alt_aa)
    return f"p.{ref}{impact.codon_index + 1}{alt}"


def clinvar_search_terms(impact: Any, gene_name: str) -> list[str]:
    simulated = lookup_clinvar(impact, gene_name)
    protein_hgvs = protein_hgvs_from_impact(impact)
    terms: list[str] = []
    if simulated:
        if simulated.variant_id.startswith("CV"):
            terms.append(f"VCV{simulated.variant_id.removeprefix('CV')}")
        terms.append(f'{gene_name}[gene] AND "{simulated.hgvs_c}" AND "{simulated.hgvs_p}"')
        terms.append(f'{gene_name}[gene] AND "{simulated.hgvs_c}"')
    if gene_name.upper() == "HBB" and impact.ref_codon == "GAG" and impact.alt_codon == "GTG":
        terms.append("rs334")
    if protein_hgvs:
        terms.append(f'{gene_name}[gene] AND "{protein_hgvs}"')
    seen: set[str] = set()
    return [term for term in terms if not (term in seen or seen.add(term))]


def first_float(items: list[dict[str, Any]], key: str) -> float:
    for item in items:
        try:
            return float(item.get(key) or 0.0)
        except (TypeError, ValueError):
            continue
    return 0.0


def clinvar_summary_to_entry(uid: str, summary: dict[str, Any], impact: Any, gene_name: str) -> ClinVarEntry:
    germline = summary.get("germline_classification") or {}
    traits = germline.get("trait_set") or []
    condition_names = list(dict.fromkeys(
        trait.get("trait_name", "")
        for trait in traits
        if trait.get("trait_name")
    ))
    if len(condition_names) > 5:
        condition_names = condition_names[:5] + [f"{len(condition_names) - 5} more"]
    condition = "; ".join(condition_names) or "not provided"

    variation_set = summary.get("variation_set") or []
    protein_hgvs = protein_hgvs_from_impact(impact)
    selected_variation = variation_set[0] if variation_set else {}
    for variation in variation_set:
        name = str(variation.get("variation_name") or "")
        if impact.ref_codon and impact.alt_codon and protein_hgvs and protein_hgvs in name:
            selected_variation = variation
            break

    hgvs_c = str(selected_variation.get("cdna_change") or "")
    variation_name = str(selected_variation.get("variation_name") or summary.get("title") or "")
    allele_frequency = first_float(selected_variation.get("allele_freq_set") or [], "value")
    supporting = summary.get("supporting_submissions") or {}
    evidence_count = len(supporting.get("scv") or [])

    return ClinVarEntry(
        variant_id=str(summary.get("accession_version") or summary.get("accession") or f"ClinVar:{uid}"),
        gene=gene_name,
        hgvs_c=hgvs_c,
        hgvs_p=protein_hgvs or str(summary.get("protein_change") or ""),
        clinical_significance=str(germline.get("description") or "Uncertain significance"),
        condition=condition,
        review_status=str(germline.get("review_status") or "not provided"),
        allele_frequency=allele_frequency,
        evidence_count=evidence_count,
        source="real",
        url=f"https://www.ncbi.nlm.nih.gov/clinvar/variation/{uid}/",
    )


def real_clinvar_lookup(impact: Any, gene_name: str) -> Optional[ClinVarEntry]:
    terms = clinvar_search_terms(impact, gene_name)
    if not terms:
        return None

    protein_hgvs = protein_hgvs_from_impact(impact)
    cache_key = "|".join([gene_name, str(impact.variant.pos_ref), impact.ref_codon, impact.alt_codon, *terms])
    if cache_key in _REAL_CLINVAR_CACHE:
        return _REAL_CLINVAR_CACHE[cache_key]

    for term in terms:
        try:
            search = eutils_json("esearch", {"db": "clinvar", "retmax": "10", "term": term})
            ids = (search.get("esearchresult") or {}).get("idlist") or []
            if not ids:
                continue
            summary = eutils_json("esummary", {"db": "clinvar", "id": ",".join(ids[:10])})
            result = summary.get("result") or {}
            for uid in result.get("uids") or []:
                item = result.get(uid) or {}
                item_text = json.dumps(item)
                if protein_hgvs and protein_hgvs not in item_text:
                    continue
                entry = clinvar_summary_to_entry(uid, item, impact, gene_name)
                _REAL_CLINVAR_CACHE[cache_key] = entry
                return entry
        except (error.URLError, TimeoutError, json.JSONDecodeError, ValueError):
            continue

    _REAL_CLINVAR_CACHE[cache_key] = None
    return None


def real_clinvar_overrides(impacts: list[Any], gene_name: str, enabled: bool) -> tuple[dict[int, ClinVarEntry], dict[str, Any]]:
    status = {
        "requested": enabled,
        "source": "real" if enabled else "simulated",
        "queried": 0,
        "matches": 0,
        "message": "Simulated educational ClinVar database only.",
    }
    if not enabled:
        return {}, status

    started = time.perf_counter()
    overrides: dict[int, ClinVarEntry] = {}
    for impact in impacts:
        if impact.impact in ("UTR_OR_OUTOFFRAME", "INCOMPLETE_CODON", "FRAMESHIFT", "INFRAME_INDEL"):
            continue
        status["queried"] += 1
        entry = real_clinvar_lookup(impact, gene_name)
        if entry:
            overrides[id(impact.variant)] = entry

    status["matches"] = len(overrides)
    status["elapsed_ms"] = round((time.perf_counter() - started) * 1000)
    status["message"] = (
        "Real ClinVar queried through NCBI E-utilities; simulated entries remain fallback."
    )
    return overrides, status


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "detail": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "errors": exc.errors(),
            }
        },
    )


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "max_sequence_length": MAX_SEQUENCE_LENGTH,
        "max_sensitivity_runs": MAX_SENSITIVITY_RUNS,
        "ai_enabled": bool(GEMINI_API_KEY),
        "real_clinvar_enabled": True,
        "real_clinvar_api_key_configured": bool(NCBI_API_KEY),
    }


@app.get("/api/presets")
def get_presets():
    return {
        "hbb_wildtype": HBB_WILDTYPE,
        "hbb_sickle": HBB_SICKLE,
    }


@app.post("/api/run")
def run_pipeline(req: RunPipelineRequest):
    return run_pipeline_result(req)


def build_annotation(
    annotation_req: Optional[GeneAnnotationRequest],
    gene_name: str,
    ref_length: int,
) -> Optional[GeneAnnotation]:
    if annotation_req is None:
        return None

    total_length = annotation_req.total_length or ref_length
    if total_length != ref_length:
        raise api_error(400, "INVALID_ANNOTATION", "annotation.total_length must match reference length")
    if annotation_req.cds_start < 0 or annotation_req.cds_end > ref_length or annotation_req.cds_start > annotation_req.cds_end:
        raise api_error(400, "INVALID_ANNOTATION", "annotation CDS bounds must be within the reference")
    if not annotation_req.exons:
        raise api_error(400, "INVALID_ANNOTATION", "annotation.exons must not be empty")

    exons = []
    for start, end in annotation_req.exons:
        if start < 0 or end > ref_length or start >= end:
            raise api_error(400, "INVALID_ANNOTATION", "annotation exon intervals must be valid 0-based half-open ranges")
        exons.append((start, end))

    exons = sorted(exons)
    for (_, prev_end), (next_start, _) in zip(exons, exons[1:]):
        if next_start < prev_end:
            raise api_error(400, "INVALID_ANNOTATION", "annotation exon intervals must not overlap")

    return GeneAnnotation(
        gene_name=annotation_req.gene_name or gene_name,
        strand=annotation_req.strand,
        total_length=total_length,
        exons=exons,
        cds_start=annotation_req.cds_start,
        cds_end=annotation_req.cds_end,
    )


def run_pipeline_result(req: RunPipelineRequest):
    ground_truth = None
    gene_name = (req.gene_name or "").strip()

    if req.dataset == DatasetType.hbb:
        ref_seq = HBB_WILDTYPE
        sample_seq = HBB_SICKLE
        if not gene_name:
            gene_name = "HBB"

    elif req.dataset == DatasetType.synthetic:
        if not gene_name:
            gene_name = "SYNTHETIC"
        if req.n_snps > req.seq_length:
            raise api_error(400, "INVALID_SNP_COUNT", "n_snps must be less than or equal to seq_length")
        ref_seq = generate_random_dna(req.seq_length, req.gc_content, seed=req.seed)
        sample_seq, ground_truth = introduce_point_mutations(ref_seq, req.n_snps, seed=req.seed + 1)

    else:
        if not gene_name:
            gene_name = "UNKNOWN"
        if not req.ref_seq or not req.sample_seq:
            raise api_error(400, "MISSING_CUSTOM_SEQUENCE", "ref_seq and sample_seq required for custom dataset")
        ok_ref, ref_seq = validate_dna(req.ref_seq)
        ok_sample, sample_seq = validate_dna(req.sample_seq)
        if not ok_ref:
            raise api_error(400, "INVALID_REFERENCE_SEQUENCE", f"Referensi tidak valid: {ref_seq}")
        if not ok_sample:
            raise api_error(400, "INVALID_SAMPLE_SEQUENCE", f"Sampel tidak valid: {sample_seq}")
        if len(ref_seq) > MAX_SEQUENCE_LENGTH or len(sample_seq) > MAX_SEQUENCE_LENGTH:
            raise api_error(
                400,
                "SEQUENCE_TOO_LONG",
                f"Custom sequences must be at most {MAX_SEQUENCE_LENGTH} bp",
            )

    codon_table = get_codon_table(req.codon_table.value)
    orfs = find_orfs(ref_seq, codon_table=codon_table)
    selected_orf = orfs[0] if req.frame_mode == FrameMode.automatic and orfs else None
    selected_frame = selected_orf.frame if selected_orf else req.frame
    selected_strand = selected_orf.strand if selected_orf else "+"

    analysis_ref_seq = reverse_complement(ref_seq) if selected_strand == "-" else ref_seq
    analysis_sample_seq = reverse_complement(sample_seq) if selected_strand == "-" else sample_seq

    ref_aln, smp_aln, score = align_sequences(analysis_ref_seq, analysis_sample_seq)
    variants = detect_variants(ref_aln, smp_aln)
    impacts = classify_all(variants, analysis_ref_seq, frame=selected_frame, codon_table=codon_table)
    display_impacts = [
        map_impact_to_original_coordinates(impact, len(ref_seq), selected_strand)
        for impact in impacts
    ]
    annotation = build_annotation(req.annotation, gene_name, len(ref_seq))
    clinvar_overrides, clinvar_lookup_status = real_clinvar_overrides(
        display_impacts,
        gene_name,
        req.clinvar_source != ClinVarSource.simulated,
    )
    assessments = assess_impacts(
        display_impacts,
        gene_name,
        len(ref_seq),
        selected_strand,
        annotation,
        clinvar_overrides=clinvar_overrides,
    )
    rows = impacts_to_dicts(display_impacts, assessments)

    snps_only = [impact.variant for impact in display_impacts if impact.variant.vtype == "SNP"]
    ev = evaluate(snps_only, ground_truth) if ground_truth else None

    aln_columns = []
    for r, s in zip(ref_aln, smp_aln):
        if r == s and r != "-":
            kind = "match"
        elif r == "-" or s == "-":
            kind = "gap"
        else:
            kind = "mismatch"
        aln_columns.append({"ref": r, "alt": s, "kind": kind})

    return {
        "ref_seq": ref_seq,
        "sample_seq": sample_seq,
        "ref_aligned": ref_aln,
        "sample_aligned": smp_aln,
        "alignment_score": score,
        "alignment_cols": aln_columns,
        "variants": rows,
        "ref_protein": translate_dna(analysis_ref_seq, selected_frame, codon_table),
        "sample_protein": translate_dna(analysis_sample_seq, selected_frame, codon_table),
        "evaluation": ev,
        "gene_name": gene_name,
        "frame_mode": req.frame_mode.value,
        "codon_table": req.codon_table.value,
        "clinvar_source": req.clinvar_source.value,
        "clinvar_lookup": clinvar_lookup_status,
        "selected_frame": selected_frame,
        "selected_strand": selected_strand,
        "orf_detected": selected_orf is not None,
        "selected_orf": orf_to_dict(selected_orf),
        "orfs": [orf_to_dict(orf) for orf in orfs[:10]],
        "annotation": {
            "gene_name": (annotation.gene_name if annotation else gene_name),
            "strand": (annotation.strand if annotation else selected_strand),
            "total_length": (annotation.total_length if annotation else len(ref_seq)),
            "exons": (annotation.exons if annotation else [(0, len(ref_seq))]),
            "cds_start": (annotation.cds_start if annotation else 0),
            "cds_end": (annotation.cds_end if annotation else len(ref_seq)),
        },
        "clinical_report": generate_clinical_report(assessments, gene_name, len(ref_seq)),
        "stats": {
            "total": len(display_impacts),
            "snps": len([impact for impact in display_impacts if impact.variant.vtype == "SNP"]),
            "ins": len([impact for impact in display_impacts if impact.variant.vtype == "INS"]),
            "dels": len([impact for impact in display_impacts if impact.variant.vtype == "DEL"]),
            "ref_len": len(ref_seq),
        },
    }


@app.post("/api/clinical-report")
def clinical_report(req: ClinicalReportRequest):
    if req.result is not None:
        report = req.result.get("clinical_report")
        if isinstance(report, str):
            return {"report": report}
        variants = req.result.get("variants") or []
        gene_name = str(req.result.get("gene_name") or "UNKNOWN")
        ref_len = (req.result.get("stats") or {}).get("ref_len") or len(str(req.result.get("ref_seq") or ""))
        if not variants:
            return {
                "report": generate_clinical_report([], gene_name, int(ref_len or 0)),
            }
        raise api_error(400, "REPORT_NOT_AVAILABLE", "result does not include clinical_report")
    if req.analysis is not None:
        result = run_pipeline_result(req.analysis)
        return {"report": result["clinical_report"]}
    raise api_error(400, "MISSING_REPORT_INPUT", "Provide either result or analysis")


def compact_result_for_ai(result: dict[str, Any]) -> dict[str, Any]:
    stats = result.get("stats") or {}
    variants = result.get("variants") or []
    if not isinstance(variants, list):
        variants = []

    impact_counts: dict[str, int] = {}
    for row in variants:
        if isinstance(row, dict):
            impact = str(row.get("impact", "UNKNOWN"))
            impact_counts[impact] = impact_counts.get(impact, 0) + 1

    ref_protein = str(result.get("ref_protein") or "")
    sample_protein = str(result.get("sample_protein") or "")
    protein_changes = sum(
        (ref_protein[i] if i < len(ref_protein) else "") != (sample_protein[i] if i < len(sample_protein) else "")
        for i in range(max(len(ref_protein), len(sample_protein)))
    )

    return {
        "stats": {
            "total": stats.get("total"),
            "snps": stats.get("snps"),
            "insertions": stats.get("ins"),
            "deletions": stats.get("dels"),
            "reference_length_bp": stats.get("ref_len"),
        },
        "alignment_score": result.get("alignment_score"),
        "protein": {
            "reference_length_aa": len(ref_protein),
            "sample_length_aa": len(sample_protein),
            "changed_residues": protein_changes,
        },
        "evaluation": result.get("evaluation"),
        "impact_counts": impact_counts,
        "variants_preview": variants[:25],
    }


def extract_gemini_text(payload: dict[str, Any]) -> str:
    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise ValueError("Gemini response did not include candidates")
    parts = candidates[0].get("content", {}).get("parts", [])
    texts = [part.get("text", "") for part in parts if isinstance(part, dict)]
    text = "".join(texts).strip()
    if not text:
        raise ValueError("Gemini response did not include text")
    return text


def parse_ai_guide(text: str) -> AIGuideResponse:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()
    data = json.loads(cleaned)
    return AIGuideResponse.model_validate(data)


def call_gemini_guide(summary: dict[str, Any]) -> AIGuideResponse:
    schema_hint = {
        "headline": "string",
        "severity": "ok | info | warning | critical",
        "summary": "string",
        "key_findings": ["string"],
        "next_steps": ["string"],
        "limitations": ["string"],
        "disclaimer": "string",
    }
    prompt = (
        "Anda adalah asisten bioinformatika untuk pengguna umum. "
        "Jelaskan hasil pipeline SNP dalam Bahasa Indonesia yang jelas dan tidak menakut-nakuti. "
        "Gunakan hanya fakta dari JSON hasil pipeline; jangan mengarang varian, diagnosis, atau klaim klinis. "
        "Berikan saran tindak lanjut yang aman seperti validasi data, cek frame baca, dan konsultasi ahli bila relevan. "
        "Balas hanya sebagai JSON valid sesuai skema ini:\n"
        f"{json.dumps(schema_hint, ensure_ascii=False)}\n\n"
        "Ringkasan hasil pipeline:\n"
        f"{json.dumps(summary, ensure_ascii=False)}"
    )
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 900,
        },
    }
    model = parse.quote(GEMINI_MODEL, safe="")
    req = request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": GEMINI_API_KEY,
        },
        method="POST",
    )
    with request.urlopen(req, timeout=AI_TIMEOUT_SECONDS) as res:
        payload = json.loads(res.read().decode("utf-8"))
    return parse_ai_guide(extract_gemini_text(payload))


@app.post("/api/ai/guide", response_model=AIGuideResponse)
def ai_guide(req: AIGuideRequest):
    if not GEMINI_API_KEY:
        raise api_error(503, "AI_NOT_CONFIGURED", "Gemini API key is not configured")
    try:
        return call_gemini_guide(compact_result_for_ai(req.result))
    except error.HTTPError as exc:
        message = exc.read().decode("utf-8", errors="replace")[:300]
        raise api_error(502, "AI_PROVIDER_ERROR", f"Gemini request failed: {message}") from exc
    except error.URLError as exc:
        raise api_error(502, "AI_NETWORK_ERROR", f"Gemini is unreachable: {exc.reason}") from exc
    except TimeoutError as exc:
        raise api_error(504, "AI_TIMEOUT", "Gemini request timed out") from exc
    except (ValueError, json.JSONDecodeError) as exc:
        raise api_error(502, "AI_RESPONSE_INVALID", "Gemini returned an invalid guide response") from exc


@app.post("/api/sensitivity")
def run_sensitivity(req: SensitivityRequest):
    if req.max_snps > req.ref_length:
        raise api_error(400, "INVALID_SNP_COUNT", "max_snps must be less than or equal to ref_length")
    if req.n_points * req.n_trials > MAX_SENSITIVITY_RUNS:
        raise api_error(
            400,
            "WORKLOAD_TOO_LARGE",
            f"n_points * n_trials must be <= {MAX_SENSITIVITY_RUNS}",
        )

    snp_values = np.linspace(5, req.max_snps, req.n_points, dtype=int).tolist()
    results = []

    for n_snp in snp_values:
        precisions, recalls, f1s = [], [], []
        for trial in range(req.n_trials):
            seed_base = 1000 + trial * 37
            ref = generate_random_dna(req.ref_length, 0.5, seed=seed_base)
            smp, gt = introduce_point_mutations(ref, int(n_snp), seed=seed_base + 5000)
            ra, sa, _ = align_sequences(ref, smp)
            vs = detect_variants(ra, sa)
            m = evaluate(vs, gt)
            precisions.append(m["precision"])
            recalls.append(m["recall"])
            f1s.append(m["f1"])

        density = round(100 * n_snp / req.ref_length, 3)
        results.append(
            {
                "n_snp": int(n_snp),
                "density": density,
                "precision": {"mean": float(np.mean(precisions)), "std": float(np.std(precisions))},
                "recall": {"mean": float(np.mean(recalls)), "std": float(np.std(recalls))},
                "f1": {"mean": float(np.mean(f1s)), "std": float(np.std(f1s))},
            }
        )

    return {"ref_length": req.ref_length, "n_trials": req.n_trials, "results": results}
