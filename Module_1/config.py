from pathlib import Path


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
ARTIFACTS_DIR = DATA_DIR / "artifacts"
MODELS_DIR = BASE_DIR / "models"

OBSERVATIONS_CSV = RAW_DATA_DIR / "observations.csv"
ENCOUNTERS_CSV = RAW_DATA_DIR / "encounters.csv"

TRAINING_DATASET = PROCESSED_DATA_DIR / "observation_training_dataset.parquet"

MODEL_FILE = MODELS_DIR / "acute_event_model.json"
CALIBRATOR_FILE = MODELS_DIR / "calibrator.pkl"
MODEL_INFO_FILE = MODELS_DIR / "model_info.json"
FEATURE_NAMES_FILE = MODELS_DIR / "feature_names.json"


# ============================================================
# FEATURE WINDOWS
# ============================================================

# Used ONLY by the ML feature engine.
FEATURE_LOOKBACK_DAYS = 365
SHORT_FEATURE_LOOKBACK_DAYS = 90

# Used ONLY by trajectory analysis.
# Kept separate from ML features intentionally.
TRAJECTORY_LOOKBACK_DAYS = 730

MIN_HISTORY_POINTS_FOR_TREND = 2


# ============================================================
# FUTURE LABEL WINDOW
# ============================================================

PREDICTION_WINDOW_DAYS = 90
SNAPSHOT_INTERVAL_DAYS = 90
MIN_HISTORY_DAYS = 180

ACUTE_ENCOUNTER_CLASSES = {
    "emergency",
    "urgentcare",
}


# ============================================================
# EXACT 29 OBSERVATIONS
#
# These are the observations supported by Module 1.
#
# Important:
# - CBC expansion is intentionally excluded.
# - Extra protein / globulin observations are excluded.
# - Every observation is processed independently.
# ============================================================

