import { apiRequest } from './api';

export type StudyActivity = {
  id: string; activity_type: string; title: string; reason: string;
  estimated_minutes: number; status: string; sequence_order: number;
  draft_preview: boolean; url: string | null; completion_available: boolean;
};
export type DailyPlan = {
  id: string; cefr_level: string; local_study_date: string; timezone_name: string;
  target_minutes: number; planned_minutes: number; status: string;
  generation: number; activities: StudyActivity[]; unavailable_activity_count: number;
  due_review_count: number;
};
export type Due = {
  cefr_level: string; due_count: number; available_vocabulary_count: number;
  new_vocabulary_count: number; next_due_at: string | null;
};
export type Question = {item_id: string; card_id: string; sequence_order: number; prompt: string; draft_preview: boolean};
export type Feedback = {id: string; item_id: string; card_id: string; submitted_answer: string;
  is_correct: boolean; correct_answer: string; explanation: string; next_due_at: string; recall_rating: string | null};
export type ReviewSession = {id: string; cefr_level: string; status: string; total_cards: number;
  answered_cards: number; unavailable_cards: number; current_question: Question | null; feedback: Feedback[]};
export type ReviewProgress = {reviews_completed: number; cards_due: number; vocabulary_items_studied: number};
export type ReviewHistory = {id: string; cefr_level: string; is_correct: boolean; reviewed_at: string; next_due_at: string};
export const study = {
  today: () => apiRequest<DailyPlan | null>('/study/today'),
  generate: (request_id: string, regenerate = false) => apiRequest<DailyPlan>('/study/today/generate', {method:'POST',body:JSON.stringify({request_id,regenerate})}),
  start: (id: string) => apiRequest<StudyActivity>(`/study/activities/${id}/start`, {method:'POST'}),
  due: () => apiRequest<Due>('/review/due'),
  startReview: (request_id: string) => apiRequest<ReviewSession>('/review/sessions', {method:'POST',body:JSON.stringify({request_id,limit:3})}),
  session: (id: string) => apiRequest<ReviewSession>(`/review/sessions/${id}`),
  answer: (id: string, item_id: string, answer: string, request_id: string, recall_rating: string) => apiRequest<Feedback>(`/review/sessions/${id}/answers`,{method:'POST',body:JSON.stringify({item_id,answer,request_id,recall_rating})}),
  complete: (id: string) => apiRequest<ReviewSession>(`/review/sessions/${id}/complete`,{method:'POST'}),
  progress: () => apiRequest<ReviewProgress>('/review/progress'),
  history: (offset = 0) => apiRequest<{items:ReviewHistory[]}>('/review/history?limit=20&offset='+offset),
  plans: () => apiRequest<{items:DailyPlan[]}>('/study/plans?limit=20'),
};
