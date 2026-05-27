import { promises as fs } from "fs";
import path from "path";

const DATA_DIR = path.join(process.cwd(), "data");
const SESSIONS_DIR = path.join(DATA_DIR, "sessions");

export interface SessionMeta {
  id: string;
  title: string;
  auto_title: string | null;
  summary: string | null;
  project: string;
  source: string;
  started_at: string | null;
  ended_at: string | null;
  date: string | null;
  message_count: number;
  tool_call_count: number;
  input_tokens: number;
  output_tokens: number;
}

export interface SessionMsg {
  role: string;
  content: string;
  tool_name: string | null;
  timestamp: string | null;
}

export interface SessionDetail extends SessionMeta {
  messages: SessionMsg[];
}

export interface Project {
  name: string;
  emoji: string;
  description: string;
  session_count: number;
  sessions: string[];
}

export interface DailyLog {
  date: string;
  session_count: number;
  sessions: SessionMeta[];
  projects: string[];
}

export interface DailyLogDetail extends Omit<DailyLog, "sessions"> {
  sessions: SessionDetail[];
}

export interface SearchResult {
  score: number;
  type: "session";
  id: string;
  title: string;
  snippet: string;
  date: string | null;
  source: string;
  project: string;
}

async function readJSON<T>(filePath: string): Promise<T | null> {
  try {
    const raw = await fs.readFile(filePath, "utf-8");
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

export async function getSessions(): Promise<SessionMeta[]> {
  const data = await readJSON<SessionMeta[]>(path.join(DATA_DIR, "sessions.json"));
  return data ?? [];
}

export async function getProjects(): Promise<Project[]> {
  const data = await readJSON<Project[]>(path.join(DATA_DIR, "projects.json"));
  return data ?? [];
}

export async function getDailyLogs(): Promise<DailyLog[]> {
  const data = await readJSON<DailyLog[]>(path.join(DATA_DIR, "daily_logs.json"));
  return data ?? [];
}

export async function getSession(id: string): Promise<SessionDetail | null> {
  try {
    return await readJSON<SessionDetail>(path.join(SESSIONS_DIR, `${id}.json`));
  } catch {
    return null;
  }
}

export async function getProject(name: string): Promise<Project | null> {
  const projects = await getProjects();
  return projects.find((p) => p.name === decodeURIComponent(name)) ?? null;
}

export async function getDailyLog(date: string): Promise<DailyLogDetail | null> {
  const logs = await getDailyLogs();
  const log = logs.find((l) => l.date === decodeURIComponent(date));
  if (!log) return null;
  const sessions = (
    await Promise.all(
      log.sessions.map(async (s) => {
        const detail = await getSession(s.id);
        return detail ?? null;
      })
    )
  ).filter((s): s is SessionDetail => s !== null);
  return { ...log, sessions };
}

export async function searchAll(query: string): Promise<SearchResult[]> {
  const q = query.toLowerCase().trim();
  if (!q) return [];

  const sessions = await getSessions();
  const results: SearchResult[] = [];

  for (const s of sessions) {
    const title = (s.auto_title || s.title || "").toLowerCase();
    const summary = (s.summary || "").toLowerCase();
    const project = (s.project || "").toLowerCase();

    let score = 0;
    if (title.includes(q)) score += 10;
    if (summary.includes(q)) score += 5;
    if (project.includes(q)) score += 3;

    if (score > 0) {
      let snippet = s.summary || "";
      if (!snippet) {
        const detail = await getSession(s.id);
        if (detail) {
          const firstUser = detail.messages.find((m) => m.role === "user");
          snippet = firstUser?.content.slice(0, 150) || "";
        }
      }
      results.push({ score, type: "session", id: s.id,
        title: s.auto_title || s.title || "(untitled)",
        snippet, date: s.date, source: s.source, project: s.project,
      });
    }
  }

  results.sort((a, b) => b.score - a.score);
  return results;
}
