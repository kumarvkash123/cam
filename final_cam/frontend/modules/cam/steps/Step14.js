"use client";
import { useEffect, useMemo, useState } from "react";

const fmt = (r, v) => {
  if (v === null || v === undefined) return "—";
  if (r.unit === "₹ Cr") return `₹ ${Number(v).toFixed(2)} Cr`;
  if (r.unit === "x") return `${Number(v).toFixed(2)}x`;
  if (r.unit === "%") return `${Number(v).toFixed(2)}%`;
  return `${v}${r.unit ? ` ${r.unit}` : ""}`;
};

export default function Step14(ctx) {
  const { sessionId, companyName, camInfo, analysisComplete, setPolicyIndexed, setPolicyAnalysisComplete, apiRequest, PageHeader, go, setError } = ctx;
  const [readiness,setReadiness]=useState(null), [result,setResult]=useState(null), [busy,setBusy]=useState(false);
  const [q,setQ]=useState(""), [category,setCategory]=useState("All"), [status,setStatus]=useState("All"), [history,setHistory]=useState([]), [copilot,setCopilot]=useState("");

  async function load() {
    if(!sessionId) return;
    try {
      const r=await apiRequest(`/api/cam/policy-readiness/${sessionId}`); setReadiness(r); setPolicyIndexed(Boolean(r.policy_available)); setPolicyAnalysisComplete(Boolean(r.analysis_complete));
      if(!r.policy_available){ go(13); return; }
      const a=await apiRequest(`/api/cam/policy-analysis/${sessionId}`); if(a.analysis) setResult(a.analysis);
      const h=await apiRequest(`/api/cam/policy-history/${sessionId}`); setHistory(h.history||[]);
    } catch(e){ setError(e.message); }
  }
  useEffect(()=>{load();},[sessionId]);

  async function run(){
    if(!readiness?.can_run_policy_analysis){
      const missing=(readiness?.missing_cam_sections||[]).map(x=>`${x.number} ${x.title}`).join(", ");
      setError(readiness?.message || (missing ? `Complete CAM sections: ${missing}` : "CAM vs Policy Analysis is not ready to run."));
      return;
    }
    setBusy(true);
    try{
      const d=await apiRequest(`/api/cam/policy-analysis/${sessionId}`,{method:"POST"});
      setResult(d.analysis); setReadiness(d.readiness); setPolicyAnalysisComplete(Boolean(d.readiness?.analysis_complete));
      const h=await apiRequest(`/api/cam/policy-history/${sessionId}`); setHistory(h.history||[]);
    }catch(e){setError(e.message)}finally{setBusy(false)}
  }

  const rows=result?.results||[];
  const cats=["All",...new Set(rows.map(r=>r.category))];
  const filtered=useMemo(()=>rows.filter(r=>(category==="All"||r.category===category)&&(status==="All"||r.result===status)&&(!q||`${r.title} ${r.rule_id} ${r.source_ref}`.toLowerCase().includes(q.toLowerCase()))),[rows,category,status,q]);
  const deviations=rows.filter(r=>r.result==="DEVIATION"||r.result==="WARNING").slice(0,4);
  const counts=result?.counts||{PASS:0,WARNING:0,DEVIATION:0,NOT_APPLICABLE:0};
  const stale=Boolean(readiness?.analysis_required);
  const canRun=Boolean(readiness?.can_run_policy_analysis);
  const camComplete=Boolean(readiness?.cam_analysis_complete ?? analysisComplete);
  const missingSections=readiness?.missing_cam_sections||[];
  const readinessTitle=!readiness?.policy_available ? "No active policy" : !camComplete ? "CAM analysis incomplete" : stale ? "Policy analysis requires refresh" : "Policy is up to date";
  const readinessText=readiness?.message || (stale ? "Policy or CAM state changed since the last analysis." : `Version ${readiness?.policy_version_used||readiness?.policy?.version||"2026.09"} was used in the latest completed analysis.`);

  return <>
    <PageHeader number={14} title="CAM vs Policy Analysis" subtitle="Select the CAM / company, apply filters and run deterministic policy checks against the active policy set." action={<div className="policy-header-actions"><button className="outline-btn">☆ Ask AI Copilot</button><button className="outline-btn">⇩ Export Report</button></div>}/>

    <section className="journey-card policy-selector-card">
      <div className="policy-section-heading">1. Select CAM / Company to Analyze</div>
      <div className="policy-filter-row">
        <label>Search CAM ID / Company / Borrower<input value={q} onChange={e=>setQ(e.target.value)} placeholder="Search CAM ID, company name, borrower..."/></label>
        <label>Company<select><option>{companyName}</option></select></label>
        <label>Loan Type<select><option>{camInfo?.loan_type || "MSME / Term Loan"}</option></select></label>
        <label>Status<select><option>{camComplete ? "Analysis Complete" : "In Analysis"}</option></select></label>
        <button className="filter-reset" onClick={()=>setQ("")}>Reset</button>
        <button className="bob-btn policy-run-btn" onClick={run} disabled={busy||!canRun}>▷ {busy?"Running Analysis...":result&&stale?"Re-run CAM vs Policy Analysis":"Run CAM vs Policy Analysis"}</button>
      </div>
      <div className="policy-top-cards">
        <div className="policy-cam-card"><span className="policy-card-icon">▦</span><div><h3>{camInfo?.cam_id||"Current CAM"} <em>Selected</em></h3><strong>{companyName}</strong><p>Facility: {camInfo?.loan_type||"MSME"} &nbsp; | &nbsp; Requested Amount: {camInfo?.loan_amount||"₹25.00 Cr"}</p></div></div>
        <div className="policy-cam-card"><span className="policy-card-icon">▤</span><div><h3>Active Policy Set <em className="active">ACTIVE</em></h3><strong>{readiness?.policy?.policy_name||"Synthetic MSME Credit Policy 2026"}</strong><p>Version {readiness?.policy?.version||"2026.09"} · {readiness?.policy?.total_rules||44} rules · {readiness?.policy?.source||"synthetic"}</p><button onClick={()=>go(13)} className="text-link">View Policy Documents →</button></div></div>
        <div className={`policy-cam-card readiness ${(!canRun||stale)?"warning":"ok"}`}><span className="policy-card-icon">{(!canRun||stale)?"!":"✓"}</span><div><h3>Policy Readiness</h3><strong>{readinessTitle}</strong><p>{readinessText}</p>{!camComplete&&missingSections.length>0&&<small className="policy-missing-sections">Pending: {missingSections.map(x=>`${x.number} ${x.title}`).join(" • ")}</small>}</div></div>
      </div>
    </section>

    <div className="policy-summary-grid">
      <section className="journey-card policy-overall"><div className="policy-section-heading">2. Overall Policy Compliance</div><div className="policy-overall-body"><div className="policy-gauge"><strong>{result?`${result.compliance}%`:"—"}</strong><span>Policy Compliant</span></div><div className="policy-kpis"><div className="pass"><b>{counts.PASS}</b><span>Passed</span></div><div className="warn"><b>{counts.WARNING}</b><span>Warnings</span></div><div className="fail"><b>{counts.DEVIATION}</b><span>Deviations</span></div><div className="na"><b>{counts.NOT_APPLICABLE}</b><span>Not Applicable</span></div><small>Total Rules Checked: <b>{result?.total_rules||0}</b></small></div></div></section>
      <section className="journey-card"><div className="policy-section-heading">3. Policy by Policy Compliance</div>{(result?.category_scores||[]).map(c=><div className="policy-progress-row" key={c.category}><span>{c.category}</span><div><i style={{width:`${c.score}%`}} className={c.score>=85?"good":c.score>=70?"mid":"bad"}/></div><b>{c.score}%</b></div>)}{!result&&<div className="policy-empty">Run analysis to see category compliance.</div>}</section>
    </div>

    <div className="policy-main-grid">
      <section className="journey-card policy-comparison"><div className="policy-section-line"><div className="policy-section-heading">4. CAM Draft vs Policy Comparison</div><div className="policy-table-filters"><select value={category} onChange={e=>setCategory(e.target.value)}>{cats.map(c=><option key={c}>{c}</option>)}</select><select value={status} onChange={e=>setStatus(e.target.value)}><option>All</option><option>PASS</option><option>WARNING</option><option>DEVIATION</option></select></div></div>
        <div className="policy-table-wrap"><table className="policy-table"><thead><tr><th>#</th><th>Parameter</th><th>CAM Draft Value</th><th>Policy Requirement</th><th>Result</th><th>Gap / Remarks</th><th>Policy Source</th><th>Action</th></tr></thead><tbody>{filtered.slice(0,12).map((r,i)=><tr key={r.rule_id}><td>{i+1}</td><td><b>{r.title}</b><small>{r.rule_id}</small></td><td>{fmt(r,r.cam_value)}</td><td>{r.operator&&r.threshold!==undefined?`${r.operator} ${fmt(r,r.threshold)}`:"As per policy"}</td><td><span className={`policy-result ${r.result.toLowerCase()}`}>{r.result}</span></td><td className={r.result!=="PASS"?"policy-gap":""}>{r.gap!==null&&r.gap!==undefined?`${r.gap>0?"+":""}${Number(r.gap).toFixed(2)} ${r.unit||""}`:"Within policy"}</td><td>{r.source_ref}</td><td><button className="text-link">View</button></td></tr>)}</tbody></table></div>
      </section>
      <section className="journey-card policy-deviations"><div className="policy-section-line"><div className="policy-section-heading">5. Key Policy Deviations ({deviations.length})</div><button className="text-link">View All</button></div>{deviations.map(r=><div className={`deviation-card ${r.result.toLowerCase()}`} key={r.rule_id}><div><b>{r.result==="DEVIATION"?"⊗":"!"} {r.title}</b><span className="severity">{r.severity}</span></div><div className="deviation-values"><span>CAM Value<strong>{fmt(r,r.cam_value)}</strong></span><span>Policy Requirement<strong>{r.operator} {fmt(r,r.threshold)}</strong></span><span>Gap<strong>{r.gap!==null?Number(r.gap).toFixed(2):"—"} {r.unit}</strong></span></div><small>Policy Source: {r.source_ref}</small><button className="outline-btn small">View Details</button></div>)}{!deviations.length&&<div className="policy-empty">No deviations to display.</div>}</section>
    </div>

    <div className="policy-bottom-grid">
      <section className="journey-card"><div className="policy-section-heading">6. Ask AI Copilot about this Analysis</div><div className="policy-copilot-input"><input value={copilot} onChange={e=>setCopilot(e.target.value)} placeholder="Ask about deviations, policy rules or recommendations..."/><button onClick={()=>setCopilot("")}>→</button></div><div className="policy-prompt-chips"><button>Why is collateral coverage a deviation?</button><button>Can this be approved with mitigants?</button><button>Show policy rules for DSCR</button><button>Suggest conditions</button></div></section>
      <section className="journey-card"><div className="policy-section-heading">7. Analysis History</div><table className="policy-history"><thead><tr><th>Policy Version</th><th>Run Date</th><th>Compliance</th><th>Passed</th><th>Warnings</th><th>Deviations</th></tr></thead><tbody>{history.map((h,i)=><tr key={i}><td>{h.policy_version}</td><td>{h.run_at?new Date(h.run_at).toLocaleDateString():"—"}</td><td>{h.compliance}%</td><td>{h.counts?.PASS||0}</td><td>{h.counts?.WARNING||0}</td><td>{h.counts?.DEVIATION||0}</td></tr>)}</tbody></table></section>
    </div>
    <div className="policy-footer-actions"><button className="outline-btn" onClick={()=>go(13)}>← Policy Documents</button><button className="bob-btn" onClick={()=>go(15)} disabled={!result||!readiness?.analysis_complete}>Continue to Final CAM Review →</button></div>
  </>;
}
