import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";

type CaseRow = {
  id: string;
  created_at: string;
  endpoint_id: string;
  schema_version: string;
  status: string;
  report: string;
  disposition: string | null;
};

type Evidence = {
  id: string;
  kind: string;
  source: string;
  captured_at: string;
  redacted_content: unknown;
  digest: string;
};

type CaseDetail = {
  id: string;
  created_at: string;
  endpoint_id: string;
  schema_version: string;
  report: string;
  payload: Record<string, unknown>;
  status: string;
  replay: boolean;
  origin: string;
  disposition: string | null;
  evidence: Evidence[];
};

type Finding = { category: string; observed_fact: string; confidence: string };
type SchemaError = { field: string; code: string; message: string; allowed?: unknown[] };
type InvestigateOut = {
  schema_snapshot: { version: string; known: boolean; stale: boolean };
  schema_errors: SchemaError[];
  queue: { request_id: string; status: string; verdict: string }[];
  webhook: { present: boolean; verified: boolean; reason: string };
  findings: Finding[];
  diagnostics_used: string[];
};
type DispositionOut = {
  disposition: string;
  confidence: string;
  uncertainty: string;
  missing?: string[];
  corrected_payload?: Record<string, unknown>;
  packet?: Record<string, unknown>;
};
type AuditEvent = { actor: string; event_type: string; timestamp: string };
type ReplayOut = {
  mode: string; badge: string; fixture_source: string;
  submitted_at: string; completed_at: string; disposition: string;
};

const API = import.meta.env.VITE_API_URL ?? "";
const WHERE: Record<string, string> = {
  "schema-validation": "the request, checked against the expected format",
  "queue-state": "the queue status",
  "webhook-unverified": "the callback delivery",
  "unknown-endpoint": "the endpoint name",
  "stale-schema": "the pinned format version",
};
const ANSWER_TITLE: Record<string, string> = {
  correction: "We can fix this.",
  "need-information": "We need one thing first.",
  escalation: "Engineering needs this.",
};
const ANSWER_STATE: Record<string, string> = {
  correction: "fix proposed",
  "need-information": "waiting on customer",
  escalation: "with engineering",
};
const ANSWER_BUTTON: Record<string, string> = {
  correction: "Approve fix",
  "need-information": "Send request",
  escalation: "Escalate",
};
const CLOSED_BEAT: Record<string, [string, string]> = {
  correction: ["Fixed — reply drafted.", "The correction is approved. The draft below is ready to send."],
  "need-information": ["Waiting on customer — request sent.", "Nothing rerun. The case rests until they reply."],
  escalation: ["With engineering.", "Packet attached. No fix promised to the customer."],
};

