const axios = require("axios");

class OpenRouterProvider {
  constructor() {
    this.name = "OpenRouter";
    this.defaultModel = "meta-llama/llama-3.3-70b-instruct";
  }

  isConfigured() {
    return Boolean(process.env.OPENROUTER_API_KEY && process.env.OPENROUTER_API_KEY.trim());
  }

  getModel() {
    return process.env.OPENROUTER_MODEL || this.defaultModel;
  }

  /**
   * Generates response from OpenRouter
   * @param {string} systemPrompt
   * @param {Array<{role: string, content: string}>} messages
   */
  async generateCompletion(systemPrompt, messages) {
    if (!this.isConfigured()) {
      throw new Error("OPENROUTER_API_KEY is not configured.");
    }

    const apiKey = process.env.OPENROUTER_API_KEY.trim();
    const model = this.getModel();
    const url = "https://openrouter.ai/api/v1/chat/completions";

    const formattedMessages = [
      { role: "system", content: systemPrompt },
      ...messages.map((m) => ({
        role: m.role === "assistant" ? "assistant" : "user",
        content: m.content,
      })),
    ];

    const payload = {
      model,
      messages: formattedMessages,
      temperature: 0.3,
      max_tokens: 850,
    };

    try {
      const response = await axios.post(url, payload, {
        headers: {
          Authorization: `Bearer ${apiKey}`,
          "HTTP-Referer": "http://localhost:5000",
          "X-Title": "MediTwin Health Assistant",
          "Content-Type": "application/json",
        },
        timeout: 25000,
      });

      const text = response.data?.choices?.[0]?.message?.content;
      if (!text) {
        throw new Error("Empty response received from OpenRouter.");
      }

      return {
        text: text.trim(),
        provider: this.name,
        model,
      };
    } catch (err) {
      const status = err.response?.status;
      const errorMsg = err.response?.data?.error?.message || err.message || "Unknown error";
      const cleanError = new Error(`OpenRouter API error (Status ${status || "network"}): ${errorMsg}`);
      cleanError.status = status;
      cleanError.isRateLimitOrQuota = status === 429 || errorMsg.toLowerCase().includes("quota") || errorMsg.toLowerCase().includes("rate limit");
      throw cleanError;
    }
  }
}

module.exports = OpenRouterProvider;
