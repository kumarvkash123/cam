"use client";
import { useState } from "react";
import { humanize, formatValue } from "../../shared/ui";

function ReportStep({index,step,report}) {
  const [open,setOpen]=useState(false);
  return <div className={`step-card ${step.status==="completed"?"step-complete":""}`}>
    <div className="step-main"><span className={`step-check ${step.status==="completed"?"done":""}`}>{step.status==="completed"?"✓":index+1}</span>
      <div><strong>{step.label}</strong><small>{humanize(step.status)}</small></div>
    </div>
    {step.status==="completed"&&report&&<><button className="report-toggle" onClick={()=>setOpen(!open)}>{open?"Hide Report":"View Report"}</button>{open&&<div className="report-body"><div className="report-summary">{report.summary||""}</div>{(report.sections||[]).map((s,i)=><div className="report-section" key={i}><div className="report-section-title">{s.title||"Data"}</div>{(s.rows||[]).map((row,j)=><div className="report-row" key={j}><span>{row.label||""}</span><strong>{formatValue(row.value)}</strong></div>)}{s.bullets?.length>0&&<ul className="report-bullets">{s.bullets.map((b,j)=><li key={j}>{b}</li>)}</ul>}</div>)}</div>}</>}
  </div>;
}



export default ReportStep;