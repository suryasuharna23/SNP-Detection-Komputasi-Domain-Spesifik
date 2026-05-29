import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import random
import io
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional

from Bio.Align import PairwiseAligner

# ── Constants ──────────────────────────────────────────────────────────────────

STANDARD_CODON_TABLE = {
    "TTT": "F", "TTC": "F",
    "TTA": "L", "TTG": "L", "CTT": "L", "CTC": "L", "CTA": "L", "CTG": "L",
    "ATT": "I", "ATC": "I", "ATA": "I",
    "ATG": "M",
    "GTT": "V", "GTC": "V", "GTA": "V", "GTG": "V",
    "TCT": "S", "TCC": "S", "TCA": "S", "TCG": "S", "AGT": "S", "AGC": "S",
    "CCT": "P", "CCC": "P", "CCA": "P", "CCG": "P",
    "ACT": "T", "ACC": "T", "ACA": "T", "ACG": "T",
    "GCT": "A", "GCC": "A", "GCA": "A", "GCG": "A",
    "TAT": "Y", "TAC": "Y",
    "CAT": "H", "CAC": "H",
    "CAA": "Q", "CAG": "Q",
    "AAT": "N", "AAC": "N",
    "AAA": "K", "AAG": "K",
    "GAT": "D", "GAC": "D",
    "GAA": "E", "GAG": "E",
    "TGT": "C", "TGC": "C",
    "TGG": "W",
    "CGT": "R", "CGC": "R", "CGA": "R", "CGG": "R", "AGA": "R", "AGG": "R",
    "GGT": "G", "GGC": "G", "GGA": "G", "GGG": "G",
    "TAA": "*", "TAG": "*", "TGA": "*",
}

AA_FULL_NAME = {
    "A": "Ala", "R": "Arg", "N": "Asn", "D": "Asp", "C": "Cys",
    "E": "Glu", "Q": "Gln", "G": "Gly", "H": "His", "I": "Ile",
    "L": "Leu", "K": "Lys", "M": "Met", "F": "Phe", "P": "Pro",
    "S": "Ser", "T": "Thr", "W": "Trp", "Y": "Tyr", "V": "Val",
    "*": "Stop",
}

IMPACT_COLORS = {
    "SILENT":            "#4C9F70",
    "MISSENSE":          "#E07A5F",
    "NONSENSE":          "#3D405B",
    "START_LOST":        "#81B29A",
    "STOP_LOST":         "#F2CC8F",
    "FRAMESHIFT":        "#555555",
    "INFRAME_INDEL":     "#888888",
    "UTR_OR_OUTOFFRAME": "#CCCCCC",
    "INCOMPLETE_CODON":  "#AAAAAA",
}

HBB_WILDTYPE = "ATGGTGCATCTGACTCCTGAGGAGAAGTCTGCCGTTACTGCCCTGTGGGGCAAGGTGAAC"
HBB_SICKLE   = "ATGGTGCATCTGACTCCTGTGGAGAAGTCTGCCGTTACTGCCCTGTGGGGCAAGGTGAAC"

# ── Pipeline ───────────────────────────────────────────────────────────────────

def generate_random_dna(length: int, gc_content: float = 0.5, seed: int = 42) -> str:
    rng = random.Random(seed)
    p_gc = gc_content / 2
    p_at = (1 - gc_content) / 2
    return "".join(rng.choices("ACGT", weights=[p_at, p_gc, p_gc, p_at], k=length))


def introduce_point_mutations(seq: str, n_snps: int, seed: int = 43) -> Tuple[str, List[Dict]]:
    rng = random.Random(seed)
    seq_list = list(seq)
    positions = rng.sample(range(len(seq)), min(n_snps, len(seq)))
    ground_truth = []
    for pos in sorted(positions):
        original = seq_list[pos]
        new_base = rng.choice([b for b in "ACGT" if b != original])
        seq_list[pos] = new_base
        ground_truth.append({"position_0based": pos, "ref": original, "alt": new_base})
    return "".join(seq_list), ground_truth


