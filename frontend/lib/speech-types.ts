export type ChatResponse = {
  answer: string;
  grounding_status: string;
  sources: {
    lesson_id: string;
    title: string;
    url: string;
    draft_preview: boolean;
  }[];
};
