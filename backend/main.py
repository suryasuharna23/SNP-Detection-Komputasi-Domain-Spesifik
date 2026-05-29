import os
from enum import Enum
from typing import Optional

import numpy as np
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from pipeline import (
    HBB_SICKLE,
    HBB_WILDTYPE,
    align_sequences,
    classify_all,
    detect_variants,
    evaluate,
    generate_random_dna,
    impacts_to_dicts,
    introduce_point_mutations,
    translate_dna,
    validate_dna,
)


MAX_SEQUENCE_LENGTH = int(os.getenv("SNP_MAX_SEQUENCE_LENGTH", "5000"))
MAX_SENSITIVITY_RUNS = int(os.getenv("SNP_MAX_SENSITIVITY_RUNS", "150"))
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


class RunPipelineRequest(BaseModel):
    dataset: DatasetType = DatasetType.synthetic
    ref_seq: Optional[str] = None
    sample_seq: Optional[str] = None
    seq_length: int = Field(300, ge=3, le=MAX_SEQUENCE_LENGTH)
    n_snps: int = Field(12, ge=0, le=MAX_SEQUENCE_LENGTH)
    gc_content: float = Field(0.5, ge=0.0, le=1.0)
    seed: int = 42
    frame: int = Field(0, ge=0, le=2)


class SensitivityRequest(BaseModel):
    ref_length: int = Field(600, ge=100, le=MAX_SEQUENCE_LENGTH)
    max_snps: int = Field(120, ge=5, le=MAX_SEQUENCE_LENGTH)
    n_points: int = Field(6, ge=3, le=10)
    n_trials: int = Field(5, ge=2, le=15)


def api_error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code, detail={"code": code, "message": message})


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
    }


@app.get("/api/presets")
def get_presets():
    return {
        "hbb_wildtype": HBB_WILDTYPE,
        "hbb_sickle": HBB_SICKLE,
    }


@app.post("/api/run")
def run_pipeline(req: RunPipelineRequest):
    ground_truth = None

    if req.dataset == DatasetType.hbb:
        ref_seq = HBB_WILDTYPE
        sample_seq = HBB_SICKLE

    elif req.dataset == DatasetType.synthetic:
        if req.n_snps > req.seq_length:
            raise api_error(400, "INVALID_SNP_COUNT", "n_snps must be less than or equal to seq_length")
        ref_seq = generate_random_dna(req.seq_length, req.gc_content, seed=req.seed)
        sample_seq, ground_truth = introduce_point_mutations(ref_seq, req.n_snps, seed=req.seed + 1)

    else:
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

    ref_aln, smp_aln, score = align_sequences(ref_seq, sample_seq)
    variants = detect_variants(ref_aln, smp_aln)
    impacts = classify_all(variants, ref_seq, frame=req.frame)
    rows = impacts_to_dicts(impacts)

    snps_only = [v for v in variants if v.vtype == "SNP"]
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
        "ref_protein": translate_dna(ref_seq, req.frame),
        "sample_protein": translate_dna(sample_seq, req.frame),
        "evaluation": ev,
        "stats": {
            "total": len(variants),
            "snps": len([v for v in variants if v.vtype == "SNP"]),
            "ins": len([v for v in variants if v.vtype == "INS"]),
            "dels": len([v for v in variants if v.vtype == "DEL"]),
            "ref_len": len(ref_seq),
        },
    }


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
