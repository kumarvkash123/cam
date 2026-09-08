"use client";

function fmt(value, suffix = "") {
  if (value === null || value === undefined || value === "") return "—";
  return `${value}${suffix}`;
}

export function BusinessModelCard({ data = {} }) {
  return <section className="journey-card bov13-card">
    <div className="bov13-title"><h2>Business Model</h2><span>Source grounded</span></div>
    <div className="bov13-kv"><span>Business Type</span><strong>{data.type || "Not available"}</strong></div>
    <div className="bov13-kv"><span>Industry</span><strong>{data.industry || "Not available"}</strong></div>
    <div className="bov13-kv"><span>Customer Model</span><strong>{data.customer_model || "Not available"}</strong></div>
    <div className="bov13-kv"><span>Revenue Model</span><strong>{data.revenue_model || "Not available"}</strong></div>
    <p className="bov13-description">{data.description || "Detailed business description is not available from current structured evidence."}</p>
    <small className="bov13-source">Source: {data.source || "Normalized CAM evidence"}</small>
  </section>;
}

export function ListCard({ title, subtitle, items = [], getText = x => x?.name || x?.segment || String(x) }) {
  return <section className="journey-card bov13-card">
    <div className="bov13-title"><h2>{title}</h2>{subtitle && <span>{subtitle}</span>}</div>
    {items.length ? <ul className="bov13-list">{items.slice(0, 8).map((x, i) => <li key={i}><span>{getText(x)}</span>{x?.source && <small>{x.source}</small>}</li>)}</ul>
      : <div className="bov13-empty">Not available from current structured evidence.</div>}
  </section>;
}

export function FootprintCard({ data = {} }) {
  const rows = [
    ["Registered Office", data.registered_office],
    ["Plants", (data.plants || []).join(", ")],
    ["Branches", (data.branches || []).join(", ")],
    ["Operating States", (data.operating_states || []).join(", ")],
    ["Export Markets", (data.export_markets || []).join(", ")],
    ["Capacity / Utilisation", data.capacity],
  ];
  return <section className="journey-card bov13-card">
    <div className="bov13-title"><h2>Operating Footprint</h2><span>Operations & geography</span></div>
    <div className="bov13-table">{rows.map(([k,v]) => <div key={k}><span>{k}</span><strong>{v || "—"}</strong></div>)}</div>
  </section>;
}

export function RevenueProfile({ data = {} }) {
  const trend = data.trend || [];
  const max = Math.max(1, ...trend.flatMap(x => [Number(x.revenue_cr)||0, Number(x.pat_cr)||0]));
  return <section className="journey-card bov13-card bov13-revenue-card">
    <div className="bov13-title"><h2>Revenue Profile & Trend</h2><span>Uploaded financial evidence</span></div>
    <div className="bov13-revenue-stats">
      <div><span>Latest Revenue</span><strong>{data.latest_revenue_cr != null ? `₹ ${data.latest_revenue_cr.toFixed(2)} Cr` : "—"}</strong></div>
      <div><span>Latest PAT</span><strong>{data.latest_pat_cr != null ? `₹ ${data.latest_pat_cr.toFixed(2)} Cr` : "—"}</strong></div>
      <div><span>Latest Growth</span><strong>{fmt(data.latest_growth_pct, "%")}</strong></div>
      <div><span>Revenue CAGR</span><strong>{fmt(data.cagr_pct, "%")}</strong></div>
    </div>
    {trend.length ? <div className="bov13-chart">
      {trend.map((p, i) => <div className="bov13-chart-group" key={`${p.year}-${i}`}>
        <div className="bov13-bars">
          <div className="bov13-bar revenue" style={{height:`${Math.max(4,(Number(p.revenue_cr)||0)/max*150)}px`}} title={`Revenue ₹${p.revenue_cr ?? "—"} Cr`}><b>{p.revenue_cr ?? ""}</b></div>
          <div className="bov13-bar pat" style={{height:`${Math.max(4,(Number(p.pat_cr)||0)/max*150)}px`}} title={`PAT ₹${p.pat_cr ?? "—"} Cr`}><b>{p.pat_cr ?? ""}</b></div>
        </div><span>{p.year}</span>
      </div>)}
    </div> : <div className="bov13-empty">Multi-year revenue trend is not available from current financial evidence.</div>}
    <div className="bov13-chart-legend"><span><i className="rev"/>Revenue (₹ Cr)</span><span><i className="pat"/>PAT (₹ Cr)</span></div>
    <small className="bov13-source">{data.note}</small>
  </section>;
}