async function get<T>(path: string): Promise<T> {
  const r = await fetch(`${API}${path}`);
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
  return (await r.json()) as T;
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(`${API}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
  return (await r.json()) as T;
}

const ink = "var(--ink)";
const secondary = "var(--secondary)";
const hairline = "var(--hairline)";

function Chevron({ direction = "right" }: { direction?: "left" | "right" }) {
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"
      style={{ transform: direction === "left" ? "rotate(180deg)" : undefined, flexShrink: 0 }}>
      <path d="M4.5 2.5 8 6l-3.5 3.5" stroke="currentColor" strokeWidth="1.5"
        strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function Check() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true" style={{ flexShrink: 0 }}>
      <circle cx="10" cy="10" r="9" stroke="var(--ok)" strokeWidth="1.5" />
      <path d="M6.5 10.2 8.8 12.5 13.5 7.5" stroke="var(--ok)" strokeWidth="1.5"
        strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <main className="rise" style={{ maxWidth: 640, margin: "0 auto", padding: "20px 20px 96px" }}>
      {children}
    </main>
  );
}

function TopBar({ onBack, practice }: { onBack: () => void; practice: boolean }) {
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between",
      padding: "8px 0 16px", borderBottom: `1px solid ${hairline}`, marginBottom: 32 }}>
      <button onClick={onBack}
        style={{ display: "inline-flex", alignItems: "center", gap: 4, background: "none",
          border: "none", color: "var(--accent-pressed)", cursor: "pointer", fontSize: 17, padding: "4px 0" }}>
        <Chevron direction="left" /> Cases
      </button>
      <span style={{ fontSize: 11, letterSpacing: "0.12em", color: secondary }}>
        {practice ? "PRACTICE · SYNTHETIC" : "LIVE FAL REQUEST"}
      </span>
    </div>
  );
}

function PrimaryButton({ onClick, children, type = "button" }: {
  onClick?: () => void; children: React.ReactNode; type?: "button" | "submit";
}) {
  const [pressed, setPressed] = useState(false);
  return (
    <button type={type} onClick={onClick} onMouseDown={() => setPressed(true)} onMouseUp={() => setPressed(false)}
      onMouseLeave={() => setPressed(false)}
      style={{ width: "100%", fontSize: 17, fontWeight: 600, padding: "14px 24px",
        background: pressed ? "var(--accent-pressed)" : "var(--accent)", color: "#fff",
        border: "none", borderRadius: 12, cursor: "pointer",
        transition: "background 160ms var(--ease-out)" }}>
      {children}
    </button>
  );
}

function QuietButton({ onClick, children }: { onClick: () => void; children: React.ReactNode }) {
  return (
    <button type="button" onClick={onClick}
      style={{ background: "none", border: "none", color: "var(--accent-pressed)",
        cursor: "pointer", fontSize: 17, padding: "12px 0" }}>
      {children}
    </button>
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <h2 style={{ fontSize: 20, fontWeight: 600, margin: "40px 0 4px", letterSpacing: "-0.01em" }}>{children}</h2>;
}

function ToolDisclosure({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ borderTop: `1px solid ${hairline}` }}>
      <details>
        <summary>
          <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
            {title} <span style={{ color: secondary }}><Chevron /></span>
          </span>
        </summary>
        <div style={{ paddingBottom: 16 }}>{children}</div>
      </details>
    </div>
  );
}

function Diff({ before, after }: { before: Record<string, unknown>; after: Record<string, unknown> }) {
  const keys = [...new Set([...Object.keys(before), ...Object.keys(after)])];
  const cell: React.CSSProperties = { padding: "10px 12px 10px 0", textAlign: "left", verticalAlign: "top" };
  return (
    <table style={{ borderCollapse: "collapse", width: "100%", fontSize: 15 }}>
      <thead>
        <tr style={{ borderBottom: `1px solid ${hairline}` }}>
          <th style={{ ...cell, fontSize: 12, fontWeight: 500, color: secondary }}>field</th>
          <th style={{ ...cell, fontSize: 12, fontWeight: 500, color: secondary }}>before</th>
          <th style={{ ...cell, fontSize: 12, fontWeight: 500, color: secondary }}>after</th>
        </tr>
      </thead>
      <tbody>
        {keys.map((k) => {
          const changed = JSON.stringify(before[k]) !== JSON.stringify(after[k]);
          return (
            <tr key={k} style={changed
              ? { background: "var(--wash)", borderBottom: `1px solid ${hairline}` }
              : { borderBottom: `1px solid ${hairline}` }}>
              <td style={cell}><code style={{ fontFamily: "var(--mono)", fontSize: 13 }}>{k}</code></td>
              <td style={{ ...cell, overflowWrap: "anywhere" }}>
                <code style={{ fontFamily: "var(--mono)", fontSize: 13 }}>{JSON.stringify(before[k])}</code>
              </td>
              <td style={{ ...cell, overflowWrap: "anywhere" }}>
                <code style={{ fontFamily: "var(--mono)", fontSize: 13, fontWeight: changed ? 600 : 400 }}>
                  {JSON.stringify(after[k])}
                </code>
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

function shortTime(iso: string) {
  const d = new Date(iso);
  return isNaN(d.getTime()) ? iso : d.toLocaleString(undefined, {
    month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
  });
}

function Detail({ id, back }: { id: string; back: () => void }) {
  const [detail, setDetail] = useState<CaseDetail | null>(null);
  const [inv, setInv] = useState<InvestigateOut | null>(null);
  const [disp, setDisp] = useState<DispositionOut | null>(null);
  const [audit, setAudit] = useState<AuditEvent[]>([]);
  const [draft, setDraft] = useState<string | null>(null);
  const [actor, setActor] = useState("analyst");
  const [replay, setReplay] = useState<ReplayOut | null>(null);
  const [liveMsg, setLiveMsg] = useState<string | null>(null);
  const [closed, setClosed] = useState<[string, string] | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      setError(null);
      const d = await get<CaseDetail>(`/cases/${id}`);
      setDetail(d);
      setInv(await post<InvestigateOut>(`/cases/${id}/investigate`, {}));
      try {
        setDisp(await get<DispositionOut>(`/cases/${id}/disposition`));
      } catch {
        setDisp(await post<DispositionOut>(`/cases/${id}/disposition`, {}));
      }
      try {
        const dr = await get<{ draft: string }>(`/cases/${id}/customer-draft`);
        setDraft(dr.draft);
      } catch { setDraft(null); }
      const h = await get<{ audit: AuditEvent[] }>(`/cases/${id}/history`);
      setAudit(h.audit);
    } catch (e) {
      setError(String(e));
    }
  }

  useEffect(() => { void load(); }, [id]);

  async function decide() {
    if (!disp) return;
    const action = disp.disposition === "correction" ? "disposition" : "customer-text";
    await post(`/cases/${id}/approve`, { action_type: action, actor });
    setClosed(CLOSED_BEAT[disp.disposition]);
    await load();
  }

  async function approve(actionType: string) {
    await post(`/cases/${id}/approve`, { action_type: actionType, actor });
    await load();
  }

  async function runReplay() {
    setReplay(await post<ReplayOut>(`/cases/${id}/replay`, {}));
    await load();
  }

  async function runLiveTest() {
    setLiveMsg(null);
    try {
      const out = await post<{ result: Record<string, unknown> }>(`/cases/${id}/live-test`, { mode: "live" });
      setLiveMsg(`Live submitted: ${JSON.stringify(out.result)}`);
    } catch (e) {
      setLiveMsg(`Live blocked: ${e}`);
    }
    await load();
  }

  function downloadExport() {
    window.open(`${API}/cases/${id}/export`, "_blank");
  }

  if (error) {
    return (
      <Shell>
        <TopBar onBack={back} practice />
        <p role="alert" style={{ color: "#b91c1c" }}>{error}</p>
      </Shell>
    );
  }
  if (!detail || !inv) {
    return (
      <Shell>
        <TopBar onBack={back} practice />
        <p style={{ color: secondary }}>Loading…</p>
      </Shell>
    );
  }

  return (
    <Shell>
      <TopBar onBack={back} practice={detail.replay} />

      <h1 style={{ fontSize: 32, fontWeight: 700, letterSpacing: "-0.02em",
        margin: "0 0 8px", textWrap: "balance" }}>
        {disp ? ANSWER_TITLE[disp.disposition] : "Reading the case…"}
      </h1>
      <p style={{ fontSize: 17, color: secondary, margin: "0 0 32px" }}>“{detail.report}”</p>

      {closed
        ? <div style={{ display: "flex", gap: 12, padding: "20px 0",
            borderTop: `1px solid ${hairline}`, borderBottom: `1px solid ${hairline}` }}>
            <Check />
            <div>
              <div style={{ fontWeight: 600 }}>{closed[0]}</div>
              <div style={{ fontSize: 15, color: secondary }}>{closed[1]}</div>
            </div>
          </div>
        : (disp && <div style={{ margin: "0 0 8px" }}>
            {disp.disposition === "need-information"
              ? <div style={{ marginBottom: 20 }}>Ask the customer for:
                  <ul style={{ margin: "8px 0 0", paddingLeft: 20 }}>
                    {disp.missing?.map((m) => <li key={m}>{m}</li>)}
                  </ul>
                </div>
              : disp.disposition === "correction"
                ? <p style={{ margin: "0 0 20px" }}>The request breaks the expected format. Send this fix?</p>
                : <p style={{ margin: "0 0 20px" }}>This won't clear with a retry or a tweak. Hand it to engineering?</p>}
            <PrimaryButton onClick={decide}>{ANSWER_BUTTON[disp.disposition]}</PrimaryButton>
          </div>)}

      <SectionTitle>Why we think so</SectionTitle>
      <div>
        {inv.findings.map((f, i) => (
          <div key={i} style={{ padding: "14px 0", borderBottom: `1px solid ${hairline}` }}>
            <div>{f.observed_fact}</div>
            <div style={{ fontSize: 13, color: secondary, marginTop: 2 }}>
              Seen in {WHERE[f.category] ?? "the case record"} · sure: {f.confidence}
            </div>
          </div>
        ))}
      </div>

      {disp?.corrected_payload && <>
        <SectionTitle>The change</SectionTitle>
        <Diff before={detail.payload} after={disp.corrected_payload} />
      </>}
      {disp?.packet && <ToolDisclosure title="Escalation packet for engineering">
        <pre style={{ margin: 0, whiteSpace: "pre-wrap", fontSize: 13,
          fontFamily: "var(--mono)" }}>{JSON.stringify(disp.packet, null, 2)}</pre>
      </ToolDisclosure>}

      {inv.schema_errors.some((e) => e.allowed && e.allowed.length > 0) && <>
        <SectionTitle>Allowed values</SectionTitle>
        {inv.schema_errors.filter((e) => e.allowed && e.allowed.length > 0).map((e, i) => (
          <p key={i} style={{ fontSize: 15, color: secondary }}>
            <code style={{ fontFamily: "var(--mono)", fontSize: 13, color: ink }}>{e.field}</code>
            {"  "}{e.allowed!.map(String).join("  ·  ")}
          </p>
        ))}
      </>}

      <SectionTitle>Show me why</SectionTitle>
      <ToolDisclosure title="Queue and callback state">
        <ul style={{ margin: "0 0 8px", paddingLeft: 20, fontSize: 15 }}>
          {inv.queue.map((q) => <li key={q.request_id}>{q.status}: {q.verdict}</li>)}
        </ul>
        {inv.webhook.present && <p style={{ fontSize: 15, color: secondary }}>{inv.webhook.reason}</p>}
      </ToolDisclosure>
      <div style={{ borderTop: `1px solid ${hairline}` }}>
        <ToolDisclosure title={`Timeline (${audit.length} events)`}>
          <ul style={{ margin: "0 0 8px", paddingLeft: 20, fontSize: 15 }}>
            {audit.map((a, i) => <li key={i}>{shortTime(a.timestamp)} — {a.actor} — {a.event_type}</li>)}
          </ul>
        </ToolDisclosure>
      </div>

      <SectionTitle>Customer draft (preview — approval required before sending)</SectionTitle>
      {draft
        ? <p style={{ margin: "8px 0 0", fontSize: 15, whiteSpace: "pre-wrap" }}>{draft}</p>
        : <p style={{ color: secondary }}>No draft yet.</p>}

      <div style={{ marginTop: 40, borderTop: `1px solid ${hairline}` }}>
        <ToolDisclosure title="Replay / live">
          <QuietButton onClick={runReplay}>Run replay</QuietButton>
          <div style={{ height: 4 }} />
          <QuietButton onClick={runLiveTest}>Live test (capped, needs approval)</QuietButton>
          {replay && <p style={{ fontSize: 14, color: secondary }}>
            {replay.badge} · source <code style={{ fontFamily: "var(--mono)", fontSize: 12 }}>{replay.fixture_source}</code> → {replay.disposition}
          </p>}
          {liveMsg && <p style={{ fontSize: 14, color: secondary }}>{liveMsg}</p>}
        </ToolDisclosure>
      </div>
      <div style={{ borderTop: `1px solid ${hairline}`, borderBottom: `1px solid ${hairline}` }}>
        <ToolDisclosure title="More approvals">
          <label style={{ display: "block", fontSize: 15, marginBottom: 4 }}>
            Actor
            <input value={actor} onChange={(e) => setActor(e.target.value)}
              style={{ marginTop: 6, maxWidth: 280 }} />
          </label>
          <QuietButton onClick={() => approve("live-test")}>Approve paid run</QuietButton>
          <div style={{ height: 4 }} />
          <QuietButton onClick={downloadExport}>Export case JSON</QuietButton>
        </ToolDisclosure>
      </div>
    </Shell>
  );
}

function App() {
  const [cases, setCases] = useState<CaseRow[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [report, setReport] = useState("");
  const [endpointId, setEndpointId] = useState("fal-ai/flux/schnell");
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    try {
      setError(null);
      const body = await get<{ data: CaseRow[] }>("/cases?page=1&pageSize=20");
      setCases(body.data ?? []);
    } catch (e) {
      setError(`Backend unreachable at :8000 — start it first. ${e}`);
    }
  }

  useEffect(() => {
    if (location.hash.startsWith("#case-")) setSelected(location.hash.slice(6));
    void refresh();
  }, []);

  async function createCase(e: React.FormEvent) {
    e.preventDefault();
    await post("/cases", {
      endpoint_id: endpointId, schema_version: "v1", report,
      payload: { prompt: report.slice(0, 200) || "demo prompt" },
    });
    setReport("");
    await refresh();
  }

  if (selected) return <Detail id={selected} back={() => { setSelected(null); void refresh(); }} />;

  return (
    <Shell>
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between",
        padding: "8px 0 16px", borderBottom: `1px solid ${hairline}`, marginBottom: 24 }}>
        <span style={{ fontSize: 17, fontWeight: 600, letterSpacing: "-0.01em" }}>Request Rescue</span>
        <span style={{ fontSize: 11, letterSpacing: "0.12em", color: secondary }}>PRACTICE · SYNTHETIC</span>
      </div>
      <p style={{ fontSize: 15, color: secondary, margin: "0 0 4px" }}>{cases.length} waiting.</p>
      <h1 style={{ fontSize: 32, fontWeight: 700, letterSpacing: "-0.02em",
        margin: "0 0 16px", textWrap: "balance" }}>What needs you most?</h1>
      {error && <p role="alert" style={{ color: "#b91c1c" }}>{error}</p>}
      {cases.length === 0 && !error && (
        <p style={{ fontSize: 15, color: secondary }}>
          Nothing waiting. Import a fixture through the API or add a case below.
        </p>
      )}
      <div>
        {cases.map((c) => (
          <button key={c.id} onClick={() => setSelected(c.id)}
            style={{ display: "flex", alignItems: "center", justifyContent: "space-between",
              gap: 12, width: "100%", background: "none", border: "none",
              borderBottom: `1px solid ${hairline}`, cursor: "pointer",
              fontSize: 17, padding: "14px 0", textAlign: "left", color: ink }}>
            <span>
              <span style={{ display: "block" }}>{c.report ? c.report.slice(0, 70) : "Untitled report"}</span>
              <span style={{ display: "block", fontSize: 13, color: secondary, marginTop: 2 }}>
                {c.disposition ? ANSWER_STATE[c.disposition] ?? c.disposition : "not read yet"}
              </span>
            </span>
            <span style={{ color: secondary }}><Chevron /></span>
          </button>
        ))}
      </div>
      <p style={{ fontSize: 14, color: secondary, margin: "24px 0 0" }}>
        Practice room — nothing here touches real traffic.
      </p>
      <div style={{ marginTop: 8, borderTop: `1px solid ${hairline}` }}>
        <details>
          <summary style={{ fontSize: 15, color: secondary }}>New case</summary>
          <form onSubmit={createCase} style={{ paddingBottom: 16 }}>
            <input value={endpointId} onChange={(e) => setEndpointId(e.target.value)}
              aria-label="endpoint id" style={{ marginBottom: 8 }} />
            <textarea value={report} onChange={(e) => setReport(e.target.value)}
              placeholder="Customer report (sanitized — no keys)" rows={3} />
            <div style={{ marginTop: 12 }}>
              <PrimaryButton type="submit">Create case</PrimaryButton>
            </div>
          </form>
        </details>
      </div>
    </Shell>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