OBSERVATION_CONFIG = {

    # ========================================================
    # VITAL SIGNS / BODY MEASUREMENTS (6)
    # ========================================================

    "Body Mass Index": {
        "label": "BMI",
        "unit": "kg/m²",
        "direction_of_concern": "higher_worse",
        "aliases": ["body mass index", "bmi"],
        "plausibility_range": (5, 100),
        "min_absolute_change": 0.3,
    },

    "Body Weight": {
        "label": "Body weight",
        "unit": "kg",
        "direction_of_concern": "neutral",
        "aliases": ["body weight", "weight", "wt"],
        "plausibility_range": (1, 500),
        "min_absolute_change": 1.0,
    },

    "Systolic Blood Pressure": {
        "label": "Systolic blood pressure",
        "unit": "mmHg",
        "direction_of_concern": "higher_worse",
        "aliases": [
            "systolic blood pressure",
            "systolic bp",
            "sbp",
            "systolic",
            "bp systolic",
            "blood pressure systolic",
        ],
        "plausibility_range": (40, 300),
        "min_absolute_change": 3.0,
    },

    "Diastolic Blood Pressure": {
        "label": "Diastolic blood pressure",
        "unit": "mmHg",
        "direction_of_concern": "higher_worse",
        "aliases": [
            "diastolic blood pressure",
            "diastolic bp",
            "dbp",
            "diastolic",
            "bp diastolic",
            "blood pressure diastolic",
        ],
        "plausibility_range": (20, 200),
        "min_absolute_change": 2.0,
    },

    "Heart rate": {
        "label": "Heart rate",
        "unit": "bpm",
        "direction_of_concern": "neutral",
        "aliases": ["heart rate", "pulse", "hr", "pulse rate"],
        "plausibility_range": (20, 250),
        "min_absolute_change": 5.0,
    },

    "Respiratory rate": {
        "label": "Respiratory rate",
        "unit": "breaths/min",
        "direction_of_concern": "neutral",
        "aliases": [
            "respiratory rate",
            "respiration rate",
            "breathing rate",
            "rr",
        ],
        "plausibility_range": (4, 80),
        "min_absolute_change": 2.0,
    },


    # ========================================================
    # LIPID PROFILE (4)
    # ========================================================

    "High Density Lipoprotein Cholesterol": {
        "label": "HDL cholesterol",
        "unit": "mg/dL",
        "direction_of_concern": "lower_worse",
        "aliases": [
            "high density lipoprotein cholesterol",
            "hdl cholesterol",
            "hdl",
            "hdl-c",
            "direct hdl",
            "direct hdl cholesterol",
            "hdl direct",
        ],
        "plausibility_range": (1, 200),
        "min_absolute_change": 3.0,
    },

    "Low Density Lipoprotein Cholesterol": {
        "label": "LDL cholesterol",
        "unit": "mg/dL",
        "direction_of_concern": "higher_worse",
        "aliases": [
            "low density lipoprotein cholesterol",
            "ldl cholesterol",
            "ldl",
            "ldl-c",
            "calculated ldl",
            "direct ldl",
            "direct ldl cholesterol",
        ],
        "plausibility_range": (1, 500),
        "min_absolute_change": 5.0,
    },

    "Triglycerides": {
        "label": "Triglycerides",
        "unit": "mg/dL",
        "direction_of_concern": "higher_worse",
        "aliases": [
            "triglycerides",
            "triglyceride",
            "tg",
            "tgl",
            "serum triglycerides",
            "s. triglycerides",
        ],
        "plausibility_range": (1, 2000),
        "min_absolute_change": 10.0,
    },

    "Total Cholesterol": {
        "label": "Total cholesterol",
        "unit": "mg/dL",
        "direction_of_concern": "higher_worse",
        "aliases": [
            "total cholesterol",
            "cholesterol total",
            "serum cholesterol",
            "cholesterol",
            "s. cholesterol",
        ],
        "plausibility_range": (20, 1000),
        "min_absolute_change": 5.0,
    },


    # ========================================================
    # GLUCOSE / DIABETES (2)
    # ========================================================

    "Glucose": {
        "label": "Blood glucose",
        "unit": "mg/dL",
        "direction_of_concern": "higher_worse",
        "aliases": [
            "glucose",
            "blood glucose",
            "serum glucose",
            "blood sugar",
            "fasting blood sugar",
            "fbs",
            "post prandial blood sugar",
            "ppbs",
            "random blood sugar",
            "rbs",
            "glucose (fasting)",
            "glucose fasting",
            "fasting plasma glucose",
            "fpg",
            "plasma glucose fasting",
            "glucose random",
            "blood sugar fasting",
            "blood sugar pp",
        ],
        "plausibility_range": (20, 1000),
        "min_absolute_change": 5.0,
    },

    "Hemoglobin A1c/Hemoglobin.total in Blood": {
        "label": "HbA1c",
        "unit": "%",
        "direction_of_concern": "higher_worse",
        "aliases": [
            "hemoglobin a1c",
            "hba1c",
            "glycated hemoglobin",
            "hemoglobin a1c/hemoglobin.total in blood",
            "glycohemoglobin",
            "a1c",
            "hba1c (glycated hemoglobin)",
            "glycosylated hemoglobin",
        ],
        "plausibility_range": (2, 25),
        "min_absolute_change": 0.2,
    },


    # ========================================================
    # ELECTROLYTES / METABOLIC (5)
    # ========================================================

    "Potassium": {
        "label": "Potassium",
        "unit": "mmol/L",
        "direction_of_concern": "neutral",
        "aliases": [
            "potassium",
            "serum potassium",
            "k",
            "k+",
            "potassium (k+)",
            "s. potassium",
            "serum k",
        ],
        "plausibility_range": (1, 10),
        "min_absolute_change": 0.3,
    },

    "Calcium": {
        "label": "Calcium",
        "unit": "mg/dL",
        "direction_of_concern": "neutral",
        "aliases": [
            "calcium",
            "serum calcium",
            "ca",
            "ca++",
            "total calcium",
            "s. calcium",
            "serum ca",
        ],
        "plausibility_range": (3, 20),
        "min_absolute_change": 0.3,
    },

    "Sodium": {
        "label": "Sodium",
        "unit": "mmol/L",
        "direction_of_concern": "neutral",
        "aliases": [
            "sodium",
            "serum sodium",
            "na",
            "na+",
            "sodium (na+)",
            "s. sodium",
            "serum na",
        ],
        "plausibility_range": (100, 180),
        "min_absolute_change": 2.0,
    },

    "Carbon Dioxide": {
        "label": "Carbon dioxide / bicarbonate",
        "unit": "mmol/L",
        "direction_of_concern": "neutral",
        "aliases": [
            "carbon dioxide",
            "bicarbonate",
            "co2",
            "bicarbonate (hco3)",
            "hco3",
            "serum bicarbonate",
        ],
        "plausibility_range": (5, 60),
        "min_absolute_change": 2.0,
    },

    "Chloride": {
        "label": "Chloride",
        "unit": "mmol/L",
        "direction_of_concern": "neutral",
        "aliases": [
            "chloride",
            "serum chloride",
            "cl",
            "cl-",
            "s. chloride",
            "serum cl",
        ],
        "plausibility_range": (60, 150),
        "min_absolute_change": 2.0,
    },


    # ========================================================
    # KIDNEY FUNCTION (3)
    # ========================================================

    "Creatinine": {
        "label": "Creatinine",
        "unit": "mg/dL",
        "direction_of_concern": "higher_worse",
        "aliases": [
            "creatinine",
            "serum creatinine",
            "s. creatinine",
            "s.creatinine",
            "creat",
            "cr",
            "creatinine serum",
            "blood creatinine",
        ],
        "plausibility_range": (0.1, 30),
        "min_absolute_change": 0.1,
    },

    "Urea Nitrogen": {
        "label": "Urea nitrogen / BUN",
        "unit": "mg/dL",
        "direction_of_concern": "higher_worse",
        "aliases": [
            "urea nitrogen",
            "bun",
            "blood urea nitrogen",
            "urea",
            "blood urea",
            "serum urea",
            "s. urea",
        ],
        "plausibility_range": (1, 300),
        "min_absolute_change": 2.0,
    },

    "Glomerular filtration rate/1.73 sq M.predicted": {
        "label": "eGFR",
        "unit": "mL/min/1.73 m²",
        "direction_of_concern": "lower_worse",
        "aliases": [
            "glomerular filtration rate",
            "egfr",
            "estimated glomerular filtration rate",
            "glomerular filtration rate/1.73 sq m.predicted",
            "gfr",
            "egfr (ckd-epi)",
            "estimated gfr",
        ],
        "plausibility_range": (1, 250),
        "min_absolute_change": 3.0,
    },


    # ========================================================
    # LIVER FUNCTION (5)
    # ========================================================

    "Aspartate aminotransferase [Enzymatic activity/volume] in Serum or Plasma": {
        "label": "AST",
        "unit": "U/L",
        "direction_of_concern": "higher_worse",
        "aliases": [
            "ast",
            "aspartate aminotransferase",
            "sgot",
            "ast (sgot)",
            "sgot/ast",
            "aspartate transaminase",
            "s.g.o.t.",
            "sgot (ast)",
        ],
        "plausibility_range": (1, 5000),
        "min_absolute_change": 5.0,
    },

    "Alanine aminotransferase [Enzymatic activity/volume] in Serum or Plasma": {
        "label": "ALT",
        "unit": "U/L",
        "direction_of_concern": "higher_worse",
        "aliases": [
            "alt",
            "alanine aminotransferase",
            "sgpt",
            "alt (sgpt)",
            "sgpt/alt",
            "alanine transaminase",
            "s.g.p.t.",
            "sgpt (alt)",
        ],
        "plausibility_range": (1, 5000),
        "min_absolute_change": 5.0,
    },

    "Alkaline phosphatase [Enzymatic activity/volume] in Serum or Plasma": {
        "label": "Alkaline phosphatase",
        "unit": "U/L",
        "direction_of_concern": "higher_worse",
        "aliases": [
            "alkaline phosphatase",
            "alp",
            "alk phos",
            "s. alkaline phosphatase",
            "serum alkaline phosphatase",
        ],
        "plausibility_range": (1, 5000),
        "min_absolute_change": 10.0,
    },

    "Bilirubin.total [Mass/volume] in Serum or Plasma": {
        "label": "Total bilirubin",
        "unit": "mg/dL",
        "direction_of_concern": "higher_worse",
        "aliases": [
            "total bilirubin",
            "bilirubin",
            "bilirubin total",
            "t. bilirubin",
            "s. bilirubin",
            "serum bilirubin total",
            "serum bilirubin",
            "bilirubin (total)",
        ],
        "plausibility_range": (0.01, 100),
        "min_absolute_change": 0.2,
    },

    "Albumin [Mass/volume] in Serum or Plasma": {
        "label": "Albumin",
        "unit": "g/dL",
        "direction_of_concern": "lower_worse",
        "aliases": [
            "albumin",
            "serum albumin",
            "s. albumin",
            "alb",
        ],
        "plausibility_range": (0.5, 10),
        "min_absolute_change": 0.2,
    },


    # ========================================================
    # CBC (4)
    #
    # Only the core four are retained for ML training.
    # ========================================================

    "Hemoglobin [Mass/volume] in Blood": {
        "label": "Hemoglobin",
        "unit": "g/dL",
        "direction_of_concern": "neutral",
        "aliases": [
            "hemoglobin",
            "haemoglobin",
            "hb",
            "hgb",
            "blood hemoglobin",
            "hemoglobin (hb)",
            "blood hb",
        ],
        "plausibility_range": (1, 25),
        "min_absolute_change": 0.5,
    },

    "Hematocrit [Volume Fraction] of Blood by Automated count": {
        "label": "Hematocrit",
        "unit": "%",
        "direction_of_concern": "neutral",
        "aliases": [
            "hematocrit",
            "haematocrit",
            "hct",
            "pcv",
            "packed cell volume",
        ],
        "plausibility_range": (5, 80),
        "min_absolute_change": 2.0,
    },

    "Leukocytes [#/volume] in Blood by Automated count": {
        "label": "Leukocytes",
        "unit": "10³/µL",
        "direction_of_concern": "neutral",
        "aliases": [
            "leukocytes",
            "white blood cells",
            "wbc",
            "wbc count",
            "total wbc",
            "total leukocyte count",
            "total leukocytes",
            "tlc",
            "white blood cell count",
            "leucocytes",
            "total leucocyte count",
            "white cells count",
        ],
        "plausibility_range": (0.1, 100),
        "min_absolute_change": 1.0,
    },

    "Platelets [#/volume] in Blood by Automated count": {
        "label": "Platelets",
        "unit": "10³/µL",
        "direction_of_concern": "neutral",
        "aliases": [
            "platelets",
            "platelet count",
            "platelet",
            "total platelet count",
            "plt",
            "tpc",
            "thrombocyte",
            "thrombocytes",
            "thrombocyte count",
        ],
        "plausibility_range": (1, 2000),
        "min_absolute_change": 20.0,
    },
}


