# SNP Detection Pipeline

Tugas mata kuliah IF3211 — Komputasi Domain Spesifik, Institut Teknologi Bandung.

Pipeline Python untuk mendeteksi Single-Nucleotide Polymorphism (SNP) pada sekuens DNA menggunakan global alignment Needleman–Wunsch, dilengkapi web app interaktif.

---

## Arsitektur

```
backend/   FastAPI (Python) — pipeline + REST API  → port 8000
frontend/  React + TypeScript + Tailwind           → port 5173
app.py     Streamlit (alternatif, standalone)
```

---

## Cara Menjalankan

### Keduanya sekaligus (PowerShell)

```powershell
cd SNP-Detection-Komputasi-Domain-Spesifik
powershell -ExecutionPolicy Bypass -File .\start.ps1
```

Buka http://localhost:5173

### Manual (2 terminal)

**Terminal 1 — Backend**
```powershell
cd backend
python -m uvicorn main:app --reload --port 8000
```

**Terminal 2 — Frontend**
```powershell
cd frontend
npm run dev
```

### Streamlit (alternatif, satu terminal)
```powershell
pip install streamlit biopython pandas numpy plotly
streamlit run app.py
```

---

## Install Dependencies

```powershell
# Backend
pip install fastapi uvicorn biopython numpy pydantic

# Frontend
cd frontend
npm install
```

---

## Fitur

- **3 Dataset**: Sintetik (panjang/jumlah SNP/GC/seed dapat diatur), HBB Sickle-Cell, Custom (input manual)
- **Alignment Viewer**: setiap basa ditampilkan sebagai card kecil, warna per basa (A/T/G/C) dan per status (match/mismatch/gap)
- **Deteksi Varian**: SNP, Insersi, Delesi
- **Klasifikasi Dampak**: Silent, Missense, Nonsense, Stop Lost, Start Lost, Frameshift
- **Insight otomatis**: distribusi dampak, temuan utama, dan kesimpulan naratif setelah pipeline dijalankan
- **Tabel Varian**: sortable, filter by dampak/tipe, download CSV
- **Charts**: track posisi SNP, distribusi dampak, matriks substitusi REF→ALT
- **Perbandingan Protein**: highlight residu yang berubah
- **Eksperimen Sensitivitas**: precision/recall/F1 vs densitas SNP, dengan zoom drag + tombol

---

## API Endpoints

| Method | Path | Deskripsi |
|--------|------|-----------|
| GET | `/api/health` | Status server |
| GET | `/api/presets` | Sekuens HBB wildtype & sickle |
| POST | `/api/run` | Jalankan pipeline |
| POST | `/api/sensitivity` | Eksperimen sensitivitas |

---

## Parameter Alignment

| Parameter | Nilai |
|-----------|-------|
| Match | +2 |
| Mismatch | −1 |
| Gap open | −2 |
| Gap extend | −1 |

---

## Test Cases (Custom Dataset, Frame 0)

### 1. Silent — protein tidak berubah
```
Ref:  ATGAAAGCCTTT
Smp:  ATGAAGGCTTTC
```
Expected: 3 SNP, semua SILENT, protein `MKAF` tidak berubah

### 2. Nonsense — kodon stop prematur
```
Ref:  ATGGAAGTGCAA
Smp:  ATGTAAGTGCAA
```
Expected: 1 SNP pos 4 (G→T), GAA→TAA, Glu→Stop, NONSENSE

### 3. Stop Lost — protein memanjang
```
Ref:  ATGCAATAACGT
Smp:  ATGCAACAACGT
```
Expected: 1 SNP pos 7 (T→C), TAA→CAA, Stop→Gln, STOP_LOST

### 4. Missense + Silent (campuran)
```
Ref:  ATGGCAGATCCC
Smp:  ATGGTAGATCCG
```
Expected: 2 SNP — pos 5 MISSENSE (Ala→Val), pos 12 SILENT (Pro→Pro)

### 5. Identik — tidak ada varian
```
Ref:  ATGCGTTAA
Smp:  ATGCGTTAA
```
Expected: 0 varian

---

## Struktur Proyek

```
SNP-Detection-Komputasi-Domain-Spesifik/
├── app.py
├── requirements.txt
├── start.ps1
├── .gitignore
├── README.md
├── backend/
│   ├── main.py
│   ├── pipeline.py
│   └── requirements.txt
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── src/
│       ├── App.tsx
│       ├── api.ts
│       ├── types.ts
│       └── components/
│           ├── InsightsPanel.tsx
│           ├── AlignmentViewer.tsx
│           ├── SNPTrack.tsx
│           ├── ImpactChart.tsx
│           ├── SubstitutionMatrix.tsx
│           ├── SensitivityChart.tsx
│           ├── VariantTable.tsx
│           ├── ImpactBadge.tsx
│           └── InputPanel.tsx
├── notebook/
│   └── snp_detection_pipeline.ipynb
└── doc/
    └── Laporan_SNP_Detection.docx (1).pdf
```

---

## Referensi

- Needleman & Wunsch (1970). *J. Mol. Biol.* 48(3), 443–453
- Cock et al. (2009). Biopython. *Bioinformatics* 25(11)
- Ingram (1957). Sickle cell. *Nature* 180, 326–328
