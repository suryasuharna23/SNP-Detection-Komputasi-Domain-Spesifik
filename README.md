# SNP Detection Pipeline

Tugas mata kuliah IF3211 - Komputasi Domain Spesifik, Institut Teknologi Bandung.

Pipeline Python untuk mendeteksi Single-Nucleotide Polymorphism (SNP) pada sekuens DNA menggunakan global alignment Needleman-Wunsch, dilengkapi web app interaktif dan generator laporan LaTeX.

## Arsitektur

```text
backend/   FastAPI + pipeline bioinformatika   -> port 8000
frontend/  React + TypeScript + Tailwind       -> port 5173 dev, port 8080 prod-like
app.py     Streamlit standalone alternatif
snp.py     CLI lintas platform untuk install, app, smoke, report, dan ci
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

## Generate Laporan LaTeX

```bash
python snp.py report --dataset hbb
python snp.py report --dataset synthetic --seq-length 300 --n-snps 12 --seed 42 --csv
python snp.py report --dataset custom --ref ATGCGTTAA --sample ATGCGTTAA --no-pdf
```

Output ditulis ke `reports/`.

- File `.tex` selalu dibuat.
- File `.pdf` dibuat hanya jika `latexmk`, `xelatex`, atau `pdflatex` tersedia.
- Gunakan `--no-pdf` untuk memaksa output `.tex` saja.
- Gunakan `--csv` untuk menulis CSV varian di samping laporan.

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

Konfigurasi environment opsional:

```env
SNP_CORS_ORIGINS=http://127.0.0.1:8080,http://localhost:8080
SNP_MAX_SEQUENCE_LENGTH=5000
SNP_MAX_SENSITIVITY_RUNS=150
VITE_API_BASE_URL=http://127.0.0.1:8000/api
```

Untuk deployment produksi terpisah di server sungguhan, jalankan backend sebagai proses Python terkelola dan sajikan `frontend/dist` melalui static host apa pun. Build frontend dengan `VITE_API_BASE_URL` yang mengarah ke backend publik.

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
| POST | `/api/sensitivity` | Eksperimen sensitivitas |

## Fitur

- Dataset sintetik, HBB sickle-cell, dan custom.
- Alignment viewer dengan status match, mismatch, dan gap.
- Deteksi SNP, insersi, dan delesi.
- Klasifikasi dampak: silent, missense, nonsense, stop lost, start lost, frameshift, in-frame indel.
- Insight otomatis, tabel varian, CSV export, charts, dan perbandingan protein.
- Eksperimen sensitivitas precision, recall, dan F1 terhadap densitas SNP.
- Generator laporan LaTeX melalui `snp.py report`.

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
