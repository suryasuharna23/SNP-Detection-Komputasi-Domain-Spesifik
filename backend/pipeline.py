import random
from collections import Counter
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
from Bio.Align import PairwiseAligner

STANDARD_CODON_TABLE: Dict[str, str] = {
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

MITOCHONDRIAL_CODON_TABLE = STANDARD_CODON_TABLE.copy()
MITOCHONDRIAL_CODON_TABLE.update({
    "AGA": "*",
    "AGG": "*",
    "TGA": "W",
    "ATA": "M",
})

CODON_TABLE = STANDARD_CODON_TABLE
CODON_TABLES: Dict[str, Dict[str, str]] = {
    "standard": STANDARD_CODON_TABLE,
    "vertebrate_mitochondrial": MITOCHONDRIAL_CODON_TABLE,
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

GRANTHAM_DISTANCE = {
    ("A","R"): 112, ("A","N"): 111, ("A","D"): 126, ("A","C"): 195, ("A","Q"): 91,
    ("A","E"): 107, ("A","G"): 60,  ("A","H"): 86,  ("A","I"): 94,  ("A","L"): 96,
    ("A","K"): 106, ("A","M"): 84,  ("A","F"): 113, ("A","P"): 27,  ("A","S"): 99,
    ("A","T"): 58,  ("A","W"): 148, ("A","Y"): 112, ("A","V"): 64,
    ("R","N"): 86,  ("R","D"): 96,  ("R","C"): 180, ("R","Q"): 43,  ("R","E"): 54,
    ("R","G"): 125, ("R","H"): 29,  ("R","I"): 97,  ("R","L"): 102, ("R","K"): 26,
    ("R","M"): 91,  ("R","F"): 97,  ("R","P"): 103, ("R","S"): 110, ("R","T"): 71,
    ("R","W"): 101, ("R","Y"): 77,  ("R","V"): 96,
    ("N","D"): 23,  ("N","C"): 139, ("N","Q"): 46,  ("N","E"): 42,  ("N","G"): 80,
    ("N","H"): 68,  ("N","I"): 149, ("N","L"): 153, ("N","K"): 94,  ("N","M"): 142,
    ("N","F"): 158, ("N","P"): 91,  ("N","S"): 46,  ("N","T"): 65,  ("N","W"): 174,
    ("N","Y"): 143, ("N","V"): 133,
    ("D","C"): 154, ("D","Q"): 61,  ("D","E"): 45,  ("D","G"): 94,  ("D","H"): 81,
    ("D","I"): 168, ("D","L"): 172, ("D","K"): 101, ("D","M"): 160, ("D","F"): 177,
    ("D","P"): 108, ("D","S"): 65,  ("D","T"): 85,  ("D","W"): 181, ("D","Y"): 160,
    ("D","V"): 152,
    ("C","Q"): 154, ("C","E"): 170, ("C","G"): 159, ("C","H"): 174, ("C","I"): 198,
    ("C","L"): 198, ("C","K"): 202, ("C","M"): 196, ("C","F"): 205, ("C","P"): 169,
    ("C","S"): 112, ("C","T"): 149, ("C","W"): 215, ("C","Y"): 194, ("C","V"): 192,
    ("Q","E"): 29,  ("Q","G"): 87,  ("Q","H"): 24,  ("Q","I"): 109, ("Q","L"): 113,
    ("Q","K"): 53,  ("Q","M"): 101, ("Q","F"): 116, ("Q","P"): 76,  ("Q","S"): 68,
    ("Q","T"): 42,  ("Q","W"): 130, ("Q","Y"): 99,  ("Q","V"): 96,
    ("E","G"): 98,  ("E","H"): 40,  ("E","I"): 134, ("E","L"): 138, ("E","K"): 56,
    ("E","M"): 126, ("E","F"): 140, ("E","P"): 93,  ("E","S"): 80,  ("E","T"): 65,
    ("E","W"): 152, ("E","Y"): 122, ("E","V"): 121,
    ("G","H"): 98,  ("G","I"): 135, ("G","L"): 138, ("G","K"): 127, ("G","M"): 127,
    ("G","F"): 153, ("G","P"): 42,  ("G","S"): 56,  ("G","T"): 59,  ("G","W"): 184,
    ("G","Y"): 147, ("G","V"): 109,
    ("H","I"): 94,  ("H","L"): 99,  ("H","K"): 32,  ("H","M"): 87,  ("H","F"): 100,
    ("H","P"): 77,  ("H","S"): 89,  ("H","T"): 47,  ("H","W"): 115, ("H","Y"): 83,
    ("H","V"): 84,
    ("I","L"): 5,   ("I","K"): 102, ("I","M"): 10,  ("I","F"): 21,  ("I","P"): 95,
    ("I","S"): 142, ("I","T"): 89,  ("I","W"): 61,  ("I","Y"): 33,  ("I","V"): 29,
    ("L","K"): 107, ("L","M"): 15,  ("L","F"): 22,  ("L","P"): 98,  ("L","S"): 145,
    ("L","T"): 92,  ("L","W"): 61,  ("L","Y"): 36,  ("L","V"): 32,
    ("K","M"): 95,  ("K","F"): 102, ("K","P"): 103, ("K","S"): 121, ("K","T"): 78,
    ("K","W"): 110, ("K","Y"): 85,  ("K","V"): 97,
    ("M","F"): 28,  ("M","P"): 87,  ("M","S"): 135, ("M","T"): 81,  ("M","W"): 67,
    ("M","Y"): 36,  ("M","V"): 21,
    ("F","P"): 114, ("F","S"): 155, ("F","T"): 103, ("F","W"): 40,  ("F","Y"): 22,
    ("F","V"): 50,
    ("P","S"): 74,  ("P","T"): 38,  ("P","W"): 147, ("P","Y"): 110, ("P","V"): 68,
    ("S","T"): 58,  ("S","W"): 177, ("S","Y"): 144, ("S","V"): 124,
    ("T","W"): 128, ("T","Y"): 92,  ("T","V"): 69,
    ("W","Y"): 37,  ("W","V"): 88,
    ("Y","V"): 55,
}

IMPACT_SEVERITY = {
    "NONSENSE": 1.0,
    "FRAMESHIFT": 1.0,
    "START_LOST": 0.95,
    "STOP_LOST": 0.85,
    "MISSENSE": 0.7,
    "INFRAME_INDEL": 0.5,
    "INCOMPLETE_CODON": 0.3,
    "UTR_OR_OUTOFFRAME": 0.2,
    "SILENT": 0.1,
}


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


@dataclass
class ORF:
    start: int
    end: int
    frame: int
    strand: str
    length_bp: int
    length_aa: int
    protein: str


@dataclass
class ClinVarEntry:
    variant_id: str
    gene: str
    hgvs_c: str
    hgvs_p: str
    clinical_significance: str
    condition: str
    review_status: str
    allele_frequency: float
    evidence_count: int
    source: str = "simulated"
    url: Optional[str] = None

    @property
    def severity_score(self) -> float:
        return {
            "Pathogenic": 1.0,
            "Pathogenic/Likely pathogenic": 0.95,
            "Likely pathogenic": 0.85,
            "VUS": 0.5,
            "Uncertain significance": 0.5,
            "Conflicting classifications of pathogenicity": 0.5,
            "Likely benign": 0.15,
            "Benign": 0.0,
        }.get(self.clinical_significance, 0.5)

    @property
    def confidence_score(self) -> float:
        review = self.review_status.lower()
        if "practice guideline" in review:
            return 1.0
        if "expert panel" in review:
            return 0.9
        if "multiple submitters" in review and "no conflicts" in review:
            return 0.8
        if "single submitter" in review:
            return 0.6
        return {
            "practice guideline": 1.0,
            "expert panel": 0.9,
            "criteria provided, multiple submitters": 0.8,
            "criteria provided, single submitter": 0.6,
            "no assertion criteria provided": 0.3,
        }.get(self.review_status, 0.3)


CLINVAR_DB: Dict[str, ClinVarEntry] = {
    "HBB:GAG_7_GTG": ClinVarEntry(
        "CV000015333", "HBB", "c.20A>T", "p.Glu7Val", "Pathogenic",
        "Sickle cell disease", "practice guideline", 0.008, 42,
    ),
    "HBB:GAG_7_AAG": ClinVarEntry(
        "CV000015334", "HBB", "c.19G>A", "p.Glu7Lys", "Pathogenic",
        "Hemoglobin C disease", "expert panel", 0.003, 15,
    ),
    "HBB:CTG_2_CCG": ClinVarEntry(
        "CV000015400", "HBB", "c.5T>C", "p.Leu2Pro", "Likely pathogenic",
        "Beta-thalassemia", "criteria provided, single submitter", 0.0001, 3,
    ),
    "BRCA1:TGT_61_TAT": ClinVarEntry(
        "CV000123456", "BRCA1", "c.181T>A", "p.Cys61Tyr", "VUS",
        "Hereditary breast and ovarian cancer",
        "criteria provided, multiple submitters", 0.0005, 8,
    ),
    "TP53:CGG_248_TGG": ClinVarEntry(
        "CV000789012", "TP53", "c.742C>T", "p.Arg248Trp", "Pathogenic",
        "Li-Fraumeni syndrome", "expert panel", 0.00001, 35,
    ),
}


@dataclass
class GeneAnnotation:
    gene_name: str
    strand: str
    total_length: int
    exons: List[Tuple[int, int]]
    cds_start: int
    cds_end: int

    @property
    def introns(self) -> List[Tuple[int, int]]:
        introns = []
        sorted_exons = sorted(self.exons)
        for i in range(len(sorted_exons) - 1):
            intron_start = sorted_exons[i][1]
            intron_end = sorted_exons[i + 1][0]
            if intron_end > intron_start:
                introns.append((intron_start, intron_end))
        return introns


@dataclass
class PathogenicityAssessment:
    impact: MutationImpact
    conservation_score: float
    grantham_distance: int
    clinvar_entry: Optional[ClinVarEntry]
    clinvar_severity: float
    region_type: str
    region_criticality: float
    rarity_bonus: float
    pathogenicity_score: float
    confidence: str
    recommendation: str

    @property
    def risk_level(self) -> str:
        if self.pathogenicity_score >= 0.8:
            return "HIGH RISK"
        if self.pathogenicity_score >= 0.5:
            return "MODERATE RISK"
        if self.pathogenicity_score >= 0.3:
            return "LOW RISK"
        return "BENIGN"


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


def complement_base(base: str) -> str:
    return {"A": "T", "T": "A", "C": "G", "G": "C", "N": "N", "-": "-"}.get(base, "N")


def get_codon_table(name: str = "standard") -> Dict[str, str]:
    return CODON_TABLES[name]


def reverse_complement(seq: str) -> str:
    comp = {"A": "T", "T": "A", "C": "G", "G": "C", "N": "N"}
    return "".join(comp.get(b, "N") for b in reversed(seq.upper()))


def find_orfs(
    seq: str,
    min_length_aa: int = 10,
    codon_table: Optional[Dict[str, str]] = None,
) -> List[ORF]:
    codon_table = codon_table or STANDARD_CODON_TABLE
    seq = seq.upper()
    orfs: List[ORF] = []

    for strand, strand_seq in [("+", seq), ("-", reverse_complement(seq))]:
        for frame in range(3):
            i = frame
            while i <= len(strand_seq) - 3:
                codon = strand_seq[i : i + 3]
                if codon != "ATG":
                    i += 3
                    continue

                protein = "M"
                j = i + 3
                while j <= len(strand_seq) - 3:
                    aa = _translate(strand_seq[j : j + 3], codon_table)
                    if aa == "*":
                        break
                    protein += aa
                    j += 3

                end_pos = j + 3 if j <= len(strand_seq) - 3 else j
                length_bp = end_pos - i
                if len(protein) >= min_length_aa:
                    if strand == "+":
                        actual_start, actual_end = i, end_pos
                    else:
                        actual_start, actual_end = len(seq) - end_pos, len(seq) - i
                    orfs.append(ORF(
                        actual_start, actual_end, frame, strand, length_bp, len(protein), protein
                    ))
                i = j + 3

    return sorted(
        orfs,
        key=lambda o: (-o.length_aa, 0 if o.strand == "+" else 1, o.frame, o.start),
    )


def _translate(codon: str, codon_table: Optional[Dict[str, str]] = None) -> str:
    codon_table = codon_table or STANDARD_CODON_TABLE
    if len(codon) != 3 or "N" in codon or "-" in codon:
        return "X"
    return codon_table.get(codon, "X")


def translate_dna(
    seq: str,
    frame: int = 0,
    codon_table: Optional[Dict[str, str]] = None,
) -> str:
    codon_table = codon_table or STANDARD_CODON_TABLE
    seq = seq[frame:]
    return "".join(_translate(seq[i : i + 3], codon_table) for i in range(0, (len(seq) // 3) * 3, 3))


def classify_snp(
    v: Variant,
    ref_seq: str,
    frame: int = 0,
    codon_table: Optional[Dict[str, str]] = None,
) -> MutationImpact:
    codon_table = codon_table or STANDARD_CODON_TABLE
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
    ra, aa = _translate(ref_c, codon_table), _translate(alt_c, codon_table)
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
    variants: List[Variant],
    ref_seq: str,
    frame: int = 0,
    codon_table: Optional[Dict[str, str]] = None,
) -> List[MutationImpact]:
    codon_table = codon_table or STANDARD_CODON_TABLE
    net = sum(1 for v in variants if v.vtype == "INS") - sum(1 for v in variants if v.vtype == "DEL")
    frameshift = net % 3 != 0
    results = []
    for v in variants:
        if v.vtype == "SNP":
            results.append(classify_snp(v, ref_seq, frame, codon_table))
        else:
            ci = (v.pos_ref - frame) // 3 if v.pos_ref >= frame else -1
            results.append(MutationImpact(
                v, ci, -1, "", "", "", "",
                "FRAMESHIFT" if frameshift else "INFRAME_INDEL",
            ))
    return results


def map_impact_to_original_coordinates(
    impact: MutationImpact,
    ref_length: int,
    strand: str,
) -> MutationImpact:
    if strand != "-":
        return impact

    v = impact.variant
    if v.vtype == "INS":
        pos_ref = max(0, min(ref_length, ref_length - v.pos_ref))
    else:
        pos_ref = max(0, min(ref_length - 1, ref_length - 1 - v.pos_ref))

    mapped_variant = Variant(
        pos_ref=pos_ref,
        pos_aln=v.pos_aln,
        ref_base=complement_base(v.ref_base),
        alt_base=complement_base(v.alt_base),
        vtype=v.vtype,
    )
    return MutationImpact(
        mapped_variant,
        impact.codon_index,
        impact.pos_in_codon,
        impact.ref_codon,
        impact.alt_codon,
        impact.ref_aa,
        impact.alt_aa,
        impact.impact,
    )


def get_grantham_distance(aa1: str, aa2: str) -> int:
    if aa1 == aa2:
        return 0
    if aa1 in ("*", "X") or aa2 in ("*", "X"):
        return 215
    key = tuple(sorted([aa1, aa2]))
    return GRANTHAM_DISTANCE.get(key, 100)


def compute_conservation_score(impact: MutationImpact) -> float:
    if impact.pos_in_codon in (0, 1):
        codon_pos_score = 1.0
    elif impact.pos_in_codon == 2:
        codon_pos_score = 0.3
    else:
        codon_pos_score = 0.5

    grantham_score = min(get_grantham_distance(impact.ref_aa, impact.alt_aa) / 215.0, 1.0)
    severity_score = IMPACT_SEVERITY.get(impact.impact, 0.5)
    score = 0.30 * codon_pos_score + 0.40 * grantham_score + 0.30 * severity_score
    return round(min(max(score, 0.0), 1.0), 4)


def lookup_clinvar(impact: MutationImpact, gene_name: str = "UNKNOWN") -> Optional[ClinVarEntry]:
    if impact.impact in ("UTR_OR_OUTOFFRAME", "INCOMPLETE_CODON", "FRAMESHIFT", "INFRAME_INDEL"):
        return None
    key = f"{gene_name}:{impact.ref_codon}_{impact.codon_index + 1}_{impact.alt_codon}"
    return CLINVAR_DB.get(key)


def default_annotation(gene_name: str, ref_length: int, strand: str = "+") -> GeneAnnotation:
    return GeneAnnotation(
        gene_name=gene_name,
        strand=strand,
        total_length=ref_length,
        exons=[(0, ref_length)],
        cds_start=0,
        cds_end=ref_length,
    )


def classify_region(pos: int, annotation: GeneAnnotation) -> Tuple[str, float]:
    for exon_start, exon_end in annotation.exons:
        for boundary in (exon_start, exon_end):
            if abs(pos - boundary) <= 2 and pos != boundary:
                for intron_start, intron_end in annotation.introns:
                    if intron_start - 2 <= pos <= intron_start + 2 or intron_end - 2 <= pos <= intron_end + 2:
                        return "SPLICE_SITE", 0.95

    for exon_start, exon_end in annotation.exons:
        if exon_start <= pos < exon_end:
            if annotation.cds_start <= pos < annotation.cds_end:
                return "EXON_CODING", 0.8
            if pos < annotation.cds_start:
                return "5_UTR", 0.4
            return "3_UTR", 0.3

    for intron_start, intron_end in annotation.introns:
        if intron_start <= pos < intron_end:
            return "INTRON", 0.15

    if pos < annotation.cds_start:
        return "PROMOTER", 0.35
    return "INTERGENIC", 0.1


def compute_pathogenicity(
    impact: MutationImpact,
    gene_name: str,
    annotation: GeneAnnotation,
    clinvar_overrides: Optional[Dict[int, ClinVarEntry]] = None,
) -> PathogenicityAssessment:
    cons_score = compute_conservation_score(impact)
    grantham = get_grantham_distance(impact.ref_aa, impact.alt_aa)
    clinvar_entry = (clinvar_overrides or {}).get(id(impact.variant)) or lookup_clinvar(impact, gene_name=gene_name)
    if clinvar_entry:
        clinvar_severity = clinvar_entry.severity_score
        clinvar_confidence = clinvar_entry.confidence_score
        rarity = 1.0 - min(clinvar_entry.allele_frequency * 100, 1.0)
    else:
        clinvar_severity = 0.5
        clinvar_confidence = 0.0
        rarity = 0.5

    region_type, region_crit = classify_region(impact.variant.pos_ref, annotation)

    w_conservation, w_clinvar, w_region, w_rarity = 0.35, 0.35, 0.20, 0.10
    if clinvar_entry is None:
        effective_w_cons = w_conservation + w_clinvar * 0.6
        effective_w_clinvar = 0.0
        effective_w_region = w_region + w_clinvar * 0.3
        effective_w_rarity = w_rarity + w_clinvar * 0.1
    else:
        effective_w_cons = w_conservation
        effective_w_clinvar = w_clinvar
        effective_w_region = w_region
        effective_w_rarity = w_rarity

    path_score = (
        effective_w_cons * cons_score
        + effective_w_clinvar * clinvar_severity
        + effective_w_region * region_crit
        + effective_w_rarity * rarity
    )
    path_score = round(min(max(path_score, 0.0), 1.0), 4)

    if clinvar_entry and clinvar_confidence >= 0.8:
        confidence = "HIGH"
    elif clinvar_entry and clinvar_confidence >= 0.5:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    if path_score >= 0.8:
        if impact.impact == "NONSENSE":
            recommendation = "Likely disease-causing (premature stop). Requires clinical validation."
        elif impact.impact == "MISSENSE":
            recommendation = "Likely damaging missense. Consider functional assay and genetic counseling."
        else:
            recommendation = "High pathogenicity score. Requires further clinical investigation."
    elif path_score >= 0.5:
        recommendation = "Moderate risk. Consider additional evidence (family history, functional data)."
    elif path_score >= 0.3:
        recommendation = "Low risk. Monitor if symptomatic; likely tolerated."
    else:
        recommendation = "Likely benign. No clinical action recommended."

    return PathogenicityAssessment(
        impact, cons_score, grantham, clinvar_entry, clinvar_severity,
        region_type, region_crit, rarity, path_score, confidence, recommendation,
    )


def assess_impacts(
    impacts: List[MutationImpact],
    gene_name: str,
    ref_length: int,
    strand: str = "+",
    annotation: Optional[GeneAnnotation] = None,
    clinvar_overrides: Optional[Dict[int, ClinVarEntry]] = None,
) -> List[PathogenicityAssessment]:
    annotation = annotation or default_annotation(gene_name, ref_length, strand)
    return [
        compute_pathogenicity(impact, gene_name, annotation, clinvar_overrides)
        for impact in impacts
    ]


def orf_to_dict(orf: Optional[ORF], include_protein: bool = True) -> Optional[Dict]:
    if not orf:
        return None
    data = {
        "start": orf.start,
        "end": orf.end,
        "frame": orf.frame,
        "strand": orf.strand,
        "length_bp": orf.length_bp,
        "length_aa": orf.length_aa,
    }
    if include_protein:
        data["protein"] = orf.protein
    return data


def clinvar_to_dict(entry: Optional[ClinVarEntry]) -> Optional[Dict]:
    if not entry:
        return None
    return {
        "variant_id": entry.variant_id,
        "gene": entry.gene,
        "hgvs_c": entry.hgvs_c,
        "hgvs_p": entry.hgvs_p,
        "clinical_significance": entry.clinical_significance,
        "condition": entry.condition,
        "review_status": entry.review_status,
        "allele_frequency": entry.allele_frequency,
        "evidence_count": entry.evidence_count,
        "source": entry.source,
        "url": entry.url,
    }


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


def impacts_to_dicts(
    impacts: List[MutationImpact],
    assessments: Optional[List[PathogenicityAssessment]] = None,
) -> List[Dict]:
    by_variant = {
        id(assessment.impact.variant): assessment
        for assessment in assessments or []
    }
    rows = []
    for imp in impacts:
        v = imp.variant
        row = {
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
        }
        assessment = by_variant.get(id(v))
        if assessment:
            row.update({
                "conservation_score": assessment.conservation_score,
                "grantham_distance": assessment.grantham_distance,
                "region_type": assessment.region_type,
                "region_criticality": assessment.region_criticality,
                "rarity_bonus": assessment.rarity_bonus,
                "clinvar_severity": assessment.clinvar_severity,
                "pathogenicity_score": assessment.pathogenicity_score,
                "risk_level": assessment.risk_level,
                "confidence": assessment.confidence,
                "recommendation": assessment.recommendation,
                "clinvar": clinvar_to_dict(assessment.clinvar_entry),
            })
        else:
            row.update({
                "conservation_score": None,
                "grantham_distance": None,
                "region_type": None,
                "region_criticality": None,
                "rarity_bonus": None,
                "clinvar_severity": None,
                "pathogenicity_score": None,
                "risk_level": None,
                "confidence": None,
                "recommendation": None,
                "clinvar": None,
            })
        rows.append(row)
    return sorted(rows, key=lambda row: (row["pos"], row["variant_type"], row["ref"], row["alt"]))


def generate_clinical_report(
    assessments: List[PathogenicityAssessment],
    gene_name: str,
    ref_length: int,
) -> str:
    lines = [
        "=" * 70,
        f"  CLINICAL VARIANT REPORT - {gene_name}",
        f"  Reference length: {ref_length} bp",
        f"  Total variants analyzed: {len(assessments)}",
        "  Date: Generated by SNP Detection Pipeline v2.0",
        "  Educational use only. Not for clinical decision-making.",
        "=" * 70,
        "",
        "  RISK SUMMARY:",
    ]

    risk_counts = Counter(a.risk_level for a in assessments)
    for level in ["HIGH RISK", "MODERATE RISK", "LOW RISK", "BENIGN"]:
        lines.append(f"    {level:<15s}: {risk_counts.get(level, 0):>3d}")

    if assessments:
        mean_score = sum(a.pathogenicity_score for a in assessments) / len(assessments)
        max_score = max(a.pathogenicity_score for a in assessments)
        lines.append(f"\n  Mean pathogenicity score: {mean_score:.4f}")
        lines.append(f"  Max pathogenicity score:  {max_score:.4f}")
    else:
        lines.append("\n  No variants were assessed.")

    lines.extend(["", "-" * 70, "  VARIANT DETAILS", "-" * 70])

    for i, assessment in enumerate(assessments, 1):
        imp = assessment.impact
        v = imp.variant
        ref_name = AA_NAMES.get(imp.ref_aa, imp.ref_aa)
        alt_name = AA_NAMES.get(imp.alt_aa, imp.alt_aa)
        lines.append(f"\n  [{i}] Position {v.pos_ref + 1} (1-based) | {v.ref_base} -> {v.alt_base}")
        lines.append(f"      Codon: {imp.ref_codon or '-'} ({ref_name or '-'}) -> {imp.alt_codon or '-'} ({alt_name or '-'})")
        lines.append(f"      Impact: {imp.impact}")
        lines.append(f"      Region: {assessment.region_type}")
        lines.append(f"      Conservation: {assessment.conservation_score:.4f}")
        if imp.ref_aa != imp.alt_aa and imp.ref_aa not in ("*", "X", "") and imp.alt_aa not in ("*", "X", ""):
            lines.append(f"      Grantham distance: {assessment.grantham_distance}")
        if assessment.clinvar_entry:
            entry = assessment.clinvar_entry
            source = f" ({entry.source})" if entry.source else ""
            lines.append(f"      ClinVar{source}: {entry.variant_id} - {entry.clinical_significance}")
            lines.append(f"      Condition: {entry.condition}")
            lines.append(f"      Evidence: {entry.evidence_count} submissions ({entry.review_status})")
        else:
            lines.append("      ClinVar: NOT FOUND")
        lines.append("      ------------------------------")
        lines.append(f"      PATHOGENICITY: {assessment.pathogenicity_score:.4f} [{assessment.risk_level}]")
        lines.append(f"      CONFIDENCE:    {assessment.confidence}")
        lines.append(f"      RECOMMENDATION: {assessment.recommendation}")

    lines.extend(["", "=" * 70, "  END OF REPORT", "=" * 70])
    return "\n".join(lines)
