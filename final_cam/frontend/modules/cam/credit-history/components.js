"use client";

const money = (v) => v === null || v === undefined ? "—" : `₹ ${Number(v).toFixed(2)} Cr`;
const val = (v, suffix="") => v === null || v === undefined || v === "" ? "—" : `${v}${suffix}`;
const tone = (s="") => /good|pass|regular|clear|low/i.test(s) ? "good" : /watch|review|medium/i.test(s) ? "watch" : /high|risk|adverse/i.test(s) ? "risk" : "neutral";

export function CreditKpis({data}) {
  const k=data?.kpis||{};
  const cards=[
    ["Commercial Credit Score", val(k.bureau_score), k.bureau_score_status, "Bureau / available source"],
    ["Total Sanctioned Exposure", money(k.sanctioned_exposure_cr), `${k.facility_count||0} Facilities`, "Existing facilities"],
    ["Total Outstanding", money(k.outstanding_cr), k.sanctioned_exposure_cr && k.outstanding_cr!=null ? `${Math.round(k.outstanding_cr/k.sanctioned_exposure_cr*100)}% of limit` : "Available evidence", "Current exposure"],
    ["Current Overdue", k.current_overdue_cr===0 ? "₹ 0" : money(k.current_overdue_cr), k.current_overdue_cr===0 ? "Nil" : k.current_overdue_cr==null ? "Unavailable" : "Review", "Bureau / banking"],
    ["Maximum DPD", k.max_dpd==null ? "—" : `${k.max_dpd} Days`, k.max_dpd_status, "Analysed repayment period"],
  ];
  return <div className="ch15-kpis">{cards.map(([l,v,s,n])=><div className="ch15-kpi" key={l}><span>{l}</span><strong>{v}</strong><em className={tone(s)}>{s}</em><small>{n}</small></div>)}</div>;
}

export function Facilities({rows=[]}) {
  return <section className="journey-card ch15-card"><div className="ch15-head"><h3>▥ Existing Loan Facilities</h3><span>{rows.length ? `${rows.length} facility record(s)` : "No structured facility feed"}</span></div><div className="ch15-table-wrap"><table className="ch15-table"><thead><tr><th>Lender</th><th>Facility Type</th><th>Sanctioned Limit</th><th>Outstanding</th><th>Utilisation</th><th>Status</th></tr></thead><tbody>{rows.length?rows.map((r,i)=><tr key={i}><td>{r.lender}</td><td>{r.facility}</td><td>{money(r.limit_cr)}</td><td>{money(r.outstanding_cr)}</td><td><div className="ch15-util"><span style={{width:`${Math.min(100,r.utilisation_pct||0)}%`}}></span></div><b>{r.utilisation_pct==null?"—":`${r.utilisation_pct}%`}</b></td><td><em className={tone(r.status)}>{r.status}</em></td></tr>):<tr><td colSpan="6" className="ch15-empty">Detailed lender-wise facility data is not available in current evidence.</td></tr>}</tbody></table></div></section>;
}

export function Repayment({data={}}) {
  const monthly=data.monthly||[]; const max=Math.max(1,...monthly.map(x=>x.dpd||0),30);
  return <section className="journey-card ch15-card"><div className="ch15-head"><h3>▣ Repayment Track Record (Last 24 Months)</h3><span>DPD / payment behavior</span></div>{monthly.length?<div className="ch15-repay-chart">{monthly.map((m,i)=><div className="ch15-month" key={i}><div className={`ch15-dpd ${m.dpd>=30?"risk":m.dpd>0?"watch":"good"}`} style={{height:`${Math.max(5,(m.dpd/max)*90)}%`}} title={`${m.period}: ${m.dpd} DPD`}></div><small>{m.period||i+1}</small></div>)}</div>:<div className="ch15-nochart">Monthly DPD series is not available. Summary metrics below remain sourced from available evidence.</div>}<div className="ch15-repay-stats"><div><b>{val(data.total_payments)}</b><span>Total Payments</span></div><div><b>{val(data.on_time)}</b><span>On Time</span></div><div><b>{val(data.delayed)}</b><span>Delayed</span></div><div><b>{val(data.dpd_30_events)}</b><span>30+ DPD</span></div></div></section>;
}

export function BankingConduct({data={}}) {
  const left=[["Average Monthly Credits",money(data.average_monthly_credits_cr)],["Average Monthly Debits",money(data.average_monthly_debits_cr)],["Average Balance",money(data.average_balance_cr)],["Minimum Balance",money(data.minimum_balance_cr)]];
  const right=[["Cheque Returns (12M)",val(data.cheque_returns_12m),data.cheque_returns_12m>0?"Watch":"Good"],["ECS / EMI Returns",val(data.emi_returns_12m),data.emi_returns_12m>0?"Watch":"Good"],["Overdrawn Days",val(data.overdrawn_days),data.overdrawn_days>15?"Watch":"Good"],["Large Cash Deposits",val(data.large_cash_deposits),"Neutral"]];
  return <section className="journey-card ch15-card"><div className="ch15-head"><h3>♜ Banking Conduct Analysis</h3><span>From available bank-statement / core-banking evidence</span></div><div className="ch15-conduct"><div>{left.map(([a,b])=><p key={a}><span>{a}</span><b>{b}</b></p>)}</div><div>{right.map(([a,b,s])=><p key={a}><span>{a}</span><b>{b}</b><em className={tone(s)}>{s}</em></p>)}</div></div></section>;
}

export function BureauSummary({rows=[]}) {return <section className="journey-card ch15-card"><div className="ch15-head"><h3>▱ Credit Bureau Summary</h3><span>Source-backed fields only</span></div><table className="ch15-table"><thead><tr><th>Parameter</th><th>Value</th><th>Status</th></tr></thead><tbody>{rows.map((r,i)=><tr key={i}><td>{r.parameter}</td><td><b>{r.display}</b></td><td>{r.status?<em className={tone(r.status)}>{r.status}</em>:"—"}</td></tr>)}</tbody></table></section>}

export function Utilisation({data={}}) {return <section className="journey-card ch15-card"><div className="ch15-head"><h3>▥ Utilisation Analysis (CC / OD)</h3><span>POC benchmarks</span></div><table className="ch15-table"><thead><tr><th>Metric</th><th>Value</th><th>Benchmark</th><th>Status</th></tr></thead><tbody>{(data.rows||[]).map((r,i)=><tr key={i}><td>{r.metric}</td><td><b>{r.display}</b></td><td>{r.benchmark}</td><td><em className={tone(r.status)}>{r.status}</em></td></tr>)}</tbody></table></section>}

export function RiskFlags({rows=[]}) {return <section className="journey-card ch15-card"><div className="ch15-head"><h3>⚠ Key Observations & Risk Flags</h3><span>Rule-based</span></div><div className="ch15-flags">{rows.map((r,i)=><div key={i} className={r.level}><i>{r.level==="good"?"✓":r.level==="watch"?"!":r.level==="risk"?"×":"i"}</i><span>{r.text}</span></div>)}</div></section>}

export function CreditCommentary({data={}}) {return <section className="journey-card ch15-comment"><div className="ch15-head"><h3>✦ AI Credit History Commentary</h3><span>{data.source==="ai_generated"?"AI narrative from calculated facts":"Deterministic fallback"}</span></div><p>{data.text||"No commentary available."}</p></section>}

export function CreditSources({items=[],methodology}) {return <div className="ch15-evidence"><span>Evidence:</span>{items.length?items.map((x,i)=><em key={i}>{x.name}</em>):<em>No credit-specific uploaded document identified</em>}<small>{methodology}</small></div>}
