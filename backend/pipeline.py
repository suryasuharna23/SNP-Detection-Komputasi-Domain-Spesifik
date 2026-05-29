import random
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
from Bio.Align import PairwiseAligner

CODON_TABLE: Dict[str, str] = {
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

AA_NAMES: Dict[str, str] = {
    "A": "Ala", "R": "Arg", "N": "Asn", "D": "Asp", "C": "Cys",
    "E": "Glu", "Q": "Gln", "G": "Gly", "H": "His", "I": "Ile",
    "L": "Leu", "K": "Lys", "M": "Met", "F": "Phe", "P": "Pro",
    "S": "Ser", "T": "Thr", "W": "Trp", "Y": "Tyr", "V": "Val",
    "*": "Stop",
}

HBB_WILDTYPE = "ATGGTGCATCTGACTCCTGAGGAGAAGTCTGCCGTTACTGCCCTGTGGGGCAAGGTGAAC"
HBB_SICKLE   = "ATGGTGCATCTGACTCCTGTGGAGAAGTCTGCCGTTACTGCCCTGTGGGGCAAGGTGAAC"


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


def generate_random_dna(length: int, gc_content: float = 0.5, seed: int = 42) -> str:
    rng = random.Random(seed)
    p_at = (1 - gc_content) / 2
    p_gc = gc_content / 2
    return "".join(rng.choices("ACGT", weights=[p_at, p_gc, p_gc, p_at], k=length))


def introduce_point_mutations(
    seq: str, n_snps: int, seed: int = 43
) -> Tuple[str, List[Dict]]:
    rng = random.Random(seed)
    seq_list = list(seq)
    positions = rng.sample(range(len(seq)), min(n_snps, len(seq)))
    ground_truth = []
    for pos in sorted(positions):
        orig = seq_list[pos]
        new  = rng.choice([b for b in "ACGT" if b != orig])
        seq_list[pos] = new
        ground_truth.append({"position_0based": pos, "ref": orig, "alt": new})
    return "".join(seq_list), ground_truth


def validate_dna(seq: str) -> Tuple[bool, str]:
    seq = seq.upper().replace(" ", "").replace("\n", "").replace("\r", "")
    invalid = set(seq) - set("ACGTN")
    if invalid:
        return False, f"Karakter tidak valid: {invalid}"
    if len(seq) < 3:
        return False, "Sekuens terlalu pendek (min 3 bp)"
    return True, seq


def align_sequences(ref: str, sample: str) -> Tuple[str, str, float]:
    aligner = PairwiseAligner()
    aligner.mode = "global"
    aligner.match_score = 2
    aligner.mismatch_score = -1
    aligner.open_gap_score = -2
    aligner.extend_gap_score = -1
    best = aligner.align(ref, sample)[0]
    return str(best[0]), str(best[1]), float(best.score)


def detect_variants(ref_aln: str, smp_aln: str) -> List[Variant]:
    variants, pos_ref = [], 0
    for pos_aln, (r, s) in enumerate(zip(ref_aln, smp_aln)):
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


def _translate(codon: str) -> str:
    if len(codon) != 3 or "N" in codon or "-" in codon:
        return "X"
    return CODON_TABLE.get(codon, "X")


def translate_dna(seq: str, frame: int = 0) -> str:
    seq = seq[frame:]
    return "".join(_translate(seq[i : i + 3]) for i in range(0, (len(seq) // 3) * 3, 3))


def classify_snp(v: Variant, ref_seq: str, frame: int = 0) -> MutationImpact:
    pos = v.pos_ref - frame
    if pos < 0:
        return MutationImpact(v, -1, -1, "", "", "", "", "UTR_OR_OUTOFFRAME")
    ci, pi = pos // 3, pos % 3
    cs, ce = frame + ci * 3, frame + ci * 3 + 3
    if ce > len(ref_seq):
        return MutationImpact(v, ci, pi, "", "", "", "", "INCOMPLETE_CODON")
    ref_c = ref_seq[cs:ce]
    alt_l = list(ref_c); alt_l[pi] = v.alt_base
    alt_c = "".join(alt_l)
    ra, aa = _translate(ref_c), _translate(alt_c)
    if ra == aa:
        impact = "SILENT"
    elif aa == "*":
        impact = "NONSENSE"
    elif ra == "*":
        impact = "STOP_LOST"
    elif ci == 0 and ra == "M" and aa != "M":
        impact = "START_LOST"
    else:
        impact = "MISSENSE"
    return MutationImpact(v, ci, pi, ref_c, alt_c, ra, aa, impact)


def classify_all(
    variants: List[Variant], ref_seq: str, frame: int = 0
) -> List[MutationImpact]:
    net = sum(1 for v in variants if v.vtype == "INS") - sum(1 for v in variants if v.vtype == "DEL")
    frameshift = net % 3 != 0
    results = []
    for v in variants:
        if v.vtype == "SNP":
            results.append(classify_snp(v, ref_seq, frame))
        else:
            ci = (v.pos_ref - frame) // 3 if v.pos_ref >= frame else -1
            results.append(MutationImpact(
                v, ci, -1, "", "", "", "",
                "FRAMESHIFT" if frameshift else "INFRAME_INDEL",
            ))
    return results


def evaluate(detected: List[Variant], ground_truth: List[Dict]) -> Dict:
    gt_set  = {(g["position_0based"], g["ref"], g["alt"]) for g in ground_truth}
    det_set = {(v.pos_ref, v.ref_base, v.alt_base) for v in detected if v.vtype == "SNP"}
    tp = len(gt_set & det_set)
    fp = len(det_set - gt_set)
    fn = len(gt_set - det_set)
    pre = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1  = 2 * pre * rec / (pre + rec) if (pre + rec) > 0 else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "precision": pre, "recall": rec, "f1": f1}


def impacts_to_dicts(impacts: List[MutationImpact]) -> List[Dict]:
    rows = []
    for imp in impacts:
        v = imp.variant
        rows.append({
            "pos":          v.pos_ref + 1,
            "variant_type": v.vtype,
            "ref":          v.ref_base,
            "alt":          v.alt_base,
            "codon_num":    imp.codon_index + 1 if imp.codon_index >= 0 else None,
            "pos_in_codon": imp.pos_in_codon + 1 if imp.pos_in_codon >= 0 else None,
            "ref_codon":    imp.ref_codon or None,
            "alt_codon":    imp.alt_codon or None,
            "ref_aa":       imp.ref_aa or None,
            "alt_aa":       imp.alt_aa or None,
            "ref_aa_name":  AA_NAMES.get(imp.ref_aa, None),
            "alt_aa_name":  AA_NAMES.get(imp.alt_aa, None),
            "impact":       imp.impact,
        })
    return rows
