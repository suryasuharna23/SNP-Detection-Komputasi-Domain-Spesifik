# Requirements Document

## Introduction

This feature brings the SNP Detection web application (FastAPI backend + React/TypeScript frontend) to parity with the extended Jupyter notebook (`notebook/snp_detection_pipeline_extended.ipynb`). The application currently implements only the core SNP pipeline: random DNA generation, Needleman-Wunsch alignment, variant detection (SNP/INS/DEL), protein translation, impact classification, precision/recall/F1 evaluation, sensitivity analysis, and an optional Gemini AI guide.

The notebook contains six additional clinical/analysis modules that are not yet present in the application. This feature ports those modules into the backend pipeline and surfaces their outputs in the frontend:

1. ORF auto-detection across all six reading frames (replacing the manual `frame` assumption)
2. Conservation scoring using a Grantham distance matrix
3. Simulated ClinVar annotation
4. Genomic region classification
5. Integrated pathogenicity scoring
6. Clinical report generation with alternative codon table support

The notebook is the source of truth for all algorithms, constants, weights, and thresholds. The feature must preserve backward compatibility with existing API consumers, maintain reproducibility via the existing seeding behavior, and keep an "educational / not for clinical use" framing consistent with an academic course project (IF3211, ITB).

## Glossary

- **Pipeline**: The backend analysis library (`backend/pipeline.py`) containing the DNA analysis functions and dataclasses.
- **Pipeline_API**: The FastAPI service (`backend/main.py`) exposing HTTP endpoints, including `POST /api/run`.
- **ORF_Detector**: The component that searches reading frames and identifies Open Reading Frames (`find_orfs`, `reverse_complement`).
- **ORF**: A dataclass describing an Open Reading Frame with fields `start`, `end`, `frame`, `strand`, `length_bp`, `length_aa`, and `protein`.
- **Impact_Classifier**: The component that classifies the protein-level impact of a variant (`classify_snp_impact`, `classify_all`).
- **Conservation_Scorer**: The component that computes a conservation score from codon position, Grantham distance, and impact severity (`compute_conservation_score`).
- **Grantham_Distance**: The biochemical distance between two amino acids based on the Grantham (1974) matrix, ranging 0 to ~215.
- **ClinVar_Annotator**: The component that looks up a variant in the simulated ClinVar database (`lookup_clinvar`, `CLINVAR_DB`).
- **ClinVarEntry**: A dataclass describing a simulated ClinVar record with fields `variant_id`, `gene`, `hgvs_c`, `hgvs_p`, `clinical_significance`, `condition`, `review_status`, `allele_frequency`, `evidence_count`, and derived properties `severity_score` and `confidence_score`.
- **Region_Classifier**: The component that classifies the genomic region of a variant position (`classify_region`, `GeneAnnotation`).
- **GeneAnnotation**: A dataclass describing simplified gene structure with fields `gene_name`, `strand`, `total_length`, `exons`, `cds_start`, `cds_end`, and a derived `introns` property.
- **Pathogenicity_Scorer**: The component that combines conservation, ClinVar, region, and rarity signals into a single pathogenicity assessment (`compute_pathogenicity`).
- **PathogenicityAssessment**: A dataclass holding the integrated per-variant result with fields including `conservation_score`, `clinvar_entry`, `clinvar_severity`, `region_type`, `region_criticality`, `rarity_bonus`, `pathogenicity_score`, `confidence`, `recommendation`, and derived `risk_level`.
- **Clinical_Report_Generator**: The component that produces a structured clinical report string (`generate_clinical_report`).
- **Codon_Table**: A mapping from DNA codons to amino acids; supported tables are the Standard table and the Vertebrate Mitochondrial table.
- **Frontend_UI**: The React/TypeScript single-page application (`frontend/src`).
- **Frontend_Types**: The TypeScript type definitions (`frontend/src/types.ts`).
- **Risk_Level**: A categorical pathogenicity label: `HIGH RISK`, `MODERATE RISK`, `LOW RISK`, or `BENIGN`.
- **Confidence_Level**: A categorical confidence label: `HIGH`, `MEDIUM`, or `LOW`.
- **Random_Seed**: The integer seed used by the Pipeline to make synthetic dataset generation reproducible.

## Requirements

### Requirement 1: ORF Auto-Detection and Reverse Complement

