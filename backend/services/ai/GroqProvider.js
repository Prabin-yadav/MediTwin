const axios = require("axios");

class GroqProvider {
  constructor() {
    this.name = "Groq";
    this.defaultModel = "qwen/qwen3.8-27b";
  }

  isConfigured() {
    return Boolean(process.env.GROQ_API_KEY && process.env.GROQ_API_KEY.trim());
  }

  getModel() {
    return process.env.GROQ_MODEL || this.defaultModel;
  }

  /**
   * Generates response from Groq
   * @param {string} systemPrompt
   * @param {Array<{role: string, content: string}>} messages
   */
  async generateCompletion(systemPrompt, messages) {
    if (!this.isConfigured()) {
      throw new Error("GROQ_API_KEY is not configured.");
    }

    const apiKey = process.env.GROQ_API_KEY.trim();
    const model = this.getModel();
    const url = "https://api.groq.com/openai/v1/chat/completions";

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
          "Content-Type": "application/json",
        },
        timeout: 25000,
      });

      const text = response.data?.choices?.[0]?.message?.content;
      if (!text) {
        throw new Error("Empty response received from Groq.");
      }

      return {
        text: text.trim(),
        provider: this.name,
        model,
      };
    } catch (err) {
      const status = err.response?.status;
      const errorMsg = err.response?.data?.error?.message || err.message || "Unknown error";
      const cleanError = new Error(`Groq API error (Status ${status || "network"}): ${errorMsg}`);
      cleanError.status = status;
      cleanError.isRateLimitOrQuota = status === 429 || errorMsg.toLowerCase().includes("quota") || errorMsg.toLowerCase().includes("rate limit");
      throw cleanError;
    }
  }
}

module.exports = GroqProvider;
