import Link from "next/link";
import { getFacts } from "@/lib/data";

// Force dynamic rendering so facts are always read fresh from disk
export const dynamic = "force-dynamic";
export const revalidate = 0;

const CATEGORY_ORDER = ["environment", "preferences", "tools", "conventions", "constraints"];

const CATEGORY_LABELS: Record<string, string> = {
  environment: "Environment",
  preferences: "Preferences",
  tools: "Tools",
  conventions: "Conventions",
  constraints: "Constraints",
};

export default async function FactsPage() {
  const data = await getFacts();
  const activeFacts = data.facts.filter((f) => f.status === "active");
  const supersededFacts = data.facts.filter((f) => f.status === "superseded");

  // Group by category
  const byCategory: Record<string, typeof activeFacts> = {};
  for (const fact of activeFacts) {
    const cat = fact.category || "other";
    if (!byCategory[cat]) byCategory[cat] = [];
    byCategory[cat].push(fact);
  }

  // Sort categories: known order first, then any new ones alphabetically
  const sortedCategories = Object.keys(byCategory).sort((a, b) => {
    const aIdx = CATEGORY_ORDER.indexOf(a);
    const bIdx = CATEGORY_ORDER.indexOf(b);
    if (aIdx >= 0 && bIdx >= 0) return aIdx - bIdx;
    if (aIdx >= 0) return -1;
    if (bIdx >= 0) return 1;
    return a.localeCompare(b);
  });

  return (
    <main className="max-w-4xl mx-auto px-6 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold mb-1">Facts</h1>
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
          Current truths extracted from conversations. Auto-categorized.
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <div className="rounded-xl p-4" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
          <div className="text-2xl font-bold" style={{ color: "var(--accent)" }}>{activeFacts.length}</div>
          <div className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>Active facts</div>
        </div>
        <div className="rounded-xl p-4" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
          <div className="text-2xl font-bold" style={{ color: "var(--gold)" }}>{supersededFacts.length}</div>
          <div className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>Superseded</div>
        </div>
        <div className="rounded-xl p-4" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
          <div className="text-2xl font-bold" style={{ color: "var(--accent)" }}>{sortedCategories.length}</div>
          <div className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>Categories</div>
        </div>
        <div className="rounded-xl p-4" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
          <div className="text-2xl font-bold" style={{ color: "var(--gold)" }}>
            {data.generated ? new Date(data.generated).toLocaleDateString() : "-"}
          </div>
          <div className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>Last updated</div>
        </div>
      </div>

      {/* Facts by category */}
      <div className="space-y-6">
        {sortedCategories.map((category) => (
          <section key={category}>
            <h2 className="text-sm font-semibold mb-3 uppercase tracking-wider flex items-center gap-2">
              <span style={{ color: "var(--accent)" }}>
                {CATEGORY_LABELS[category] || category}
              </span>
              <span className="text-xs font-normal" style={{ color: "var(--text-muted)" }}>
                ({byCategory[category].length})
              </span>
            </h2>
            <div className="space-y-2">
              {byCategory[category].map((fact) => (
                <div
                  key={fact.id}
                  className="rounded-lg px-4 py-3 text-sm flex items-start gap-3"
                  style={{ background: "var(--surface)", border: "1px solid var(--border)" }}
                >
                  <span style={{ color: "var(--accent)" }} className="mt-0.5">-</span>
                  <div className="flex-1" style={{ color: "var(--text)" }}>{fact.fact}</div>
                  <span className="text-xs shrink-0" style={{ color: "var(--text-muted)" }}>
                    {fact.created || "unknown"}
                  </span>
                </div>
              ))}
            </div>
          </section>
        ))}
      </div>

      {/* Superseded facts */}
      {supersededFacts.length > 0 && (
        <section className="mt-10">
          <h2 className="text-sm font-semibold mb-3 uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
            Superseded ({supersededFacts.length})
          </h2>
          <div className="space-y-2">
            {supersededFacts.map((fact) => (
              <div
                key={fact.id}
                className="rounded-lg px-4 py-3 text-sm flex items-start gap-3 opacity-60"
                style={{ background: "var(--surface)", border: "1px solid var(--border)" }}
              >
                <span style={{ color: "var(--text-muted)" }} className="mt-0.5">-</span>
                <div className="flex-1" style={{ color: "var(--text-muted)" }}>
                  {fact.fact}
                  {fact.superseded_by && (
                    <span className="ml-2 text-xs">
                      superseded by {fact.superseded_by}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}
    </main>
  );
}