**User Story:** As a researcher analyzing a sequence whose reading frame is unknown, I want the Pipeline to automatically detect the most likely Open Reading Frame across all six reading frames, so that impact classification uses a biologically plausible frame instead of assuming frame 0.

#### Acceptance Criteria

1. THE ORF_Detector SHALL provide a reverse-complement function that maps A↔T, C↔G, maps N to N, and reverses the sequence order.
2. THE ORF_Detector SHALL search all six reading frames, comprising the three forward-strand frames (0, 1, 2) and the three reverse-complement-strand frames (0, 1, 2).
3. WHEN scanning a frame, THE ORF_Detector SHALL begin each candidate ORF at an `ATG` start codon and extend the ORF until a stop codon defined by the active Codon_Table is reached or the sequence ends.
4. THE ORF_Detector SHALL exclude any candidate ORF whose translated protein length is below the configured minimum amino-acid length, which SHALL default to 10 amino acids when not specified.
5. WHERE an ORF is found on the reverse-complement strand, THE ORF_Detector SHALL report `start` and `end` coordinates mapped back to the original input sequence coordinate system.
6. THE ORF_Detector SHALL return the detected ORF records sorted by protein length in descending order with the longest ORF first, and WHERE two or more ORFs have equal protein length, THE ORF_Detector SHALL order them by strand (forward strand before reverse-complement strand), then by ascending frame number, then by ascending `start` coordinate, so that repeated runs on identical input produce identical ordering.
7. THE ORF_Detector SHALL populate each ORF record with `start`, `end`, `frame`, `strand`, `length_bp`, `length_aa`, and `protein` fields.
8. WHEN at least one ORF is detected, THE Pipeline SHALL use the `frame` and `strand` of the longest detected ORF as the reading frame and strand for impact classification and translation.
9. IF no ORF satisfies the minimum length, THEN THE Pipeline SHALL fall back to reading frame 0 on the forward strand.

### Requirement 2: Backward-Compatible Frame Selection

**User Story:** As an existing user of the application, I want the new automatic frame detection to be optional, so that my existing requests and reproducible runs continue to behave as before.

#### Acceptance Criteria

1. THE Pipeline_API SHALL accept a frame-selection mode on `POST /api/run` whose value is either `automatic` (ORF-based frame detection) or `manual` (a caller-supplied frame value).
2. WHERE the request specifies `manual` frame selection, THE Pipeline_API SHALL classify and translate using the supplied `frame` value (0, 1, or 2) on the forward strand, producing the same selected frame, strand, protein, and per-variant impact outputs as the current implementation.
3. WHERE the request does not specify a frame-selection mode, THE Pipeline_API SHALL default to `manual` mode with frame 0 on the forward strand, preserving the current contract for existing clients.
4. WHEN `automatic` frame detection is selected, THE Pipeline_API SHALL include the detected frame and strand in the response.
5. WHEN at least one ORF is detected, THE Pipeline_API SHALL include in the `POST /api/run` response a summary of the longest detected ORF comprising its `start`, `end`, `frame`, `strand`, `length_bp`, and `length_aa`.
6. IF `automatic` frame detection is selected and no ORF satisfies the minimum length, THEN THE Pipeline_API SHALL report frame 0 and the forward strand in the response and SHALL indicate that no ORF was detected.

### Requirement 3: Conservation Scoring

**User Story:** As a researcher assessing variant impact, I want each coding SNP to receive a conservation score, so that I can gauge how biochemically disruptive the change is likely to be.

#### Acceptance Criteria

