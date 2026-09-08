"use client";

const sevClass=(s)=>String(s||"").toLowerCase().replace(/\s+/g,"-");
const badge=(s)=><span className={`ra16-badge ${sevClass(s)}`}>{s||"—"}</span>;

export function OverallRisk({data}){
 const o=data?.overall||{}; const score=o.score;
 return <section className="journey-card ra16-card"><div className="ra16-head"><h3>Overall Risk Assessment</h3><span>Decision support</span></div><div className="ra16-overall"><div className={`ra16-gauge ${sevClass(o.rating)}`}><div><b>{score==null?"—":score}</b><span>{score==null?"":" / 100"}</span></div><em>{o.rating||"Not Assessed"}</em></div><div className="ra16-counts"><p><i className="high"/>High Risks <b>{o.high??0}</b></p><p><i className="moderate"/>Moderate Risks <b>{o.moderate??0}</b></p><p><i className="low"/>Low Categories <b>{o.low??0}</b></p><p><i className="high"/>Policy Deviations <b>{o.policy_deviations??0}</b></p></div></div></section>
}

export function CategorySummary({rows=[]}){
 return <section className="journey-card ra16-card"><div className="ra16-head"><h3>Risk Category Summary</h3><span>{rows.filter(x=>x.available).length} assessed</span></div><div className="ra16-categories">{rows.map((r,i)=><div key={i}><span>{r.category}</span><div className="ra16-meter"><i className={sevClass(r.severity)} style={{width:r.score==null?"0%":`${Math.max(8,r.score)}%`}}/></div>{badge(r.severity)}</div>)}</div></section>
}

export function RiskMatrix({risks=[]}){
 const cells=[["High","Low"],["High","Medium"],["High","High"],["Medium","Low"],["Medium","Medium"],["Medium","High"],["Low","Low"],["Low","Medium"],["Low","High"]];
 const count=(l,i)=>risks.filter(r=>String(r.likelihood).toLowerCase()===l.toLowerCase()&&String(r.impact).toLowerCase()===i.toLowerCase()).length;
 return <section className="journey-card ra16-card"><div className="ra16-head"><h3>Risk Matrix</h3><span>Likelihood × impact</span></div><div className="ra16-matrix-wrap"><span className="ra16-y">Likelihood</span><div className="ra16-matrix">{cells.map(([l,i],idx)=>{const c=count(l,i); return <div key={idx} className={`m-${l.toLowerCase()}-${i.toLowerCase()}`} title={`${l} likelihood / ${i} impact`}>{c>0?<b>{c}</b>:null}</div>})}</div><span className="ra16-x">Impact →</span></div><div className="ra16-matrix-legend"><span><i className="low"/>Low</span><span><i className="moderate"/>Moderate</span><span><i className="high"/>High</span></div></section>
}

export function RiskRegister({rows=[]}){
 return <section className="journey-card ra16-card ra16-register"><div className="ra16-head"><h3>Key Risks & Mitigation Plan</h3><span>{rows.length} identified</span></div><div className="ra16-table-wrap"><table className="ra16-table"><thead><tr><th>#</th><th>Risk Area</th><th>Key Risk / Observation</th><th>Severity</th><th>Mitigation Factors / Suggested Conditions</th></tr></thead><tbody>{rows.length?rows.map((r,i)=><tr key={i}><td>{i+1}</td><td><b>{r.risk_area}</b><small>{r.category}</small></td><td>{r.observation}<small>Source: {r.source}</small></td><td>{badge(r.severity)}</td><td><ul>{(r.mitigation||[]).map((m,j)=><li key={j}>{m}</li>)}</ul></td></tr>):<tr><td colSpan="5" className="ra16-empty">No material risk trigger was identified from the currently assessed data. Unassessed categories remain excluded.</td></tr>}</tbody></table></div></section>
}

