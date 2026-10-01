# MediTwin: AI-Powered Personalized Health Intelligence Platform

[![React](https://img.shields.io/badge/React-19.2-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-8.2-646CFF?logo=vite&logoColor=white)](https://vitejs.dev/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-4.3-06B6D4?logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)
[![Node.js](https://img.shields.io/badge/Node.js-18+-339933?logo=node.js&logoColor=white)](https://nodejs.org/)
[![Express](https://img.shields.io/badge/Express-4.21-000000?logo=express&logoColor=white)](https://expressjs.com/)
[![MongoDB](https://img.shields.io/badge/MongoDB-Mongoose%208-47A248?logo=mongodb&logoColor=white)](https://www.mongodb.com/)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![XGBoost](https://img.shields.io/badge/XGBoost-2.0+-FF6600?logo=xgboost&logoColor=white)](https://xgboost.readthedocs.io/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0+-EE4C2C?logo=pytorch&logoColor=white)](https://pytorch.org/)

---

## 📋 Executive Overview

**MediTwin** is a multi-modal clinical decision support system (CDSS) that delivers end-to-end personalized healthcare intelligence. It bridges longitudinal electronic health records (EHR), free-text patient symptom reasoning, and evidence-based clinical practice guidelines into a single role-based clinical workflow for **patients, doctors, and administrators**.

### The Healthcare Challenge
1. **Fragmented Patient Trajectories:** Traditional tools treat lab reports and acute symptoms in isolation.
2. **Delayed Intervention:** Acute deterioration events often occur without timely risk forecasting.
3. **Information Overload for Clinicians:** Physicians must cross-reference lab histories, differential diagnoses, and contraindication guidelines under strict time constraints.

### The MediTwin Solution
MediTwin synthesizes three specialized AI engines into a unified clinical pipeline:
- **Module 1 — XGBoost Acute Risk Engine:** Analyzes longitudinal lab/vital trajectories over 90- and 365-day windows to forecast 90-day acute-event probability with interpretable SHAP feature contributions.
- **Module 2 — DDXPlus Differential Diagnosis Engine:** Uses a PyTorch neural classifier with NLP symptom normalization to rank 49 pathologies from free text or symptom checklists.
- **Module 3 — Clinical Rules & Guideline Engine:** Fuses Modules 1 and 2, checks live drug references (RxNorm + OpenFDA), evaluates contraindications, and produces prioritized, personalized treatment and surveillance protocols.

---

## ✨ Key Features

- **Role-based access** — Patient, Doctor, and Admin experiences with JWT auth and Google OAuth sign-in.
- **PDF lab-report ingestion** — Upload a lab PDF; MediTwin extracts observations (PyMuPDF) and lets you review/confirm before analysis.
- **Manual health entry** — Enter biomarkers directly when no report is available.
- **90-day acute-risk forecasting** with top risk-increasing / risk-reducing factors.
- **Symptom-to-diagnosis** differential ranking across 49 pathologies.
- **Personalized treatment recommendations** with drug lookups and safety flags.
- **Doctor workflow** — ID-verified doctors view patient details and submit clinical feedback.
- **Admin console** — Review and verify/reject doctor applications; platform statistics.
- **Consolidated clinical reports**, timeline, dashboard KPIs, and surveillance alerts.

---

## 🏛️ System Architecture

The React SPA talks to a single Express API. The backend persists everything in MongoDB and
invokes the three Python AI engines **directly as child processes** (`child_process.spawnSync`) —
no separate ML servers are required to run the app. (Standalone FastAPI entrypoints, `api.py`,
exist per module as an optional alternative, but are not used by the default flow.)

```
                        +-----------------------------------------------+
                        |            PATIENT / DOCTOR / ADMIN           |
                        |     Web SPA (React 19 + Vite + Tailwind)      |
                        +-----------------------+-----------------------+
                                                | REST API / JWT + Google OAuth
                                                v
                        +-----------------------------------------------+
                        |          EXPRESS.JS BACKEND (Node.js)         |
                        |  Auth / Roles  •  Health  •  Disease          |
                        |  Treatment  •  Reports  •  Doctor  •  Admin   |
                        |  MongoDB (Mongoose)  •  PDF ingest (Multer)   |
                        +---+-----------------+-----------------+-------+
                            | spawnSync        | spawnSync       | spawnSync
                            v                  v                 v
          +-----------------+--+   +-----------+--------+   +-----+----------------+
          |     MODULE 1       |   |     MODULE 2       |   |     MODULE 3         |
          | predict_risk.py    |   | run_inference.py   |   | run_recommend.py     |
          | XGBoost + SHAP     |   | PyTorch MLP + NLP  |   | Rules + Drug Lookups |
          | 29 types→348 feats |   | 223 evidence atoms |   | RxNorm / OpenFDA     |
          | 90-day risk        |   | 49 pathologies     |   | Safety flags         |
          +-----------------+--+   +-----------+--------+   +-----+----------------+
                            |                  |                 |
                            +------------------+-----------------+
                                               v
                        +-----------------------------------------------+
                        |            MONGODB REPOSITORY LAYER           |
                        | Users • HealthRecords • RiskPredictions       |
                        | SymptomAnalyses • Treatments • DoctorFeedback |
                        | Activity logs                                 |
                        +-----------------------------------------------+
```

> **PDF ingest path:** `POST /api/health/upload-pdf` → `extract_pdf_report.py` (PyMuPDF) →
> patient reviews extracted values → `POST /api/health/confirm-extracted` → Module 1 → Module 3.

---

## 🧩 AI Modules

### 🛡️ Module 1 — Future Acute-Event Risk Prediction

Computes the probability of an **acute hospital encounter** (ER / urgent care) within a
**90-day forward horizon**.

- **Observations (29):** vitals/anthropometrics, metabolic & renal panel, lipid profile,
  electrolytes & hematology.
- **Feature engineering (348):** for each of the 29 observations, 12 temporal statistics over
  90- and 365-day windows — `latest`, `mean_365d`, `min/max_365d`, `std_365d`, `mean_90d`,
  `slope_365d`, `slope_90d`, `absolute_change_365d`, `relative_change_365d`, `days_since_latest`,
  and a `missing` indicator. (29 × 12 = 348 features.)
- **Model:** `XGBClassifier` with Tree-SHAP explainability. Patient-grouped split to prevent
  temporal leakage. `scale_pos_weight ≈ 1.739` for class imbalance.
- **Trained on:** 95,890 snapshots / 11,981 patients (76,747 train rows / 9,584 patients,
  19,143 test rows / 2,397 patients).
- **Performance:** ROC-AUC **0.8162**, PR-AUC **0.7582**, specificity **91.2%** and precision
  **78.4%** at threshold 0.50; F1 **0.661** at the recommended operating threshold **0.45**.
- **Runtime model files (committed):** `models/xgboost_model.json`, `xgboost_feature_names.json`,
  `xgboost_feature_mapping.json`, `feature_imputer.pkl`, `xgboost_metrics.json`.
- **Entrypoint:** `predict_risk.py <health_record.json>` → writes `outputs/<patient>/prediction_report.json`.

### 🧠 Module 2 — Symptom-to-Disease Differential Diagnosis

Converts free text or symptom checklists into a ranked differential across **49 pathologies**.

- **Evidence ontology:** DDXPlus — **223 evidence codes** (208 binary symptoms + 15 categorical/
  location/intensity attributes).
- **NLP matching pipeline:** rule-based alias matching (`mappings/symptom_aliases.json`), fuzzy
  matching (`rapidfuzz`), phonetic/typo tolerance, negation detection ("denies fever"), and a
  value extractor for pain location, radiation, intensity (1–10), and onset.
- **Model:** PyTorch MLP (dropout + batch norm, softmax over 49 classes) over a multi-hot evidence
  + demographics vector. ~99.7% top-k validation accuracy.
- **Runtime files (committed):** `runs/checkpoints/best_model.pt`, plus
  `module2_data_clean/{evidence_vocab,id_to_condition,preprocessing_metadata,evidence_graph}.json`.
- **Entrypoint:** `run_inference.py --text "..."` (or `--symptoms ...`) → JSON differential.

### 💊 Module 3 — Multimodal Clinical Decision Support

Fuses Module 2 diagnoses with Module 1 biomarker trajectories to produce individualized,
prioritized recommendations.

- **Scoring:** `Score = w1·P(disease) + w2·relevance + w3·severity + w4·acute_risk − w5·safety_penalty − w6·uncertainty_penalty`.
- **Drug knowledge:** RxNorm (NLM) normalization + OpenFDA label warnings, with a local
  `cache/drug_information_cache.json` fallback for offline/air-gapped use.
- **Entrypoint:** `run_recommend.py` consuming Module 1 + Module 2 outputs → treatment plan JSON.

---

## 💻 Tech Stack

**Frontend** — React 19.2, Vite 8.2, Tailwind CSS 4.3, React Router DOM 7, Recharts 3, Lucide
React, Axios.

**Backend** — Node.js 18+, Express 4.21, MongoDB + Mongoose 8, `jsonwebtoken` + `bcryptjs`,
`multer` (uploads), `nanoid` (patient IDs), `axios`, `dotenv`. Python engines are invoked via
Node `child_process.spawnSync`.

**Machine Learning (Python 3.10–3.12)** — XGBoost, PyTorch, scikit-learn, pandas, NumPy,
Matplotlib, RapidFuzz, spaCy, joblib, PyMuPDF. Optional API mode: FastAPI + Uvicorn + Pydantic.

---

## 📂 Project Structure

```
MediTwin/
├── backend/                     # Node.js + Express API (port 5000)
│   ├── config/                  # db.js, seedAdmin.js
│   ├── controllers/             # auth, dashboard, disease, health, report,
│   │                            #   treatment, doctor, externalDoctor, admin
│   ├── middleware/              # authMiddleware (protect/requireDoctor/requireAdmin), doctorUpload
│   ├── models/                  # User, HealthRecord, RiskPrediction, SymptomAnalysis,
│   │                            #   TreatmentRecommendation, DoctorFeedback, Activity
│   ├── routes/                  # auth, health, disease, treatment, dashboard,
│   │                            #   reports, doctor, admin, externalDoctor
│   ├── services/                # module1/2/3Service.js (spawnSync), pdfExtractorService.js
│   ├── uploads/                 # doctor-ID uploads (git-ignored, .gitkeep tracked)
│   ├── server.js                # App entry point
│   └── .env.example             # Backend env template
│
├── frontend/                    # React 19 + Vite + Tailwind SPA (port 5173)
│   ├── src/
│   │   ├── components/          # Sidebar, RiskGauge, ManualHealthForm, PdfReviewModal,
│   │   │                        #   ProtectedLayout, GoogleAuthButton
│   │   ├── context/             # AuthContext, ThemeContext, DiseaseJobContext
│   │   ├── lib/                 # api.js (Axios client + interceptors)
│   │   ├── pages/               # Dashboard, Health, Disease, Treatment, Reports, Timeline,
│   │   │                        #   Alerts, Profile, Login, Signup, FindDoctor,
│   │   │                        #   DoctorDashboard, DoctorStatus, AdminDashboard
│   │   ├── App.jsx  main.jsx  index.css
│   │   └── vite.config.js
│   └── .env.example             # Frontend env template
│
├── Module_1/                    # Future Risk Engine (XGBoost)
│   ├── models/                  # xgboost_model.json + feature maps (committed)
│   ├── predict_risk.py          # CLI runner called by backend
│   ├── extract_pdf_report.py    # PDF lab-report extraction (PyMuPDF)
│   ├── feature_engine.py  train_model.py  train_xgboost.py  evaluate_model.py  api.py  …
│   └── sample_patient.json  sample_lab_report.pdf
│
├── Module_2/                    # Differential Diagnosis Engine (PyTorch)
│   ├── inference/               # pipeline, matchers, conversation engine, value extractor
│   ├── mappings/                # DDXPlus symptom alias dictionaries
│   ├── module2_data_clean/      # vocab/mapping JSONs committed; tensor splits git-ignored
│   ├── runs/checkpoints/        # best_model.pt (committed)
│   ├── run_inference.py  train.py  model.py  dataset.py  data_preprocessing.py  api.py  …
│   └── README.md
│
├── Module_3/                    # Clinical Decision Support Engine
│   ├── cache/                   # offline RxNorm/OpenFDA drug cache
│   ├── run_recommend.py  module3_engine.py  drug_api_client.py  report_generator.py  api.py
│   ├── clinical_thresholds.json  treatment_knowledge.json  requirements.txt
│   └── README.md
│
├── start.ps1                    # One-click Windows startup (backend + frontend)
├── .gitignore
└── README.md
```

---

## 📦 What's in the Repo (and what isn't)

To keep the repository lean while remaining runnable, **only the model artifacts the app loads at
inference time are committed**. Large, regenerable training assets are excluded via `.gitignore`:

**Committed (app runs out-of-the-box):** all source code; `Module_1/models/xgboost_model.json`
+ feature maps; `Module_2/runs/checkpoints/best_model.pt` + vocab/mapping JSONs;
`Module_3/cache/drug_information_cache.json`; sample inputs.

**Ignored (regenerate locally if you want to retrain):**
- `Module_1/data/`, `Module_1/outputs/`, `Module_1/evaluation_results/` — training data & eval dumps.
- `Module_1/models/baseline_random_forest.pkl` — 81 MB baseline, not used at inference.
- `Module_2/module2_data_clean/{train,validation,test}/` — tokenized tensors (incl. files >100 MB
  that GitHub rejects).
- `Module_2/runs/leakage_audit/`, `Module_2/runs/checkpoints/last_model.pt`.
- All `.env` files, `node_modules/`, build output, `__pycache__/`, and `backend/uploads/*` (PII).

To regenerate training data/models: Module 1 → `prepare_data.py` → `generate_labels.py` →
`build_training_dataset.py` → `train_xgboost.py`; Module 2 → `data_preprocessing.py` → `train.py`.

---

## ⚙️ Installation & Setup

### 1. Prerequisites
- **Node.js** 18+
- **Python** 3.10 / 3.11 / 3.12 with `pip`
- **MongoDB** running at `mongodb://localhost:27017` (or a MongoDB Atlas URI)

### 2. Python ML dependencies
```bash
pip install xgboost torch pandas numpy scikit-learn matplotlib rapidfuzz spacy joblib pymupdf

# Optional: spaCy English model for symptom matching
python -m spacy download en_core_web_sm

# Optional: only if running the standalone FastAPI module servers
pip install fastapi uvicorn pydantic
```

### 3. Backend
```bash
cd backend
npm install
cp .env.example .env     # then edit .env with your real values
```

Key `.env` variables: `MONGO_URI`, `JWT_SECRET`, `PORT` (5000), `CLIENT_ORIGIN`
(http://localhost:5173), `PYTHON_EXEC` (`py` on Windows, `python3` on macOS/Linux),
`ADMIN_EMAIL` / `ADMIN_PASSWORD` / `ADMIN_NAME` (seeded on first boot), and optional
`GOOGLE_CLIENT_ID`.

### 4. Frontend
```bash
cd ../frontend
npm install
cp .env.example .env     # set VITE_GOOGLE_CLIENT_ID if using Google sign-in
```

### 5. Running the App

**Option A — One-click (Windows PowerShell), from the project root:**
```powershell
.\start.ps1
```
Frees ports 5000/5173, starts the backend and the Vite dev server, and opens the browser.

**Option B — Manual (two terminals):**
```bash
# Terminal 1
cd backend && node server.js        # or: npm run dev  (nodemon)
```
```bash
# Terminal 2
cd frontend && npm run dev
```
Backend health check: `http://localhost:5000/api/ping` · Frontend: `http://localhost:5173`

---

## 📡 REST API

All protected routes require an `Authorization: Bearer <JWT>` header.

### Auth — `/api/auth`
- `POST /signup` — Register (patients, or doctors with an `idDocument` upload). Issues a unique patient ID.
- `POST /login` — Authenticate; returns a JWT.
- `POST /google` — Google OAuth sign-in.
- `GET /me` — Current user profile.

### Health / Risk — `/api/health`
- `POST /upload-pdf` — Upload a lab-report PDF (≤25 MB); extracts observations for review.
- `POST /confirm-extracted` — Confirm reviewed values → triggers Module 1 (+ Module 3).
- `POST /manual-entry` — Submit biomarkers manually.
- `POST /upload` — Upload a structured health-record JSON.
- `GET /risk-latest` · `GET /risk-history` · `GET /records`

### Disease — `/api/disease`
- `POST /predict` — `inputText` and/or `symptoms[]` → Module 2 differential (+ Module 3).
- `GET /latest` · `GET /history`

### Treatment — `/api/treatment`
- `POST /generate` — Re-run Module 3 over stored patient data.
- `GET /latest` · `GET /history`

### Reports & Dashboard — `/api/reports`, `/api/dashboard`
- `GET /reports/full` — Consolidated multi-modal clinical report.
- `GET /reports/history` · `GET /dashboard` — KPIs, alerts, biomarker findings, activity.

### Doctor — `/api/doctor` *(verified doctors only)*
- `GET /patient/:patientId` · `POST /feedback` · `GET /recent-patients`

### Admin — `/api/admin` *(admin only)*
- `GET /stats` · `GET /doctors` · `POST /doctors/:id/verify` · `POST /doctors/:id/reject` · `GET /patients`

### Public Doctors — `/api/public-doctors`
- `GET /` · `GET /filters` · `GET /:id` — Browse/filter the public doctor directory.

---

## 👥 Roles & Access
- **Patient** — Default role on signup. Health input, diagnosis, treatment, reports, find doctors.
- **Doctor** — Registers with an ID document; access unlocks after **admin verification**.
- **Admin** — Seeded on first boot from `.env`; verifies doctors and views platform stats.

---

## 🛡️ Medical Disclaimer

> **IMPORTANT:** MediTwin is an academic and research clinical-decision-support platform. Its risk
> calculations, differential diagnoses, and treatment recommendations are intended to assist
> healthcare professionals and educate patients. **They are not a medical diagnosis, prescription,
> or definitive clinical directive.** All plans must be verified by a licensed physician before
> clinical use.
