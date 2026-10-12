const User = require("../models/User");
const HealthRecord = require("../models/HealthRecord");
const RiskPrediction = require("../models/RiskPrediction");
const SymptomAnalysis = require("../models/SymptomAnalysis");
const TreatmentRecommendation = require("../models/TreatmentRecommendation");

/**
 * Calculates age given a Date of Birth
 */
function calculateAge(dob) {
  if (!dob) return null;
  const diff = Date.now() - new Date(dob).getTime();
  const ageDt = new Date(diff);
  return Math.abs(ageDt.getUTCFullYear() - 1970);
}

/**
 * 1. getHealthSummary:
 * High-level, token-efficient patient snapshot (profile, latest risk, top differential condition, treatment status)
 */
async function getHealthSummary(patientId) {
  const [user, latestRisk, latestDisease, latestTreatment] = await Promise.all([
    User.findOne({ patientId }).select("name dateOfBirth gender").lean(),
    RiskPrediction.findOne({ patientId }).sort({ createdAt: -1 }).select("riskCategory probabilityPercent predictionHorizonDays createdAt").lean(),
    SymptomAnalysis.findOne({ patientId }).sort({ createdAt: -1 }).select("predictions createdAt").lean(),
    TreatmentRecommendation.findOne({ patientId }).sort({ createdAt: -1 }).select("urgencyLevel createdAt").lean(),
  ]);

  const age = user?.dateOfBirth ? calculateAge(user.dateOfBirth) : "Not recorded";
  const gender = user?.gender || "Not recorded";
  const name = user?.name ? user.name.split(" ")[0] : "Patient";

  const topCondition = latestDisease?.predictions?.[0];

  return {
    patientProfile: {
      firstName: name,
      age,
      gender,
    },
    latestAcuteRisk: latestRisk
      ? `${latestRisk.riskCategory} risk (${latestRisk.probabilityPercent?.toFixed?.(1) || latestRisk.probabilityPercent}% 90-day probability, evaluated ${new Date(latestRisk.createdAt).toISOString().split("T")[0]})`
      : "No acute risk prediction recorded yet",
    latestDifferential: topCondition
      ? `${topCondition.disease} (Confidence: ${topCondition.confidence || "MODERATE"}, probability: ${((topCondition.probability || 0) * 100).toFixed(0)}%)`
      : "No symptom differential prediction recorded yet",
    treatmentUrgency: latestTreatment?.urgencyLevel || "No active treatment plan recorded",
  };
}

/**
 * 2. getLabHistory:
 * Retrieves recent lab and vital observations from health records. Deduplicates by observation name to show latest values.
 */
async function getLabHistory(patientId) {
  const records = await HealthRecord.find({ patientId })
    .sort({ reportDate: -1, createdAt: -1 })
    .limit(3)
    .select("reportDate source fileName observations")
    .lean();

  if (!records || records.length === 0) {
    return { status: "No laboratory records or vitals recorded in MediTwin." };
  }

  const latestReadings = new Map();

  for (const rec of records) {
    const reportDateStr = rec.reportDate ? new Date(rec.reportDate).toISOString().split("T")[0] : "Unknown date";
    if (Array.isArray(rec.observations)) {
      for (const obs of rec.observations) {
        const key = (obs.canonicalName || obs.name || "").toLowerCase().trim();
        if (key && !latestReadings.has(key)) {
          latestReadings.set(key, {
            name: obs.label || obs.canonicalName || obs.name,
            value: obs.value,
            unit: obs.unit || "",
            plausible: obs.plausible !== false,
            date: reportDateStr,
          });
        }
      }
    }
  }

  const items = Array.from(latestReadings.values()).slice(0, 15);
  return {
    totalRecords: records.length,
    latestObservations: items,
  };
}

/**
 * 3. getRiskAssessments:
 * Retrieves longitudinal acute-risk predictions (Module 1), top contributing factors (SHAP), and biomarker trends.
 */
