"use client";

export function SourceBadge({ status }) {
  const key = String(status || "fetched").toLowerCase();
  const labelMap = {
    official_source: "Official Source",
    fetched: "Fetched",
    verified: "Verified",
    validated: "Validated",
    matched: "Matched",
    processed: "Processed",
    review_required: "Review Required",
    mismatch: "Mismatch",
    pending: "Pending",
  };
  return <span className={`biv12-badge ${key}`}>{labelMap[key] || status || "Fetched"}</span>;
}

export function FieldRow({ label, item, formatter }) {
  const value = item?.value;
  const renderedValue = value === null || value === undefined || value === ""
    ? "—"
    : formatter
      ? formatter(value)
      : String(value);

  return (
    <div className="biv12-field-row">
      <span className="biv12-field-label">{label}</span>
      <div className="biv12-field-value">
        <strong title={String(renderedValue)}>{renderedValue}</strong>
        <small>{item?.source || "—"}</small>
      </div>
      <SourceBadge status={item?.status || "pending"} />
    </div>
  );
}

export function BorrowerHeader({ data }) {
  const c = data?.corporate_profile || {};
  const r = data?.registration || {};
  const bank = data?.bank_relationship || {};
  return (
    <section className="biv12-borrower-card">
      <div className="biv12-company-icon">▥</div>
      <div className="biv12-borrower-main">
        <div className="biv12-name-line">
          <h2>{data?.company_name || "Borrower"}</h2>
          <span className="biv12-active">{c.company_status?.value || "Profile"}</span>
          {bank.existing_customer?.value === true && <span className="biv12-existing">Existing Customer</span>}
        </div>
        <div className="biv12-meta">
          <span>CIN: {c.cin?.value || "—"}</span>
          <span>GSTIN: {r.gstin?.value || "—"}</span>
          <span>PAN: {r.pan?.value || "—"}</span>
          <span>Industry: {c.industry?.value || "—"}</span>
          <span>RM: {bank.relationship_manager?.value || "—"}</span>
        </div>
      </div>
    </section>
  );
}

export function VerificationSummary({ summary }) {
  const cards = [
    ["Total Sources", summary?.total_sources ?? 0, "blue"],
    ["Verified", summary?.verified ?? 0, "green"],
    ["Official / Fetched", summary?.official_fetched ?? 0, "blue"],
    ["Pending / Issues", summary?.pending_issues ?? 0, (summary?.pending_issues || 0) ? "red" : "green"],
  ];
  return (
    <section className="journey-card biv12-card">
      <div className="biv12-title"><h2>Verification Summary</h2></div>
      <div className="biv12-summary-grid">
        {cards.map(([label, value, tone]) => <div key={label} className={`biv12-summary-card ${tone}`}><span>{label}</span><strong>{value}</strong></div>)}
      </div>
      <div className={(summary?.pending_issues || 0) ? "biv12-alert warn" : "biv12-alert ok"}>{summary?.message}</div>
    </section>
  );
}

export function SourceInformation({ sources = [] }) {
  return (
    <section className="journey-card biv12-card">
      <div className="biv12-title"><h2>Source Information</h2><span>{sources.length} sources</span></div>
      <div className="biv12-source-list">
        {sources.slice(0, 9).map((s, i) => (
          <div key={`${s.name}-${i}`}>
            <div><strong>{s.name}</strong><small>{s.source_type}{s.detail ? ` · ${s.detail}` : ""}</small></div>
            <SourceBadge status={s.status} />
          </div>
        ))}
        {!sources.length && <p className="muted">No source records are available yet.</p>}
      </div>
    </section>
  );
}

export function PeopleCard({ people = [] }) {
  return (
    <section className="journey-card biv12-card">
      <div className="biv12-title"><h2>Key Promoters / Directors</h2><span>MCA / disclosures</span></div>
      <div className="biv12-people-table">
        <div className="head"><b>Name</b><b>Designation</b><b>DIN</b></div>
        {people.slice(0, 6).map((p, i) => <div key={`${p.name}-${i}`}><span>{p.name}</span><span>{p.designation || "—"}</span><span>{p.din || "—"}</span></div>)}
        {!people.length && <p className="muted">Promoter/director details are not available from current structured sources.</p>}
      </div>
    </section>
  );
}

