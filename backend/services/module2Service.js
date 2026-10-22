/**
 * Module 2 Service — Disease Prediction Service
 * 
 * 1. Primary path: High-speed async HTTP call to Module 2 FastAPI daemon (port 8002).
 *    Executes in-memory predictions in ~30ms without spinning up a new Python process.
 * 2. Fallback path: Fully asynchronous child_process.spawn (non-blocking).
 *    Never blocks the Node.js event loop so concurrent API requests (dashboard,
 *    treatment, auth, find-doctor) always stay 100% responsive.
 */
const axios = require("axios");
const { spawn } = require("child_process");
const path = require("path");

const rawApiUrl     = process.env.MODULE2_API || "http://127.0.0.1:8002";
const MODULE2_API_URL = rawApiUrl.endsWith("/predict-disease")
  ? rawApiUrl
  : `${rawApiUrl.replace(/\/+$/, "")}/predict-disease`;
const PYTHON          = process.env.PYTHON_EXEC || "py";
const MODULE2_DIR      = path.resolve(__dirname, "../../Module_2");
const SCRIPT           = path.join(MODULE2_DIR, "run_inference.py");

function extractJson(stdout) {
  if (!stdout) throw new Error("No stdout output from Module 2");
  const lines = stdout.trim().split(/\r?\n/);
  for (let i = lines.length - 1; i >= 0; i--) {
    const line = lines[i].trim();
    if (line.startsWith("{") && line.endsWith("}")) {
      try {
        return JSON.parse(line);
      } catch {}
    }
  }
  const start = stdout.indexOf("{");
  const end = stdout.lastIndexOf("}");
  if (start !== -1 && end !== -1 && end > start) {
    return JSON.parse(stdout.slice(start, end + 1));
  }
  throw new Error(`No JSON found in Module 2 output: ${stdout.slice(-1000)}`);
}

/**
 * Execute run_inference.py via asynchronous child_process.spawn.
 * Event-driven: does not block the Node.js main thread.
 */
function spawnModule2Async(args) {
  return new Promise((resolve, reject) => {
    const child = spawn(PYTHON, args, {
      cwd: MODULE2_DIR,
      env: {
        ...process.env,
        PYTHONIOENCODING: "utf-8",
        PYTHONUTF8: "1",
        M2_FAST_MATCHER: "1",
      },
    });

    let stdout = "";
    let stderr = "";

    const timer = setTimeout(() => {
      child.kill("SIGTERM");
      reject(new Error("Module 2 inference timed out after 60 seconds"));
    }, 60000);

    child.stdout.on("data", (chunk) => {
      stdout += chunk.toString("utf-8");
    });

    child.stderr.on("data", (chunk) => {
      stderr += chunk.toString("utf-8");
    });

    child.on("error", (err) => {
      clearTimeout(timer);
      reject(err);
    });

    child.on("close", (code) => {
      clearTimeout(timer);
      try {
        const parsed = extractJson(stdout);
        if (parsed.status === "error" || parsed.error) {
          return reject(new Error(parsed.error || "Module 2 prediction error"));
        }
        return resolve(parsed);
      } catch (e) {
        if (code !== 0) {
          return reject(
            new Error(`Module 2 exited with code ${code}: ${stderr.slice(-1000) || stdout.slice(-1000)}`)
          );
        }
        return reject(
          new Error(`Failed to parse Module 2 output: ${e.message}\nOutput: ${stdout.slice(-1000)}`)
        );
      }
    });
  });
}

const predictDisease = async (symptoms = [], age = 30, sex = "unknown", text = "", topk = 5) => {
  const normSymptoms = Array.isArray(symptoms) ? symptoms : [];
  const normText = (text && text.trim()) ? text.trim() : normSymptoms.join(", ");

  if (!normText && normSymptoms.length === 0) {
    throw new Error("No symptoms or text provided");
  }

  // ── Strategy 1: Fast HTTP call to running Module 2 daemon ─────────────────
  try {
    const response = await axios.post(
      MODULE2_API_URL,
      {
        text: normText,
        symptoms: normSymptoms,
        age: Number(age) || 30,
        sex: String(sex || "unknown"),
        top_k: Number(topk) || 5,
      },
      {
        timeout: 6000,
        headers: { "Content-Type": "application/json" },
      }
    );

    if (response.data && (response.data.predictions || response.data.status)) {
      return response.data;
    }
  } catch (apiErr) {
    // Daemon offline or timed out; log and fall through to asynchronous spawn
    console.log(`[Module 2] Daemon unavailable (${apiErr.message}). Using asynchronous CLI worker...`);
  }

  // ── Strategy 2: Non-blocking async CLI fallback ────────────────────────────
  const args = [SCRIPT];
  if (normText) {
    args.push("--text", normText);
  } else {
    args.push("--symptoms", ...normSymptoms);
  }
  args.push("--age", String(age || 30));
  args.push("--sex", String(sex || "unknown"));
  args.push("--topk", String(topk || 5));

  return await spawnModule2Async(args);
};

module.exports = { predictDisease };