# ============================================================
# EXTENDED CLINICAL OBSERVATIONS
#
# Broad spectrum laboratory and clinical tests supported for
# patient dashboard display, longitudinal tracking, and OCR
# extraction across all medical report formats.
# ============================================================

EXTENDED_OBSERVATIONS = {
    # CBC Differentials
    "Neutrophils": {
        "label": "Neutrophils",
        "unit": "%",
        "aliases": ["neutrophils", "neutrophil", "neutrophil count", "polymorphs", "polymorphonuclear leukocytes", "segs", "segmented neutrophils", "neut"],
        "plausibility_range": (0, 100),
    },
    "Lymphocytes": {
        "label": "Lymphocytes",
        "unit": "%",
        "aliases": ["lymphocytes", "lymphocyte", "lymphocyte count", "lymph", "lymphs", "total lymphocytes"],
        "plausibility_range": (0, 100),
    },
    "Monocytes": {
        "label": "Monocytes",
        "unit": "%",
        "aliases": ["monocytes", "monocyte", "monocyte count", "mono", "monos"],
        "plausibility_range": (0, 100),
    },
    "Eosinophils": {
        "label": "Eosinophils",
        "unit": "%",
        "aliases": ["eosinophils", "eosinophil", "eosinophil count", "eos", "absolute eosinophil count", "aec"],
        "plausibility_range": (0, 100),
    },
    "Basophils": {
        "label": "Basophils",
        "unit": "%",
        "aliases": ["basophils", "basophil", "basophil count", "baso", "basos"],
        "plausibility_range": (0, 100),
    },
    "Red Blood Cell Count": {
        "label": "RBC Count",
        "unit": "10⁶/µL",
        "aliases": ["red blood cell count", "rbc count", "rbc", "total rbc", "red blood cells", "erythrocyte count", "total erythrocyte count"],
        "plausibility_range": (0.5, 12.0),
    },
    "Mean Corpuscular Volume": {
        "label": "MCV",
        "unit": "fL",
        "aliases": ["mean corpuscular volume", "mcv"],
        "plausibility_range": (40, 150),
    },
    "Mean Corpuscular Hemoglobin": {
        "label": "MCH",
        "unit": "pg",
        "aliases": ["mean corpuscular hemoglobin", "mch"],
        "plausibility_range": (10, 60),
    },
    "Mean Corpuscular Hemoglobin Concentration": {
        "label": "MCHC",
        "unit": "g/dL",
        "aliases": ["mean corpuscular hemoglobin concentration", "mchc"],
        "plausibility_range": (15, 50),
    },
    "Red Cell Distribution Width": {
        "label": "RDW",
        "unit": "%",
        "aliases": ["red cell distribution width", "rdw", "rdw-cv", "rdw-sd", "rdw cv", "rdw sd"],
        "plausibility_range": (5, 40),
    },
    "Erythrocyte Sedimentation Rate": {
        "label": "ESR",
        "unit": "mm/hr",
        "aliases": ["erythrocyte sedimentation rate", "esr", "esr westergren", "westergren esr", "sedimentation rate"],
        "plausibility_range": (0, 150),
    },

    # Thyroid Function
    "Thyroid Stimulating Hormone": {
        "label": "TSH",
        "unit": "µIU/mL",
        "aliases": ["thyroid stimulating hormone", "tsh", "s. tsh", "serum tsh", "ultrasensitive tsh", "tsh - thyroid stimulating hormone"],
        "plausibility_range": (0.01, 100),
    },
    "Triiodothyronine": {
        "label": "Total T3",
        "unit": "ng/dL",
        "aliases": ["triiodothyronine", "total t3", "t3 total", "t3", "serum t3"],
        "plausibility_range": (10, 800),
    },
    "Free Triiodothyronine": {
        "label": "Free T3 (FT3)",
        "unit": "pg/mL",
        "aliases": ["free triiodothyronine", "free t3", "ft3"],
        "plausibility_range": (0.5, 30),
    },
    "Thyroxine": {
        "label": "Total T4",
        "unit": "µg/dL",
        "aliases": ["thyroxine", "total t4", "t4 total", "t4", "serum t4"],
        "plausibility_range": (0.5, 30),
    },
    "Free Thyroxine": {
        "label": "Free T4 (FT4)",
        "unit": "ng/dL",
        "aliases": ["free thyroxine", "free t4", "ft4"],
        "plausibility_range": (0.1, 10),
    },

    # Vitamins & Minerals
    "Vitamin D": {
        "label": "Vitamin D (25-OH)",
        "unit": "ng/mL",
        "aliases": ["vitamin d", "25-hydroxy vitamin d", "25-oh vitamin d", "vit d", "vitamin d3", "25-oh vit d", "total 25-hydroxyvitamin d", "25-hydroxyvitamin d"],
        "plausibility_range": (2, 200),
    },
    "Vitamin B12": {
        "label": "Vitamin B12",
        "unit": "pg/mL",
        "aliases": ["vitamin b12", "vit b12", "cyanocobalamin", "b12", "serum b12"],
        "plausibility_range": (20, 3000),
    },
    "Serum Iron": {
        "label": "Serum Iron",
        "unit": "µg/dL",
        "aliases": ["serum iron", "iron", "fe"],
        "plausibility_range": (5, 500),
    },
    "Ferritin": {
        "label": "Serum Ferritin",
        "unit": "ng/mL",
        "aliases": ["ferritin", "serum ferritin", "s. ferritin"],
        "plausibility_range": (1, 5000),
    },

    # Renal & Liver Extended
    "Uric Acid": {
        "label": "Uric Acid",
        "unit": "mg/dL",
        "aliases": ["uric acid", "serum uric acid", "s. uric acid"],
        "plausibility_range": (0.5, 25),
    },
    "Total Protein": {
        "label": "Total Protein",
        "unit": "g/dL",
        "aliases": ["total protein", "serum total protein", "protein total", "s. protein"],
        "plausibility_range": (2.0, 15.0),
    },
    "Globulin": {
        "label": "Serum Globulin",
        "unit": "g/dL",
        "aliases": ["globulin", "serum globulin", "s. globulin"],
        "plausibility_range": (0.5, 10.0),
    },
    "Albumin Globulin Ratio": {
        "label": "A/G Ratio",
        "unit": "ratio",
        "aliases": ["albumin globulin ratio", "a/g ratio", "ag ratio", "albumin / globulin ratio"],
        "plausibility_range": (0.1, 5.0),
    },
    "Bilirubin Direct": {
        "label": "Direct Bilirubin",
        "unit": "mg/dL",
        "aliases": ["direct bilirubin", "conjugated bilirubin", "bilirubin direct", "d. bilirubin"],
        "plausibility_range": (0.01, 30.0),
    },
    "Bilirubin Indirect": {
        "label": "Indirect Bilirubin",
        "unit": "mg/dL",
        "aliases": ["indirect bilirubin", "unconjugated bilirubin", "bilirubin indirect"],
        "plausibility_range": (0.01, 30.0),
    },
    "Gamma Glutamyl Transferase": {
        "label": "GGT",
        "unit": "U/L",
        "aliases": ["gamma glutamyl transferase", "ggt", "ggtp", "gamma gt"],
        "plausibility_range": (1, 2000),
    },
}


