const axios = require("axios");

class GeminiProvider {
  constructor() {
    this.name = "Gemini";
    this.defaultModel = "gemini-2.5-flash";
  }

  isConfigured() {
    return Boolean(process.env.GEMINI_API_KEY && process.env.GEMINI_API_KEY.trim());
  }

  getModel() {
    return process.env.GEMINI_MODEL || this.defaultModel;
  }

  /**
   * Generates response from Gemini
   * @param {string} systemPrompt
   * @param {Array<{role: string, content: string}>} messages
   */
  async generateCompletion(systemPrompt, messages) {
    if (!this.isConfigured()) {
      throw new Error("GEMINI_API_KEY is not configured.");
    }

    const apiKey = process.env.GEMINI_API_KEY.trim();
    const model = this.getModel();
    const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${apiKey}`;

    // Convert messages to Gemini format: 'user' -> 'user', 'assistant' -> 'model'
    const contents = [];

    // Multi-turn messages
    for (const msg of messages) {
      contents.push({
        role: msg.role === "assistant" ? "model" : "user",
        parts: [{ text: msg.content }],
      });
    }

    const payload = {
      systemInstruction: {
        parts: [{ text: systemPrompt }],
      },
      contents,
      generationConfig: {
        temperature: 0.3,
        maxOutputTokens: 850,
      },
    };

    try {
      const response = await axios.post(url, payload, {
        headers: { "Content-Type": "application/json" },
        timeout: 25000,
      });

      const candidate = response.data?.candidates?.[0];
      const text = candidate?.content?.parts?.[0]?.text;

      if (!text) {
        // If candidate was blocked by safety filters
        const finishReason = candidate?.finishReason;
        if (finishReason) {
          throw new Error(`Gemini response stopped: ${finishReason}`);
        }
        throw new Error("Empty response received from Gemini.");
      }

      return {
        text: text.trim(),
        provider: this.name,
        model,
      };
    } catch (err) {
      // If systemInstruction is rejected on older/alternative models, retry by prepending system prompt
      if (err.response?.status === 400 && err.response?.data?.error?.message?.includes("systemInstruction")) {
        return this._retryWithoutSystemInstruction(url, systemPrompt, messages, model);
      }

      const status = err.response?.status;
      const errorMsg = err.response?.data?.error?.message || err.message || "Unknown error";
      const cleanError = new Error(`Gemini API error (Status ${status || "network"}): ${errorMsg}`);
      cleanError.status = status;
      cleanError.isRateLimitOrQuota = status === 429 || errorMsg.toLowerCase().includes("quota") || errorMsg.toLowerCase().includes("rate limit");
      throw cleanError;
    }
  }

  async _retryWithoutSystemInstruction(url, systemPrompt, messages, model) {
    const contents = [];
    if (messages.length > 0) {
      const first = messages[0];
      contents.push({
        role: first.role === "assistant" ? "model" : "user",
        parts: [{ text: `${systemPrompt}\n\n---\n${first.content}` }],
      });
      for (let i = 1; i < messages.length; i++) {
        contents.push({
          role: messages[i].role === "assistant" ? "model" : "user",
          parts: [{ text: messages[i].content }],
        });
      }
    }

    const response = await axios.post(
      url,
      {
        contents,
        generationConfig: { temperature: 0.3, maxOutputTokens: 850 },
      },
      { headers: { "Content-Type": "application/json" }, timeout: 25000 }
    );

    const text = response.data?.candidates?.[0]?.content?.parts?.[0]?.text;
    if (!text) throw new Error("Empty response from Gemini fallback structure.");
    return { text: text.trim(), provider: this.name, model };
  }
}

module.exports = GeminiProvider;