1. THE Conservation_Scorer SHALL expose the Grantham distance matrix from Grantham (1974) and a lookup that is symmetric with respect to amino-acid pair order, returning identical Grantham distances for the pair (A, B) and the pair (B, A).
2. IF both amino acids in a lookup are identical, THEN THE Conservation_Scorer SHALL return a Grantham distance of 0, and this rule SHALL take precedence over the stop, unknown, and absent-pair rules.
3. IF the two amino acids in a lookup are not identical and either amino acid is a stop (`*`) or unknown (`X`), THEN THE Conservation_Scorer SHALL return a Grantham distance of 215.
4. IF an amino-acid pair in a lookup is not identical, contains no stop (`*`) or unknown (`X`) amino acid, and is absent from the Grantham matrix, THEN THE Conservation_Scorer SHALL return a default Grantham distance of 100.
5. THE Conservation_Scorer SHALL compute the codon-position component as 1.0 for codon positions 1 and 2, 0.3 for codon position 3 (wobble), and 0.5 when the codon position is not one of positions 1, 2, or 3 (undetermined).
6. THE Conservation_Scorer SHALL compute the Grantham component by dividing the Grantham distance by 215 and capping the result at 1.0.
7. THE Conservation_Scorer SHALL compute the severity component using the impact-severity mapping defined in the notebook (NONSENSE = 1.0, FRAMESHIFT = 1.0, START_LOST = 0.95, STOP_LOST = 0.85, MISSENSE = 0.7, INFRAME_INDEL = 0.5, INCOMPLETE_CODON = 0.3, UTR_OR_OUTOFFRAME = 0.2, SILENT = 0.1), and SHALL use a default severity component of 0.5 for any impact class not present in the mapping.
8. THE Conservation_Scorer SHALL compute the final conservation score as `0.30 × codon_position_component + 0.40 × Grantham_component + 0.30 × severity_component`, rounded to 4 decimal places.
9. THE Conservation_Scorer SHALL produce a conservation score within the inclusive range 0.0 to 1.0.
10. WHEN a coding SNP impact record is supplied, THE Conservation_Scorer SHALL compute a conservation score from the record's codon position, the Grantham distance between its reference and alternate amino acids, and its impact-severity class.

### Requirement 4: Simulated ClinVar Annotation

**User Story:** As a researcher reviewing detected variants, I want known variants to be matched against a simulated ClinVar database, so that I can see established clinical significance for demonstration cases such as the HBB sickle-cell mutation.

#### Acceptance Criteria

1. THE ClinVar_Annotator SHALL provide a simulated ClinVar database containing exactly five demonstration entries defined in the notebook: three for the HBB gene, one for the BRCA1 gene, and one for the TP53 gene.
2. THE ClinVar_Annotator SHALL key each database entry using the format `GENE:ref_codon_codonpos1based_alt_codon`, where the codon position is 1-based.
3. WHEN a coding SNP impact and a gene name are supplied, THE ClinVar_Annotator SHALL construct the lookup key from the gene name, reference codon, 1-based codon index, and alternate codon, and SHALL return the ClinVarEntry whose key matches exactly and case-sensitively.
4. WHERE no gene name is supplied to a lookup, THE ClinVar_Annotator SHALL use the default gene name `UNKNOWN` when constructing the lookup key.
5. IF the variant impact is one of UTR_OR_OUTOFFRAME, INCOMPLETE_CODON, FRAMESHIFT, or INFRAME_INDEL, THEN THE ClinVar_Annotator SHALL return no ClinVar match without constructing a lookup key.
6. WHEN no database entry matches the constructed key, THE ClinVar_Annotator SHALL return no ClinVar match, represented as an absent ClinVarEntry.
7. THE ClinVarEntry SHALL expose a `severity_score` property mapping clinical significance to a 0.0–1.0 value (Pathogenic = 1.0, Likely pathogenic = 0.85, VUS = 0.5, Likely benign = 0.15, Benign = 0.0), defaulting to 0.5 for unrecognized significance.
8. THE ClinVarEntry SHALL expose a `confidence_score` property mapping review status to a 0.0–1.0 value (practice guideline = 1.0, expert panel = 0.9, criteria provided multiple submitters = 0.8, criteria provided single submitter = 0.6, no assertion criteria provided = 0.3), defaulting to 0.3 for unrecognized review status.

### Requirement 5: Genomic Region Classification

**User Story:** As a researcher, I want each variant position classified by its genomic region, so that I can account for how location within a gene structure affects potential impact.

#### Acceptance Criteria

