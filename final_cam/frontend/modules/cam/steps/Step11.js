"use client";
import { useEffect, useMemo, useState } from "react";

const statusClass = (s) => String(s || "").toLowerCase().replace(/_/g, "-");
const severityClass = (s) => String(s || "").toLowerCase();

function ComplianceTable({ rows = [], filter, setFilter }) {
  const filtered = rows.filter((r) => {
    const catOk = !filter.category || filter.category === "All" || r.category === filter.category;
    const statusOk = !filter.status || filter.status === "All" || r.status === filter.status;
    const q = String(filter.q || "").trim().toLowerCase();
    const text = `${r.name} ${r.category} ${r.evidence} ${r.remarks}`.toLowerCase();
    return catOk && statusOk && (!q || text.includes(q));
  });
  const categories = ["All", ...Array.from(new Set(rows.map((r) => r.category).filter(Boolean)))];
  return <section className="journey-card rc23-checklist">
    <div className="rc23-section-head"><div><h2>Compliance Checklist ({rows.length} Checks)</h2><p>Deterministic checks using the latest CAM and supporting evidence.</p></div>
      <div className="rc23-filters">
        <select value={filter.category} onChange={e=>setFilter(f=>({...f,category:e.target.value}))}>{categories.map(x=><option key={x}>{x}</option>)}</select>
        <select value={filter.status} onChange={e=>setFilter(f=>({...f,status:e.target.value}))}>{["All","PASS","WARNING","FAIL","REVIEW","NOT_APPLICABLE"].map(x=><option key={x}>{x}</option>)}</select>
        <input value={filter.q} onChange={e=>setFilter(f=>({...f,q:e.target.value}))} placeholder="Search checks..." />
      </div>
    </div>
    <div className="rc23-table-wrap"><table className="rc23-table"><thead><tr><th>#</th><th>Compliance Check</th><th>Category</th><th>Status</th><th>Evidence / Source</th><th>Remarks</th></tr></thead><tbody>
      {filtered.map((r,i)=><tr key={r.code || i}><td>{i+1}</td><td><b>{r.name}</b><small>{r.code}</small></td><td>{r.category}</td><td><span className={`rc23-status ${statusClass(r.status)}`}>{r.status}</span></td><td>{r.evidence}<small>{r.source}</small></td><td>{r.remarks}</td></tr>)}
      {!filtered.length&&<tr><td colSpan="6" className="rc23-empty">No checks match the selected filters.</td></tr>}
    </tbody></table></div>
  </section>;
}

function IssueList({ title, rows = [], kind }) {
  return <section className="journey-card rc23-issues"><div className="rc23-section-head"><div><h2>{title} ({rows.length})</h2></div></div>
    {rows.length ? <div className="rc23-issue-list">{rows.slice(0,6).map((r,i)=><div key={r.code || i} className={`rc23-issue ${kind}`}><div><strong>{r.name}</strong><span className={`rc23-severity ${severityClass(r.severity)}`}>{r.severity || "Review"}</span></div><p>{r.remarks}</p><small>{r.evidence}</small></div>)}</div> : <div className="rc23-empty">No {title.toLowerCase()} identified.</div>}
  </section>;
}

