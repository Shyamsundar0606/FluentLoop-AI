import { apiRequest } from '@/lib/api';
import type { ApiFrenchLevel, Page } from '@/lib/curriculum';

export interface SessionExercise {
  tiles?: { id: string; text: string }[];
  left_items?: { id: string; text: string }[];
  right_items?: { id: string; text: string }[];
  submitted_answer?: ExerciseAnswer | null;
  id: string;
  exercise_id: string | null;
  exercise_order: number;
  type: string;
  prompt: string;
  instructions: string;
  options: { id: string; text: string; sequence_order: number }[];
  answered: boolean;
  feedback: {
    is_correct: boolean;
    correct_answer: string;
    explanation: string;
    awarded_points: number;
    max_points: number;
    answered_at: string;
  } | null;
}

export interface LearningSession {
  activity_key?: string;
  id: string;
  lesson_id: string;
  lesson_content_version: string;
  cefr_level: ApiFrenchLevel;
  status: 'in_progress' | 'completed' | 'abandoned';
  preview_mode: boolean;
  started_at: string;
  last_activity_at: string;
  completed_at: string | null;
  current_section_position: number;
  current_exercise_position: number;
  total_exercises: number;
  answered_exercises: number;
  score_points: number;
  max_score_points: number;
  percentage: number;
  lesson: {
    learning_flow_version?: number;
    id: string;
    title: string;
    description: string;
    level: ApiFrenchLevel;
    content_version: string;
    estimated_minutes: number;
    course_title: string;
    unit_title: string;
    objectives: { title: string; description: string }[];
    sections: { type: string; title: string; content: string; sequence_order: number }[];
    vocabulary: {
      lemma: string;
      part_of_speech: string;
      grammatical_gender: string | null;
      translation: string;
      definition_french: string;
      ipa: string | null;
    }[];
    grammar: {
      title: string;
      summary: string;
      teaching?: {
        forms?: [string, string][];
        recap?: string;
        common_mistakes?: { incorrect: string; correct: string; explanation: string }[];
        vocabulary_examples?: Record<string, [string, string]>;
      };
      rules: {
        explanation: string;
        examples: { french: string; english: string }[];
      }[];
    }[];
    dialogues: {
      title: string;
      context: string;
      turns: { speaker: string; french: string; english: string }[];
    }[];
  };
  exercises: SessionExercise[];
}

export function saveLearningPosition(sessionId: string, position: number): Promise<LearningSession> {
  return apiRequest(`/learning/sessions/${encodeURIComponent(sessionId)}/position`, {
    method: 'POST', body: JSON.stringify({ position }),
  });
}

export function learningReturnUrl(session: Pick<LearningSession, 'cefr_level' | 'lesson_id' | 'activity_key'>) {
  const topic = grammarPracticeTopic(session.activity_key);
  if (topic) return `/grammar?level=${session.cefr_level.toLowerCase()}&topic=${encodeURIComponent(topic)}`;
  const path = session.activity_key?.startsWith('practice:') ? '/practice' : '/courses';
  return `${path}?level=${session.cefr_level.toLowerCase()}&lesson=${encodeURIComponent(session.lesson_id)}`;
}

export function grammarPracticeTopic(activityKey?: string) {
  return activityKey?.match(/^practice:grammar:([0-9a-f-]{36}):/i)?.[1];
}

export function submittedAnswerText(exercise: SessionExercise): string {
  const answer = exercise.submitted_answer;
  if (!answer) return 'Saved answer';
  if ('text_answer' in answer) return answer.text_answer;
  if ('selected_option_id' in answer) return exercise.options.find(o => o.id === answer.selected_option_id)?.text ?? 'Saved choice';
  if ('tile_ids' in answer) return answer.tile_ids.map(id => exercise.tiles?.find(t => t.id === id)?.text ?? 'Saved word').join(' ');
  return Object.entries(answer.matches).map(([l, r]) => `${exercise.left_items?.find(t => t.id === l)?.text ?? 'Saved item'} → ${exercise.right_items?.find(t => t.id === r)?.text ?? 'Saved match'}`).join('; ');
}

export type ExerciseAnswer = { selected_option_id: string } | { text_answer: string } | { tile_ids: string[] } | { matches: Record<string, string> };

export function submitExerciseAnswer(sessionId: string, exerciseId: string, answer: ExerciseAnswer, key: string): Promise<AnswerResult> {
  return apiRequest(`/learning/sessions/${encodeURIComponent(sessionId)}/answers`, {
    method: 'POST', body: JSON.stringify({ session_exercise_id: exerciseId, ...answer, idempotency_key: key }),
  });
}

