import { apiRequest } from "./api";

export type TutorMode =
  | "tutor"
  | "vocabulary"
  | "grammar"
  | "correction"
  | "roleplay";
export const tutorModes: [TutorMode, string][] = [
  ["tutor", "Ask the tutor"],
  ["vocabulary", "Vocabulary help"],
  ["grammar", "Grammar help"],
  ["correction", "Sentence correction"],
  ["roleplay", "French conversation"],
];
export type Source = {
  lesson_id: string;
  title: string;
  url: string;
  draft_preview: boolean;
};
export type Correction = {
  original_text: string;
  corrected_text: string;
  has_errors: boolean;
  explanations: string[];
  alternative_expressions: string[];
};
export type TutorMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  response_status: string;
  grounding_status: string;
  request_id: string | null;
  sources: Source[];
  correction: Correction | null;
};
export type Conversation = {
  id: string;
  title: string;
  mode: TutorMode;
  cefr_level: string;
  scenario_id: string | null;
  status: string;
  preview_mode: boolean;
  updated_at: string;
  messages: TutorMessage[];
  has_more_messages: boolean;
};
export type Scenario = {
  id: string;
  title: string;
  cefr_level: string;
  description: string;
  tutor_role: string;
  learner_role: string;
  provenance: string;
  opening_situation: string;
  suggested_vocabulary: string[];
};
export type Recommendation = {
  id: string;
  topic: string;
  reason: string;
  cefr_level: string;
  lesson: Source | null;
  suggested_action: string;
};
export const ai = {
  health: () =>
    apiRequest<{ available: boolean; message: string }>("/ai/health"),
  conversations: (mode = "", offset = 0) =>
    apiRequest<Conversation[]>(
      `/ai/conversations?limit=20&offset=${offset}${mode ? `&mode=${mode}` : ""}`,
    ),
  create: (mode: TutorMode, title?: string) =>
    apiRequest<Conversation>("/ai/conversations", {
      method: "POST",
      body: JSON.stringify({ mode, title: title || "French practice" }),
    }),
  get: (id: string, before?: string) =>
    apiRequest<Conversation>(
      `/ai/conversations/${id}${before ? `?before=${before}` : ""}`,
    ),
  send: (id: string, message: string, request_id: string) =>
    apiRequest(`/ai/conversations/${id}/messages`, {
      method: "POST",
      body: JSON.stringify({ message, request_id }),
    }),
  archive: (id: string) =>
    apiRequest(`/ai/conversations/${id}/archive`, { method: "POST" }),
  rename: (id: string, title: string) =>
    apiRequest(`/ai/conversations/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ title }),
    }),
  scenarios: (level?: string) =>
    apiRequest<Scenario[]>(`/ai/scenarios${level ? `?level=${level}` : ""}`),
  start: (id: string) =>
    apiRequest<Conversation>(`/ai/scenarios/${id}/start`, { method: "POST" }),
  recommendations: () => apiRequest<Recommendation[]>("/ai/recommendations"),
  refreshRecommendations: () =>
    apiRequest<Recommendation[]>("/ai/recommendations/refresh", {
      method: "POST",
    }),
};
