"use client";
import { useEffect, useState } from "react";

export default function Step15(ctx) {
  const { sessionId, camInfo, policyIndexed, policyAnalysisComplete, setPolicyAnalysisComplete, analysisComplete, companyName, docsProcessed, camSections, camSectionStepMap, go, PageHeader, DataTable, apiRequest, setError } = ctx;
  const [readiness,setReadiness]=useState(null);
  useEffect(()=>{
    if(!sessionId) return;
    apiRequest(`/api/cam/policy-readiness/${sessionId}`).then(r=>{setReadiness(r);setPolicyAnalysisComplete(Boolean(r.analysis_complete));}).catch(e=>setError(e.message));
  },[sessionId]);
  const camComplete=Boolean(readiness?.cam_analysis_complete ?? analysisComplete);
  const policyCurrent=Boolean(readiness?.analysis_complete ?? policyAnalysisComplete);
  const finalCamReady = camComplete && policyCurrent;
  const completion = camComplete ? 100 : 0;
  return <>
    <PageHeader number={15} title="Final CAM Review" subtitle="Review all CAM sections and confirm that the current active policy has been analyzed before moving to final CAM generation." action={<button className="outline-btn" onClick={()=>go(14)}>View Policy Analysis</button>}/>
    <div className="final-progress"><div className="final-progress-line"/>{camSections.map((title,i)=><div className={`final-node ${camComplete?"done":""}`} key={title}><span>{camComplete?"✓":i+1}</span><small>{i+1}</small></div>)}</div>
    <div className="two-pane">
      <section className="journey-card"><div className="panel-title"><h2>CAM Section Review</h2><span>{completion}% complete</span></div>{camSections.map((title,i)=><div className="review-row" key={title}><span className={camComplete?"review-ok":"review-pending"}>{camComplete?"✓":"!"}</span><div><strong>{title}</strong><small>{camComplete?"Analysis available for reviewer confirmation":"Analysis pending"}</small></div><button onClick={()=>go(camSectionStepMap[i])}>Review</button></div>)}</section>
      <section className="journey-card"><div className="panel-title"><h2>Final CAM Readiness</h2><span className={`status-chip ${finalCamReady?"success":""}`}>{finalCamReady?"READY":"PENDING"}</span></div><DataTable rows={[["Borrower",companyName],["CAM ID",camInfo?.cam_id||"—"],["CAM Analysis",camComplete?"Completed":"Pending"],["Policy Repository",policyIndexed?"Active":"Pending"],["CAM vs Policy Analysis",policyCurrent?"Completed / Current":"Pending / Stale"],["Document Evidence",docsProcessed?`${docsProcessed} processed`:"Pending"]]}/>{!finalCamReady&&<div className="mapping-note">{readiness?.message || "Complete CAM analysis and run CAM vs Policy Analysis against the current policy version before generation."}</div>}<button className="bob-btn full" disabled={!finalCamReady} onClick={()=>go(16)}>Continue to Generate CAM →</button></section>
    </div>
  </>;
}
