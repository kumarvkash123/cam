"use client";
import { useEffect, useState } from "react";
import { API_BASE as API } from "../api";

export default function Step16(ctx){
 const {sessionId,camInfo,companyName,generated,generateCam,analysisComplete,policyAnalysisComplete,apiRequest,setPolicyAnalysisComplete,go,PageHeader,DataTable,setError}=ctx;
 const [ready,setReady]=useState(null);
 useEffect(()=>{ if(!sessionId)return; apiRequest(`/api/cam/policy-readiness/${sessionId}`).then(r=>{setReady(r);setPolicyAnalysisComplete(Boolean(r.analysis_complete)); if(r.analysis_required) setError(r.message || "Policy has changed or policy analysis is stale. Re-run CAM vs Policy Analysis before generating CAM.");}).catch(e=>setError(e.message)); },[sessionId]);
 const camComplete=Boolean(ready?.cam_analysis_complete ?? analysisComplete);
 const policyCurrent=Boolean(ready?.analysis_complete ?? policyAnalysisComplete);
 const canGenerate=camComplete&&policyCurrent;
 return <>
  <PageHeader number={16} title="Generate CAM" subtitle="Generate the final CAM document only after analysis, policy validation and final review are complete." action={<button className="outline-btn" onClick={()=>go(15)}>← Final CAM Review</button>}/>
  <div className="generate-cam-layout"><section className="journey-card"><div className="panel-title"><h2>Generation Readiness</h2><span className={`status-chip ${canGenerate?"success":""}`}>{canGenerate?"READY":"BLOCKED"}</span></div><DataTable rows={[["Borrower",companyName],["CAM ID",camInfo?.cam_id||"—"],["CAM Analysis",camComplete?"Complete":"Pending"],["Policy Version",ready?.policy?.version||"—"],["Policy Freshness",ready?.analysis_complete?"Current":"Re-analysis required"],["Final Review","Completed"]]}/>{!canGenerate&&<div className="mapping-note">The active policy version must match the version used in the latest CAM vs Policy Analysis. <button className="text-link" onClick={()=>go(14)}>Go to Policy Analysis</button></div>}<button className="bob-btn full" onClick={generateCam} disabled={!canGenerate}>Generate Final CAM Document →</button></section><section className="journey-card"><h2>Generated Output</h2>{generated?<div className="download-panel"><strong>Final CAM generated successfully</strong><p>The generated document uses the current reviewed CAM and policy-analysis state.</p><div className="download-links"><a href={`${API}/api/cam/download/${sessionId}/docx`}>Download DOCX</a>{generated.pdf_available&&<a href={`${API}/api/cam/download/${sessionId}/pdf`}>Download PDF</a>}</div></div>:<div className="policy-empty">No final CAM generated yet.</div>}</section></div>
 </>;
}
