import Link from "next/link";
import { getDecisions } from "@/lib/data";

// Force dynamic rendering so decisions are always read fresh from disk
export const dynamic = "force-dynamic";
export const revalidate = 0;

export default async function DecisionsPage() {
  const data = await getDecisions();
  const activeDecisions = data.decisions.filter((d) => d.status === "active");
  const supersededDecisions = data.decisions.filter((d) => d.status === "superseded");

  // Group active by category
  const byCategory: Record<string, typeof activeDecisions> = {};
  for (const dec of activeDecisions) {
    const cat = dec.category || "other";
    if (!byCategory[cat]) byCategory[cat] = [];
    byCategory[cat].push(dec);
  }

  return (
    <main className="max-w-4xl mx-auto px-6 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold mb-1">Decisions</h1>
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
          Decision trail with supersedence. When a decision is replaced, the old one is marked superseded, not deleted.
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <div className="rounded-xl p-4" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
          <div className="text-2xl font-bold" style={{ color: "var(--accent)" }}>{activeDecisions.length}</div>
          <div className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>Active decisions</div>
        </div>
        <div className="rounded-xl p-4" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
          <div className="text-2xl font-bold" style={{ color: "var(--gold)" }}>{supersededDecisions.length}</div>
          <div className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>Superseded</div>
        </div>
        <div className="rounded-xl p-4" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
          <div className="text-2xl font-bold" style={{ color: "var(--accent)" }}>{Object.keys(byCategory).length}</div>
          <div className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>Categories</div>
        </div>
        <div className="rounded-xl p-4" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
          <div className="text-2xl font-bold" style={{ color: "var(--gold)" }}>
            {data.generated ? new Date(data.generated).toLocaleDateString() : "-"}
          </div>
          <div className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>Last updated</div>
        </div>
      </div>

      {/* Supersedence trail visualization */}
      {supersededDecisions.length > 0 && (
        <div className="mb-8 rounded-xl p-4" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
          <h2 className="text-sm font-semibold mb-3 uppercase tracking-wider" style={{ color: "var(--gold)" }}>
            Supersedence Trail
          </h2>
          <div className="space-y-2">
            {supersededDecisions.map((dec) => (
              <div key={dec.id} className="text-sm flex items-center gap-2" style={{ color: "var(--text-muted)" }}>
                <span className="line-through">{dec.decision}</span>
                <span style={{ color: "var(--text)", margin: "0 4px" }}>{"→"}</span>
                <span style={{ color: "var(--accent)" }}>
                  {activeDecisions.find((a) => a.id === dec.superseded_by)?.decision || "replaced"}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Active decisions by category */}
      <div className="space-y-6">
        {Object.entries(byCategory).map(([category, decisions]) => (
          <section key={category}>
            <h2 className="text-sm font-semibold mb-3 uppercase tracking-wider flex items-center gap-2">
              <span style={{ color: "var(--accent)" }}>{category}</span>
              <span className="text-xs font-normal" style={{ color: "var(--text-muted)" }}>
                ({decisions.length})
              </span>
            </h2>
            <div className="space-y-2">
              {decisions.map((dec) => (
                <div
                  key={dec.id}
                  className="rounded-lg px-4 py-3 text-sm flex items-start gap-3"
                  style={{ background: "var(--surface)", border: "1px solid var(--border)" }}
                >
                  <span style={{ color: "var(--accent)" }} className="mt-0.5">-</span>
                  <div className="flex-1" style={{ color: "var(--text)" }}>
                    {dec.decision}
                    {dec.reason && (
                      <div className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
                        Reason: {dec.reason}
                      </div>
                    )}
                  </div>
                  <span className="text-xs shrink-0" style={{ color: "var(--text-muted)" }}>
                    {dec.created || "unknown"}
                  </span>
                </div>
              ))}
            </div>
          </section>
        ))}
      </div>
    </main>
  );
}
