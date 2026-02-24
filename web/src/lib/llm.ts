/**
 * Multi-provider LLM abstraction.
 * Supports Anthropic (Claude), OpenAI (GPT), and xAI (Grok).
 * Makes raw HTTP calls — no SDK dependencies.
 */

export type Provider = "anthropic" | "openai" | "xai";

export interface LLMConfig {
  provider: Provider;
  apiKey: string;
  model?: string;
}

export interface Message {
  role: "user" | "assistant" | "system";
  content: string;
}

const DEFAULT_MODELS: Record<Provider, string> = {
  anthropic: "claude-sonnet-4-6-20250514",
  openai: "gpt-4o",
  xai: "grok-3",
};

const BASE_URLS: Record<Provider, string> = {
  anthropic: "https://api.anthropic.com",
  openai: "https://api.openai.com",
  xai: "https://api.x.ai",
};

export async function chatCompletion(
  config: LLMConfig,
  messages: Message[],
  maxTokens: number = 4096
): Promise<string> {
  const model = config.model || DEFAULT_MODELS[config.provider];

  if (config.provider === "anthropic") {
    return anthropicComplete(config.apiKey, model, messages, maxTokens);
  }
  // OpenAI and xAI use the same API format
  return openaiComplete(config.provider, config.apiKey, model, messages, maxTokens);
}

async function anthropicComplete(
  apiKey: string,
  model: string,
  messages: Message[],
  maxTokens: number
): Promise<string> {
  // Anthropic uses a system param, not a system message
  const systemMsg = messages.find((m) => m.role === "system");
  const userMessages = messages.filter((m) => m.role !== "system");

  const body: Record<string, unknown> = {
    model,
    max_tokens: maxTokens,
    messages: userMessages.map((m) => ({ role: m.role, content: m.content })),
  };
  if (systemMsg) {
    body.system = systemMsg.content;
  }

  const resp = await fetch(`${BASE_URLS.anthropic}/v1/messages`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-api-key": apiKey,
      "anthropic-version": "2023-06-01",
    },
    body: JSON.stringify(body),
  });

  if (!resp.ok) {
    throw new Error(`Anthropic API error (${resp.status}). Check your API key.`);
  }

  const data = await resp.json();
  return data.content?.[0]?.text || "";
}

async function openaiComplete(
  provider: Provider,
  apiKey: string,
  model: string,
  messages: Message[],
  maxTokens: number
): Promise<string> {
  const resp = await fetch(`${BASE_URLS[provider]}/v1/chat/completions`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      model,
      max_tokens: maxTokens,
      messages: messages.map((m) => ({ role: m.role, content: m.content })),
    }),
  });

  if (!resp.ok) {
    throw new Error(`${provider} API error (${resp.status}). Check your API key.`);
  }

  const data = await resp.json();
  return data.choices?.[0]?.message?.content || "";
}

export function getProviderLabel(provider: Provider): string {
  switch (provider) {
    case "anthropic": return "Claude (Anthropic)";
    case "openai": return "ChatGPT (OpenAI)";
    case "xai": return "Grok (xAI)";
  }
}

export function getModelOptions(provider: Provider): string[] {
  switch (provider) {
    case "anthropic":
      return ["claude-sonnet-4-6-20250514", "claude-haiku-4-5-20251001"];
    case "openai":
      return ["gpt-4o", "gpt-4o-mini"];
    case "xai":
      return ["grok-3", "grok-3-mini"];
  }
}
