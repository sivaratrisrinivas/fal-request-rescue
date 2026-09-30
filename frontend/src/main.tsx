import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";

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

const API = "";
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
const badge: React.CSSProperties = { border: "1px solid #999", borderRadius: 4, padding: "2px 8px" };

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

function Diff({ before, after }: { before: Record<string, unknown>; after: Record<string, unknown> }) {
  const keys = [...new Set([...Object.keys(before), ...Object.keys(after)])];
  return (
    <table>
      <thead><tr><th>field</th><th>before</th><th>after</th></tr></thead>
      <tbody>
        {keys.map((k) => {
          const changed = JSON.stringify(before[k]) !== JSON.stringify(after[k]);
          return (
            <tr key={k} style={changed ? { background: "#fff8dc" } : undefined}>
              <td><code>{k}</code></td>
              <td><code>{JSON.stringify(before[k])}</code></td>
              <td><code>{JSON.stringify(after[k])}</code></td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
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

  if (error) return <main><p role="alert" style={{ color: "crimson" }}>{error}</p><button onClick={back}>Back</button></main>;
  if (!detail || !inv) return <main><p>Loading…</p></main>;

  return (
    <div style={{
      borderTop: detail.replay ? "10px solid #d6a94c" : "10px solid #dc2626",
      minHeight: "100vh", background: detail.replay ? "#faf6ef" : "#fef2f2",
    }}>
      <span style={{
        background: detail.replay ? "#d6a94c" : "#dc2626",
        color: detail.replay ? "#1c1917" : "#fff",
        fontSize: 12, letterSpacing: 2, padding: "4px 14px", borderRadius: "0 0 8px 0",
      }}>
        {detail.replay ? "PRACTICE · SYNTHETIC" : "LIVE FAL REQUEST"}
      </span>
      <main style={{ fontFamily: "Georgia, serif", maxWidth: 680, margin: "0 auto", padding: "24px 20px 80px" }}>
      <p style={{ fontFamily: "system-ui", fontSize: 14 }}>
        <button onClick={back} style={{ background: "none", border: "none", color: "#9a3412", textDecoration: "underline", cursor: "pointer", fontSize: 14, padding: 0 }}>
          ← waiting
        </button>
      </p>

      <h1>{disp ? ANSWER_TITLE[disp.disposition] : "Reading the case…"}</h1>
      <p><em>“{detail.report}”</em></p>

      {closed
        ? <div style={{ background: "#ecfdf5", border: "1px solid #6ee7b7", borderRadius: 12, padding: 18 }}>
          <strong>{closed[0]}</strong><br /><small>{closed[1]}</small>
        </div>
        : (disp && <>
          <div style={{ background: "#fff", border: "1px solid #ddd", borderRadius: 12, padding: 18 }}>
            {disp.disposition === "need-information"
              ? <>Ask the customer for:<ul>{disp.missing?.map((m) => <li key={m}>{m}</li>)}</ul></>
              : disp.disposition === "correction"
                ? <p>The request breaks the expected format. Send this fix?</p>
                : <p>This won't clear with a retry or a tweak. Hand it to engineering?</p>}
            <button onClick={decide} style={{ fontSize: 17, padding: "12px 24px" }}>
              {disp ? ANSWER_BUTTON[disp.disposition] : ""}
            </button>
          </div>
        </>)}

      <h2>Why we think so</h2>
      {inv.findings.map((f, i) => (
        <div key={i} style={{ background: "#fff", border: "1px solid #eee", borderRadius: 10, padding: "12px 14px", marginBottom: 8 }}>
          <div>{f.observed_fact}</div>
          <div style={{ fontSize: 13, color: "#777" }}>
            Seen in {WHERE[f.category] ?? "the case record"} · sure: {f.confidence}
          </div>
        </div>
      ))}

      {disp?.corrected_payload && <>
        <h2>The change</h2>
        <Diff before={detail.payload} after={disp.corrected_payload} />
      </>}
      {disp?.packet && <details><summary>Escalation packet for engineering</summary>
        <pre>{JSON.stringify(disp.packet, null, 2)}</pre></details>}

      <h2>Replay / live</h2>
      <button onClick={runReplay}>Run replay</button>{" "}
      <button onClick={runLiveTest}>Live test (capped, needs approval)</button>
      {replay && <p><span style={badge}>{replay.badge}</span> source <code>{replay.fixture_source}</code> → {replay.disposition} ({replay.submitted_at} – {replay.completed_at})</p>}
      {liveMsg && <p>{liveMsg}</p>}

      <h2>Allowed values</h2>
      {inv.schema_errors.filter((e) => e.allowed && e.allowed.length > 0).map((e, i) => (
        <p key={i}><code>{e.field}</code>{" "}
          {e.allowed!.map((a) => (
            <span key={String(a)} style={{ ...badge, marginRight: 6 }}>{String(a)}</span>
          ))}
        </p>
      ))}
      {inv.schema_errors.filter((e) => e.allowed && e.allowed.length > 0).length === 0 &&
        <p style={{ color: "#777" }}>No fixed options involved — nothing to pick from.</p>}

      <h2>Show me why</h2>
      <details><summary>Queue and callback state</summary>
        <ul>{inv.queue.map((q) => <li key={q.request_id}>{q.status}: {q.verdict}</li>)}</ul>
        {inv.webhook.present && <p>{inv.webhook.reason}</p>}
      </details>
      <details><summary>Timeline ({audit.length} events)</summary>
        <ul>{audit.map((a, i) => <li key={i}>{a.timestamp} — {a.actor} — {a.event_type}</li>)}</ul>
      </details>
      <details><summary>Export for engineering</summary>
        <p><button onClick={downloadExport}>Download case JSON</button></p>
      </details>

      <h2>Customer draft (preview — approval required before sending)</h2>
      {draft ? <pre>{draft}</pre> : <p>No draft yet.</p>}

      <h2>More approvals</h2>
      <label>Actor <input value={actor} onChange={(e) => setActor(e.target.value)} /></label>{" "}
      <button onClick={() => approve("live-test")}>Approve paid run</button>{" "}
      <button onClick={downloadExport}>Export case JSON</button>
      </main>
    </div>
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
    <div style={{ borderTop: "10px solid #d6a94c", minHeight: "100vh", background: "#faf6ef" }}>
      <span style={{ background: "#d6a94c", fontSize: 12, letterSpacing: 2, padding: "4px 14px", borderRadius: "0 0 8px 0" }}>
        PRACTICE · SYNTHETIC
      </span>
      <main style={{ fontFamily: "Georgia, serif", maxWidth: 680, margin: "0 auto", padding: "24px 20px 80px" }}>
        <p style={{ fontFamily: "system-ui", fontSize: 14, color: "#57534e" }}>{cases.length} waiting.</p>
        <h1>What needs you most?</h1>
        {error && <p role="alert" style={{ color: "crimson" }}>{error}</p>}
        {cases.map((c) => (
          <p key={c.id} style={{ fontFamily: "system-ui", fontSize: 15 }}>
            <button onClick={() => setSelected(c.id)}
              style={{ background: "none", border: "none", color: "#9a3412", textDecoration: "underline", cursor: "pointer", fontSize: 15, padding: 0 }}>
              {c.report ? c.report.slice(0, 70) : "Untitled report"}
            </button>{" "}— {c.disposition ?? "not read yet"}
          </p>
        ))}
        <p style={{ fontFamily: "system-ui", fontSize: 14, color: "#57534e" }}>
          Practice room — nothing here touches real traffic.
        </p>
        <details>
          <summary style={{ fontFamily: "system-ui", fontSize: 14, cursor: "pointer" }}>＋ New case</summary>
          <form onSubmit={createCase} style={{ marginTop: 8 }}>
            <input value={endpointId} onChange={(e) => setEndpointId(e.target.value)} aria-label="endpoint id" style={{ width: "100%", marginBottom: 8 }} />
            <textarea value={report} onChange={(e) => setReport(e.target.value)} placeholder="Customer report (sanitized — no keys)" rows={3} style={{ width: "100%" }} />
            <button type="submit">Create case</button>
          </form>
        </details>
      </main>
    </div>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