export function Thresholds({rows=[]}){
 return <section className="journey-card ra16-card"><div className="ra16-head"><h3>Policy / Threshold Comparison</h3><span>Configured / available rules</span></div><div className="ra16-table-wrap"><table className="ra16-table ra16-threshold"><thead><tr><th>Indicator</th><th>Actual Value</th><th>Threshold</th><th>Result</th></tr></thead><tbody>{rows.length?rows.map((r,i)=><tr key={i}><td><b>{r.indicator}</b><small>{r.source}</small></td><td>{r.actual}</td><td>{r.threshold}</td><td>{badge(r.result)}</td></tr>):<tr><td colSpan="4" className="ra16-empty">No calculated threshold comparison is currently available.</td></tr>}</tbody></table></div></section>
}

function ListCard({title,items=[],kind}){return <section className="journey-card ra16-card"><div className="ra16-head"><h3>{title}</h3><span>{items.length}</span></div><div className="ra16-list">{items.length?items.map((x,i)=><div key={i} className={kind}><i>{kind==="positive"?"✓":"!"}</i><span>{x}</span></div>):<div className="ra16-empty-block">No item available from current evidence.</div>}</div></section>}
export function PositiveFactors({items}){return <ListCard title="Positive / Mitigating Factors" items={items} kind="positive"/>}
export function Concerns({items}){return <ListCard title="Key Concerns" items={items} kind="concern"/>}

export function RiskCommentary({data}){const text=data?.text||"Risk commentary is not available.";const bullets=String(text).replace(/\b(Pvt|Ltd|Mr|Mrs|Ms|Dr|Prof|No|Cr)\./g,"$1§").split(/(?<=[.!?])\s+(?=[A-Z0-9₹])/).filter(Boolean).map(x=>x.replace(/§/g,"."));return <section className="journey-card ra16-card ra16-comment"><div className="ra16-head"><h3>✦ AI Risk Assessment & Commentary</h3><span>{data?.source==="ai_generated"?"AI phrasing":"Deterministic fallback"}</span></div><ul className="cam-narrative-bullets">{bullets.map((x,i)=><li key={i}>{x}</li>)}</ul>{data?.error&&<small>AI note: {data.error}</small>}</section>}

export function RiskSources({items=[],methodology,notice}){return <div className="ra16-evidence"><strong>Evidence:</strong>{items.map((x,i)=><span key={i}>{x.name}</span>)}<small>{methodology}</small><em>{notice}</em></div>}

export function RiskAssessmentRegister({rows=[]}){
 return <section className="journey-card ra16-card ra16-register"><div className="ra16-head"><h3>Risk Assessment Register</h3><span>{rows.length} identified</span></div><div className="ra16-table-wrap"><table className="ra16-table"><thead><tr><th>#</th><th>Risk Area</th><th>Key Risk / Observation</th><th>Severity</th><th>Evidence</th></tr></thead><tbody>{rows.length?rows.map((r,i)=><tr key={i}><td>{i+1}</td><td><b>{r.risk_area}</b><small>{r.category}</small></td><td>{r.observation}</td><td>{badge(r.severity)}</td><td>{r.source||"CAM evidence"}</td></tr>):<tr><td colSpan="5" className="ra16-empty">No material risk trigger was identified from the currently assessed data.</td></tr>}</tbody></table></div></section>
}

export function MitigationPlan({rows=[]}){
 return <section className="journey-card ra16-card ra16-register ra16-mitigation-plan"><div className="ra16-head"><h3>Final Risk Mitigation Plan</h3><span>Post Point-7 / Point-10 refresh</span></div><div className="ra16-table-wrap"><table className="ra16-table"><thead><tr><th>#</th><th>Risk Area</th><th>Severity</th><th>Final Mitigation Factors / Suggested Controls</th><th>Evidence</th></tr></thead><tbody>{rows.length?rows.map((r,i)=><tr key={i}><td>{i+1}</td><td><b>{r.risk_area}</b><small>{r.category}</small></td><td>{badge(r.severity)}</td><td><ul>{(r.mitigation||[]).map((m,j)=><li key={j}>{m}</li>)}</ul></td><td>{r.source||"CAM evidence"}</td></tr>):<tr><td colSpan="5" className="ra16-empty">No material mitigation item is required from the currently assessed evidence.</td></tr>}</tbody></table></div></section>
}
