"use client";

import { useEffect, useMemo, useState } from "react";

const LABELS = {
  complete: "Complete",
  partial: "Partial",
  review_required: "Review Required",
  missing: "Missing",
  processed: "Processed",
  under_review: "Under Review",
};

function pretty(v) {
  const key = String(v || "").toLowerCase().replaceAll(" ", "_");
  return LABELS[key] || String(v || "Pending").replaceAll("_", " ");
}

export default function Step4(ctx) {
  const { sessionId, companyName, camInfo, mca, analysis, analysisStarted, startAnalysis, apiRequest, PageHeader, go, setError } = ctx;
  const [ready, setReady] = useState(null);
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const [opening, setOpening] = useState(false);

  async function loadReadiness() {
    if (!sessionId) return;
    try {
      setLoading(true);
      setReady(await apiRequest(`/api/cam/readiness/${sessionId}`));
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }

  async function openLoanSummaryWhenReady() {
    if (opening || !sessionId) return;
    setOpening(true);
    try {
      const summary = await apiRequest(`/api/cam/loan-summary/${sessionId}`);
      if (summary?.summary_source === "ai_generated" && summary?.executive_summary && summary?.context) go(5);
      else setError((summary?.llm_status || {}).error || "Loan Summary is not ready yet.");
    } catch (e) { setError(e.message); }
    finally { setOpening(false); }
  }

  useEffect(() => { loadReadiness(); /* eslint-disable-next-line */ }, [sessionId]);
  useEffect(() => {
    if (analysis?.loan_summary_ready) openLoanSummaryWhenReady();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [analysis?.loan_summary_ready]);

  const mcaData = mca?.data || mca || {};
  const score = ready?.score || 0;
  const stages = analysis?.analysis_stages || {};
  const preparing = analysisStarted && !analysis?.loan_summary_ready;
  const stageRows = [
    ["evidence", "Borrower & verified evidence"], ["financial", "Financial analysis"],
    ["credit_risk", "Credit & risk evidence"], ["collateral_compliance", "Collateral & compliance"],
    ["loan_summary", "Groq Executive Loan Summary"], ["regulatory_compliance", "9 Regulatory & Compliance"], ["remaining_cam", "Final CAM packaging"],
  ];
  const high = useMemo(() => (ready?.missing_items || []).filter(x => x.priority === "high").length, [ready]);

  async function begin() {
    setStarting(true);
    const ok = await startAnalysis();
    setStarting(false);
    if (!ok) return;
  }

  async function retryGroq() {
    setRetrying(true);
    try {
      const summary = await apiRequest(`/api/cam/loan-summary/${sessionId}?refresh=1`);
      if (summary?.summary_source === "ai_generated" && summary?.executive_summary) go(5);
      else setError((summary?.llm_status || {}).error || "Groq Loan Summary generation failed.");
    } catch (e) { setError(e.message); }
    finally { setRetrying(false); }
  }

  return <>
    <PageHeader number={4} title="CAM Readiness / Start CAM" subtitle="Review data completeness and ensure required inputs are available before starting CAM preparation." />

    <section className="journey-card readiness-borrower">
      <div className="readiness-borrower-icon">▥</div>
      <div className="readiness-borrower-main">
        <div className="readiness-borrower-title"><h2>{companyName}</h2><span className="readiness-active">Active</span></div>
        <p>CIN: {mcaData.cin || "—"} <b>│</b> GSTIN: {mcaData.gstin || "—"} <b>│</b> PAN: {mcaData.pan || "—"}</p>
        <p>Industry: {mcaData.industry || "Not available"} <b>│</b> RM: {camInfo?.relationship_manager || "Not assigned"}</p>
      </div>
      <button className="secondary-btn" onClick={() => go(6)}>View Borrower Profile</button>
    </section>

    {!preparing && !analysis?.loan_summary_ready ? <>
      <div className="readiness-top-grid">
        <section className="journey-card readiness-panel">
          <div className="panel-title"><h2>CAM Readiness Checklist</h2><span>{ready?.completed_modules || 0} / {ready?.total_modules || 7} modules</span></div>
          <div className="readiness-list">
            {(ready?.checklist || []).map(x => <div className="readiness-row" key={x.key}>
              <div><strong>{x.label}</strong><small>{x.description}</small></div>
              <span className={`readiness-status ${x.status}`}>{pretty(x.status)}</span><b>{x.weight}%</b>
            </div>)}
          </div>
          <button className="readiness-link" onClick={() => go(3)}>View Detailed Readiness →</button>
        </section>

        <section className="journey-card readiness-panel">
          <div className="panel-title"><h2>Key Documents Overview</h2><button className="link-button" onClick={() => go(2)}>View All Documents</button></div>
          <div className="readiness-doc-head"><span>Document</span><span>Status</span></div>
          {(ready?.documents || []).map((d,i) => <div className="readiness-doc-row" key={`${d.name}-${i}`}><span>▧ &nbsp;{d.name}</span><span className={`readiness-status ${String(d.status).toLowerCase().replaceAll(" ","_")}`}>{pretty(d.status)}</span></div>)}
          {!loading && !(ready?.documents || []).length && <p className="muted">No supporting documents uploaded.</p>}
          <button className="readiness-link" onClick={() => go(2)}>Go to Documents Center →</button>
        </section>

        <section className="journey-card readiness-panel readiness-score-panel">
          <h2>CAM Readiness Score</h2>
          <div className="readiness-donut" style={{"--ready": `${score * 3.6}deg`}}><div><strong>{score}%</strong><span>CAM Ready</span></div></div>
          <div className="readiness-legend"><span>● Completed <b>{ready?.completed_modules || 0}</b></span><span>● In Progress <b>{ready?.in_progress_modules || 0}</b></span><span>● Pending <b>{ready?.pending_modules || 0}</b></span></div>
          <div className="readiness-good">✓ {score}% of weighted CAM inputs are currently ready.</div>
        </section>
      </div>

      <div className="readiness-bottom-grid">
        <section className="journey-card readiness-panel">
          <div className="panel-title"><h2>Missing / Pending Items ({ready?.missing_items?.length || 0})</h2></div>
          <div className="pending-table"><div className="pending-head"><b>Item</b><b>Description</b><b>Priority</b><b>Mandatory?</b><b>Action</b></div>
          {(ready?.missing_items || []).map((x,i)=><div className="pending-row" key={i}><span>{x.item}</span><span>{x.description}</span><span className={`priority ${x.priority}`}>{pretty(x.priority)}</span><span>{x.mandatory ? "Yes" : "No"}</span><button onClick={() => go(x.action === "upload" ? 2 : 3)}>{pretty(x.action)}</button></div>)}</div>
          {!ready?.missing_items?.length && <div className="readiness-good">✓ No material pending items identified.</div>}
        </section>

        <section className="journey-card readiness-panel readiness-summary">
          <h2>Readiness Summary</h2>
          <p>Most critical CAM inputs are available. Review pending items for a more complete appraisal.</p>
          {(ready?.missing_items?.length || 0) > 0 && <div className="readiness-warning">! {high} high-priority and {(ready?.missing_items?.length || 0)-high} other recommended item(s) require attention. CAM can still be started.</div>}
          <button className="start-cam-btn" disabled={!ready?.can_start_cam || starting} onClick={begin}>{starting ? "Starting CAM..." : "Start CAM Preparation →"}</button>
          <small>Available evidence will be used. Missing optional inputs remain clearly flagged in the CAM.</small>
        </section>
      </div>
    </> : <section className="journey-card cam-preparing-card">
      <div className="cam-preparing-head"><div><h2>{analysis?.loan_summary_ready ? "Loan Summary Ready" : "Preparing CAM"}</h2><p>{analysis?.current_step || "Preparing verified CAM evidence..."}</p></div><strong>{Number(analysis?.progress || 0)}%</strong></div>
      <div className="cam-progress-track"><span style={{width:`${Number(analysis?.progress || 0)}%`}} /></div>
      <div className="cam-stage-list">{stageRows.map(([key,label]) => { const st=stages[key] || "pending"; return <div className={`cam-stage ${st}`} key={key}><span>{st === "completed" ? "✓" : st === "running" ? "●" : st === "failed" ? "!" : "○"}</span><strong>{label}</strong><small>{pretty(st)}</small></div>; })}</div>
      {analysis?.loan_summary_error && <div className="readiness-warning"><strong>Loan Summary AI generation failed.</strong><br/>{analysis.loan_summary_error}<br/><button className="secondary-btn" disabled={retrying} onClick={retryGroq}>{retrying ? "Retrying Groq..." : "Retry Groq"}</button></div>}
      {analysis?.loan_summary_ready && <div className="readiness-good">✓ Loan Summary is ready. Opening Step 5 while remaining CAM sections continue in the background...</div>}
      {!analysis?.loan_summary_ready && !analysis?.loan_summary_error && <p className="muted">Please wait on this screen until the Loan Summary data and Groq narrative are ready.</p>}
    </section>}
  </>;
}
