import { expect, test } from '@playwright/test';

test('resume a lesson, submit a server-graded answer, and view saved results', async ({ page }) => {
  const sessionId = 'a1f2c3d4-1111-4111-8111-111111111111';
  const lessonId = 'b2f3c4d5-2222-4222-8222-222222222222';
  const exerciseId = 'c3f4d5e6-3333-4333-8333-333333333333';
  const optionId = 'd4f5e6f7-4444-4444-8444-444444444444';
  const now = '2026-11-02T13:00:00Z';
  let answered = false;
  let completed = false;
  const session = () => ({
    id: sessionId,
    lesson_id: lessonId,
    lesson_content_version: '1.0.1',
    cefr_level: 'A1',
    status: completed ? 'completed' : 'in_progress',
    preview_mode: false,
    started_at: now,
    last_activity_at: now,
    completed_at: completed ? now : null,
    current_section_position: 0,
    current_exercise_position: answered ? 1 : 0,
    total_exercises: 1,
    answered_exercises: answered ? 1 : 0,
    score_points: answered ? 1 : 0,
    max_score_points: 1,
    percentage: answered ? 100 : 0,
    lesson: {
      id: lessonId,
      title: 'Bonjour',
      description: 'Greet someone in French.',
      level: 'A1',
      content_version: '1.0.1',
      estimated_minutes: 5,
      course_title: 'French A1',
      unit_title: 'Introductions',
      objectives: [],
      sections: [],
      vocabulary: [],
      grammar: [],
      dialogues: [],
    },
    exercises: [{
      id: exerciseId,
      exercise_id: exerciseId,
      exercise_order: 1,
      type: 'multiple_choice',
      prompt: 'How do you say hello?',
      instructions: 'Choose one answer.',
      options: [{ id: optionId, text: 'Bonjour', sequence_order: 1 }],
      answered,
      feedback: answered
        ? {
            is_correct: true,
            correct_answer: 'Bonjour',
            explanation: 'Bonjour is a greeting.',
            awarded_points: 1,
            max_points: 1,
            answered_at: now,
          }
        : null,
    }],
  });

  await page.route(`${process.env.PLAYWRIGHT_API_BASE_URL ?? 'http://127.0.0.1:8001/api/v1'}/**`, async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    const headers = {
      'access-control-allow-origin': new URL(process.env.PLAYWRIGHT_BASE_URL ?? 'http://127.0.0.1:3001').origin,
      'access-control-allow-credentials': 'true',
    };
    if (request.method() === 'OPTIONS') {
      await route.fulfill({
        status: 200,
        headers: {
          ...headers,
          'access-control-allow-methods': 'GET, POST',
          'access-control-allow-headers': 'content-type, x-csrf-token',
        },
      });
      return;
    }

    let body: Record<string, unknown> = {};
    if (path.endsWith('/auth/me')) {
      body = {
        user: {
          id: 'e5f6a7b8-5555-4555-8555-555555555555',
          email: 'learner@example.test',
          role: 'learner',
          email_verified: true,
          display_name: 'Test Learner',
          preferred_name: null,
          native_language: 'English',
          country: null,
          timezone: 'UTC',
          learning_goal: null,
          onboarding_completed: true,
          preferences: {
            explanation_language: 'English',
            target_language: 'French',
            current_level: 'a1',
            target_level: null,
            daily_study_minutes: 15,
            learning_focus: 'balanced',
            theme: 'system',
            audio_playback_speed: 1,
          },
        },
      };
    } else if (path.endsWith(`/learning/sessions/${sessionId}/answers`)) {
      answered = true;
      body = {
        session_id: sessionId,
        session_exercise_id: exerciseId,
        is_correct: true,
        correct_answer: 'Bonjour',
        explanation: 'Bonjour is a greeting.',
        awarded_points: 1,
        max_points: 1,
        answered_exercises: 1,
        total_exercises: 1,
        score_points: 1,
        max_score_points: 1,
        percentage: 100,
        idempotent_replay: false,
      };
    } else if (path.endsWith(`/learning/sessions/${sessionId}/complete`)) {
      completed = true;
      body = {
        session_id: sessionId,
        lesson_id: lessonId,
        lesson_title: 'Bonjour',
        cefr_level: 'A1',
        status: 'completed',
        correct_answers: 1,
        incorrect_answers: 0,
        total_questions: 1,
        score_points: 1,
        max_score_points: 1,
        percentage: 100,
        completion_count: 1,
        completed_at: now,
      };
    } else if (path.endsWith(`/learning/sessions/${sessionId}/results`)) {
      body = {
        session_id: sessionId,
        lesson_id: lessonId,
        lesson_title: 'Bonjour',
        cefr_level: 'A1',
        status: 'completed',
        correct_answers: 1,
        incorrect_answers: 0,
        total_questions: 1,
        score_points: 1,
        max_score_points: 1,
        percentage: 100,
        completion_count: 1,
        completed_at: now,
      };
    } else if (path.endsWith(`/learning/sessions/${sessionId}`)) {
      body = session();
    } else if (path.endsWith(`/learning/sessions/${sessionId}/resume`)) {
      body = session();
    } else {
      await route.fulfill({
        status: 404,
        headers,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Not found.' }),
      });
      return;
    }

    await route.fulfill({
      status: 200,
      headers,
      contentType: 'application/json',
      body: JSON.stringify(body),
    });
  });

  await page.goto(`/learning/sessions/${sessionId}`);
  await expect(page.getByRole('heading', { name: 'Bonjour' })).toBeVisible();
  await page.getByLabel('Bonjour').check();
  await page.getByRole('button', { name: 'Submit answer' }).click();
  await expect(page.getByRole('heading', { name: 'Correct!' })).toBeVisible();
  await expect(
    page.getByRole('region', { name: 'Exercise' }).getByText('Bonjour is a greeting.'),
  ).toBeVisible();
  await page.getByRole('button', { name: 'Continue to completion' }).click();
  await page.getByRole('button', { name: 'Complete lesson' }).click();
  await expect(page).toHaveURL(new RegExp(`/learning/results/${sessionId}$`));
  await expect(page.getByText('100%', { exact: true })).toBeVisible();
  await expect(page.getByText('1 correct · 0 incorrect · 1 questions')).toBeVisible();
});