def validate_dna(seq: str) -> Tuple[bool, str]:
    seq_upper = seq.upper().replace(" ", "").replace("\n", "").replace("\r", "")
    invalid = set(seq_upper) - set("ACGTN")
    if invalid:
        return False, f"Karakter tidak valid ditemukan: {invalid}"
    if len(seq_upper) < 3:
        return False, "Sekuens terlalu pendek (minimal 3 bp)."
    return True, seq_upper


def align_sequences(ref_seq: str, sample_seq: str) -> Tuple[str, str, float]:
    aligner = PairwiseAligner()
    aligner.mode = "global"
    aligner.match_score = 2
    aligner.mismatch_score = -1
    aligner.open_gap_score = -2
    aligner.extend_gap_score = -1
    alignments = aligner.align(ref_seq, sample_seq)
    best = alignments[0]
    return str(best[0]), str(best[1]), float(best.score)


@dataclass
class Variant:
    pos_ref: int
    pos_aln: int
    ref_base: str
    alt_base: str
    vtype: str  # SNP | INS | DEL


@dataclass
class MutationImpact:
    variant: Variant
    codon_index: int
    pos_in_codon: int
    ref_codon: str
    alt_codon: str
    ref_aa: str
    alt_aa: str
    impact: str


def detect_variants(ref_aligned: str, sample_aligned: str) -> List[Variant]:
    variants = []
    pos_ref = 0
    for pos_aln, (r, s) in enumerate(zip(ref_aligned, sample_aligned)):
        if r == s:
            if r != "-":
                pos_ref += 1
            continue
        if r == "-":
            variants.append(Variant(pos_ref, pos_aln, "-", s, "INS"))
        elif s == "-":
            variants.append(Variant(pos_ref, pos_aln, r, "-", "DEL"))
            pos_ref += 1
        else:
            variants.append(Variant(pos_ref, pos_aln, r, s, "SNP"))
            pos_ref += 1
    return variants


def translate_codon(codon: str) -> str:
    if len(codon) != 3 or "N" in codon or "-" in codon:
        return "X"
    return STANDARD_CODON_TABLE.get(codon, "X")


