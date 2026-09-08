"use client";

const money = (v) => (v === null || v === undefined ? "—" : `₹ ${Number(v).toFixed(2)} Cr`);
const pct = (v) => (v === null || v === undefined ? "—" : `${v >= 0 ? "+" : ""}${Number(v).toFixed(1)}%`);
const x = (v) => (v === null || v === undefined ? "—" : `${Number(v).toFixed(2)}x`);

export function BorrowerStrip({data, companyData, mcaData, camInfo}) {
  return <section className="fa14-borrower">
    <div className="fa14-building">▥</div>
    <div className="fa14-borrower-main">
      <div><strong>{data?.company_name || companyData?.company_name || "Borrower"}</strong><span>Existing Borrower</span></div>
      <small>CIN: {companyData?.cin || mcaData?.cin || "Not available"} &nbsp; | &nbsp; Industry: {companyData?.industry || "Not available"}</small>
    </div>
    <div className="fa14-borrower-stat"><small>CAM ID</small><strong>{data?.cam_id || camInfo?.cam_id || "Pending"}</strong></div>
    <div className="fa14-borrower-stat"><small>Latest Period</small><strong>{data?.latest_year || "Latest"}</strong></div>
  </section>;
}

export function KpiRow({items=[]}) {
  return <div className="fa14-kpis">{items.map((item) => {
    const up = item.change_pct !== null && item.change_pct !== undefined && item.change_pct >= 0;
    return <div className="fa14-kpi" key={item.label}>
      <small>{item.label}</small><strong>{money(item.value_cr)}</strong>
      <span className={item.change_pct == null ? "muted" : up ? "up" : "down"}>{item.change_pct == null ? "No prior period" : `${up ? "▲" : "▼"} ${Math.abs(item.change_pct).toFixed(1)}%`} <em>vs. previous period</em></span>
    </div>;
  })}</div>;
}

export function RatioTable({rows=[]}) {
  return <section className="fa14-card fa14-ratios"><div className="fa14-card-head"><div><h2>Financial Ratios</h2><p>Latest available period</p></div><span className="fa14-auto">Auto calculated</span></div>
    <div className="fa14-table-scroll"><table><thead><tr><th>Ratio</th><th>Value</th><th>Bank Benchmark</th><th>Status</th></tr></thead><tbody>
      {rows.map(r => <tr key={r.key}><td>{r.label}</td><td><strong>{r.display_value}</strong></td><td>{r.benchmark}</td><td><span className={`fa14-status ${r.status.toLowerCase()}`}>{r.status === "Pass" ? "✓ " : r.status === "Review" ? "! " : ""}{r.status}</span></td></tr>)}
    </tbody></table></div>
  </section>;
}

export function TrendChart({series=[]}) {
  const all = series.flatMap(s => s.values_cr || []).filter(v => Number.isFinite(Number(v)));
  const max = Math.max(1, ...all.map(Number));
  const revenue = series.find(s=>s.label==="Revenue") || series[0];
  const years = revenue?.years || [];
  return <section className="fa14-card fa14-trend"><div className="fa14-card-head"><div><h2>Key Financial Trends <span>(₹ in Crore)</span></h2><p>Extracted multi-period financial performance</p></div></div>
    {series.length ? <div className="fa14-chart-area"><div className="fa14-legend">{series.map(s=><span key={s.label}><i className={`dot ${s.label.toLowerCase()}`}></i>{s.label}</span>)}</div>
      <div className="fa14-chart-grid">{years.map((year, yi)=><div className="fa14-year-group" key={year}><div className="fa14-bars">{series.map((s, si)=>{const val=Number(s.values_cr?.[yi] ?? 0); const h=Math.max(4, Math.round((Math.abs(val)/max)*150)); return <div className={`fa14-bar s${si+1}`} key={s.label} style={{height:`${h}px`}} title={`${s.label}: ₹${val.toFixed(2)} Cr`}><b>{val ? val.toFixed(0) : ""}</b></div>})}</div><small>{year}</small></div>)}</div>
    </div> : <div className="fa14-empty">Multi-period trends were not found in the uploaded financial statements.</div>}
  </section>;
}

