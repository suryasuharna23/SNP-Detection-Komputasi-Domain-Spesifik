# SNP Detection Pipeline

Tugas mata kuliah IF3211 - Komputasi Domain Spesifik, Institut Teknologi Bandung.

Pipeline Python untuk mendeteksi Single-Nucleotide Polymorphism (SNP) pada sekuens DNA menggunakan global alignment Needleman-Wunsch, dilengkapi web app.

## Tim

| Nama | NIM |
| --- | --- |
| Surya Suharna | 18223075 |
| Muhammad Faiz Alfikrona | 18223009 |
| Ni Made Sekar Jelita P. | 18223101 |

## Arsitektur

```text
backend/   FastAPI + pipeline bioinformatika   -> port 8000
frontend/  React + TypeScript + Tailwind       -> port 5173 dev, port 8080 prod-like
notebook/  Jupyter Notebook pipeline SNP detection (snp_detection_pipeline_extended.ipynb)
app.py     Streamlit standalone alternatif
snp.py     CLI lintas platform untuk install, app, smoke, report, dan ci
doc/       Laporan dan dokumentasi proyek
slides/    Slide presentasi
```

## Quick Start Demo

```bash
python snp.py install
python snp.py app
```

Buka:

- App: http://localhost:5173
- API docs: http://localhost:8000/docs

`python snp.py app` hanya menandai app siap setelah backend `/api/health` dan frontend sudah bisa diakses.

## Pemeriksaan Dan Smoke Test

```bash
python snp.py check
python snp.py smoke
python snp.py ci
```

- `check` memeriksa Python, npm, dependency backend, dependency frontend, dan LaTeX engine opsional.
- `smoke` menjalankan API smoke test terhadap backend yang sedang hidup, lalu membuat laporan `.tex`.
- `ci` menjalankan compile check Python, report generation, frontend type-check, dan frontend production build.

Jika backend berjalan di URL lain:

```bash
python snp.py smoke --backend-url http://127.0.0.1:8000 --frontend-url http://127.0.0.1:5173
```

## Production-Like Lokal

```bash
python snp.py prod
```

Default:

- Frontend: http://localhost:8080
- Backend: http://localhost:8000

`prod` menjalankan dua service terpisah secara lokal:

- Backend FastAPI tanpa reload.
- Frontend dari hasil build `frontend/dist`, disajikan oleh static server Python.
- Readiness check untuk kedua service sebelum URL ditandai siap.

Perintah terkait:

```bash
# Build frontend produksi saja
python snp.py build

# Serve frontend/dist saja
python snp.py serve-frontend

# Smoke test stack production-like
python snp.py smoke --backend-url http://127.0.0.1:8000 --frontend-url http://127.0.0.1:8080
```

## Manual Development

Backend:

```bash
cd backend
python -m uvicorn main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm run dev
```

Frontend checks:

```bash
cd frontend
npm run check
npm run build
```

Streamlit alternatif:

```bash
pip install streamlit biopython pandas numpy plotly
streamlit run app.py
```

## API Endpoints

| Method | Path | Deskripsi |
| --- | --- | --- |
| GET | `/api/health` | Status server dan limit runtime |
| GET | `/api/presets` | Sekuens HBB wildtype dan sickle |
| POST | `/api/run` | Jalankan pipeline SNP |
| POST | `/api/ai/guide` | Panduan hasil berbasis Gemini |
| POST | `/api/sensitivity` | Eksperimen sensitivitas |
| POST | `/api/clinical` | Analisis klinis extended per varian |
| GET | `/api/clinvar/{rsid}` | Lookup data ClinVar nyata via NCBI E-utilities |

## Fitur

- Dataset sintetik, HBB sickle-cell, dan custom.
- Alignment viewer dengan status match, mismatch, dan gap.
- Deteksi SNP, insersi, dan delesi.
- Klasifikasi dampak: silent, missense, nonsense, stop lost, start lost, frameshift, in-frame indel.
- Insight otomatis, panduan AI Gemini opsional, tabel varian, CSV export, charts, dan perbandingan protein.
- Eksperimen sensitivitas precision, recall, dan F1 terhadap densitas SNP.
- Analisis klinis extended: lookup ClinVar nyata via NCBI E-utilities, skor patogenisitas, anotasi fenotip, dan rekomendasi klinis berbasis AI.
- Jupyter Notebook pipeline lengkap di `notebook/snp_detection_pipeline_extended.ipynb` untuk eksplorasi dan reproduksi eksperimen.
- Web app interaktif (React + TypeScript + Tailwind) di direktori `frontend/`.

## Test Cases Custom Dataset, Frame 0

Silent:

```text
Ref: ATGAAAGCCTTT
Smp: ATGAAGGCTTTC
Expected: 3 SNP, semua SILENT, protein MKAF tidak berubah
```

Nonsense:

```text
Ref: ATGGAAGTGCAA
Smp: ATGTAAGTGCAA
Expected: 1 SNP pos 4 (G -> T), GAA -> TAA, Glu -> Stop, NONSENSE
```

Stop lost:

```text
Ref: ATGCAATAACGT
Smp: ATGCAACAACGT
Expected: 1 SNP pos 7 (T -> C), TAA -> CAA, Stop -> Gln, STOP_LOST
```

Missense + silent:

```text
Ref: ATGGCAGATCCC
Smp: ATGGTAGATCCG
Expected: 2 SNP, pos 5 MISSENSE (Ala -> Val), pos 12 SILENT (Pro -> Pro)
```

Identik:

```text
Ref: ATGCGTTAA
Smp: ATGCGTTAA
Expected: 0 varian
```

## Referensi

- Needleman & Wunsch (1970). Journal of Molecular Biology 48(3), 443-453.
- Cock et al. (2009). Biopython. Bioinformatics 25(11).
- Ingram (1957). Sickle cell. Nature 180, 326-328.