def translate_dna(seq: str, frame: int = 0) -> str:
    seq = seq[frame:]
    n = (len(seq) // 3) * 3
    return "".join(translate_codon(seq[i : i + 3]) for i in range(0, n, 3))


def classify_snp_impact(variant: Variant, ref_seq: str, frame: int = 0) -> MutationImpact:
    pos = variant.pos_ref - frame
    if pos < 0:
        return MutationImpact(variant, -1, -1, "", "", "", "", "UTR_OR_OUTOFFRAME")
    codon_idx = pos // 3
    pos_in_codon = pos % 3
    codon_start = frame + codon_idx * 3
    codon_end = codon_start + 3
    if codon_end > len(ref_seq):
        return MutationImpact(variant, codon_idx, pos_in_codon, "", "", "", "", "INCOMPLETE_CODON")
    ref_codon = ref_seq[codon_start:codon_end]
    alt_list = list(ref_codon)
    alt_list[pos_in_codon] = variant.alt_base
    alt_codon = "".join(alt_list)
    ref_aa = translate_codon(ref_codon)
    alt_aa = translate_codon(alt_codon)
    if ref_aa == alt_aa:
        impact = "SILENT"
    elif alt_aa == "*":
        impact = "NONSENSE"
    elif ref_aa == "*":
        impact = "STOP_LOST"
    elif codon_idx == 0 and ref_aa == "M" and alt_aa != "M":
        impact = "START_LOST"
    else:
        impact = "MISSENSE"
    return MutationImpact(variant, codon_idx, pos_in_codon, ref_codon, alt_codon, ref_aa, alt_aa, impact)


def classify_all(variants: List[Variant], ref_seq: str, frame: int = 0) -> List[MutationImpact]:
    net = sum(1 for v in variants if v.vtype == "INS") - sum(1 for v in variants if v.vtype == "DEL")
    frameshift = net % 3 != 0
    impacts = []
    for v in variants:
        if v.vtype == "SNP":
            impacts.append(classify_snp_impact(v, ref_seq, frame))
        else:
            codon_idx = (v.pos_ref - frame) // 3 if v.pos_ref >= frame else -1
            label = "FRAMESHIFT" if frameshift else "INFRAME_INDEL"
            impacts.append(MutationImpact(v, codon_idx, -1, "", "", "", "", label))
    return impacts


def impacts_to_df(impacts: List[MutationImpact]) -> pd.DataFrame:
    rows = []
    for imp in impacts:
        v = imp.variant
        rows.append({
            "Pos (1-based)":   v.pos_ref + 1,
            "Tipe Varian":     v.vtype,
            "Ref":             v.ref_base,
            "Alt":             v.alt_base,
            "Kodon #":         imp.codon_index + 1 if imp.codon_index >= 0 else None,
            "Pos dlm Kodon":   imp.pos_in_codon + 1 if imp.pos_in_codon >= 0 else None,
            "Kodon Ref":       imp.ref_codon or "-",
            "Kodon Alt":       imp.alt_codon or "-",
            "AA Ref":          imp.ref_aa or "-",
            "AA Alt":          imp.alt_aa or "-",
            "AA Ref (Nama)":   AA_FULL_NAME.get(imp.ref_aa, "-"),
            "AA Alt (Nama)":   AA_FULL_NAME.get(imp.alt_aa, "-"),
            "Dampak":          imp.impact,
        })
    return pd.DataFrame(rows)


def evaluate_detection(detected: List[Variant], ground_truth: List[Dict]) -> Dict:
    gt_set  = {(g["position_0based"], g["ref"], g["alt"]) for g in ground_truth}
    det_set = {(v.pos_ref, v.ref_base, v.alt_base) for v in detected if v.vtype == "SNP"}
    tp = len(gt_set & det_set)
    fp = len(det_set - gt_set)
    fn = len(gt_set - det_set)
    pre = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1  = 2 * pre * rec / (pre + rec) if (pre + rec) > 0 else 0.0
    return {"TP": tp, "FP": fp, "FN": fn, "Precision": pre, "Recall": rec, "F1": f1}


# ── Visualization ──────────────────────────────────────────────────────────────

def fig_snp_track(df: pd.DataFrame, ref_length: int) -> go.Figure:
    snps = df[df["Tipe Varian"] == "SNP"]
    fig = go.Figure()

    fig.add_shape(type="rect", x0=0, x1=ref_length, y0=-0.3, y1=0.3,
                  fillcolor="lightgray", line_width=0, layer="below")

    for impact, grp in snps.groupby("Dampak"):
        color = IMPACT_COLORS.get(impact, "#999")
        fig.add_trace(go.Scatter(
            x=grp["Pos (1-based)"], y=[0] * len(grp),
            mode="markers",
            marker=dict(symbol="line-ns-open", size=22, color=color,
                        line=dict(color=color, width=3)),
            name=impact,
            customdata=list(zip(grp["Ref"], grp["Alt"], grp["Kodon Ref"],
                                grp["Kodon Alt"], grp["AA Ref (Nama)"], grp["AA Alt (Nama)"])),
            hovertemplate=(
                "<b>Pos %{x}</b><br>"
                "%{customdata[0]} → %{customdata[1]}<br>"
                "Kodon: %{customdata[2]} → %{customdata[3]}<br>"
                "AA: %{customdata[4]} → %{customdata[5]}<br>"
                f"<b>{impact}</b><extra></extra>"
            ),
        ))

    fig.update_layout(
        title="Distribusi Posisi SNP sepanjang Sekuens",
        xaxis_title="Posisi (bp)", xaxis_range=[0, ref_length],
        yaxis=dict(visible=False, range=[-1, 1]),
        height=200, margin=dict(l=10, r=10, t=45, b=10),
        legend=dict(orientation="h", y=-0.5, x=0),
        plot_bgcolor="white",
    )
    return fig


def fig_impact_bar(df: pd.DataFrame) -> go.Figure:
    counts = df["Dampak"].value_counts().reset_index()
    counts.columns = ["Dampak", "Jumlah"]
    fig = px.bar(
        counts, x="Dampak", y="Jumlah",
        color="Dampak", color_discrete_map=IMPACT_COLORS,
        text="Jumlah", title="Distribusi Kategori Dampak Mutasi",
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(showlegend=False, height=340,
                      margin=dict(t=50, b=60), yaxis_title="Jumlah Varian")
    return fig


def fig_subst_matrix(df: pd.DataFrame) -> go.Figure:
    snps = df[df["Tipe Varian"] == "SNP"]
    bases = ["A", "C", "G", "T"]
    mat = pd.DataFrame(0, index=bases, columns=bases)
    for _, row in snps.iterrows():
        r, a = row["Ref"], row["Alt"]
        if r in bases and a in bases:
            mat.loc[r, a] += 1
    fig = px.imshow(
        mat, title="Matriks Substitusi REF → ALT",
        labels=dict(x="Basa Alt (ALT)", y="Basa Ref (REF)", color="Frekuensi"),
        color_continuous_scale="YlOrRd", text_auto=True,
    )
    fig.update_layout(height=340, margin=dict(t=50))
    return fig


def render_alignment_html(ref_aln: str, smp_aln: str, cols: int = 70) -> str:
    style_match   = "color:#333"
    style_gap     = "color:#aaa;background:#f5f5f5"
    style_ref_mm  = "color:#c0392b;font-weight:bold"
    style_smp_mm  = "color:#2980b9;font-weight:bold"

    chunks = []
    for start in range(0, len(ref_aln), cols):
        r_chunk = ref_aln[start : start + cols]
        s_chunk = smp_aln[start : start + cols]
        end = start + len(r_chunk)

        ref_html = smp_html = mid = ""
        for r, s in zip(r_chunk, s_chunk):
            if r == s and r != "-":
                ref_html += f'<span style="{style_match}">{r}</span>'
                smp_html += f'<span style="{style_match}">{s}</span>'
                mid += "|"
            elif r == "-" or s == "-":
                ref_html += f'<span style="{style_gap}">{r}</span>'
                smp_html += f'<span style="{style_gap}">{s}</span>'
                mid += " "
            else:
                ref_html += f'<span style="{style_ref_mm}">{r}</span>'
                smp_html += f'<span style="{style_smp_mm}">{s}</span>'
                mid += "·"

        chunks.append(
            f'<span style="color:#888;font-size:0.8em">REF  [{start+1:>5}-{end:>5}]</span> {ref_html}\n'
            f'<span style="color:transparent">               </span> {mid}\n'
            f'<span style="color:#888;font-size:0.8em">SMPL [{start+1:>5}-{end:>5}]</span> {smp_html}\n'
        )

    body = "\n".join(chunks)
    return (
        '<div style="font-family:\'Courier New\',monospace;font-size:13px;'
        'line-height:1.7;overflow-x:auto;white-space:pre;padding:0.5rem;'
        'background:#fafafa;border-radius:6px;max-height:380px;overflow-y:auto">'
        + body + "</div>"
    )


# ── Page config ────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="SNP Detection — IF3211 ITB",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
[data-testid="stMetricValue"] { font-size: 1.6rem; }
.impact-pill {
    display: inline-block; padding: 2px 10px; border-radius: 12px;
    font-size: 0.78rem; font-weight: 700; letter-spacing: 0.03em;
}
</style>
""", unsafe_allow_html=True)

# ── Sidebar ────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 🧬 SNP Detection")
    st.caption("IF3211 — Komputasi Domain Spesifik · ITB")
    st.markdown("---")

    with st.expander("📘 Apa itu SNP?", expanded=True):
        st.markdown("""
**Single-Nucleotide Polymorphism (SNP)** adalah variasi satu nukleotida
pada sekuens DNA yang dapat memengaruhi fungsi protein.

| Kategori | Keterangan |
|---|---|
| 🟢 **Silent** | Asam amino tidak berubah |
| 🔴 **Missense** | Asam amino berbeda |
| ⚫ **Nonsense** | Kodon stop prematur |
| 🟡 **Stop Lost** | Kodon stop hilang |
| 🔵 **Frameshift** | Indel bukan kelipatan 3 |
        """)

    with st.expander("⚙️ Algoritma Needleman–Wunsch"):
        st.markdown(r"""
Global alignment menggunakan DP:

$$F(i,j) = \max\begin{cases}
F(i-1,j-1)+s(x_i,y_j)\\
F(i-1,j)+g\\
F(i,j-1)+g
\end{cases}$$

**Parameter yang digunakan:**
- Match: **+2**
- Mismatch: **−1**
- Gap open: **−2**, extend: **−1**
        """)

    st.markdown("---")
    st.caption("Dibuat dengan Streamlit + Biopython + Plotly")

# ── Tabs ───────────────────────────────────────────────────────────────────────

tab_demo, tab_sens, tab_about = st.tabs(
    ["🔬 Demo Pipeline", "📊 Eksperimen Sensitivitas", "📖 Tentang"]
)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Demo Pipeline
# ══════════════════════════════════════════════════════════════════════════════

with tab_demo:
    st.header("Demo Pipeline Deteksi SNP")

    inp_col, res_col = st.columns([1, 2], gap="large")

    # ── Input panel ───────────────────────────────────────────────────────────
    with inp_col:
        st.subheader("Parameter Input")

        dataset = st.radio(
            "Pilih dataset:",
            ["🧪 Sintetik (terkendali)", "🩸 HBB — Sickle-Cell Anemia", "✏️ Custom"],
        )

        ref_seq = sample_seq = ""
        gt: Optional[List[Dict]] = None

        if dataset == "🧪 Sintetik (terkendali)":
            seq_len  = st.slider("Panjang referensi (bp)", 60, 900, 300, step=30)
            n_snps   = st.slider("Jumlah SNP disisipkan", 1, max(1, seq_len // 6), 12)
            gc_pct   = st.slider("GC content (%)", 30, 70, 50)
            seed_val = st.number_input("Random seed", value=42, step=1)

            ref_seq    = generate_random_dna(seq_len, gc_pct / 100, seed=int(seed_val))
            sample_seq, gt = introduce_point_mutations(ref_seq, n_snps, seed=int(seed_val) + 1)

        elif dataset == "🩸 HBB — Sickle-Cell Anemia":
            st.info(
                "**Gen β-globin manusia (HBB)** — fragmen 60 bp ekson 1.  \n"
                "Mutasi **A → T** pada posisi 20 mengubah kodon GAG→GTG "
                "(Glutamat→Valin), penyebab *sickle-cell anemia*."
            )
            st.code(f"WT  : {HBB_WILDTYPE}")
            st.code(f"SC  : {HBB_SICKLE}")
            ref_seq, sample_seq = HBB_WILDTYPE, HBB_SICKLE

        else:
            ref_input = st.text_area("Sekuens Referensi", placeholder="ATGGTGCATCTG…", height=100)
            smp_input = st.text_area("Sekuens Sampel",    placeholder="ATGGTGCATCTG…", height=100)

            if ref_input.strip():
                ok, val = validate_dna(ref_input)
                if ok:
                    ref_seq = val
                else:
                    st.error(f"Referensi: {val}")
            if smp_input.strip():
                ok, val = validate_dna(smp_input)
                if ok:
                    sample_seq = val
                else:
                    st.error(f"Sampel: {val}")

        frame = st.selectbox("Reading frame", [0, 1, 2],
                             help="Frame translasi DNA → protein (0, 1, atau 2)")

        can_run = bool(ref_seq and sample_seq)
        run_btn = st.button(
            "▶ Jalankan Pipeline", type="primary",
            use_container_width=True, disabled=not can_run,
        )
        if not can_run and dataset == "✏️ Custom":
            st.caption("Masukkan kedua sekuens terlebih dahulu.")

    # ── Results panel ─────────────────────────────────────────────────────────
    with res_col:
        if run_btn:
            with st.spinner("Menyelaraskan sekuens dan mendeteksi varian…"):
                try:
                    ref_aln, smp_aln, aln_score = align_sequences(ref_seq, sample_seq)
                    variants  = detect_variants(ref_aln, smp_aln)
                    impacts   = classify_all(variants, ref_seq, frame=int(frame))
                    df        = impacts_to_df(impacts)
                    snps_only = [v for v in variants if v.vtype == "SNP"]

                    # ── Summary metrics ───────────────────────────────────────
                    st.subheader("Ringkasan Hasil")
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Panjang Ref",     f"{len(ref_seq)} bp")
                    c2.metric("Total Varian",    len(variants))
                    c3.metric("SNP Terdeteksi",  len(snps_only))
                    c4.metric("Skor Alignment",  f"{aln_score:.0f}")

                    if gt:
                        ev = evaluate_detection(snps_only, gt)
                        st.markdown("**Evaluasi vs Ground Truth (dataset sintetik):**")
                        e1, e2, e3, e4 = st.columns(4)
                        e1.metric("TP",        ev["TP"])
                        e2.metric("Precision", f"{ev['Precision']:.3f}")
                        e3.metric("Recall",    f"{ev['Recall']:.3f}")
                        e4.metric("F1-Score",  f"{ev['F1']:.3f}")

                    st.divider()

                    # ── Alignment view ────────────────────────────────────────
                    with st.expander("👁 Pratinjau Alignment", expanded=True):
                        st.markdown(
                            render_alignment_html(ref_aln, smp_aln),
                            unsafe_allow_html=True,
                        )
                        st.caption(
                            "Merah = basa Ref pada posisi mismatch · "
                            "Biru = basa Alt (sampel) · "
                            "| = match · · = mismatch · spasi = gap"
                        )

                    # ── Variant table ─────────────────────────────────────────
                    with st.expander("📋 Tabel Varian Terdeteksi", expanded=True):
                        if df.empty:
                            st.success("Tidak ada varian terdeteksi — sekuens identik!")
                        else:
                            styled = df.style.map(
                                lambda v: (
                                    f"background:{IMPACT_COLORS.get(v,'#fff')}33;"
                                    f"color:{IMPACT_COLORS.get(v,'#333')};"
                                    "font-weight:700"
                                ),
                                subset=["Dampak"],
                            )
                            st.dataframe(styled, use_container_width=True, hide_index=True)

                            csv_buf = io.BytesIO()
                            df.to_csv(csv_buf, index=False)
                            st.download_button(
                                "⬇ Unduh CSV",
                                data=csv_buf.getvalue(),
                                file_name="snp_variants.csv",
                                mime="text/csv",
                            )

                    # ── Plots ─────────────────────────────────────────────────
                    if not df.empty:
                        st.subheader("Visualisasi Interaktif")
                        st.plotly_chart(
                            fig_snp_track(df, len(ref_seq)),
                            use_container_width=True,
                        )

                        p1, p2 = st.columns(2)
                        with p1:
                            st.plotly_chart(fig_impact_bar(df), use_container_width=True)
                        with p2:
                            st.plotly_chart(fig_subst_matrix(df), use_container_width=True)

                    # ── Protein translation ───────────────────────────────────
                    with st.expander("🔬 Perbandingan Protein", expanded=False):
                        prot_ref = translate_dna(ref_seq, int(frame))
                        prot_smp = translate_dna(sample_seq, int(frame))
                        diff_aa  = sum(a != b for a, b in zip(prot_ref, prot_smp))

                        pa, pb = st.columns(2)
                        pa.markdown("**Protein Referensi:**")
                        pa.code(prot_ref or "(kosong)", language=None)
                        pb.markdown("**Protein Sampel:**")
                        pb.code(prot_smp or "(kosong)", language=None)

                        if diff_aa == 0:
                            st.success("Protein identik — semua mutasi bersifat silent.")
                        else:
                            st.warning(f"{diff_aa} residu asam amino berubah.")

                except Exception as exc:
                    st.error(f"Error saat menjalankan pipeline: {exc}")

        else:
            st.info(
                "Pilih dataset dan atur parameter di panel kiri, "
                "lalu klik **▶ Jalankan Pipeline** untuk melihat hasil."
            )
            st.markdown("""
**Yang akan ditampilkan:**
- Visualisasi alignment (highlight mismatch/SNP)
- Tabel varian lengkap (posisi, basa, kodon, asam amino, dampak)
- Track posisi SNP sepanjang sekuens
- Distribusi kategori dampak mutasi
- Matriks substitusi REF → ALT
- Perbandingan sekuens protein
            """)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Sensitivity Experiment
# ══════════════════════════════════════════════════════════════════════════════

with tab_sens:
    st.header("Eksperimen Sensitivitas Deteksi SNP")
    st.markdown(
        "Ukur bagaimana **precision, recall, dan F1-score** berubah "
        "seiring meningkatnya densitas mutasi pada sekuens."
    )

    s1, s2 = st.columns([1, 2], gap="large")

    with s1:
        st.subheader("Parameter Eksperimen")
        exp_len    = st.slider("Panjang referensi (bp)", 200, 1000, 600, step=100)
        exp_max    = st.slider("SNP maksimum per sekuens", 10, min(200, exp_len // 3), 120, step=10)
        exp_pts    = st.slider("Jumlah titik densitas", 3, 8, 6)
        exp_trials = st.slider("Trial per titik densitas", 2, 10, 5)
        run_exp    = st.button("▶ Jalankan Eksperimen", type="primary", use_container_width=True)

        st.caption(
            f"Estimasi: {exp_pts * exp_trials} alignment akan dijalankan. "
            "Mungkin membutuhkan beberapa detik."
        )

    with s2:
        if run_exp:
            snp_vals = np.linspace(5, exp_max, exp_pts, dtype=int).tolist()
            results  = []

            prog = st.progress(0, text="Memulai eksperimen…")
            total = len(snp_vals) * exp_trials
            done  = 0

            for n_snp in snp_vals:
                for trial in range(exp_trials):
                    base_seed = 1000 + trial * 37
                    ref  = generate_random_dna(exp_len, 0.5, seed=base_seed)
                    smp, gt_e = introduce_point_mutations(ref, int(n_snp), seed=base_seed + 5000)
                    ra, sa, _ = align_sequences(ref, smp)
                    vs = detect_variants(ra, sa)
                    m  = evaluate_detection(vs, gt_e)
                    results.append({
                        "n_snp":       n_snp,
                        "Densitas (%)": round(100 * n_snp / exp_len, 2),
                        "Precision":   m["Precision"],
                        "Recall":      m["Recall"],
                        "F1":          m["F1"],
                    })
                    done += 1
                    prog.progress(done / total,
                                  text=f"SNP={n_snp}, trial {trial+1}/{exp_trials}")

            prog.empty()

            df_exp = pd.DataFrame(results)
            df_agg = (
                df_exp.groupby("Densitas (%)")
                .agg(
                    Pre_mean=("Precision", "mean"), Pre_std=("Precision", "std"),
                    Rec_mean=("Recall",    "mean"), Rec_std=("Recall",    "std"),
                    F1_mean =("F1",        "mean"), F1_std =("F1",        "std"),
                )
                .reset_index()
            )

            fig_s = go.Figure()
            palette = {"Precision": "#1f77b4", "Recall": "#ff7f0e", "F1": "#2ca02c"}
            for metric, color in palette.items():
                col_m = metric[0:3] + "_mean" if metric == "Precision" else metric[:3] + "_mean"
                col_s = metric[0:3] + "_std"  if metric == "Precision" else metric[:3] + "_std"
                # Fix column names
                col_m = {"Precision": "Pre_mean", "Recall": "Rec_mean", "F1": "F1_mean"}[metric]
                col_s = {"Precision": "Pre_std",  "Recall": "Rec_std",  "F1": "F1_std" }[metric]

                fig_s.add_trace(go.Scatter(
                    x=df_agg["Densitas (%)"], y=df_agg[col_m],
                    error_y=dict(array=df_agg[col_s].fillna(0).tolist(), thickness=1.5, width=6),
                    mode="lines+markers",
                    name=metric, line=dict(color=color, width=2.5),
                    marker=dict(size=8),
                ))

            fig_s.update_layout(
                title=f"Sensitivitas Pipeline SNP (ref={exp_len} bp, {exp_trials} trial/titik)",
                xaxis_title="Densitas SNP (% dari panjang sekuens)",
                yaxis_title="Nilai Metrik",
                yaxis_range=[0, 1.05],
                height=450,
                legend=dict(orientation="h", y=-0.2),
            )
            st.plotly_chart(fig_s, use_container_width=True)

            with st.expander("📊 Tabel Agregasi"):
                fmt = {c: "{:.4f}" for c in df_agg.columns if c != "Densitas (%)"}
                st.dataframe(df_agg.style.format(fmt), use_container_width=True, hide_index=True)

            exp_csv = io.BytesIO()
            df_exp.to_csv(exp_csv, index=False)
            st.download_button("⬇ Unduh Data Eksperimen",
                               data=exp_csv.getvalue(),
                               file_name="sensitivity_experiment.csv",
                               mime="text/csv")
        else:
            st.info("Atur parameter di kiri, lalu klik **▶ Jalankan Eksperimen**.")
            st.markdown("""
**Apa yang diukur?**

Eksperimen ini membuat sekuens referensi acak, menyisipkan sejumlah SNP yang
diketahui (*ground truth*), lalu menjalankan pipeline dan membandingkan
hasilnya dengan ground truth.

Diulang beberapa trial per titik densitas untuk mendapatkan error bar yang
representatif.

**Hasil yang diharapkan:** F1-score tetap tinggi (≈1.0) pada densitas rendah,
namun mulai turun ketika banyak basa berbeda berdekatan sehingga aligner lebih
memilih gap daripada mismatch berturut-turut.
            """)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — About
# ══════════════════════════════════════════════════════════════════════════════

with tab_about:
    st.header("Tentang Proyek")

    a1, a2 = st.columns(2, gap="large")

    with a1:
        st.subheader("Latar Belakang")
        st.markdown("""
Proyek ini merupakan implementasi pipeline komputasi bioinformatika untuk
mata kuliah **IF3211 — Komputasi Domain Spesifik**, Institut Teknologi Bandung.

Pipeline terdiri dari empat tahap utama:

```
FASTA / Input
    │
    ▼
[Sequence Alignment]   ← Needleman–Wunsch
    │
    ▼
[Deteksi Varian]       ← SNP, INS, DEL
    │
    ▼
[Klasifikasi Dampak]   ← Silent / Missense /
    │                     Nonsense / Stop Lost /
    ▼                     Frameshift
[Visualisasi & Laporan]
```
        """)

        st.subheader("Contoh Biologis: Sickle-Cell Anemia")
        st.markdown("""
Mutasi tunggal **A → T** pada kodon ke-7 gen β-globin (HBB) mengubah
**Glutamat (Glu)** menjadi **Valin (Val)**:

```
Wild-type  → GAG → Glu  → eritrosit normal
Sickle-cell→ GTG → Val  → eritrosit berbentuk sabit
```

Pipeline ini berhasil mereproduksi temuan klasik tersebut secara otomatis.
        """)

    with a2:
        st.subheader("Teknologi")
        st.markdown("""
| Komponen | Library |
|---|---|
| Sequence Alignment | Biopython `PairwiseAligner` |
| Manipulasi Data | Pandas, NumPy |
| Visualisasi Interaktif | Plotly |
| Web Framework | Streamlit |
| Bahasa | Python 3 |
        """)

        st.subheader("Referensi")
        st.markdown("""
1. **Needleman & Wunsch** (1970). A general method applicable to the search
   for similarities in the amino acid sequence of two proteins.
   *J. Mol. Biol.* 48(3), 443–453.
2. **Cock et al.** (2009). Biopython. *Bioinformatics* 25(11), 1422–1423.
3. **Ingram** (1957). Gene mutations in human haemoglobin.
   *Nature* 180, 326–328.
4. **Sherry et al.** (2001). dbSNP. *Nucleic Acids Res.* 29(1), 308–311.
        """)

        st.subheader("Cara Menjalankan")
        st.code("""
# Install dependencies
pip install streamlit biopython pandas numpy plotly

# Jalankan aplikasi
streamlit run app.py
        """, language="bash")