# ============================================================
# DERIVED CONFIGURATION
# ============================================================

SUPPORTED_OBSERVATIONS = list(OBSERVATION_CONFIG.keys())

# Safety check: exactly 29 observations.
if len(SUPPORTED_OBSERVATIONS) != 29:
    raise RuntimeError(
        f"Expected exactly 29 observations, found "
        f"{len(SUPPORTED_OBSERVATIONS)}."
    )


OBSERVATION_ALIASES = {}

for canonical_name, info in OBSERVATION_CONFIG.items():
    OBSERVATION_ALIASES[canonical_name.lower()] = canonical_name
    for alias in info["aliases"]:
        OBSERVATION_ALIASES[alias.lower()] = canonical_name

# Extended observation aliases mapping
EXTENDED_ALIASES = {}
for ext_name, info in EXTENDED_OBSERVATIONS.items():
    EXTENDED_ALIASES[ext_name.lower()] = ext_name
    for alias in info["aliases"]:
        EXTENDED_ALIASES[alias.lower()] = ext_name



# ============================================================
# TRAJECTORY SETTINGS
# ============================================================

TRAJECTORY_RELATIVE_CHANGE_THRESHOLD = 0.03
TRAJECTORY_MIN_SUPPORTED_SIGNALS = 2


# ============================================================
# MODEL SETTINGS
# ============================================================

RANDOM_STATE = 42

TEST_SIZE = 0.15
VALIDATION_SIZE = 0.15

XGBOOST_PARAMS = {
    "n_estimators": 500,
    "max_depth": 5,
    "learning_rate": 0.03,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "eval_metric": "logloss",
    "random_state": RANDOM_STATE,
}


# ============================================================
# RISK DISPLAY THRESHOLDS
# ============================================================

RISK_THRESHOLDS = {
    "low_max": 0.15,
    "elevated_max": 0.30,
    "high_max": 0.50,
}