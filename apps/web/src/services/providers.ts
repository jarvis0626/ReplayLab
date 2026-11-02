import type { Provider } from "../types";

export const usesCloud = (provider?: Provider) =>
  provider?.mode === "meta" || provider?.mode === "nvidia";

export const providerName = (provider?: Provider) =>
  provider?.mode === "nvidia" ? "NVIDIA" : provider?.mode === "meta" ? "Meta" : "Local OCR";

export const providerModels = (provider?: Provider) =>
  provider?.model || provider?.models?.join(", ") || "Configured model";
