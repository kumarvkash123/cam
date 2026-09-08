"use client";

const money=(v)=>v===null||v===undefined||v===""?"—":`₹ ${Number(v).toFixed(2)} Cr`;
const fmt=(v,u)=>{if(v===null||v===undefined||v==="")return "—"; if(u==="cr")return money(v); if(u==="months")return `${Number(v).toFixed(0)} Months`; if(u==="pct")return `${Number(v).toFixed(2)}%`; if(u==="x")return `${Number(v).toFixed(2)}x`; return String(v)};
const badge=(s)=>{const k=String(s||"Not Assessed").toLowerCase().replace(/[\s/]+/g,"-");return <span className={`lt18-badge ${k}`}>{s||"Not Assessed"}</span>};

export function TermsKpis({data}){const f=data.facility||{},r=data.repayment||{},s=data.security||{};return <div className="lt18-kpis">
  <div><span>Requested Amount</span><strong>{money(f.requested_amount_cr)}</strong><small>Proposal input</small></div>
  <div><span>Proposed Amount</span><strong>{money(f.proposed_amount_cr)}</strong><small>{f.requested_amount_cr===f.proposed_amount_cr?"As requested":"Officer / rule structured"}</small></div>
  <div><span>Proposed Tenor</span><strong>{r.tenor_months?`${r.tenor_months} Months`:"—"}</strong><small>{r.tenor_months?`${(r.tenor_months/12).toFixed(1)} years`:"Not available"}</small></div>
  <div><span>Moratorium</span><strong>{r.moratorium_months!=null?`${r.moratorium_months} Months`:"—"}</strong><small>Principal moratorium</small></div>
  <div><span>Security Coverage</span><strong>{s.coverage_ratio!=null?`${Number(s.coverage_ratio).toFixed(2)}x`:"—"}</strong><small>{s.eligible_value_cr!=null?`Eligible ${money(s.eligible_value_cr)}`:"Not assessed"}</small></div>
  <div><span>Overall Status</span><strong className="lt18-status-text">{data.overall_status||"Not Assessed"}</strong><small>Subject to credit approval</small></div>
</div>}

export function FacilityStructure({data}){const f=data.facility||{};return <section className="journey-card lt18-card"><div className="panel-title"><h2>Facility Structure</h2><span>Proposed structure</span></div><div className="lt18-pairs">
  {[['Facility Type',f.facility_type],['Sanction Type',f.sanction_type],['Proposed Amount',money(f.proposed_amount_cr)],['Purpose',f.purpose],['Utilization Schedule',f.utilization_schedule],['Nature of Facility',f.nature],['Sub-Limit (if any)',f.sub_limit]].map(([a,b])=><div key={a}><span>{a}</span><strong>{b||'Not available'}</strong></div>)}
</div></section>}

export function ComparisonTable({rows=[]}){return <section className="journey-card lt18-card lt18-comparison"><div className="panel-title"><h2>Requested vs Proposed vs Policy</h2><span>Deterministic comparison</span></div><div className="lt18-table-wrap"><table className="lt18-table"><thead><tr><th>Parameter</th><th>Requested</th><th>Proposed</th><th>Policy Limit</th><th>Status</th></tr></thead><tbody>{rows.map((r,i)=><tr key={i}><td><strong>{r.parameter}</strong></td><td>{fmt(r.requested,r.unit)}</td><td>{fmt(r.proposed,r.unit)}</td><td>{r.policy}</td><td>{badge(r.status)}</td></tr>)}</tbody></table></div></section>}

export function PricingDetails({data={}}){return <section className="journey-card lt18-card"><div className="panel-title"><h2>Pricing Details</h2><span>Proposal / pricing data</span></div><div className="lt18-pairs">
  {[['Benchmark',data.benchmark_name],['Benchmark Rate',data.benchmark_rate!=null?`${Number(data.benchmark_rate).toFixed(2)}%`:'Not available'],['Risk / Product Spread',data.spread_bps!=null?`${Number(data.spread_bps).toFixed(0)} bps`:'Not available'],['Indicative Interest Rate',data.indicative_rate!=null?`${Number(data.indicative_rate).toFixed(2)}% p.a.`:'Not available'],['Rate Type',data.rate_type],['Reset Frequency',data.reset_frequency],['Processing Fee',data.processing_fee],['Other Charges',data.other_charges]].map(([a,b])=><div key={a}><span>{a}</span><strong>{b}</strong></div>)}
</div><small className="lt18-note">{data.notice}</small></section>}

