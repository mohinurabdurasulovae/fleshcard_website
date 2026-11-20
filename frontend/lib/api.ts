import useSWR, { type SWRConfiguration } from "swr";
import type { Category } from "./utils";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function handle(r: Response) {
  if (!r.ok) {
    let msg = r.statusText;
    try {
      const j = await r.json();
      msg = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail ?? j);
    } catch {}
    throw new ApiError(r.status, msg || `Request failed (${r.status})`);
  }
  return r.json();
}

export const fetcher = (url: string) => fetch(url).then(handle);

export const api = {
  get: <T = any>(url: string): Promise<T> => fetch(url).then(handle),
  post: <T = any>(url: string, body?: unknown): Promise<T> =>
    fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body ?? {}) }).then(handle),
  patch: <T = any>(url: string, body?: unknown): Promise<T> =>
    fetch(url, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body ?? {}) }).then(handle),
  del: <T = any>(url: string): Promise<T> => fetch(url, { method: "DELETE" }).then(handle),
  upload: <T = any>(url: string, form: FormData): Promise<T> => fetch(url, { method: "POST", body: form }).then(handle),
};

export function useApi<T = any>(url: string | null, config?: SWRConfiguration) {
  return useSWR<T>(url, fetcher, { revalidateOnFocus: false, keepPreviousData: true, ...config });
}

// ------------------------------------------------------------------ types
export interface SourceRef { id: number; key: string; name: string; category?: Category }
export interface TopicRef { id: number; slug: string; name: string; score?: number }

export interface DocBrief {
  id: number; title: string; subject: string; category: Category; format: string; url: string; file_url: string;
  author: string; license: string; summary: string; word_count: number; page_count: number; status: string;
  review_status: string; error: string; attempts: number; has_file: boolean; source: SourceRef | null;
  course: { id: number; code: string; title: string; university: string } | null; topics: TopicRef[];
  flashcard_count: number | null; created_at: string; snippet?: string;
}

export interface Section { title: string; level: number; page: number | null; start: number; end: number; index?: number; text?: string }

export interface DocDetail extends DocBrief {
  sections: Section[];
  topic_sections: { topic: TopicRef; score: number; hits: number; sections: number[] }[];
  card_types: Record<string, number>;
  similar: (DocBrief & { similarity: number })[];
  katex_macros: Record<string, string>;
  repo_path?: string;
}

export interface Course {
  id: number; code: string; title: string; subject: string; university: string; url: string; description: string;
  instructors: string; term: string; license: string; source: SourceRef; category: Category;
  document_count: number | null; flashcard_count: number | null;
}

export interface Flashcard {
  id: number; document_id: number; category: Category; subject: string; card_type: string; question: string;
  answer: string; excerpt: string; section_index: number | null; section_title: string; page: number | null;
  char_start: number | null; char_end: number | null; generator: string; confidence: number; topic: TopicRef | null;
  document: { id: number; title: string; url: string; format: string; author: string; license: string; source: string;
    course: string; university: string; katex_macros: Record<string, string> };
  evaluations?: { count: number; mean_score: number | null };
}

export interface Meta {
  subjects: string[];
  criteria: { key: string; label: string; description: string }[];
  rating_scale: { level: number; label: string; score: number }[];
  card_types: { key: string; label: string }[];
  ai: { enabled: boolean; provider: string; model: string };
}

export interface Job {
  id: number; status: string; kind: string; subjects: string[]; source_keys: string[]; options: Record<string, any>;
  total: number; processed: number; succeeded: number; failed: number; skipped: number; current: string;
  progress: number; created_at: string; started_at: string | null; finished_at: string | null; log_tail: string[]; log?: string[];
}

export function useMeta() {
  return useApi<Meta>("/api/meta", { revalidateIfStale: false });
}
