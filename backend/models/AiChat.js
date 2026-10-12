const mongoose = require("mongoose");

const messageItemSchema = new mongoose.Schema(
  {
    role: {
      type: String,
      enum: ["user", "assistant"],
      required: true,
    },
    content: {
      type: String,
      required: true,
    },
    provider: {
      type: String,
      default: null,
    },
    model: {
      type: String,
      default: null,
    },
    createdAt: {
      type: Date,
      default: Date.now,
    },
  },
  { _id: true }
);

const aiChatSchema = new mongoose.Schema(
  {
    patientId: {
      type: String,
      required: true,
      unique: true,
      index: true,
    },
    messages: [messageItemSchema],
  },
  { timestamps: true }
);

module.exports = mongoose.model("AiChat", aiChatSchema);
