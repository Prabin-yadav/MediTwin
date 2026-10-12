const express = require("express");
const router = express.Router();
const { protect, requirePatient } = require("../middleware/authMiddleware");
const {
  chatWithAssistant,
  getHistory,
  clearHistory,
  getSuggestedPrompts,
} = require("../controllers/assistantController");

// All assistant routes require an authenticated patient session
router.use(protect, requirePatient);

router.post("/chat", chatWithAssistant);
router.get("/history", getHistory);
router.delete("/history", clearHistory);
router.get("/prompts", getSuggestedPrompts);

module.exports = router;
