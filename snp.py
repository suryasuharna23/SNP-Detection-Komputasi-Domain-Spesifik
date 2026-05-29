#!/usr/bin/env python3
"""Cross-platform CLI for the SNP Detection project."""

from __future__ import annotations

import argparse
import csv
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
from datetime import datetime
from typing import Any
from urllib import error, request


ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
REPORTS = ROOT / "reports"


def load_project_env() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


load_project_env()

DEFAULT_BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8000"))
DEFAULT_DEV_FRONTEND_PORT = int(os.getenv("FRONTEND_PORT", "5173"))
DEFAULT_PROD_FRONTEND_PORT = int(os.getenv("FRONTEND_PORT", "8080"))


def print_step(message: str) -> None:
    print(f"[snp] {message}")


def command_name(name: str) -> str:
    if os.name == "nt" and name == "npm":
        return "npm.cmd"
    return name


def find_command(name: str) -> str | None:
    return shutil.which(command_name(name)) or shutil.which(name)


def run_checked(args: list[str], cwd: Path, env: dict[str, str] | None = None) -> None:
    print_step(f"running: {' '.join(args)}")
    subprocess.run(args, cwd=cwd, check=True, env=env)


def port_open(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.25)
        return sock.connect_ex((host, port)) == 0


def require_free_port(port: int, label: str) -> None:
    if port_open(port):
        raise SystemExit(f"{label} port {port} is already in use.")


def http_get_json(url: str, timeout: float = 5.0) -> Any:
    with request.urlopen(url, timeout=timeout) as res:
        return json.loads(res.read().decode("utf-8"))


def http_post_json(url: str, payload: dict[str, Any], timeout: float = 30.0) -> Any:
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=timeout) as res:
        return json.loads(res.read().decode("utf-8"))


