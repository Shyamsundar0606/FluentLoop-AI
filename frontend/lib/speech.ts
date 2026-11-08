import { apiRequest, API_BASE_URL } from "./api";
import type { ChatResponse } from "./speech-types";
export type Audio = {
  status: string;
  asset_id: string | null;
  spoken_text?: string | null;
  duration_ms?: number | null;
};
export type Transcript = {
  status: string;
  text: string;
  language: string | null;
  duration_ms: number;
  audio_quality: string[];
};
export type Turn = {
  id: string;
  request_id: string;
  transcript: string;
  transcription_status: string;
  transcription: Transcript | null;
  review?: {
    source_turn_id: string;
    original_text: string;
    confirmed_text: string;
    confirmed_at: string;
    edited?: boolean;
  } | null;
  tutor: ChatResponse | null;
  tutor_audio: Audio;
  input_audio_id: string | null;
  status: string;
  created_at: string;
};
export type Session = {
  id: string;
  conversation_id: string;
  title: string;
  cefr_level: string;
  scenario_id: string | null;
  status: string;
  draft_preview: boolean;
  last_activity_at: string;
  turns: Turn[];
  has_more_turns: boolean;
  opening_french?: string | null;
};
export type Target = {
  id: string;
  text: string;
  english: string;
  level: string;
  lesson_id: string;
  content_version: string;
  draft_preview: boolean;
  guidance: string;
};
export type Attempt = {
  id: string;
  request_id: string;
  target: Target;
  recognized_text: string;
  recognition_match: boolean | null;
  recognition_feedback: string;
  assessment_status: string;
  acoustic_score: null;
  limitations: string;
  input_audio_id: string | null;
  created_at: string;
  transcription: Transcript;
};
export type Progress = {
  target: Target;
  attempt_count: number;
  last_practiced_at: string;
  latest_assessment_status: string;
  latest_validated_score: null;
};
export const audioURL = (id: string) => `${API_BASE_URL}/speech/audio/${id}`;
export const speech = {
  health: () =>
    apiRequest<{ asr: boolean; tts: boolean; acoustic_assessment: string }>(
      "/speech/health",
    ),
  sessions: (offset = 0) =>
    apiRequest<Session[]>(`/speech/sessions?offset=${offset}`),
  get: (id: string, offset = 0) =>
    apiRequest<Session>(`/speech/sessions/${id}?offset=${offset}`),
  start: (scenario_id?: string) =>
    apiRequest<Session>("/speech/sessions", {
      method: "POST",
      body: JSON.stringify({ scenario_id: scenario_id || null }),
    }),
  startForConversation: (conversation_id: string) =>
    apiRequest<Session>("/speech/sessions", {
      method: "POST", body: JSON.stringify({ conversation_id }),
    }),
  scenarios: () =>
    apiRequest<
      {
        id: string;
        title: string;
        cefr_level: string;
        description: string;
        tutor_role: string;
        learner_role: string;
      }[]
    >("/speech/scenarios"),
  turn: (
    id: string,
    audio: Blob,
    request_id: string,
    retain_audio: boolean,
    signal?: AbortSignal,
  ) => {
    const form = new FormData();
    form.append("audio", audio, "recording");
    form.append("request_id", request_id);
    form.append("retain_audio", String(retain_audio));
    return apiRequest<Turn>(`/speech/sessions/${id}/turns`, {
      method: "POST",
      body: form,
      signal,
    });
  },
  text: (id: string, message: string, request_id: string, reviewed_turn_id?: string) =>
    apiRequest<Turn>(`/speech/sessions/${id}/text`, {
      method: "POST",
      body: JSON.stringify({ message, request_id, reviewed_turn_id }),
    }),
  retryAudio: (id: string, tid: string) =>
    apiRequest<Turn>(`/speech/sessions/${id}/turns/${tid}/audio`, {
      method: "POST",
    }),
  complete: (id: string) =>
    apiRequest<Session>(`/speech/sessions/${id}/complete`, { method: "POST" }),
  targets: () => apiRequest<Target[]>("/speech/pronunciation/targets"),
  target: (id: string) =>
    apiRequest<Target>(
      `/speech/pronunciation/targets/${encodeURIComponent(id)}`,
    ),
  attempt: (
    target_id: string,
    audio: Blob,
    request_id: string,
    retain_audio: boolean,
    signal?: AbortSignal,
  ) => {
    const form = new FormData();
    form.append("audio", audio, "recording");
    form.append("target_id", target_id);
    form.append("request_id", request_id);
    form.append("retain_audio", String(retain_audio));
    return apiRequest<Attempt>("/speech/pronunciation/attempts", {
      method: "POST",
      body: form,
      signal,
    });
  },
  attempts: (offset = 0, targetId?: string) =>
    apiRequest<Attempt[]>(
      `/speech/pronunciation/history?offset=${offset}${targetId ? `&target_id=${encodeURIComponent(targetId)}` : ""}`,
    ),
  progress: () => apiRequest<Progress[]>("/speech/pronunciation/progress"),
  synthesize: (text: string, target_id?: string) =>
    apiRequest<Audio>("/speech/synthesize", {
      method: "POST",
      body: JSON.stringify({
        text,
        target_id: target_id || null,
        language: "fr",
      }),
    }),
  deleteAudio: (id: string) =>
    apiRequest(`/speech/audio/${id}`, { method: "DELETE" }),
};
