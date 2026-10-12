const GeminiProvider = require("./GeminiProvider");
const OpenRouterProvider = require("./OpenRouterProvider");
const GroqProvider = require("./GroqProvider");

class AIProviderManager {
  constructor() {
    this.gemini = new GeminiProvider();
    this.openrouter = new OpenRouterProvider();
    this.groq = new GroqProvider();

    // Strict priority fallback order: 1. Gemini -> 2. OpenRouter -> 3. Groq
    this.providers = [this.gemini, this.openrouter, this.groq];
  }

  /**
   * Generates a completion through the provider fallback chain.
   *
   * @param {string} systemPrompt - Clinical instructions & patient context
   * @param {Array<{role: string, content: string}>} messages - Conversational history & user message
   * @returns {Promise<{text: string, provider: string, model: string}>}
   */
  async generateResponse(systemPrompt, messages) {
    const attemptedErrors = [];

    for (const provider of this.providers) {
      if (!provider.isConfigured()) {
        console.log(`[AIProviderManager] ${provider.name} skipped: API key is not configured.`);
        continue;
      }

      try {
        console.log(`[AIProviderManager] Attempting generation with primary/active provider: ${provider.name} (${provider.getModel()})...`);
        const result = await provider.generateCompletion(systemPrompt, messages);

        // Sanity check on response text
        if (!result || !result.text) {
          throw new Error(`${provider.name} returned empty text output.`);
        }

        console.log(`[AIProviderManager] Successfully generated response using ${result.provider} (${result.model}).`);
        return result;
      } catch (err) {
        // Safe logging: log provider name and error message, never log keys or patient data
        const safeErrorSnippet = err.message || "Unknown error";
        console.warn(`[AIProviderManager] ${provider.name} encountered an error: "${safeErrorSnippet}". Attempting next provider in fallback order...`);
        attemptedErrors.push({ provider: provider.name, error: safeErrorSnippet });
      }
    }

    // If we reach here, all configured providers either failed or no provider was configured
    console.error("[AIProviderManager] All AI providers failed or were unconfigured.", attemptedErrors);

    if (attemptedErrors.length === 0) {
      const configError = new Error(
        "No AI provider is currently configured. Please ensure at least one API key (GEMINI_API_KEY, OPENROUTER_API_KEY, or GROQ_API_KEY) is set in backend .env."
      );
      configError.code = "NO_PROVIDERS_CONFIGURED";
      throw configError;
    }

    const failureError = new Error(
      "The AI Health Assistant is temporarily unavailable because all AI services were busy or encountered rate limits. Please try again in a few moments."
    );
    failureError.code = "ALL_PROVIDERS_FAILED";
    failureError.details = attemptedErrors;
    throw failureError;
  }
}

// Singleton instance
module.exports = new AIProviderManager();