export default function Step11(ctx) {
  const { sessionId, apiRequest, PageHeader, go, setJourneyStep } = ctx;
  const [data,setData]=useState(null);
  const [loading,setLoading]=useState(true);
  const [running,setRunning]=useState(false);
  const [error,setError]=useState("");
  const [filter,setFilter]=useState({category:"All",status:"All",q:""});

  async function load(force=false){
    if(!sessionId)return;
    setLoading(true); setError("");
    try{
      const path=`/api/cam/regulatory-compliance/${sessionId}${force?"?refresh=1":""}`;
      setData(await apiRequest(path));
    }catch(e){ setError(e.message || "Unable to load Regulatory & Compliance checks"); }
    finally{setLoading(false);}
  }
  async function rerun(){
    if(!sessionId)return;
    setRunning(true); setError("");
    try{ setData(await apiRequest(`/api/cam/regulatory-compliance/${sessionId}`,{method:"POST"})); }
    catch(e){setError(e.message || "Unable to run compliance checks");}
    finally{setRunning(false);}
  }
  useEffect(()=>{load(false)},[sessionId]);

  const counts=data?.counts||{};
  const score=Number(data?.overall_score||0);
  const ready=Boolean(data?.status==="completed");
  const categories=useMemo(()=>data?.category_scores||[],[data]);

  return <div className="rc23-page">
    <PageHeader number="9" title="Regulatory & Compliance Checks" subtitle="Verify regulatory, statutory and internal policy compliance with clear exceptions, evidence and mitigants." action={<div className="rc23-header-actions"><button className="outline-btn" onClick={()=>go(13)}>View Policy</button><button className="bob-btn" disabled={running} onClick={rerun}>{running?"Running Checks...":ready?"↻ Re-run Compliance Checks":"▶ Run Compliance Checks"}</button></div>} />

    {loading&&<section className="journey-card rc23-loading">Loading Point 9 compliance checks from the latest CAM data…</section>}
    {error&&<section className="journey-card rc23-error"><strong>Compliance analysis needs attention.</strong><span>{error}</span>{!running&&<button className="outline-btn" onClick={rerun}>Run Compliance Checks</button>}</section>}

    {data&&<>
      <div className="rc23-summary-grid">
        <section className="journey-card rc23-overall">
          <div className="rc23-ring" style={{"--score":`${score}%`}}><div><strong>{score}%</strong><span>Compliance</span></div></div>
          <div className="rc23-overall-main"><div className="rc23-title-line"><h2>Overall Compliance Status</h2><span className={`rc23-label ${score>=80?"good":score>=60?"warn":"bad"}`}>{data.overall_label}</span></div>
            <div className="rc23-kpis"><div className="pass"><b>{counts.passed||0}</b><span>Passed</span></div><div className="warn"><b>{counts.warnings||0}</b><span>Warnings</span></div><div className="fail"><b>{counts.failed||0}</b><span>Failed</span></div><div className="na"><b>{(counts.not_applicable||0)+(counts.review||0)}</b><span>Review / N.A.</span></div></div>
            <div className="rc23-meta">Total Checks: <b>{data.total_checks}</b> · Last Run: <b>{data.generated_at?new Date(data.generated_at).toLocaleString():"—"}</b> · Status: <b>Completed</b></div>
          </div>
        </section>
        <section className={`journey-card rc23-readiness ${ready?"ok":"warn"}`}><div className="rc23-ready-icon">{ready?"✓":"!"}</div><div><h2>Compliance Readiness</h2><strong>{ready?"Ready for Policy Analysis":"Compliance run required"}</strong><p>{ready?"All current Point 9 checks have been evaluated. Continue to CAM vs Policy Analysis.":"Run Point 9 checks before continuing."}</p></div></section>
      </div>

      <div className="rc23-main-grid">
        <ComplianceTable rows={data.checks||[]} filter={filter} setFilter={setFilter}/>
        <aside className="rc23-side">
          <section className="journey-card rc23-categories"><h2>Compliance by Category</h2>{categories.map((r,i)=><div className="rc23-cat" key={i}><span>{r.category}</span><div><i style={{width:`${r.score}%`}} className={r.score>=90?"good":r.score>=75?"mid":"bad"}/></div><b>{r.score}%</b></div>)}</section>
          <section className="journey-card rc23-actions"><h2>Quick Actions</h2><button onClick={rerun}>↻ Re-run Compliance Checks</button><button onClick={()=>go(13)}>▤ View Policy Documents</button><button onClick={()=>go(14)} disabled={!ready}>⚖ Open CAM vs Policy Analysis</button></section>
        </aside>
      </div>

      <div className="rc23-two"><IssueList title="Key Exceptions" rows={data.exceptions||[]} kind="fail"/><IssueList title="Warnings" rows={data.warnings_list||[]} kind="warn"/></div>

      <div className="rc23-two">
        <section className="journey-card rc23-mitigants"><div className="rc23-section-head"><div><h2>Mitigants & Recommendations</h2><p>Action items mapped directly to deterministic findings.</p></div></div>{(data.mitigants||[]).length?<div className="rc23-mit-list">{data.mitigants.map((m,i)=><div key={i}><span>{i+1}</span><div><strong>{m.recommendation}</strong><small>{m.related_issue}</small></div><b className={`rc23-severity ${severityClass(m.priority)}`}>{m.priority}</b></div>)}</div>:<div className="rc23-empty">No mitigation action is currently required.</div>}</section>
        <section className="journey-card rc23-insights"><div className="rc23-section-head"><div><h2>✦ AI-style Insights</h2><p>Bullet presentation of deterministic results; no AI pass/fail decision.</p></div></div><ul>{(data.ai_insights||[]).map((x,i)=><li key={i}>{x}</li>)}</ul><small>{data.methodology}</small></section>
      </div>

      <div className="rc23-footer"><button className="outline-btn" onClick={()=>setJourneyStep?setJourneyStep(10):go(10)}>← Back to Loan Terms</button><button className="bob-btn" disabled={!ready} onClick={()=>go(14)}>Continue to CAM vs Policy Analysis →</button></div>
    </>}
  </div>;
}
