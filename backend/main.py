from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List
import numpy as np

from pipeline import (
    generate_random_dna, introduce_point_mutations, validate_dna,
    align_sequences, detect_variants, classify_all, evaluate,
    impacts_to_dicts, translate_dna,
    HBB_WILDTYPE, HBB_SICKLE,
)

app = FastAPI(title="SNP Detection API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response models ──────────────────────────────────────────────────

class RunPipelineRequest(BaseModel):
    dataset:    str = "synthetic"      # synthetic | hbb | custom
    ref_seq:    Optional[str] = None
    sample_seq: Optional[str] = None
    seq_length: int = 300
    n_snps:     int = 12
    gc_content: float = 0.5
    seed:       int = 42
    frame:      int = 0


class SensitivityRequest(BaseModel):
    ref_length: int   = Field(600, ge=100, le=2000)
    max_snps:   int   = Field(120, ge=5, le=500)
    n_points:   int   = Field(6, ge=3, le=10)
    n_trials:   int   = Field(5, ge=2, le=15)


# ── Endpoints ──────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/presets")
def get_presets():
    return {
        "hbb_wildtype": HBB_WILDTYPE,
        "hbb_sickle":   HBB_SICKLE,
    }


@app.post("/api/run")
def run_pipeline(req: RunPipelineRequest):
    ground_truth = None

    if req.dataset == "hbb":
        ref_seq    = HBB_WILDTYPE
        sample_seq = HBB_SICKLE

    elif req.dataset == "synthetic":
        ref_seq = generate_random_dna(req.seq_length, req.gc_content, seed=req.seed)
        sample_seq, ground_truth = introduce_point_mutations(
            ref_seq, req.n_snps, seed=req.seed + 1
        )

    else:  # custom
        if not req.ref_seq or not req.sample_seq:
            raise HTTPException(400, "ref_seq and sample_seq required for custom dataset")
        ok1, ref_seq = validate_dna(req.ref_seq)
        ok2, sample_seq = validate_dna(req.sample_seq)
        if not ok1:
            raise HTTPException(400, f"Referensi tidak valid: {ref_seq}")
        if not ok2:
            raise HTTPException(400, f"Sampel tidak valid: {sample_seq}")

    ref_aln, smp_aln, score = align_sequences(ref_seq, sample_seq)
    variants = detect_variants(ref_aln, smp_aln)
    impacts  = classify_all(variants, ref_seq, frame=req.frame)
    rows     = impacts_to_dicts(impacts)

    snps_only = [v for v in variants if v.vtype == "SNP"]
    ev = evaluate(snps_only, ground_truth) if ground_truth else None

    # Build alignment columns for frontend rendering
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
        "ref_seq":         ref_seq,
        "sample_seq":      sample_seq,
        "ref_aligned":     ref_aln,
        "sample_aligned":  smp_aln,
        "alignment_score": score,
        "alignment_cols":  aln_columns,
        "variants":        rows,
        "ref_protein":     translate_dna(ref_seq, req.frame),
        "sample_protein":  translate_dna(sample_seq, req.frame),
        "evaluation":      ev,
        "stats": {
            "total":    len(variants),
            "snps":     len([v for v in variants if v.vtype == "SNP"]),
            "ins":      len([v for v in variants if v.vtype == "INS"]),
            "dels":     len([v for v in variants if v.vtype == "DEL"]),
            "ref_len":  len(ref_seq),
        },
    }


@app.post("/api/sensitivity")
def run_sensitivity(req: SensitivityRequest):
    snp_values = np.linspace(5, req.max_snps, req.n_points, dtype=int).tolist()
    results = []

    for n_snp in snp_values:
        precisions, recalls, f1s = [], [], []
        for trial in range(req.n_trials):
            seed_base = 1000 + trial * 37
            ref  = generate_random_dna(req.ref_length, 0.5, seed=seed_base)
            smp, gt = introduce_point_mutations(ref, int(n_snp), seed=seed_base + 5000)
            ra, sa, _ = align_sequences(ref, smp)
            vs = detect_variants(ra, sa)
            m  = evaluate(vs, gt)
            precisions.append(m["precision"])
            recalls.append(m["recall"])
            f1s.append(m["f1"])

        density = round(100 * n_snp / req.ref_length, 3)
        results.append({
            "n_snp":     int(n_snp),
            "density":   density,
            "precision": {"mean": float(np.mean(precisions)), "std": float(np.std(precisions))},
            "recall":    {"mean": float(np.mean(recalls)),    "std": float(np.std(recalls))},
            "f1":        {"mean": float(np.mean(f1s)),        "std": float(np.std(f1s))},
        })

    return {"ref_length": req.ref_length, "n_trials": req.n_trials, "results": results}
