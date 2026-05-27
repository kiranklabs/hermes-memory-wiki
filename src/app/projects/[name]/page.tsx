import Link from "next/link";
import { getProject, getSession } from "@/lib/data";
import { formatDate } from "@/lib/format";

export default async function ProjectPage({
  params,
}: {
  params: Promise<{ name: string }>;
}) {
  const { name } = await params;
  const project = await getProject(name);

  if (!project) {
    return (
      <main className="max-w-4xl mx-auto px-6 py-8">
        <h1 className="text-2xl font-bold">Project not found</h1>
      </main>
    );
  }

  const sessions = (
    await Promise.all(
      project.sessions.map(async (id) => {
        const s = await getSession(id);
        return s ?? null;
      })
    )
  ).filter((s): s is NonNullable<typeof s> => s !== null);

  return (
    <main className="max-w-4xl mx-auto px-6 py-8">
      <header className="mb-8">
        <h1 className="text-2xl font-bold flex items-center gap-3">
          <span className="text-3xl">{project.emoji}</span>
          {project.name}
        </h1>
        <p className="mt-2" style={{ color: "var(--text-muted)" }}>
          {project.description}
        </p>
        <p className="mt-1 text-sm" style={{ color: "var(--text-muted)" }}>
          {project.session_count} session{project.session_count !== 1 ? "s" : ""}
        </p>
      </header>

      <div className="space-y-4">
        {sessions.map((session) => {
          const displayTitle = session.auto_title || session.title || "(untitled)";
          return (
            <Link
              key={session.id}
              href={`/sessions/${session.id}`}
              style={{ background: "var(--surface)", border: "1px solid var(--border)" }}
              className="block rounded-lg p-5 transition-colors hover:border-[var(--accent)]"
            >
              <h3 className="font-semibold text-lg">{displayTitle}</h3>
              {session.summary && (
                <p className="text-sm mt-2 leading-relaxed" style={{ color: "var(--text-muted)" }}>
                  {session.summary}
                </p>
              )}
              <div
                className="text-sm mt-3 flex items-center gap-3 flex-wrap"
                style={{ color: "var(--text-muted)" }}
              >
                <span>{formatDate(session.started_at)}</span>
                <span>{session.message_count} msg{session.message_count !== 1 ? "s" : ""}</span>
                <span className="capitalize">{session.source}</span>
              </div>
            </Link>
          );
        })}
      </div>
    </main>
  );
}
