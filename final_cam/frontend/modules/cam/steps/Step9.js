"use client";
import { useEffect, useState } from "react";
import { CreditKpis, Facilities, Repayment, BankingConduct, BureauSummary, Utilisation, RiskFlags, CreditCommentary, CreditSources } from "../credit-history/components";
import { OverallRisk, CategorySummary, RiskMatrix, RiskAssessmentRegister, Thresholds, PositiveFactors, Concerns, RiskCommentary, RiskSources, MitigationPlan } from "../risk-assessment/components";
import { BorrowerStrip } from "../financial-analysis/components";

export default function Step9(ctx) {
  const {
    sessionId, apiRequest, PageHeader, setJourneyStep,
    companyData, mcaData, camInfo,
    step9Subsection, setStep9Subsection,
    setStep10Subsection,
  } = ctx;

  const subsection = step9Subsection || "credit";
  const setSubsection = (value) => setStep9Subsection ? setStep9Subsection(value) : null;
  const [data,setData]=useState(null); const [loading,setLoading]=useState(true); const [error,setError]=useState("");
  const [risk,setRisk]=useState(null); const [riskLoading,setRiskLoading]=useState(false); const [riskError,setRiskError]=useState("");

  async function load(refresh=false){
    if(!sessionId) return; setLoading(true); setError("");
    try{setData(await apiRequest(`/api/cam/credit-history/${sessionId}${refresh?"?refresh=1":""}`));}
    catch(e){setError(e.message||"Unable to load credit history");}
    finally{setLoading(false);}
  }
  async function loadRisk(refresh=false){
    if(!sessionId) return; setRiskLoading(true); setRiskError("");
    try{setRisk(await apiRequest(`/api/cam/risk-assessment/${sessionId}${refresh?"?refresh=1":""}`));}
    catch(e){setRiskError(e.message||"Unable to load risk assessment");}
    finally{setRiskLoading(false);}
  }

  useEffect(()=>{ if(!data) load(false); },[sessionId]);
  useEffect(()=>{
    if((subsection==="risk" || subsection==="mitigation") && !riskLoading){
      // 6B is deliberately refreshed after Point 10 so collateral and industry/peer
      // evidence are included in the final mitigation view.
      loadRisk(subsection === "mitigation");
    }
  },[subsection,sessionId]);

  if(subsection==="risk") return <div className="ra16-page">
    <PageHeader number="6A" title="Risk Assessment" subtitle="CAM Point 6A: identify and evaluate key risks before collateral and peer/market evidence is folded into the final mitigation view." action={<button className="outline-btn" onClick={()=>loadRisk(true)}>↻ Refresh Risk</button>} />
    {riskLoading&&<section className="journey-card ra16-loading">Consolidating financial, repayment, business and policy risk evidence…</section>}
    {riskError&&<section className="journey-card ra16-error"><strong>Unable to load Risk Assessment.</strong><span>{riskError}</span><button className="outline-btn" onClick={()=>loadRisk(true)}>Retry</button></section>}
    {risk&&<>
      <BorrowerStrip data={risk} companyData={companyData} mcaData={mcaData} camInfo={camInfo}/>
      <div className="ra16-title"><span>6A</span><div><h2>Risk Assessment</h2><p>Risk identification and threshold assessment before Point 7 and Point 10 complete the analytical picture.</p></div><label>Assessment phase</label></div>
      <div className="ra16-top"><OverallRisk data={risk}/><CategorySummary rows={risk.categories}/><RiskMatrix risks={risk.risks}/></div>
      <div className="ra16-main"><RiskAssessmentRegister rows={risk.risks}/><Thresholds rows={risk.policy_triggers}/></div>
      <div className="ra16-bottom"><PositiveFactors items={risk.positive_factors}/><Concerns items={risk.key_concerns}/><RiskCommentary data={risk.commentary}/></div>
      <RiskSources items={risk.sources} methodology={risk.methodology} notice={risk.decision_notice}/>
      <div className="ra16-flow-note"><strong>Next analytical sequence:</strong> 7 Collateral Details → 10 Peer Benchmarking → 6B Risk Mitigation.</div>
      <div className="ra16-footer"><button className="outline-btn" onClick={()=>setSubsection("credit")}>← Previous: Credit History & Repayment</button><button className="bob-btn" onClick={()=>{if(setStep10Subsection)setStep10Subsection("collateral");setJourneyStep(10)}}>Next: Collateral Details →</button></div>
    </>}
  </div>;

  if(subsection==="mitigation") return <div className="ra16-page ra16-mitigation-page">
    <PageHeader number="6B" title="Risk Mitigation" subtitle="CAM Point 6B: refresh the risk view after collateral and peer/market analysis, then define controlled mitigating factors before proposing loan terms." action={<button className="outline-btn" onClick={()=>loadRisk(true)}>↻ Refresh Final Risk</button>} />
    {riskLoading&&<section className="journey-card ra16-loading">Refreshing final risk and mitigants using Points 7 and 10…</section>}
    {riskError&&<section className="journey-card ra16-error"><strong>Unable to load Risk Mitigation.</strong><span>{riskError}</span><button className="outline-btn" onClick={()=>loadRisk(true)}>Retry</button></section>}
    {risk&&<>
      <BorrowerStrip data={risk} companyData={companyData} mcaData={mcaData} camInfo={camInfo}/>
      <div className="ra16-title"><span>6B</span><div><h2>Risk Mitigation</h2><p>Final mitigation plan after collateral strength and Point 10 industry/peer context are incorporated.</p></div><label>Post-analysis refresh</label></div>
      <div className="ra16-top"><OverallRisk data={risk}/><CategorySummary rows={risk.categories}/><PositiveFactors items={risk.positive_factors}/></div>
      <MitigationPlan rows={risk.risks}/>
      <div className="ra16-bottom"><Concerns items={risk.key_concerns}/><Thresholds rows={risk.policy_triggers}/><RiskCommentary data={risk.commentary}/></div>
      <RiskSources items={risk.sources} methodology={risk.methodology} notice={risk.decision_notice}/>
      <div className="ra16-flow-note"><strong>Analytical picture complete:</strong> 1 → 2 → 3 → 4 → 5 → 6A → 7 → 10 → 6B. Point 8 can now propose terms from this completed analysis.</div>
      <div className="ra16-footer"><button className="outline-btn" onClick={()=>setJourneyStep(12)}>← Previous: Peer Benchmarking</button><button className="bob-btn" onClick={()=>{if(setStep10Subsection)setStep10Subsection("terms");setJourneyStep(10)}}>Next: Loan Terms & Conditions →</button></div>
    </>}
  </div>;

  return <div className="ch15-page">
    <PageHeader number="5" title="Credit History & Repayment Track Record" subtitle="CAM Point 5: analyse the borrower’s credit conduct, repayment behaviour and banking relationship." action={<button className="outline-btn" onClick={()=>load(true)}>↻ Refresh Data</button>} />
    {loading&&<section className="journey-card ch15-loading">Building credit history from bureau, banking and uploaded document evidence…</section>}
    {error&&<section className="journey-card ch15-error"><strong>Unable to load Credit History.</strong><span>{error}</span><button className="outline-btn" onClick={()=>load(true)}>Retry</button></section>}
    {data&&<>
      <div className="ch15-title"><span>5</span><div><h2>Credit History & Repayment Track Record</h2><p>Source-backed credit conduct, repayment behaviour, facility utilisation and banking observations.</p></div><label>Last 24 Months</label></div>
      <CreditKpis data={data}/>
      <div className="ch15-grid ch15-main"><Facilities rows={data.facilities}/><Repayment data={data.repayment}/></div>
      <div className="ch15-grid"><BankingConduct data={data.banking_conduct}/><BureauSummary rows={data.bureau_summary}/></div>
      <div className="ch15-grid"><Utilisation data={data.utilisation}/><RiskFlags rows={data.risk_flags}/></div>
      <CreditCommentary data={data.commentary}/>
      <CreditSources items={data.sources} methodology={data.methodology}/>
      <div className="ch15-footer"><button className="outline-btn" onClick={()=>setJourneyStep(8)}>← Previous: Financial Analysis</button><button className="bob-btn" onClick={()=>setSubsection("risk")}>Next: 6A Risk Assessment →</button></div>
    </>}
  </div>;
}
