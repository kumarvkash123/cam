"use client";

const money=(v)=>v===null||v===undefined?"—":`₹ ${Number(v).toFixed(2)} Cr`;
const chip=(s)=>{const x=String(s||"Not available").toLowerCase().replace(/\s+/g,"-");return <span className={`col17-chip ${x}`}>{s||"Not available"}</span>};

export function CollateralKpis({data}){
  const s=data.summary||{};
  return <div className="col17-kpis">
    <div><span>Total Securities</span><strong>{s.security_count??0}</strong><small>Primary: {s.primary_count??0} · Collateral: {s.collateral_count??0}</small></div>
    <div><span>Total Market Value</span><strong>{money(s.market_value_cr)}</strong><small>Captured securities</small></div>
    <div><span>Eligible Security Value</span><strong>{money(s.eligible_value_cr)}</strong><small>After available adjustments</small></div>
    <div><span>Proposed Exposure</span><strong>{money(s.proposed_exposure_cr)}</strong><small>Proposal amount</small></div>
    <div><span>Security Coverage</span><strong>{s.coverage_ratio!=null?`${Number(s.coverage_ratio).toFixed(2)}x`:"—"}</strong><small>{s.status||"Not assessed"} · threshold {s.policy_threshold?`${Number(s.policy_threshold).toFixed(2)}x`:"—"}</small></div>
  </div>
}

export function SecurityTable({rows=[]}){
  return <section className="journey-card col17-panel"><div className="panel-title"><h2>Security Details</h2><span>{rows.length} captured</span></div>
    <div className="col17-table-wrap"><table className="col17-table"><thead><tr><th>#</th><th>Security / Asset</th><th>Type</th><th>Owner</th><th>Market Value</th><th>Eligible Value</th><th>Charge</th><th>Status</th></tr></thead><tbody>
      {rows.length?rows.map((r,i)=><tr key={r.id||i}><td>{i+1}</td><td><strong>{r.security}</strong><small>{r.category||""}</small></td><td>{r.type||"—"}</td><td>{r.owner||"—"}</td><td>{money(r.market_value_cr)}</td><td>{money(r.eligible_value_cr)}</td><td>{r.charge||"—"}</td><td>{chip(r.charge_status)}</td></tr>):<tr><td colSpan="8" className="col17-empty">No collateral/security could be identified from the current proposal or uploaded evidence.</td></tr>}
    </tbody></table></div></section>
}

export function CoveragePanel({data={}}){
  const max=Math.max(Number(data.market_value_cr||0),Number(data.eligible_value_cr||0),Number(data.proposed_exposure_cr||0),1);
  const bars=[['Market Value',data.market_value_cr],['Eligible Value',data.eligible_value_cr],['Exposure',data.proposed_exposure_cr]];
  return <section className="journey-card col17-panel"><div className="panel-title"><h2>Security Coverage Analysis</h2><span>Deterministic</span></div>
    <div className="col17-bars">{bars.map(([l,v])=><div key={l}><b style={{height:`${Math.max(8,(Number(v||0)/max)*110)}px`}}></b><strong>{v!=null?Number(v).toFixed(2):'—'}</strong><span>{l}</span></div>)}</div>
    <div className="col17-summary-list"><div><span>Eligible Security Value</span><strong>{money(data.eligible_value_cr)}</strong></div><div><span>Proposed Exposure</span><strong>{money(data.proposed_exposure_cr)}</strong></div><div><span>Security Coverage</span><strong>{data.coverage_ratio!=null?`${Number(data.coverage_ratio).toFixed(2)}x`:'—'}</strong></div><div><span>Configured Threshold</span><strong>{data.policy_threshold?`≥ ${Number(data.policy_threshold).toFixed(2)}x`:'—'}</strong></div><div><span>Coverage Status</span>{chip(data.status)}</div></div>
    <small className="col17-method">{data.threshold_source}</small>
  </section>
}

export function ValuationTable({rows=[]}){
  return <section className="journey-card col17-panel"><div className="panel-title"><h2>Valuation Details</h2><span>Age checked automatically</span></div><div className="col17-table-wrap"><table className="col17-table"><thead><tr><th>Security</th><th>Valuer</th><th>Valuation Date</th><th>Market</th><th>Realizable</th><th>Distress</th><th>Age</th><th>Status</th></tr></thead><tbody>
  {rows.length?rows.map((r,i)=><tr key={i}><td><strong>{r.security}</strong></td><td>{r.valuer}</td><td>{r.valuation_date}</td><td>{money(r.market_value_cr)}</td><td>{money(r.realizable_value_cr)}</td><td>{money(r.distress_value_cr)}</td><td>{r.age_months!=null?`${r.age_months} months`:'—'}</td><td>{chip(r.status)}</td></tr>):<tr><td colSpan="8" className="col17-empty">No valuation evidence available.</td></tr>}
  </tbody></table></div></section>
}

export function ValidationChecks({rows=[]}){return <section className="journey-card col17-panel"><div className="panel-title"><h2>Ownership & Charge Validation</h2><span>Cross-checks</span></div><div className="col17-checks">{rows.map((r,i)=><div key={i}><span>{r.check}</span><strong>{r.detail}</strong>{chip(r.status)}</div>)}</div></section>}

export function DocumentChecklist({rows=[]}){return <section className="journey-card col17-panel"><div className="panel-title"><h2>Document Checklist</h2><span>Evidence availability</span></div><div className="col17-checks docs">{rows.map((r,i)=><div key={i}><span>{r.document}</span><strong>{r.remarks}</strong>{chip(r.status)}</div>)}</div></section>}

export function Observations({rows=[]}){return <section className="journey-card col17-panel"><div className="panel-title"><h2>Key Observations</h2><span>Rules & evidence</span></div><div className="col17-observations">{rows.map((r,i)=><p className={r.level||'info'} key={i}><i>{r.level==='good'?'✓':r.level==='risk'?'!':'•'}</i>{r.text}</p>)}</div></section>}

export function CollateralCommentary({data={}}){return <section className="journey-card col17-panel col17-commentary"><div className="panel-title"><h2>✦ AI Collateral Commentary</h2><span>{data.source==='ai_generated'?'Groq · grounded':'Deterministic fallback'}</span></div><p>{data.text||'No commentary available.'}</p></section>}

export function CollateralSources({items=[],methodology,notice}){return <details className="journey-card col17-sources"><summary>Evidence & methodology ({items.length} source{items.length===1?'':'s'})</summary><p>{methodology}</p>{items.map((s,i)=><div key={i}><strong>{s.document_type||s.type}</strong><span>{s.name}</span></div>)}<small>{notice}</small></details>}