1. THE Region_Classifier SHALL accept a 0-based position and a GeneAnnotation describing `gene_name`, `strand`, `total_length`, `exons`, `cds_start`, and `cds_end`, where exon and coding coordinates are 0-based half-open intervals `[start, end)`.
2. THE GeneAnnotation SHALL derive intron intervals from the gaps between sorted exon intervals.
3. THE Region_Classifier SHALL evaluate region membership in the following precedence order: SPLICE_SITE first, then EXON_CODING / 5_UTR / 3_UTR, then INTRON, then PROMOTER / INTERGENIC, returning the first matching classification.
4. WHEN a position lies within 2 base pairs of an exon boundary (excluding the boundary position itself) and within 2 base pairs of an intron boundary, THE Region_Classifier SHALL classify the region as `SPLICE_SITE` with criticality 0.95.
5. WHEN a position lies within an exon interval and within the coding interval (`cds_start` ≤ position < `cds_end`), THE Region_Classifier SHALL classify the region as `EXON_CODING` with criticality 0.80.
6. WHEN a position lies within an exon interval and before the coding start (position < `cds_start`), THE Region_Classifier SHALL classify the region as `5_UTR` with criticality 0.40.
7. WHEN a position lies within an exon interval and at or after the coding end (position ≥ `cds_end`), THE Region_Classifier SHALL classify the region as `3_UTR` with criticality 0.30.
8. WHEN a position lies within an intron interval, THE Region_Classifier SHALL classify the region as `INTRON` with criticality 0.15.
9. WHEN a position lies outside all exon and intron intervals and before the coding start (position < `cds_start`), THE Region_Classifier SHALL classify the region as `PROMOTER` with criticality 0.35.
10. WHEN a position lies outside all exon and intron intervals and at or after the coding start (position ≥ `cds_start`), THE Region_Classifier SHALL classify the region as `INTERGENIC` with criticality 0.10.
11. THE Region_Classifier SHALL return, for every classified position, a region type that is one of `SPLICE_SITE`, `EXON_CODING`, `5_UTR`, `3_UTR`, `INTRON`, `PROMOTER`, or `INTERGENIC`, together with a criticality score in the inclusive range 0.0 to 1.0.

### Requirement 6: Integrated Pathogenicity Scoring

**User Story:** As a researcher, I want a single integrated pathogenicity score per variant that combines conservation, ClinVar, region, and rarity signals, so that I can prioritize variants for further review.

#### Acceptance Criteria

1. THE Pathogenicity_Scorer SHALL compute, for each variant, the conservation score, ClinVar severity, region type and criticality, and a rarity value, each bounded to the inclusive range 0.0 to 1.0.
2. WHEN a ClinVar entry is found, THE Pathogenicity_Scorer SHALL derive the rarity value from the entry's allele frequency as `1.0 - min(allele_frequency × 100, 1.0)`, bounded to the inclusive range 0.0 to 1.0.
3. IF no ClinVar entry is found, THEN THE Pathogenicity_Scorer SHALL set ClinVar severity to 0.5, ClinVar confidence to 0.0, and rarity to 0.5.
4. WHEN a ClinVar entry is found, THE Pathogenicity_Scorer SHALL use effective weights conservation 0.35, ClinVar 0.35, region 0.20, and rarity 0.10.
5. IF no ClinVar entry is found, THEN THE Pathogenicity_Scorer SHALL redistribute the ClinVar weight by adding 0.60 of it to the conservation weight, 0.30 of it to the region weight, and 0.10 of it to the rarity weight, and SHALL set the effective ClinVar weight to 0.0.
6. THE Pathogenicity_Scorer SHALL compute the pathogenicity score as the sum of each effective weight multiplied by its component (conservation score, ClinVar severity, region criticality, and rarity), clamp the result to the inclusive range 0.0 to 1.0, and round to 4 decimal places.
7. THE Pathogenicity_Scorer SHALL derive Risk_Level as `HIGH RISK` when the score is at least 0.8, `MODERATE RISK` when the score is at least 0.5 and below 0.8, `LOW RISK` when the score is at least 0.3 and below 0.5, and `BENIGN` when the score is below 0.3.
8. THE Pathogenicity_Scorer SHALL derive Confidence_Level as `HIGH` when a ClinVar entry is found with confidence score at least 0.8, `MEDIUM` when a ClinVar entry is found with confidence score at least 0.5 and below 0.8, and `LOW` otherwise, including when no ClinVar entry is found.
9. WHEN the pathogenicity score is at least 0.8, THE Pathogenicity_Scorer SHALL select a high-risk recommendation specific to the impact class, distinguishing the NONSENSE case, the MISSENSE case, and all other impact classes.
10. WHEN the pathogenicity score is below 0.8, THE Pathogenicity_Scorer SHALL select a recommendation by score band: a moderate-risk recommendation when the score is at least 0.5, a low-risk recommendation when the score is at least 0.3 and below 0.5, and a benign recommendation when the score is below 0.3.
11. THE Pathogenicity_Scorer SHALL populate a PathogenicityAssessment containing the conservation score, ClinVar entry (or absence), ClinVar severity, region type, region criticality, rarity value, pathogenicity score, confidence, and recommendation.