async function getRiskAssessments(patientId) {
  const latestRisk = await RiskPrediction.findOne({ patientId })
    .sort({ createdAt: -1 })
    .select("probability probabilityPercent riskCategory predictionHorizonDays dataConfidence trends importantFactors createdAt")
    .lean();

  if (!latestRisk) {
    return { status: "No acute-risk assessment currently recorded." };
  }

  // Extract top factors (SHAP)
  const topFactors = Array.isArray(latestRisk.importantFactors)
    ? latestRisk.importantFactors.slice(0, 5).map((f) => ({
        feature: f.feature_name || f.name || f.feature,
        impact: f.impact || f.direction || f.value,
      }))
    : [];

  // Extract key trends
  const trends = Array.isArray(latestRisk.trends)
    ? latestRisk.trends.slice(0, 5).map((t) => ({
        biomarker: t.observation || t.name,
        latestValue: `${t.latest_value || ""} ${t.unit || ""}`.trim(),
        trend: t.trend,
      }))
    : [];

  return {
    evaluatedAt: latestRisk.createdAt ? new Date(latestRisk.createdAt).toISOString().split("T")[0] : null,
    riskCategory: latestRisk.riskCategory,
    probabilityPercent: latestRisk.probabilityPercent,
    predictionHorizonDays: latestRisk.predictionHorizonDays || 90,
    featureCoveragePercent: latestRisk.dataConfidence?.feature_coverage_percent || null,
    topContributingFactors: topFactors,
    biomarkerTrends: trends,
  };
}

/**
 * 4. getDiseasePredictions:
 * Retrieves symptom analysis and differential diagnoses (Module 2).
 */
async function getDiseasePredictions(patientId) {
  const latestDisease = await SymptomAnalysis.findOne({ patientId })
    .sort({ createdAt: -1 })
    .select("inputText symptoms predictions createdAt")
    .lean();

  if (!latestDisease) {
    return { status: "No symptom or disease prediction assessments recorded." };
  }

  const topConditions = Array.isArray(latestDisease.predictions)
    ? latestDisease.predictions.slice(0, 4).map((p) => ({
        disease: p.disease,
        probability: `${((p.probability || 0) * 100).toFixed(1)}%`,
        confidence: p.confidence,
      }))
    : [];

  return {
    analyzedAt: latestDisease.createdAt ? new Date(latestDisease.createdAt).toISOString().split("T")[0] : null,
    reportedSymptoms: latestDisease.symptoms || [],
    userInputSnippet: latestDisease.inputText ? latestDisease.inputText.slice(0, 120) : null,
    differentialConditions: topConditions,
  };
}

/**
 * 5. getTreatmentPlan:
 * Retrieves clinical decision support recommendations, lifestyle advice, and drug interactions (Module 3).
 */
async function getTreatmentPlan(patientId) {
  const latestTreatment = await TreatmentRecommendation.findOne({ patientId })
    .sort({ createdAt: -1 })
    .select("urgencyLevel recommendations drugLookups fullReport createdAt")
    .lean();

  if (!latestTreatment) {
    return { status: "No treatment recommendations currently formulated." };
  }

  let formattedRecs = [];
  const recs = latestTreatment.recommendations || latestTreatment.fullReport?.recommendations;

  if (Array.isArray(recs)) {
    formattedRecs = recs.slice(0, 5).map((r) => ({
      condition: r.condition || r.disease || "Clinical Care Item",
      category: r.category || "General",
      firstLineApproach: Array.isArray(r.first_line_approach) ? r.first_line_approach : [],
      medicationClasses: Array.isArray(r.medication_classes) ? r.medication_classes : [],
      commonExamples: Array.isArray(r.common_examples) ? r.common_examples : [],
      monitoring: Array.isArray(r.monitoring) ? r.monitoring : [],
      clinicalConsiderations: Array.isArray(r.clinical_considerations) ? r.clinical_considerations : [],
    }));
  } else if (recs && typeof recs === "object") {
    for (const [key, val] of Object.entries(recs)) {
      if (typeof val === "object" && val !== null) {
        formattedRecs.push({
          condition: val.condition || val.disease || key,
          category: val.category || "General",
          firstLineApproach: Array.isArray(val.first_line_approach) ? val.first_line_approach : [],
          medicationClasses: Array.isArray(val.medication_classes) ? val.medication_classes : [],
          commonExamples: Array.isArray(val.common_examples) ? val.common_examples : [],
          monitoring: Array.isArray(val.monitoring) ? val.monitoring : [],
        });
      }
    }
  }

  return {
    formulatedAt: latestTreatment.createdAt ? new Date(latestTreatment.createdAt).toISOString().split("T")[0] : null,
    urgencyLevel: latestTreatment.urgencyLevel || latestTreatment.fullReport?.urgency?.urgency_level || "ROUTINE_FOLLOW_UP",
    recommendations: formattedRecs,
    drugWarnings: latestTreatment.drugLookups ? "Drug guidance and safety lookups recorded in system" : null,
  };
}

