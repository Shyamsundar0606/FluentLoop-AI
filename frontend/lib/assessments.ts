import { apiRequest } from "@/lib/api";
import type { LearningSession } from "@/lib/learning";
export const MAX_WRITING_CHARACTERS = 8000;

export type AssessmentSkill = "grammar" | "vocabulary" | "reading" | "listening" | "writing";
export type AssessmentDefinition = {
  id: string;
  skill: AssessmentSkill;
  lesson_id: string;
  title: string;
  level: string;
  question_count: number;
  duration_minutes: number;
  content_version: string;
  scoring_policy: string;
  objectives?: { title: string; description: string }[];
};
export type AssessmentHistoryItem = {
  id: string;
  skill: AssessmentSkill;
  title: string;
  level: string;
  status: "in_progress" | "completed" | "abandoned";
  started_at: string;
  completed_at: string | null;
  answered: number;
  question_count: number;
  score_points: number;
  max_score_points: number;
  percentage: number | null;
  draft_preview: boolean;
};
export type AssessmentInsights = {
  level: string;
  sample_limit: number;
  has_older_history: boolean;
  skills: {
    skill: AssessmentSkill;
    completed_sessions: number;
    correct_answers: number;
    answered_questions: number;
    percentage: number | null;
    evidence: string;
  }[];
  notice: string;
  writing?: { submissions: number; sample_limit: number; has_older_history: boolean; evidence: string };
  recommendations?: { title: string; unresolved_questions: number; url: string }[];
  mistake_attempt_window?: number;
};

export type WritingTask = {
  lesson_id: string; title: string; level: string; content_version: string;
  prompt: string; draft_preview: boolean;
};
export type WritingSubmission = {
  id: string; lesson_id: string; level: string; content_version: string;
  prompt: string; original_text: string; created_at: string; draft_preview: boolean;
  feedback_status: "not_requested" | "available" | "unavailable";
  advisory_feedback: { task_completion: string; grammar_suggestions: string[]; vocabulary_suggestions: string[]; clarity: string } | null;
  notice: string;
};

export const assessments = {
  catalog: (level?: string) => apiRequest<{ level: string; draft_preview: boolean; items: AssessmentDefinition[] }>(`/learning/assessments${level ? `?level=${encodeURIComponent(level.toUpperCase())}` : ''}`),
  start: (item: AssessmentDefinition) => apiRequest<LearningSession>("/learning/assessments/sessions", {
    method: "POST", body: JSON.stringify({ skill: item.skill, lesson_id: item.lesson_id }),
  }),
  history: (offset = 0) => apiRequest<{ items: AssessmentHistoryItem[]; next_offset: number | null }>(`/learning/assessments/history?offset=${offset}`),
  insights: () => apiRequest<AssessmentInsights>("/learning/assessments/insights"),
  writingTask: (id: string) => apiRequest<WritingTask>(`/learning/assessments/writing/tasks/${encodeURIComponent(id)}`),
  submitWriting: (lessonId: string, text: string, key: string) => apiRequest<WritingSubmission>("/learning/assessments/writing", {
    method: "POST", body: JSON.stringify({ lesson_id: lessonId, text, idempotency_key: key }),
  }),
  writing: (id: string) => apiRequest<WritingSubmission>(`/learning/assessments/writing/${encodeURIComponent(id)}`),
  writingFeedback: (id: string) => apiRequest<WritingSubmission>(`/learning/assessments/writing/${encodeURIComponent(id)}/feedback`, { method: "POST" }),
  writingHistory: (offset = 0) => apiRequest<{ items: WritingSubmission[]; next_offset: number | null }>(`/learning/assessments/writing/history?offset=${offset}`),
};