### Requirement 7: Alternative Codon Table Support

**User Story:** As a researcher analyzing mitochondrial sequences, I want to choose the vertebrate mitochondrial codon table, so that translation and impact classification reflect the correct genetic code.

#### Acceptance Criteria

1. THE Pipeline SHALL provide a Standard Codon_Table and a Vertebrate Mitochondrial Codon_Table, where the mitochondrial table reassigns AGA and AGG to stop, TGA to Trp (W), and ATA to Met (M).
2. THE Pipeline SHALL accept a Codon_Table selection parameter on its translation and impact-classification functions, defaulting to the Standard Codon_Table.
3. WHEN the Vertebrate Mitochondrial Codon_Table is selected, THE Impact_Classifier SHALL use the mitochondrial stop-codon set and amino-acid assignments for translation and impact classification.
4. WHEN the Vertebrate Mitochondrial Codon_Table is selected, THE ORF_Detector SHALL use the mitochondrial stop-codon set when delimiting ORFs.
5. THE Pipeline_API SHALL accept a codon-table selection parameter on `POST /api/run` and SHALL default to the Standard Codon_Table when the parameter is absent.
6. IF an unrecognized codon-table value is supplied, THEN THE Pipeline_API SHALL reject the request with a validation error identifying the invalid parameter.

### Requirement 8: Extended Pipeline Run Response

**User Story:** As a frontend developer, I want the `POST /api/run` response to include the new per-variant clinical fields and ORF metadata, so that I can render the extended analysis without additional requests.

#### Acceptance Criteria

1. THE Pipeline_API SHALL accept an optional gene-name parameter on `POST /api/run` and SHALL use a defined default gene name when the parameter is absent.
2. THE Pipeline_API SHALL include, for each detected variant in the `POST /api/run` response, the fields `conservation_score`, `grantham_distance`, `region_type`, `region_criticality`, `pathogenicity_score`, `risk_level`, `confidence`, and `recommendation`.
3. WHEN a variant matches a ClinVar entry, THE Pipeline_API SHALL include the ClinVar fields `variant_id`, `gene`, `hgvs_c`, `hgvs_p`, `clinical_significance`, `condition`, `review_status`, `allele_frequency`, and `evidence_count` for that variant.
4. WHEN a variant has no ClinVar match, THE Pipeline_API SHALL represent the ClinVar information for that variant as absent.
5. THE Pipeline_API SHALL retain all fields present in the current `POST /api/run` response so that existing clients continue to function.
6. THE Pipeline_API SHALL include ORF and frame metadata in the `POST /api/run` response as specified in Requirement 2.
7. WHILE the requested dataset is the synthetic dataset with a fixed Random_Seed, THE Pipeline_API SHALL produce identical extended results across repeated runs with identical parameters.

### Requirement 9: Clinical Report Generation

**User Story:** As a researcher, I want to generate a structured clinical report summarizing all assessed variants, so that I can review the findings in a single readable document.

#### Acceptance Criteria

1. THE Clinical_Report_Generator SHALL produce a report that includes the gene name, reference length, total number of variants analyzed, and a generation marker.
2. THE Clinical_Report_Generator SHALL include a risk summary that counts variants in each Risk_Level category (`HIGH RISK`, `MODERATE RISK`, `LOW RISK`, `BENIGN`).
3. THE Clinical_Report_Generator SHALL include the mean pathogenicity score and the maximum pathogenicity score across the assessed variants.
4. THE Clinical_Report_Generator SHALL include, for each variant, the 1-based position, base change, codon change with amino-acid names, impact class, region type, conservation score, pathogenicity score, Risk_Level, Confidence_Level, and recommendation.
5. WHEN a variant has a ClinVar match, THE Clinical_Report_Generator SHALL include the ClinVar identifier, clinical significance, condition, and evidence summary for that variant.
6. WHEN a variant has a missense change between two standard amino acids, THE Clinical_Report_Generator SHALL include the Grantham distance for that variant.
7. THE Pipeline_API SHALL expose an endpoint that returns the generated clinical report for a requested analysis.
8. THE generated clinical report SHALL include an educational, non-clinical-use disclaimer.