export function MarketPosition({ data = {} }) {
  return <section className="journey-card bov13-card">
    <div className="bov13-title"><h2>Market Position</h2><span>External / industry data</span></div>
    <div className="bov13-table">
      <div><span>Industry</span><strong>{data.industry || "—"}</strong></div>
      <div><span>Industry Growth</span><strong>{fmt(data.industry_growth_pct, "%")}</strong></div>
      <div><span>Industry Median EBITDA Margin</span><strong>{fmt(data.industry_median_ebitda_margin_pct, "%")}</strong></div>
      <div><span>Borrower EBITDA Margin</span><strong>{fmt(data.borrower_ebitda_margin_pct, "%")}</strong></div>
      <div><span>Credit Rating</span><strong>{[data.credit_rating, data.outlook].filter(Boolean).join(" / ") || "—"}</strong></div>
    </div>
    <div className="bov13-note">{data.positioning_note}</div>
  </section>;
}

export function StrengthRiskCard({ strengths = [], risks = [] }) {
  return <section className="journey-card bov13-card">
    <div className="bov13-title"><h2>Business Strengths & Risks</h2><span>Evidence based</span></div>
    <div className="bov13-sr-grid"><div><h3>Strengths</h3>{strengths.length ? <ul>{strengths.map((x,i)=><li key={i}>{x}</li>)}</ul> : <p>Not enough structured evidence to identify specific strengths.</p>}</div>
    <div><h3>Risks / Gaps</h3>{risks.length ? <ul>{risks.map((x,i)=><li key={i}>{x}</li>)}</ul> : <p>No material business risk item is available from current structured evidence.</p>}</div></div>
  </section>;
}

export function RecentDevelopments({ items = [], industryItems = [] }) {
  const combined = [...items.map(x => ({...x, kind:"Company"})), ...industryItems.map(x => ({...x, kind:"Industry"}))].slice(0,6);
  return <section className="journey-card bov13-card">
    <div className="bov13-title"><h2>Recent Developments</h2><span>Public information</span></div>
    {combined.length ? <div className="bov13-news">{combined.map((x,i)=><div key={i}><span>{x.kind}</span><strong>{x.title || x.summary || "Public information item"}</strong><small>{[x.date,x.source].filter(Boolean).join(" · ")}</small></div>)}</div>
      : <div className="bov13-empty">No recent public development is available in the current feed.</div>}
  </section>;
}

export function AIOverview({ data, onAsk }) {
  const ok = data?.ai_overview_source === "ai_generated";
  return <section className="journey-card bov13-card bov13-ai">
    <div className="bov13-title"><h2>AI Business Overview</h2><span className={ok ? "bov13-ai-ok" : "bov13-ai-warn"}>{ok ? "Groq AI Draft" : "Groq Not Ready"}</span></div>
    {data?.ai_overview ? <p>{data.ai_overview}</p> : <div className="bov13-empty">Business Overview could not be generated by Groq. {data?.llm_status?.error || "AI service is unavailable."}</div>}
    <div className="bov13-ai-note">AI summarizes supplied evidence only. Financial calculations, source facts and final credit decisions remain deterministic / human controlled.</div>
    <button className="outline-btn" onClick={onAsk}>✦ Ask Copilot</button>
  </section>;
}

export function SourcesStrip({ sources = [] }) {
  return <section className="journey-card bov13-sources"><strong>Sources</strong>{sources.map((s,i)=><span key={i}>{s.name} · {s.status}</span>)}</section>;
}

export function BusinessCopilotDrawer({ open, onClose, chat = [], message, setMessage, sendCamChat, busy }) {
  if (!open) return null;
  const suggestions = ["Explain the business model", "What are the key products?", "Summarize revenue growth", "What are the business risks?", "What public developments were found?"];
  const ask = async (q) => { if (q && q.trim()) await sendCamChat(q.trim()); };
  return <aside className="bov13-drawer">
    <div className="bov13-drawer-head"><div><strong>CAM Assistant</strong><span>Business Overview Copilot</span></div><button onClick={onClose}>×</button></div>
    <div className="bov13-suggestions">{suggestions.map(q=><button key={q} disabled={busy} onClick={()=>ask(q)}>{q}</button>)}</div>
    <div className="bov13-chat">{chat.slice(-10).map((m,i)=><div key={i} className={m.who === "You" ? "user" : "ai"}><strong>{m.who}</strong><p>{m.text}</p></div>)}</div>
    <form className="bov13-chat-input" onSubmit={e=>{e.preventDefault(); ask(message);}}><input value={message} onChange={e=>setMessage(e.target.value)} placeholder="Ask about business, customers, operations, revenue..."/><button className="bob-btn" disabled={busy || !message.trim()}>Ask</button></form>
  </aside>;
}