export function ConflictsCard({ conflicts = [] }) {
  if (!conflicts.length) return null;
  return (
    <section className="journey-card biv12-card biv12-conflicts">
      <div className="biv12-title"><h2>Source Differences Requiring Review</h2><span>{conflicts.length}</span></div>
      {conflicts.map((c, i) => <div className="biv12-conflict" key={`${c.field}-${i}`}><strong>{c.field}</strong><span>Primary: {String(c.primary || "—")}</span><span>Comparison: {String(c.comparison || "—")}</span></div>)}
    </section>
  );
}

export function BorrowerOverview({ data, onAsk }) {
  return (
    <section className="journey-card biv12-card biv12-overview">
      <div className="biv12-title"><h2>AI Borrower Overview</h2><SourceBadge status={data?.ai_overview_source === "ai_generated" ? "verified" : "pending"} /></div>
      {data?.ai_overview ? <p>{data.ai_overview}</p> : <div className="biv12-alert warn">Borrower overview was not generated by Groq. {data?.llm_status?.error || "AI service is not available."}</div>}
      <div className="biv12-ai-note">AI summarizes supplied evidence only. Identifiers, verification results and calculations remain source/rule based.</div>
      <button className="outline-btn" onClick={onAsk}>✦ Ask Copilot</button>
    </section>
  );
}

export function CopilotDrawer({ open, onClose, chat = [], message, setMessage, sendCamChat, busy }) {
  if (!open) return null;
  const suggestions = ["Who are the promoters?", "What came from MCA?", "Are there any source mismatches?", "Where does the company operate?", "Summarize public information only."];
  return (
    <aside className="biv12-drawer">
      <div className="biv12-drawer-head"><div><strong>CAM Assistant</strong><span>Borrower Information Copilot</span></div><button onClick={onClose}>×</button></div>
      <div className="biv12-suggestions">{suggestions.map(q => <button key={q} onClick={() => sendCamChat(q)} disabled={busy}>{q}</button>)}</div>
      <div className="biv12-chat-scroll">
        {chat.slice(-10).map((m, i) => <div key={i} className={m.who === "You" ? "biv12-user-msg" : "biv12-ai-msg"}><strong>{m.who}</strong><div>{m.text}</div>{m.sources?.length ? <small>Sources: {m.sources.slice(0,4).map(s => s.title || s.source || s.type).filter(Boolean).join(" · ")}</small> : null}</div>)}
      </div>
      <form className="biv12-chat-input" onSubmit={(e) => { e.preventDefault(); sendCamChat(message); }}><input value={message} onChange={e => setMessage(e.target.value)} placeholder="Ask about borrower, promoters, sources..."/><button className="bob-btn" disabled={busy || !message.trim()}>Ask</button></form>
    </aside>
  );
}

export function ExternalVerificationMatrix({ rows = [], provider = {} }) {
  if (!rows.length) return null;
  return (
    <section className="journey-card biv12-card">
      <div className="biv12-title">
        <h2>Document vs External Verification</h2>
        <span>{provider?.name || "Verification provider"}{provider?.synthetic ? " · Synthetic POC fallback" : ""}</span>
      </div>
      {provider?.synthetic && <div className="biv12-alert warn">FileSure/real verification was unavailable for one or more checks. Synthetic POC verification is clearly labelled and must not be treated as a real registry result.</div>}
      <div className="biv12-people-table">
        <div className="head"><b>Field</b><b>Uploaded Document</b><b>Verified Source</b></div>
        {rows.map((r, i) => (
          <div key={`${r.field}-${i}`}>
            <span><strong>{r.field}</strong><br/><SourceBadge status={String(r.status || "pending").toLowerCase()} /></span>
            <span>{r.document_value ?? "—"}</span>
            <span>{r.verified_value ?? "—"}<br/><small>{r.verification_source || "—"}</small></span>
          </div>
        ))}
      </div>
    </section>
  );
}