### Requirement 10: Frontend Type Definitions

**User Story:** As a frontend developer, I want the TypeScript types to model the extended response, so that the UI consumes the new fields with type safety.

#### Acceptance Criteria

1. THE Frontend_Types SHALL extend the `Variant` interface to include `conservation_score`, `grantham_distance`, `region_type`, `region_criticality`, `pathogenicity_score`, `risk_level`, `confidence`, and `recommendation`.
2. THE Frontend_Types SHALL define a ClinVar type containing `variant_id`, `gene`, `hgvs_c`, `hgvs_p`, `clinical_significance`, `condition`, `review_status`, `allele_frequency`, and `evidence_count`, and SHALL allow the ClinVar field on a variant to be absent.
3. THE Frontend_Types SHALL define an ORF type containing `start`, `end`, `frame`, `strand`, `length_bp`, `length_aa`, and `protein`.
4. THE Frontend_Types SHALL extend the `PipelineResult` interface to include the ORF and frame metadata and any new top-level fields returned by the Pipeline_API.
5. THE Frontend_Types SHALL extend the run-parameters type to include the optional frame-selection mode, codon-table selection, and gene-name parameters.

### Requirement 11: Frontend Display of Extended Analysis

**User Story:** As a user of the web application, I want to see the ORF detection, conservation, ClinVar, region, and pathogenicity results in the UI, so that I can interpret the extended analysis visually.

#### Acceptance Criteria

1. THE Frontend_UI SHALL display the detected ORF and selected reading frame, including the strand, when automatic frame detection is used.
2. THE Frontend_UI SHALL display, for each variant, the conservation score and the pathogenicity score.
3. THE Frontend_UI SHALL display the Risk_Level for each variant using a visual indicator that distinguishes the four risk categories.
4. WHEN a variant has a ClinVar match, THE Frontend_UI SHALL display the ClinVar identifier, clinical significance, and condition for that variant.
5. WHEN a variant has no ClinVar match, THE Frontend_UI SHALL indicate that no ClinVar record was found for that variant.
6. THE Frontend_UI SHALL display the region type and criticality for each variant.
7. THE Frontend_UI SHALL provide a clinical report view that presents the structured report described in Requirement 9.
8. THE Frontend_UI SHALL provide controls for selecting the frame-selection mode, the codon table, and the gene name, consistent with the parameters accepted by the Pipeline_API.
9. WHILE the application has not yet received an extended analysis result, THE Frontend_UI SHALL render without errors and SHALL not display empty extended sections as populated data.

### Requirement 12: Educational Framing and Disclaimers

**User Story:** As a course instructor and as a user, I want the pathogenicity and clinical-report features to be clearly framed as educational and not for clinical use, so that the outputs are not mistaken for medical advice.

#### Acceptance Criteria

1. THE Frontend_UI SHALL display an "educational use only, not for clinical decision-making" disclaimer in proximity to the pathogenicity scores and the clinical report view.
2. THE Clinical_Report_Generator SHALL embed an educational, non-clinical-use disclaimer within the generated report.
3. WHERE the optional AI guide is used with extended results, THE Pipeline_API SHALL continue to instruct the AI assistant to avoid clinical diagnoses and clinical claims.
4. THE Frontend_UI SHALL describe the ClinVar annotation as a simulated demonstration database rather than a live ClinVar query.

### Requirement 13: Input Validation and Error Handling

**User Story:** As a user submitting analysis requests, I want clear errors when my extended-analysis inputs are invalid, so that I can correct my request.

#### Acceptance Criteria

1. IF the request selects manual frame mode with a frame value outside 0–2, THEN THE Pipeline_API SHALL reject the request with a validation error identifying the invalid frame.
2. IF the request supplies an unrecognized codon-table value, THEN THE Pipeline_API SHALL reject the request with a validation error identifying the invalid codon-table parameter.
3. IF the clinical-report endpoint is invoked with no assessed variants available, THEN THE Pipeline_API SHALL return a report that states no variants were assessed rather than failing.
4. WHEN any extended-analysis request fails validation, THE Pipeline_API SHALL return an error payload using the existing error structure of code and message.