export interface SessionListItem {
  id: string;
  lesson_id: string;
  lesson_title: string;
  cefr_level: ApiFrenchLevel;
  lesson_content_version: string;
  status: 'in_progress' | 'completed' | 'abandoned';
  started_at: string;
  last_activity_at: string;
  completed_at: string | null;
  total_exercises: number;
  answered_exercises: number;
  percentage: number;
}

export interface LearningDashboard {
  current_level: ApiFrenchLevel;
  lessons_started: number;
  lessons_completed: number;
  lessons_in_progress: number;
  active_sessions: SessionListItem[];
  total_answered_exercises: number;
  average_completed_session_score: number;
  recent_activity: {
    event_type: string;
    lesson_id: string | null;
    created_at: string;
    metadata: Record<string, unknown>;
  }[];
  learning_path: {
    lesson_id: string;
    title: string;
    level: ApiFrenchLevel;
    status: 'not_started' | 'in_progress' | 'completed';
  }[];
}

export interface LessonProgress {
  lesson_id: string;
  lesson_title: string;
  cefr_level: ApiFrenchLevel;
  status: 'not_started' | 'in_progress' | 'completed';
  first_started_at: string | null;
  last_studied_at: string | null;
  completed_at: string | null;
  best_score: number;
  latest_score: number;
  completion_count: number;
}

export interface AnswerResult {
  session_id: string;
  session_exercise_id: string;
  is_correct: boolean;
  correct_answer: string;
  explanation: string;
  awarded_points: number;
  max_points: number;
  answered_exercises: number;
  total_exercises: number;
  score_points: number;
  max_score_points: number;
  percentage: number;
  idempotent_replay: boolean;
}

export interface CompletionResult {
  activity_key?: string;
  session_id: string;
  lesson_id: string;
  lesson_title: string;
  cefr_level: ApiFrenchLevel;
  status: 'completed';
  correct_answers: number;
  incorrect_answers: number;
  total_questions: number;
  score_points: number;
  max_score_points: number;
  percentage: number;
  completion_count: number;
  completed_at: string;
}

export function startLearningSession(lessonId: string): Promise<LearningSession> {
  return apiRequest('/learning/sessions', {
    method: 'POST',
    body: JSON.stringify({ lesson_id: lessonId }),
  });
}

export function getLearningSession(sessionId: string): Promise<LearningSession> {
  return apiRequest(`/learning/sessions/${encodeURIComponent(sessionId)}`);
}

export function resumeLearningSession(sessionId: string): Promise<LearningSession> {
  return apiRequest(`/learning/sessions/${encodeURIComponent(sessionId)}/resume`, {
    method: 'POST',
  });
}

export function listLearningSessions(
  status: SessionListItem['status'] = 'in_progress',
): Promise<Page<SessionListItem>> {
  return apiRequest(`/learning/sessions?status=${status}&limit=50`);
}

export function submitLearningAnswer(
  sessionId: string,
  sessionExerciseId: string,
  selectedOptionId: string,
  idempotencyKey: string,
): Promise<AnswerResult> {
  return apiRequest(`/learning/sessions/${encodeURIComponent(sessionId)}/answers`, {
    method: 'POST',
    body: JSON.stringify({
      session_exercise_id: sessionExerciseId,
      selected_option_id: selectedOptionId,
      idempotency_key: idempotencyKey,
    }),
  });
}

export function completeLearningSession(sessionId: string): Promise<CompletionResult> {
  return apiRequest(`/learning/sessions/${encodeURIComponent(sessionId)}/complete`, {
    method: 'POST',
  });
}

export function getLearningResults(sessionId: string): Promise<CompletionResult> {
  return apiRequest(`/learning/sessions/${encodeURIComponent(sessionId)}/results`);
}

export function abandonLearningSession(sessionId: string): Promise<void> {
  return apiRequest(`/learning/sessions/${encodeURIComponent(sessionId)}/abandon`, {
    method: 'POST',
  });
}

export function getLearningDashboard(): Promise<LearningDashboard> {
  return apiRequest('/learning/dashboard');
}

export function getLearningProgress(): Promise<Page<LessonProgress>> {
  return apiRequest('/learning/progress?limit=100');
}

export function getLessonProgress(lessonId: string): Promise<LessonProgress> {
  return apiRequest(`/learning/progress/lessons/${encodeURIComponent(lessonId)}`);
}
