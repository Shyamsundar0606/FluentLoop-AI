import { apiRequest } from '@/lib/api';
import type { FrenchLevel } from '@/lib/learning-levels';

export type ApiFrenchLevel = Uppercase<FrenchLevel>;

export interface Page<T> {
  items: T[];
  limit: number;
  offset: number;
  total: number;
}

export interface LevelInfo {
  code: ApiFrenchLevel;
  display_name: string;
  description: string;
  rank: number;
  published_course_count: number;
  content_available: boolean;
  draft_preview_course_count: number;
}

export interface Course {
  id: string;
  level: ApiFrenchLevel;
  slug: string;
  title: string;
  description: string;
  explanation_language: string;
  estimated_minutes: number;
  unit_count: number;
  lesson_count: number;
  objectives: { code: string; title: string; description: string; skill_category: string }[];
  content_status: string;
  draft_preview: boolean;
}

export interface Unit {
  id: string;
  course_id: string;
  slug: string;
  title: string;
  description: string;
  sequence_order: number;
  lesson_count: number;
  content_status: string;
  draft_preview: boolean;
}

export interface Lesson {
  id: string;
  unit_id: string;
  slug: string;
  title: string;
  description: string;
  sequence_order: number;
  estimated_minutes: number;
  level: ApiFrenchLevel;
  content_status: string;
  draft_preview: boolean;
}

export interface LessonDetail extends Lesson {
  sections: { type: string; title: string; content: string; sequence_order: number }[];
  objectives: { code: string; title: string; description: string; skill_category: string }[];
  dialogues: Dialogue[];
}

export interface VocabularyItem {
  id: string;
  lemma: string;
  part_of_speech: string;
  grammatical_gender: string | null;
  translation: string;
  definition_french: string;
  ipa: string | null;
  examples: { french_text: string; english_translation: string; context: string | null }[];
}

export interface GrammarTopic {
  id: string;
  slug: string;
  title: string;
  level: ApiFrenchLevel;
  summary: string;
  rules: string[];
  examples: { french_sentence: string; english_translation: string; explanation: string | null }[];
}

export interface ExercisePreview {
  id: string;
  type: string;
  prompt: string;
  instructions: string;
  level: ApiFrenchLevel;
  sequence_order: number;
  options: { id: string; text: string; sequence_order: number }[];
}

export interface Dialogue {
  id: string;
  slug: string;
  title: string;
  level: ApiFrenchLevel;
  context: string;
  english_context: string;
  turns: {
    speaker_label: string;
    sequence_order: number;
    french_text: string;
    english_translation: string;
  }[];
}

export function listLevels(): Promise<LevelInfo[]> {
  return apiRequest('/levels');
}

export function listCourses(level: FrenchLevel): Promise<Page<Course>> {
  return apiRequest(`/courses?level=${level.toUpperCase()}`);
}

export function listUnits(courseId: string): Promise<Page<Unit>> {
  return apiRequest(`/courses/${encodeURIComponent(courseId)}/units?limit=100`);
}

export function listLessons(unitId: string): Promise<Page<Lesson>> {
  return apiRequest(`/units/${encodeURIComponent(unitId)}/lessons?limit=100`);
}

export function getCourse(courseId: string): Promise<Course> {
  return apiRequest(`/courses/${encodeURIComponent(courseId)}`);
}

export function getLesson(lessonId: string): Promise<LessonDetail> {
  return apiRequest(`/lessons/${encodeURIComponent(lessonId)}`);
}

export function getLessonVocabulary(lessonId: string): Promise<Page<VocabularyItem>> {
  return apiRequest(`/lessons/${encodeURIComponent(lessonId)}/vocabulary?limit=100`);
}

export function getLessonGrammar(lessonId: string): Promise<Page<GrammarTopic>> {
  return apiRequest(`/lessons/${encodeURIComponent(lessonId)}/grammar?limit=100`);
}

export function getLessonExercises(lessonId: string): Promise<Page<ExercisePreview>> {
  return apiRequest(`/lessons/${encodeURIComponent(lessonId)}/exercises?limit=100`);
}

export function searchVocabulary(level: FrenchLevel, search: string): Promise<Page<VocabularyItem>> {
  const params = new URLSearchParams({ level: level.toUpperCase(), limit: '100' });
  if (search.trim()) params.set('search', search.trim());
  return apiRequest(`/vocabulary?${params.toString()}`);
}

export function listGrammar(level: FrenchLevel): Promise<Page<GrammarTopic>> {
  return apiRequest(`/grammar?level=${level.toUpperCase()}&limit=100`);
}