/**
 * 6. getMedicalHistory:
 * Longitudinal summary of past records, historical risks, and past symptoms.
 */
async function getMedicalHistory(patientId) {
  const [recordsCount, pastRisks, pastAnalyses] = await Promise.all([
    HealthRecord.countDocuments({ patientId }),
    RiskPrediction.find({ patientId }).sort({ createdAt: -1 }).limit(3).select("riskCategory probabilityPercent createdAt").lean(),
    SymptomAnalysis.find({ patientId }).sort({ createdAt: -1 }).limit(3).select("predictions createdAt").lean(),
  ]);

  return {
    totalLabAndVitalUploads: recordsCount,
    historicalRiskAssessments: pastRisks.map((r) => ({
      date: new Date(r.createdAt).toISOString().split("T")[0],
      risk: `${r.riskCategory} (${r.probabilityPercent?.toFixed?.(0)}%)`,
    })),
    historicalDifferentialChecks: pastAnalyses.map((a) => ({
      date: new Date(a.createdAt).toISOString().split("T")[0],
      topCondition: a.predictions?.[0]?.disease || "Unknown",
    })),
  };
}

/**
 * Formats a clean, token-efficient clinical text block for the LLM
 */
function formatContextAsText(summary, specificContexts) {
  const lines = [];

  // Always include baseline patient profile
  lines.push("### VERIFIED PATIENT SUMMARY (FROM MEDITWIN RECORDS):");
  lines.push(`- Patient: ${summary.patientProfile.firstName} (${summary.patientProfile.gender}, Age: ${summary.patientProfile.age})`);
  lines.push(`- Future Acute Risk Status: ${summary.latestAcuteRisk}`);
  lines.push(`- Latest Symptom Differential: ${summary.latestDifferential}`);
  lines.push(`- Clinical Urgency Level: ${summary.treatmentUrgency}`);

  if (specificContexts.labs && specificContexts.labs.latestObservations) {
    lines.push("\n### RECENT LAB READINGS & VITALS:");
    for (const obs of specificContexts.labs.latestObservations) {
      lines.push(`- ${obs.name}: ${obs.value} ${obs.unit} (${obs.date})`);
    }
  }

  if (specificContexts.risk && specificContexts.risk.riskCategory) {
    lines.push("\n### DETAILED ACUTE RISK EVALUATION (MODULE 1):");
    lines.push(`- 90-Day Probability: ${specificContexts.risk.probabilityPercent?.toFixed?.(1)}% (${specificContexts.risk.riskCategory})`);
    if (specificContexts.risk.topContributingFactors?.length > 0) {
      lines.push("- Key Drivers: " + specificContexts.risk.topContributingFactors.map((f) => `${f.feature} (${f.impact})`).join(", "));
    }
    if (specificContexts.risk.biomarkerTrends?.length > 0) {
      lines.push("- Biomarker Trends: " + specificContexts.risk.biomarkerTrends.map((t) => `${t.biomarker}: ${t.trend} (${t.latestValue})`).join(", "));
    }
  }

  if (specificContexts.disease && specificContexts.disease.differentialConditions) {
    lines.push("\n### DIFFERENTIAL DIAGNOSIS (MODULE 2):");
    if (specificContexts.disease.reportedSymptoms?.length > 0) {
      lines.push(`- Reported Symptoms: ${specificContexts.disease.reportedSymptoms.join(", ")}`);
    }
    lines.push("- Top Matches: " + specificContexts.disease.differentialConditions.map((c) => `${c.disease} (${c.probability}, ${c.confidence})`).join("; "));
  }

  if (specificContexts.treatment && (specificContexts.treatment.urgencyLevel || specificContexts.treatment.recommendations?.length > 0)) {
    lines.push("\n### CLINICAL RECOMMENDATIONS & CARE PLAN (MODULE 3):");
    lines.push(`- Overall Urgency Level: ${specificContexts.treatment.urgencyLevel}`);
    if (Array.isArray(specificContexts.treatment.recommendations)) {
      for (const rec of specificContexts.treatment.recommendations) {
        if (typeof rec === "string") {
          lines.push(`- ${rec}`);
        } else if (rec.condition) {
          lines.push(`\n* Target Condition: ${rec.condition} (${rec.category || "Clinical"})`);
          if (rec.firstLineApproach && rec.firstLineApproach.length > 0) {
            lines.push(`  - First-Line / Non-Pharmacological: ${rec.firstLineApproach.join("; ")}`);
          }
          if (rec.medicationClasses && rec.medicationClasses.length > 0) {
            lines.push(`  - Recommended Medication Classes: ${rec.medicationClasses.join(", ")}`);
          }
          if (rec.commonExamples && rec.commonExamples.length > 0) {
            lines.push(`  - Common Medicine Examples: ${rec.commonExamples.join(", ")}`);
          }
          if (rec.monitoring && rec.monitoring.length > 0) {
            lines.push(`  - Clinical Monitoring: ${rec.monitoring.join("; ")}`);
          }
        }
      }
    }
  }

  if (specificContexts.history && specificContexts.history.totalLabAndVitalUploads > 0) {
    lines.push("\n### MEDICAL TIMELINE OVERVIEW:");
    lines.push(`- Total recorded diagnostic files: ${specificContexts.history.totalLabAndVitalUploads}`);
    if (specificContexts.history.historicalRiskAssessments?.length > 0) {
      lines.push("- Past Risk Checks: " + specificContexts.history.historicalRiskAssessments.map((r) => `${r.date}: ${r.risk}`).join("; "));
    }
  }

  return lines.join("\n");
}

