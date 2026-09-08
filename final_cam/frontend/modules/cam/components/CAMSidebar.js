"use client";

import { useEffect, useState } from "react";
import { BOBMark, Icon } from "../../../shared/ui";
import { CAM_ANALYSIS_FLOW, analysisFlowItemForState } from "../config/camWorkflow";

export default function CAMSidebar({journeyStep,step9Subsection,step10Subsection,journeyCollapsed,setJourneyCollapsed,setJourneyStep,setStep9Subsection,setStep10Subsection}) {
  const isAnalysisPage = journeyStep >= 5 && journeyStep <= 12;
  const [analysisOpen,setAnalysisOpen]=useState(isAnalysisPage || journeyStep===4);
  useEffect(()=>{ if(isAnalysisPage) setAnalysisOpen(true); },[isAnalysisPage]);
  const activeAnalysis=analysisFlowItemForState({journeyStep,step9Subsection,step10Subsection});
  function go(item){ if(item.step9Subsection)setStep9Subsection(item.step9Subsection); if(item.step10Subsection)setStep10Subsection(item.step10Subsection); setJourneyStep(item.step); }
  const topItems=[
    {key:"borrower",label:"Borrower Search",icon:"users",step:1},
    {key:"documents",label:"Documents Center",icon:"file",step:2},
    {key:"review",label:"Document Review",icon:"file",step:3},
  ];
  const lowerItems=[
    {step:13,label:"Policy Documents",icon:"file"},
    {step:14,label:"CAM vs Policy Analysis",icon:"chart"},
    {step:15,label:"Final CAM Review",icon:"shield"},
    {step:16,label:"Generate CAM",icon:"file"},
  ];
  return <aside className={`process-sidebar cam-nav-sidebar ${journeyCollapsed?"collapsed":""}`} aria-label="CAM navigation">
    <div className="process-brand"><BOBMark small/><div><strong>Bank of Baroda</strong><span>CAM AI Platform</span></div><button className="process-collapse" onClick={()=>setJourneyCollapsed(!journeyCollapsed)}><Icon name="menu"/></button></div>
    <nav className="cam-nav-scroll">
      {topItems.map(item=><button key={item.key} className={`cam-nav-top ${journeyStep===item.step?"active":""}`} onClick={()=>setJourneyStep(item.step)} title={journeyCollapsed?item.label:""}><Icon name={item.icon}/><span>{item.label}</span></button>)}
      <button className={`cam-nav-top cam-analysis-toggle ${journeyStep===4||isAnalysisPage?"section-active":""}`} onClick={()=>{if(journeyCollapsed){setJourneyCollapsed(false);setAnalysisOpen(true);return;}setAnalysisOpen(v=>!v);if(journeyStep<4)setJourneyStep(4);}} aria-expanded={analysisOpen}><Icon name="chart"/><span>CAM Analysis</span>{!journeyCollapsed&&<b className="cam-analysis-chevron">{analysisOpen?"⌃":"⌄"}</b>}</button>
      {!journeyCollapsed&&analysisOpen&&<div className="cam-analysis-submenu">{CAM_ANALYSIS_FLOW.map(item=>{const active=activeAnalysis?.id===item.id;return <button key={item.id} className={`cam-analysis-item ${active?"active":""}`} onClick={()=>go(item)}><span className="cam-section-badge">{item.section}</span><span className="cam-section-label">{item.label}</span></button>})}</div>}
      <div className="cam-nav-divider"/>
      {lowerItems.map(item=><button key={item.step} className={`cam-nav-top ${journeyStep===item.step?"active":""}`} onClick={()=>setJourneyStep(item.step)} title={journeyCollapsed?item.label:""}><Icon name={item.icon}/><span>{item.label}</span></button>)}
      <div className="cam-nav-divider"/>
      <button className="cam-nav-top" onClick={()=>window.dispatchEvent(new CustomEvent("bob-dashboard"))}><Icon name="file"/><span>Reports</span></button>
      <button className="cam-nav-top" onClick={()=>window.dispatchEvent(new CustomEvent("bob-dashboard"))}><Icon name="settings"/><span>Settings</span></button>
    </nav>
    <div className="process-user"><div className="avatar">CO</div><div><strong>Credit Officer</strong><small>CAM Workspace</small></div></div>
  </aside>;
}