export function RepaymentStructure({data={}}){return <section className="journey-card lt18-card"><div className="panel-title"><h2>Repayment Structure</h2><span>Proposed servicing</span></div><div className="lt18-pairs">
  {[['Repayment Type',data.type],['Total Tenor',data.tenor_months?`${data.tenor_months} Months`:'Not available'],['Moratorium (Principal)',data.moratorium_months!=null?`${data.moratorium_months} Months`:'Not available'],['Repayment Period',data.repayment_period_months!=null?`${data.repayment_period_months} Months`:'Not available'],['Interest Payment',data.interest_payment],['Estimated Instalment',data.estimated_installment]].map(([a,b])=><div key={a}><span>{a}</span><strong>{b}</strong></div>)}
</div></section>}

export function SecurityTerms({data={}}){return <section className="journey-card lt18-card"><div className="panel-title"><h2>Security & Collateral</h2><span>From Point 7</span></div><div className="lt18-pairs">
  {[['Primary Security',data.primary_security],['Collateral Security',data.collateral_security],['Security Coverage',data.coverage_ratio!=null?`${Number(data.coverage_ratio).toFixed(2)}x (Eligible: ${money(data.eligible_value_cr)})`:'Not assessed'],['Charge Creation',data.charge_creation],['Insurance',data.insurance],['Valuation Validity',data.valuation_validity]].map(([a,b])=><div key={a}><span>{a}</span><strong>{b}</strong></div>)}
</div></section>}

export function Covenants({rows=[]}){const groups=[...new Set(rows.map(r=>r.group))];return <section className="journey-card lt18-card"><div className="panel-title"><h2>Key Covenants</h2><span>Risk / policy linked</span></div><div className="lt18-covenants">{groups.map(g=><div key={g}><h3>{g}</h3>{rows.filter(r=>r.group===g).map((r,i)=><p key={i}><i>✓</i><span>{r.text}<small>{r.source}</small></span></p>)}</div>)}</div></section>}

export function Conditions({title,items=[]}){return <section className="journey-card lt18-card"><div className="panel-title"><h2>{title}</h2><span>{items.length} condition{items.length===1?'':'s'}</span></div><ol className="lt18-conditions">{items.map((x,i)=><li key={i}>{x}</li>)}</ol></section>}

export function Deviations({rows=[]}){return <section className="journey-card lt18-card"><div className="panel-title"><h2>Policy Deviations / Exceptions</h2><span>{rows.length?`${rows.length} item(s)`:'None identified'}</span></div>{rows.length?<div className="lt18-table-wrap"><table className="lt18-table"><thead><tr><th>Parameter</th><th>Details</th><th>Status</th><th>Action / Mitigant</th></tr></thead><tbody>{rows.map((r,i)=><tr key={i}><td><strong>{r.parameter}</strong></td><td>{r.details}</td><td>{badge(r.status)}</td><td>{r.action}</td></tr>)}</tbody></table></div>:<div className="lt18-empty">No policy deviation identified from available assessed fields.</div>}</section>}

export function TermsCommentary({data={}}){return <section className="journey-card lt18-card lt18-commentary"><div className="panel-title"><h2>✦ AI Loan Terms Commentary</h2><span>{data.source==='ai_generated'?'Groq · grounded':'Deterministic fallback'}</span></div><p>{data.text||'No commentary available.'}</p>{data.error&&<small>AI commentary unavailable: {data.error}</small>}</section>}

export function TermsEditor({draft,onChange,onSave,onCancel,saving}){return <section className="journey-card lt18-editor"><div className="panel-title"><h2>Edit Proposed Terms</h2><span>Officer override — audited in session state</span></div><div className="lt18-edit-grid">
  <label>Facility Type<input value={draft.facility_type||''} onChange={e=>onChange('facility_type',e.target.value)}/></label>
  <label>Proposed Amount (₹ Cr)<input type="number" min="0" step="0.01" value={draft.proposed_amount_cr??''} onChange={e=>onChange('proposed_amount_cr',e.target.value)}/></label>
  <label>Tenor (Months)<input type="number" min="0" step="1" value={draft.tenor_months??''} onChange={e=>onChange('tenor_months',e.target.value)}/></label>
  <label>Moratorium (Months)<input type="number" min="0" step="1" value={draft.moratorium_months??''} onChange={e=>onChange('moratorium_months',e.target.value)}/></label>
  <label>Interest Rate (%)<input type="number" min="0" step="0.01" value={draft.interest_rate??''} onChange={e=>onChange('interest_rate',e.target.value)}/></label>
  <label>Repayment<input value={draft.repayment||''} onChange={e=>onChange('repayment',e.target.value)}/></label>
</div><div className="lt18-editor-actions"><button className="outline-btn" onClick={onCancel} disabled={saving}>Cancel</button><button className="bob-btn" onClick={onSave} disabled={saving}>{saving?'Saving…':'Save / Update'}</button></div></section>}