/**
 * buildContextForQuery:
 * Intelligently retrieves only relevant patient context sections based on the query keywords/intent.
 * Keeps token usage minimal and context maximally relevant.
 */
async function buildContextForQuery(patientId, query = "") {
  const q = query.toLowerCase();

  // Basic summary is always retrieved (very small)
  const summary = await getHealthSummary(patientId);

  // Intent triggers
  const needsRisk = /risk|hospital|er|urgent|acute|emergency|chance|likely|danger|odds/i.test(q);
  const needsDisease = /symptom|disease|diagnos|condition|sick|ill|ache|pain|cough|fever|headache|rash|feeling/i.test(q);
  const needsTreatment = /treat|med|drug|pill|prescription|diet|food|lifestyle|recommend|manage|cure|remedy|exercise/i.test(q);
  const needsLabs = /lab|test|blood|result|glucose|sugar|cholesterol|creatinine|hba1c|pressure|bp|rate|vitals|reading|metric/i.test(q);
  const needsHistory = /history|past|previous|timeline|trend|record|before|change/i.test(q);

  // If question is broad/general, provide a balanced compact highlight
  const isGeneral = !needsRisk && !needsDisease && !needsTreatment && !needsLabs && !needsHistory;

  const contextPromises = {};

  if (needsLabs || isGeneral) {
    contextPromises.labs = getLabHistory(patientId);
  }
  if (needsRisk || isGeneral) {
    contextPromises.risk = getRiskAssessments(patientId);
  }
  if (needsDisease || isGeneral) {
    contextPromises.disease = getDiseasePredictions(patientId);
  }
  if (needsTreatment || isGeneral) {
    contextPromises.treatment = getTreatmentPlan(patientId);
  }
  if (needsHistory) {
    contextPromises.history = getMedicalHistory(patientId);
  }

  const resolvedKeys = Object.keys(contextPromises);
  const resolvedValues = await Promise.all(Object.values(contextPromises));

  const specificContexts = {};
  resolvedKeys.forEach((key, idx) => {
    specificContexts[key] = resolvedValues[idx];
  });

  const formattedContextText = formatContextAsText(summary, specificContexts);

  return {
    summary,
    specificContexts,
    formattedText: formattedContextText,
  };
}

module.exports = {
  getHealthSummary,
  getLabHistory,
  getRiskAssessments,
  getDiseasePredictions,
  getTreatmentPlan,
  getMedicalHistory,
  buildContextForQuery,
};