def wait_for_url(url: str, timeout: float = 30.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with request.urlopen(url, timeout=2.0) as res:
                if 200 <= res.status < 500:
                    return True
        except Exception:
            time.sleep(0.4)
    return False


def ensure_pip() -> bool:
    if subprocess.run(
        [sys.executable, "-m", "pip", "--version"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode == 0:
        return True

    print_step("pip is not available for this Python; trying ensurepip")
    if subprocess.run([sys.executable, "-m", "ensurepip", "--upgrade"]).returncode == 0:
        return subprocess.run(
            [sys.executable, "-m", "pip", "--version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode == 0
    return False


def stream_process(prefix: str, proc: subprocess.Popen[str]) -> threading.Thread:
    def reader() -> None:
        assert proc.stdout is not None
        for line in proc.stdout:
            print(f"[{prefix}] {line.rstrip()}")

    thread = threading.Thread(target=reader, daemon=True)
    thread.start()
    return thread


def terminate_process(proc: subprocess.Popen[str]) -> None:
    if proc.poll() is not None:
        return
    try:
        if os.name == "nt":
            proc.terminate()
        else:
            proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=8)
    except subprocess.TimeoutExpired:
        proc.kill()


def cmd_app(args: argparse.Namespace) -> int:
    npm = find_command("npm")
    if not npm:
        print("npm was not found. Install Node.js, then run `python snp.py install`.")
        return 1
    require_free_port(args.backend_port, "backend")
    require_free_port(args.frontend_port, "frontend")

    backend_cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "main:app",
        "--reload",
        "--port",
        str(args.backend_port),
    ]
    frontend_cmd = [
        npm,
        "run",
        "dev",
        "--",
        "--host",
        "127.0.0.1",
        "--port",
        str(args.frontend_port),
    ]
    backend_env = os.environ.copy()
    backend_env["SNP_CORS_ORIGINS"] = (
        f"http://127.0.0.1:{args.frontend_port},"
        f"http://localhost:{args.frontend_port}"
    )
    frontend_env = os.environ.copy()
    frontend_env["VITE_API_BASE_URL"] = "/api"

    print_step(f"backend:  http://localhost:{args.backend_port}")
    print_step(f"frontend: http://localhost:{args.frontend_port}")
    print_step("press Ctrl+C to stop both servers")

    procs: list[subprocess.Popen[str]] = []
    try:
        backend_proc = subprocess.Popen(
            backend_cmd,
            cwd=BACKEND,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=backend_env,
        )
        procs.append(backend_proc)
        stream_process("backend", backend_proc)

        frontend_proc = subprocess.Popen(
            frontend_cmd,
            cwd=FRONTEND,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=frontend_env,
        )
        procs.append(frontend_proc)
        stream_process("frontend", frontend_proc)

        backend_ready = wait_for_url(f"http://127.0.0.1:{args.backend_port}/api/health", args.ready_timeout)
        frontend_ready = wait_for_url(f"http://127.0.0.1:{args.frontend_port}", args.ready_timeout)
        if not backend_ready or not frontend_ready:
            raise SystemExit("servers started but readiness checks did not pass before timeout")
        print_step(f"ready: http://localhost:{args.frontend_port}")
        print_step(f"api docs: http://localhost:{args.backend_port}/docs")

        while True:
            for proc in procs:
                code = proc.poll()
                if code is not None:
                    print_step(f"a server exited with code {code}; stopping remaining servers")
                    return code
            threading.Event().wait(0.5)
    except KeyboardInterrupt:
        print()
        print_step("stopping servers")
        return 0
    finally:
        for proc in reversed(procs):
            terminate_process(proc)


def cmd_install(_: argparse.Namespace) -> int:
    npm = find_command("npm")
    if not npm:
        print("npm was not found. Install Node.js before installing frontend dependencies.")
        return 1
    if not ensure_pip():
        print("pip is not available for this Python. Use a Python installation that includes pip.")
        return 1

    run_checked([sys.executable, "-m", "pip", "install", "-r", "backend/requirements.txt"], ROOT)
    run_checked([npm, "install"], FRONTEND)
    print_step("dependencies installed")
    return 0


def module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def cmd_check(_: argparse.Namespace) -> int:
    checks = [
        ("Python", sys.executable),
        ("npm", find_command("npm") or "missing"),
        ("Biopython", "available" if module_available("Bio") else "missing"),
        ("FastAPI", "available" if module_available("fastapi") else "missing"),
        ("Uvicorn", "available" if module_available("uvicorn") else "missing"),
        ("frontend node_modules", "available" if (FRONTEND / "node_modules").exists() else "missing"),
        ("latexmk", find_command("latexmk") or "optional missing"),
        ("xelatex", find_command("xelatex") or "optional missing"),
        ("pdflatex", find_command("pdflatex") or "optional missing"),
    ]
    for label, value in checks:
        print(f"{label:22} {value}")
    return 0


def cmd_smoke(args: argparse.Namespace) -> int:
    backend = args.backend_url.rstrip("/")
    print_step(f"checking backend at {backend}")
    health = http_get_json(f"{backend}/api/health")
    if health.get("status") != "ok":
        raise SystemExit(f"unexpected health response: {health}")

    hbb = http_post_json(f"{backend}/api/run", {"dataset": "hbb", "frame": 0})
    if hbb["stats"]["snps"] != 1 or hbb["variants"][0]["pos"] != 20:
        raise SystemExit("HBB smoke test failed: expected one SNP at position 20")
    print_step("HBB API smoke passed")

    identical = http_post_json(
        f"{backend}/api/run",
        {"dataset": "custom", "ref_seq": "ATGCGTTAA", "sample_seq": "ATGCGTTAA", "frame": 0},
    )
    if identical["stats"]["total"] != 0:
        raise SystemExit("custom identical smoke test failed: expected zero variants")
    print_step("custom API smoke passed")

    report_args = argparse.Namespace(
        dataset="hbb",
        seq_length=300,
        n_snps=12,
        gc_content=0.5,
        seed=42,
        frame=0,
        ref=None,
        sample=None,
        ref_file=None,
        sample_file=None,
        output_dir=args.output_dir,
        no_pdf=True,
        csv=False,
    )
    cmd_report(report_args)
    print_step("report smoke passed")

    if args.frontend_url:
        if not wait_for_url(args.frontend_url.rstrip("/"), timeout=5.0):
            raise SystemExit(f"frontend smoke failed: {args.frontend_url} is not reachable")
        print_step("frontend smoke passed")

    return 0


def cmd_ci(_: argparse.Namespace) -> int:
    npm = find_command("npm")
    if not npm:
        print("npm was not found. Install Node.js before running CI checks.")
        return 1

    run_checked([sys.executable, "-m", "py_compile", "snp.py", "backend/main.py", "backend/pipeline.py"], ROOT)

    for dataset in ("hbb", "synthetic", "custom"):
        report_args = argparse.Namespace(
            dataset=dataset,
            seq_length=90,
            n_snps=5,
            gc_content=0.5,
            seed=42,
            frame=0,
            ref="ATGCGTTAA" if dataset == "custom" else None,
            sample="ATGCGTTAA" if dataset == "custom" else None,
            ref_file=None,
            sample_file=None,
            output_dir=None,
            no_pdf=True,
            csv=False,
        )
        cmd_report(report_args)

    run_checked([npm, "run", "check"], FRONTEND)
    run_checked([npm, "run", "build"], FRONTEND)
    print_step("CI checks passed")
    return 0


def frontend_build_env(api_base_url: str | None = None) -> dict[str, str]:
    env = os.environ.copy()
    if api_base_url:
        env["VITE_API_BASE_URL"] = api_base_url
    elif "VITE_API_BASE_URL" not in env:
        env["VITE_API_BASE_URL"] = "http://127.0.0.1:8000/api"
    return env


def cmd_build(args: argparse.Namespace) -> int:
    npm = find_command("npm")
    if not npm:
        print("npm was not found. Install Node.js before building the frontend.")
        return 1
    env = frontend_build_env(args.api_base_url)
    run_checked([npm, "run", "check"], FRONTEND, env=env)
    run_checked([npm, "run", "build"], FRONTEND, env=env)
    index = FRONTEND / "dist" / "index.html"
    if not index.exists():
        raise SystemExit("frontend build did not create frontend/dist/index.html")
    print_step(f"frontend build ready at {index}")
    return 0


class SpaHandler(SimpleHTTPRequestHandler):
    def send_head(self):  # type: ignore[override]
        path = self.translate_path(self.path)
        if not Path(path).exists() and "." not in Path(self.path).name:
            self.path = "/index.html"
        return super().send_head()

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[frontend] {self.address_string()} - {fmt % args}")


def cmd_serve_frontend(args: argparse.Namespace) -> int:
    dist = FRONTEND / "dist"
    index = dist / "index.html"
    if not index.exists():
        raise SystemExit("frontend/dist/index.html is missing. Run `python snp.py build` first.")
    require_free_port(args.port, "frontend")
    handler = partial(SpaHandler, directory=str(dist))
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print_step(f"serving built frontend at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print()
    finally:
        server.server_close()
    return 0


def prod_env(frontend_port: int, backend_port: int, api_base_url: str | None) -> dict[str, str]:
    env = os.environ.copy()
    if "SNP_CORS_ORIGINS" not in env:
        env["SNP_CORS_ORIGINS"] = (
            f"http://127.0.0.1:{frontend_port},"
            f"http://localhost:{frontend_port}"
        )
    if "SNP_MAX_SEQUENCE_LENGTH" not in env:
        env["SNP_MAX_SEQUENCE_LENGTH"] = "5000"
    if "SNP_MAX_SENSITIVITY_RUNS" not in env:
        env["SNP_MAX_SENSITIVITY_RUNS"] = "150"
    env["VITE_API_BASE_URL"] = api_base_url or env.get(
        "VITE_API_BASE_URL",
        f"http://127.0.0.1:{backend_port}/api",
    )
    return env


def cmd_prod(args: argparse.Namespace) -> int:
    require_free_port(args.backend_port, "backend")
    require_free_port(args.frontend_port, "frontend")
    env = prod_env(args.frontend_port, args.backend_port, args.api_base_url)

    build_args = argparse.Namespace(api_base_url=env["VITE_API_BASE_URL"])
    cmd_build(build_args)

    backend_cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "main:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(args.backend_port),
    ]
    frontend_cmd = [
        sys.executable,
        str(ROOT / "snp.py"),
        "serve-frontend",
        "--host",
        "127.0.0.1",
        "--port",
        str(args.frontend_port),
    ]

    print_step(f"backend:  http://127.0.0.1:{args.backend_port}")
    print_step(f"frontend: http://127.0.0.1:{args.frontend_port}")
    print_step(f"api base baked into frontend: {env['VITE_API_BASE_URL']}")
    print_step("press Ctrl+C to stop both services")

    procs: list[subprocess.Popen[str]] = []
    try:
        backend_proc = subprocess.Popen(
            backend_cmd,
            cwd=BACKEND,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env,
        )
        procs.append(backend_proc)
        stream_process("backend", backend_proc)

        frontend_proc = subprocess.Popen(
            frontend_cmd,
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env,
        )
        procs.append(frontend_proc)
        stream_process("frontend", frontend_proc)

        backend_ready = wait_for_url(f"http://127.0.0.1:{args.backend_port}/api/health", args.ready_timeout)
        frontend_ready = wait_for_url(f"http://127.0.0.1:{args.frontend_port}", args.ready_timeout)
        if not backend_ready or not frontend_ready:
            raise SystemExit("services started but readiness checks did not pass before timeout")
        print_step(f"ready: http://127.0.0.1:{args.frontend_port}")

        while True:
            for proc in procs:
                code = proc.poll()
                if code is not None:
                    print_step(f"a service exited with code {code}; stopping remaining services")
                    return code
            threading.Event().wait(0.5)
    except KeyboardInterrupt:
        print()
        print_step("stopping services")
        return 0
    finally:
        for proc in reversed(procs):
            terminate_process(proc)


def import_pipeline() -> Any:
    sys.path.insert(0, str(BACKEND))
    try:
        import pipeline  # type: ignore
    except ModuleNotFoundError as exc:
        if exc.name == "Bio":
            raise SystemExit(
                "Biopython is not installed. Run `python snp.py install` first."
            ) from exc
        raise
    return pipeline


def read_sequence_arg(value: str | None, file_value: str | None, label: str) -> str | None:
    if value and file_value:
        raise SystemExit(f"Use either --{label} or --{label}-file, not both.")
    if file_value:
        return Path(file_value).read_text(encoding="utf-8")
    return value


def normalize_gc(value: float) -> float:
    return value / 100.0 if value > 1 else value


def run_pipeline_for_report(args: argparse.Namespace) -> dict[str, Any]:
    pipeline = import_pipeline()
    dataset = args.dataset
    ground_truth = None

    if dataset == "hbb":
        ref_seq = pipeline.HBB_WILDTYPE
        sample_seq = pipeline.HBB_SICKLE
    elif dataset == "synthetic":
        ref_seq = pipeline.generate_random_dna(args.seq_length, normalize_gc(args.gc_content), seed=args.seed)
        sample_seq, ground_truth = pipeline.introduce_point_mutations(ref_seq, args.n_snps, seed=args.seed + 1)
    else:
        ref_raw = read_sequence_arg(args.ref, args.ref_file, "ref")
        sample_raw = read_sequence_arg(args.sample, args.sample_file, "sample")
        if not ref_raw or not sample_raw:
            raise SystemExit("custom dataset requires --ref/--sample or --ref-file/--sample-file")
        ok_ref, ref_seq = pipeline.validate_dna(ref_raw)
        ok_sample, sample_seq = pipeline.validate_dna(sample_raw)
        if not ok_ref:
            raise SystemExit(f"Reference sequence is invalid: {ref_seq}")
        if not ok_sample:
            raise SystemExit(f"Sample sequence is invalid: {sample_seq}")

    ref_aln, sample_aln, score = pipeline.align_sequences(ref_seq, sample_seq)
    variants = pipeline.detect_variants(ref_aln, sample_aln)
    impacts = pipeline.classify_all(variants, ref_seq, frame=args.frame)
    rows = pipeline.impacts_to_dicts(impacts)
    snps_only = [v for v in variants if v.vtype == "SNP"]
    evaluation = pipeline.evaluate(snps_only, ground_truth) if ground_truth else None

    return {
        "dataset": dataset,
        "frame": args.frame,
        "ref_seq": ref_seq,
        "sample_seq": sample_seq,
        "ref_aligned": ref_aln,
        "sample_aligned": sample_aln,
        "alignment_score": score,
        "variants": rows,
        "ref_protein": pipeline.translate_dna(ref_seq, args.frame),
        "sample_protein": pipeline.translate_dna(sample_seq, args.frame),
        "evaluation": evaluation,
        "stats": {
            "total": len(variants),
            "snps": len([v for v in variants if v.vtype == "SNP"]),
            "ins": len([v for v in variants if v.vtype == "INS"]),
            "dels": len([v for v in variants if v.vtype == "DEL"]),
            "ref_len": len(ref_seq),
            "sample_len": len(sample_seq),
        },
    }


LATEX_REPLACEMENTS = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def latex_escape(value: Any) -> str:
    text = "" if value is None else str(value)
    return "".join(LATEX_REPLACEMENTS.get(ch, ch) for ch in text)


def code_text(value: Any) -> str:
    return r"\texttt{" + latex_escape(value) + "}"


def sequence_preview(seq: str, max_len: int = 180) -> str:
    if len(seq) <= max_len:
        return seq
    return seq[:max_len] + "..."


def impact_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        impact = str(row["impact"])
        counts[impact] = counts.get(impact, 0) + 1
    return counts


def protein_diff(ref: str, sample: str) -> int:
    n = max(len(ref), len(sample))
    return sum((ref[i] if i < len(ref) else "") != (sample[i] if i < len(sample) else "") for i in range(n))


def conclusion(result: dict[str, Any]) -> str:
    stats = result["stats"]
    rows = result["variants"]
    if stats["total"] == 0:
        return "No variants were detected. The reference and sample sequences are identical under the selected alignment parameters."

    counts = impact_counts(rows)
    high = sum(counts.get(k, 0) for k in ["NONSENSE", "FRAMESHIFT", "STOP_LOST", "START_LOST"])
    if high:
        return f"The pipeline detected {stats['total']} variants, including {high} high-impact variants that may alter protein function."
    if counts.get("MISSENSE", 0):
        return f"The pipeline detected {stats['total']} variants with {counts.get('MISSENSE', 0)} missense changes affecting the protein sequence."
    if counts.get("SILENT", 0) == stats["total"]:
        return "All detected variants are silent, so the translated protein sequence is unchanged."
    return f"The pipeline detected {stats['total']} variants with mixed predicted impacts."


def render_variant_rows(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return r"\multicolumn{9}{l}{No variants detected.}\\"

    out = []
    for row in rows:
        codon = "-"
        if row.get("ref_codon"):
            codon = f"{row.get('ref_codon')} -> {row.get('alt_codon')}"
        aa = "-"
        if row.get("ref_aa"):
            aa = f"{row.get('ref_aa')}({row.get('ref_aa_name')}) -> {row.get('alt_aa')}({row.get('alt_aa_name')})"
        out.append(
            " & ".join(
                [
                    latex_escape(row["pos"]),
                    latex_escape(row["variant_type"]),
                    code_text(row["ref"]),
                    code_text(row["alt"]),
                    latex_escape(row.get("codon_num") or "-"),
                    latex_escape(row.get("pos_in_codon") or "-"),
                    code_text(codon),
                    code_text(aa),
                    latex_escape(row["impact"]),
                ]
            )
            + r"\\"
        )
    return "\n".join(out)


def render_report(result: dict[str, Any]) -> str:
    stats = result["stats"]
    rows = result["variants"]
    counts = impact_counts(rows)
    count_lines = "\n".join(
        rf"\item {latex_escape(k)}: {v}" for k, v in sorted(counts.items())
    ) or r"\item No variant impacts."
    evaluation = result["evaluation"]
    if evaluation:
        eval_block = rf"""
\section*{{Synthetic Ground Truth Evaluation}}
\begin{{tabular}}{{rrrrrr}}
TP & FP & FN & Precision & Recall & F1\\
\hline
{evaluation["tp"]} & {evaluation["fp"]} & {evaluation["fn"]} & {evaluation["precision"]:.3f} & {evaluation["recall"]:.3f} & {evaluation["f1"]:.3f}\\
\end{{tabular}}
"""
    else:
        eval_block = ""

    protein_changes = protein_diff(result["ref_protein"], result["sample_protein"])
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return rf"""\documentclass[11pt,a4paper]{{article}}
\usepackage[margin=2cm]{{geometry}}
\usepackage{{longtable}}
\usepackage{{booktabs}}
\usepackage{{array}}
\usepackage{{hyperref}}
\usepackage{{xcolor}}
\usepackage{{courier}}
\setlength{{\parindent}}{{0pt}}
\setlength{{\parskip}}{{0.6em}}

\title{{SNP Detection Report}}
\author{{Generated by snp.py}}
\date{{{latex_escape(generated_at)}}}

\begin{{document}}
\maketitle

\section*{{Run Parameters}}
\begin{{tabular}}{{ll}}
Dataset & {latex_escape(result["dataset"])}\\
Reading frame & {latex_escape(result["frame"])}\\
Reference length & {stats["ref_len"]} bp\\
Sample length & {stats["sample_len"]} bp\\
Alignment score & {result["alignment_score"]:.2f}\\
\end{{tabular}}

\section*{{Summary}}
\begin{{tabular}}{{lr}}
Total variants & {stats["total"]}\\
SNPs & {stats["snps"]}\\
Insertions & {stats["ins"]}\\
Deletions & {stats["dels"]}\\
Protein residue changes & {protein_changes}\\
\end{{tabular}}

\section*{{Impact Distribution}}
\begin{{itemize}}
{count_lines}
\end{{itemize}}

{eval_block}

\section*{{Sequence Preview}}
\textbf{{Reference}}\\
{code_text(sequence_preview(result["ref_seq"]))}

\textbf{{Sample}}\\
{code_text(sequence_preview(result["sample_seq"]))}

\section*{{Protein Preview}}
\textbf{{Reference protein}}\\
{code_text(sequence_preview(result["ref_protein"], 220))}

\textbf{{Sample protein}}\\
{code_text(sequence_preview(result["sample_protein"], 220))}

\section*{{Variant Table}}
\small
\begin{{longtable}}{{rlllllllp{{3.2cm}}}}
\toprule
Pos & Type & Ref & Alt & Codon & Codon Pos & Codon Change & AA Change & Impact\\
\midrule
\endhead
{render_variant_rows(rows)}
\bottomrule
\end{{longtable}}
\normalsize

\section*{{Conclusion}}
{latex_escape(conclusion(result))}

\end{{document}}
"""


def write_variant_csv(result: dict[str, Any], csv_path: Path) -> None:
    fields = [
        "pos",
        "variant_type",
        "ref",
        "alt",
        "codon_num",
        "pos_in_codon",
        "ref_codon",
        "alt_codon",
        "ref_aa",
        "alt_aa",
        "ref_aa_name",
        "alt_aa_name",
        "impact",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in result["variants"]:
            writer.writerow({field: row.get(field, "") for field in fields})


def build_pdf(tex_path: Path) -> bool:
    engines: list[tuple[str, list[str]]] = []
    latexmk = find_command("latexmk")
    if latexmk:
        engines.append((latexmk, [latexmk, "-pdf", "-interaction=nonstopmode", "-halt-on-error", tex_path.name]))
    xelatex = find_command("xelatex")
    if xelatex:
        engines.append((xelatex, [xelatex, "-interaction=nonstopmode", "-halt-on-error", tex_path.name]))
    pdflatex = find_command("pdflatex")
    if pdflatex:
        engines.append((pdflatex, [pdflatex, "-interaction=nonstopmode", "-halt-on-error", tex_path.name]))

    if not engines:
        print_step("no LaTeX engine found; wrote .tex only")
        return False

    for engine, cmd in engines:
        print_step(f"building PDF with {Path(engine).name}")
        runs = 1 if "latexmk" in Path(engine).name else 2
        ok = True
        for _ in range(runs):
            proc = subprocess.run(cmd, cwd=tex_path.parent)
            if proc.returncode != 0:
                ok = False
                break
        if ok and tex_path.with_suffix(".pdf").exists():
            return True
    print_step("LaTeX build failed; keeping .tex output")
    return False


def cmd_report(args: argparse.Namespace) -> int:
    result = run_pipeline_for_report(args)
    out_dir = Path(args.output_dir).resolve() if args.output_dir else REPORTS
    out_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    tex_path = out_dir / f"snp_report_{args.dataset}_{timestamp}.tex"
    tex_path.write_text(render_report(result), encoding="utf-8")
    print_step(f"wrote {tex_path}")
    if args.csv:
        csv_path = tex_path.with_suffix(".csv")
        write_variant_csv(result, csv_path)
        print_step(f"wrote {csv_path}")

    if args.no_pdf:
        return 0
    if build_pdf(tex_path):
        print_step(f"wrote {tex_path.with_suffix('.pdf')}")
    else:
        print_step(f"manual build example: pdflatex {tex_path.name}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SNP Detection all-in-one CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    app = sub.add_parser("app", help="start backend and frontend")
    app.add_argument("--backend-port", type=int, default=DEFAULT_BACKEND_PORT)
    app.add_argument("--frontend-port", type=int, default=DEFAULT_DEV_FRONTEND_PORT)
    app.add_argument("--ready-timeout", type=float, default=30.0)
    app.set_defaults(func=cmd_app)

    build = sub.add_parser("build", help="type-check and build the production frontend")
    build.add_argument("--api-base-url", help="VITE_API_BASE_URL to bake into the frontend build")
    build.set_defaults(func=cmd_build)

    serve = sub.add_parser("serve-frontend", help="serve frontend/dist with the built-in Python static server")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=DEFAULT_PROD_FRONTEND_PORT)
    serve.set_defaults(func=cmd_serve_frontend)

    prod = sub.add_parser("prod", help="run production-like backend and built frontend locally")
    prod.add_argument("--backend-port", type=int, default=DEFAULT_BACKEND_PORT)
    prod.add_argument("--frontend-port", type=int, default=DEFAULT_PROD_FRONTEND_PORT)
    prod.add_argument("--api-base-url", help="VITE_API_BASE_URL to bake into the frontend build")
    prod.add_argument("--ready-timeout", type=float, default=30.0)
    prod.set_defaults(func=cmd_prod)

    install = sub.add_parser("install", help="install backend and frontend dependencies")
    install.set_defaults(func=cmd_install)

    check = sub.add_parser("check", help="check runtime dependencies")
    check.set_defaults(func=cmd_check)

    smoke = sub.add_parser("smoke", help="run API and report smoke tests")
    smoke.add_argument("--backend-url", default="http://127.0.0.1:8000")
    smoke.add_argument("--frontend-url")
    smoke.add_argument("--output-dir")
    smoke.set_defaults(func=cmd_smoke)

    report = sub.add_parser("report", help="generate a LaTeX report and optional PDF")
    report.add_argument("--dataset", choices=["synthetic", "hbb", "custom"], default="synthetic")
    report.add_argument("--seq-length", type=int, default=300)
    report.add_argument("--n-snps", type=int, default=12)
    report.add_argument("--gc-content", type=float, default=0.5)
    report.add_argument("--seed", type=int, default=42)
    report.add_argument("--frame", type=int, choices=[0, 1, 2], default=0)
    report.add_argument("--ref")
    report.add_argument("--sample")
    report.add_argument("--ref-file")
    report.add_argument("--sample-file")
    report.add_argument("--output-dir")
    report.add_argument("--no-pdf", action="store_true")
    report.add_argument("--csv", action="store_true", help="write a variant CSV beside the report")
    report.set_defaults(func=cmd_report)

    ci = sub.add_parser("ci", help="run local CI checks")
    ci.set_defaults(func=cmd_ci)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except subprocess.CalledProcessError as exc:
        print(f"command failed with exit code {exc.returncode}: {' '.join(exc.cmd)}")
        return exc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