export function MovementTable({rows=[]}) {
  return <section className="fa14-card"><div className="fa14-card-head"><div><h2>Material Movements</h2><p>Compared with the previous reported period</p></div></div>
    <div className="fa14-table-scroll"><table className="fa14-movement"><thead><tr><th>Metric</th><th>Previous</th><th>Current</th><th>Change</th><th>Observation</th></tr></thead><tbody>
      {rows.length ? rows.map(r=><tr key={r.metric}><td><strong>{r.metric}</strong></td><td>{money(r.previous_cr)}</td><td>{money(r.current_cr)}</td><td><span className={r.change_pct >= 0 ? "fa14-positive" : "fa14-negative"}>{r.change_pct >= 0 ? "▲" : "▼"} {Math.abs(r.change_pct || 0).toFixed(1)}%</span></td><td className={r.severity === "review" ? "fa14-review-cell" : ""}>{r.observation}{r.severity === "review" ? " • Material movement" : ""}</td></tr>) : <tr><td colSpan="5">No two-period movement data is available.</td></tr>}
    </tbody></table></div>
  </section>;
}

export function StressTable({rows=[]}) {
  const metrics = [
    ["Revenue (₹ Cr)", "revenue_cr", money], ["EBITDA (₹ Cr)", "ebitda_cr", money],
    ["Interest Coverage", "interest_coverage", x], ["DSCR", "dscr", x], ["Debt / EBITDA", "debt_ebitda", x],
  ];
  return <section className="fa14-card"><div className="fa14-card-head"><div><h2>Stress Testing Results</h2><p>Deterministic base, moderate and severe scenarios</p></div><span className="fa14-assumption">Scenario assumptions</span></div>
    {rows.length ? <div className="fa14-table-scroll"><table className="fa14-stress"><thead><tr><th>Metric</th>{rows.map(r=><th key={r.scenario}>{r.scenario}<small>{r.assumptions?.revenue_change_pct ? ` (${r.assumptions.revenue_change_pct}% Revenue)` : ""}</small></th>)}</tr></thead><tbody>
      {metrics.map(([label,key,fmt])=><tr key={key}><td>{label}</td>{rows.map(r=><td key={r.scenario}>{fmt(r[key])}</td>)}</tr>)}
      <tr><td><strong>Overall Assessment</strong></td>{rows.map(r=><td key={r.scenario}><span className={`fa14-scenario ${String(r.assessment).toLowerCase()}`}>{r.assessment}</span></td>)}</tr>
    </tbody></table></div> : <div className="fa14-empty">Stress testing requires base financial ratios and metrics.</div>}
  </section>;
}

export function Commentary({commentary}) {
  const sec = commentary?.sections || {};
  const blocks = [
    ["Financial Performance", "financial_performance"], ["Liquidity & Working Capital", "liquidity_working_capital"],
    ["Leverage & Coverage", "leverage_coverage"], ["Stress Testing Conclusion", "stress_testing"],
  ];
  return <section className="fa14-card fa14-commentary"><div className="fa14-card-head"><div><h2>✦ AI Financial Insights & Commentary</h2><p>All numbers originate from deterministic calculations; AI only phrases commentary.</p></div><span className={`fa14-source ${commentary?.source || "deterministic"}`}>{commentary?.source === "ai_generated" ? "Groq commentary" : "Rule commentary"}</span></div>
    <div className="fa14-comment-grid">{blocks.map(([label,key])=><div key={key}><h3>{label}</h3>{(sec[key] || []).map((text,i)=><p key={i}><i className={text.toLowerCase().includes("review") || text.toLowerCase().includes("stressed") || text.toLowerCase().includes("below") ? "warn" : "ok"}>{text.toLowerCase().includes("review") || text.toLowerCase().includes("stressed") || text.toLowerCase().includes("below") ? "!" : "✓"}</i>{text}</p>)}</div>)}</div>
    {commentary?.error && <small className="fa14-ai-error">AI narrative unavailable; deterministic commentary is shown. {commentary.error}</small>}
  </section>;
}

export function Sources({items=[]}) {
  if (!items.length) return null;
  return <div className="fa14-sources"><strong>Financial evidence used:</strong>{items.slice(0,6).map((s,i)=><span key={`${s.name}-${i}`}>{s.name} <em>{s.type}</em></span>)}</div>;
}
