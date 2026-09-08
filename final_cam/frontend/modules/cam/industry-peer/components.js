"use client";

function tone(value) {
  const v = String(value || "").toLowerCase();
  if (["better", "positive", "low", "stable"].some(x => v.includes(x))) return "good";
  if (["weaker", "weak", "high", "watch"].some(x => v.includes(x))) return "warn";
  if (["in line", "moderate"].some(x => v.includes(x))) return "info";
  return "muted";
}

export function Point10Kpis({ data }) {
  const s = data?.summary || {};
  const rows = [
    ["Industry Growth", s.industry_growth_pct == null ? "—" : `${Number(s.industry_growth_pct).toFixed(1)}%`, "Available market data"],
    ["Industry Outlook", s.overall_outlook || "Not assessed", "Market context"],
    ["Peer Metrics Assessed", `${s.peer_metrics_assessed || 0}/${s.peer_metrics_total || 0}`, "No estimation of missing peers"],
    ["Relative Strengths", s.relative_strengths ?? 0, "Borrower vs benchmark"],
    ["Relative Risks", s.relative_risks ?? 0, "Borrower vs benchmark"],
  ];
  return <div className="ip19-kpis">{rows.map(([label,value,note]) => <div className="ip19-kpi" key={label}><span>{label}</span><strong>{value}</strong><small>{note}</small></div>)}</div>;
}

export function IndustryOverview({ data }) {
  const x = data?.industry_overview || {};
  const rows = [
    ["Industry", x.industry || "Not identified"],
    ["Industry Growth", x.growth_pct == null ? "Not available" : `${Number(x.growth_pct).toFixed(1)}%`],
    ["Overall Outlook", x.outlook || "Not assessed"],
    ["Industry Median EBITDA Margin", x.industry_median_ebitda_margin_pct == null ? "Not available" : `${Number(x.industry_median_ebitda_margin_pct).toFixed(1)}%`],
    ["Market Data Provider", x.data_provider || "Not available"],
  ];
  return <section className="journey-card ip19-card"><div className="ip19-head"><h3>Industry Overview</h3><span className={`ip19-badge ${tone(x.outlook)}`}>{x.outlook || "Not assessed"}</span></div><div className="ip19-detail-list">{rows.map(([k,v]) => <div key={k}><span>{k}</span><strong>{v}</strong></div>)}</div></section>;
}

export function PeerBenchmarkTable({ rows = [] }) {
  return <section className="journey-card ip19-card ip19-peer"><div className="ip19-head"><h3>Peer / Industry Benchmarking</h3><span>Source-backed only</span></div><div className="ip19-table-wrap"><table><thead><tr><th>Metric</th><th>Borrower</th><th>Benchmark</th><th>Benchmark Type</th><th>Position</th></tr></thead><tbody>{rows.map((r,i)=><tr key={`${r.metric}-${i}`}><td><strong>{r.metric}</strong></td><td>{r.borrower || "—"}</td><td>{r.benchmark || "—"}</td><td>{r.benchmark_label || "—"}</td><td><span className={`ip19-badge ${tone(r.position)}`}>{r.position || "Not available"}</span></td></tr>)}</tbody></table></div></section>;
}

export function MarketFactors({ rows = [] }) {
  return <section className="journey-card ip19-card"><div className="ip19-head"><h3>Market Factors</h3><span>Deterministic assessment</span></div><div className="ip19-factor-grid">{rows.map((r,i)=><div className="ip19-factor" key={`${r.factor}-${i}`}><span>{r.factor}</span><strong className={tone(r.assessment)}>{r.assessment}</strong><div className="ip19-track"><i className={tone(r.assessment)} /></div></div>)}</div></section>;
}

function BulletPanel({ title, items = [], kind }) {
  return <section className="journey-card ip19-card"><div className="ip19-head"><h3>{title}</h3><span>{items.length} item{items.length===1?"":"s"}</span></div>{items.length?<div className="ip19-bullets">{items.map((x,i)=><div key={i} className={kind}><b>{kind==="good"?"✓":"!"}</b><span>{x}</span></div>)}</div>:<p className="ip19-empty">No source-backed observation available.</p>}</section>;
}

export function StrengthsRisks({ strengths, risks }) {
  return <div className="ip19-two"><BulletPanel title="Relative Strengths" items={strengths} kind="good"/><BulletPanel title="Industry / Peer Risks" items={risks} kind="warn"/></div>;
}

export function IndustryDevelopments({ rows = [] }) {
  return <section className="journey-card ip19-card"><div className="ip19-head"><h3>Industry Developments</h3><span>Supporting public evidence</span></div>{rows.length?<div className="ip19-news">{rows.map((r,i)=><article key={i}><strong>{r.title}</strong>{r.snippet&&<p>{r.snippet}</p>}<small>{r.source || "Public information"}</small></article>)}</div>:<p className="ip19-empty">No public-industry observations are available in the configured data mode.</p>}</section>;
}

export function IndustryCommentary({ data }) {
  const c = data?.commentary || {};
  return <section className="journey-card ip19-card ip19-commentary"><div className="ip19-head"><h3>✦ AI Industry & Peer Commentary</h3><span>{c.source === "ai_generated" ? "Groq narrative" : "Deterministic narrative"}</span></div><p>{c.text || "Commentary not available."}</p>{c.error&&<small>AI fallback: {c.error}</small>}</section>;
}

export function IndustrySources({ data }) {
  return <section className="journey-card ip19-card ip19-sources"><div className="ip19-head"><h3>Evidence & Methodology</h3><span>{(data?.sources || []).length} sources</span></div><div className="ip19-source-grid">{(data?.sources||[]).map((s,i)=><div key={i}><strong>{s.name}</strong><span>{s.type}</span><small>{s.status}</small></div>)}</div><p>{data?.methodology}</p><div className="ip19-notice">{data?.decision_notice}</div></section>;
}
