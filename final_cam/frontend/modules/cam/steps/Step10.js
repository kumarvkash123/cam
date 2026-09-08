"use client";
import { useEffect, useMemo, useState } from "react";
import { BorrowerStrip } from "../financial-analysis/components";
import { CollateralKpis, SecurityTable, CoveragePanel, ValuationTable, ValidationChecks, DocumentChecklist, Observations, CollateralCommentary, CollateralSources } from "../collateral/components";
import { TermsKpis, FacilityStructure, ComparisonTable, PricingDetails, RepaymentStructure, SecurityTerms, Covenants, Conditions, Deviations, TermsCommentary, TermsEditor } from "../loan-terms/components";

export default function Step10(ctx) {
  const {sessionId,apiRequest,PageHeader,setJourneyStep,companyData,mcaData,camInfo,step10Subsection,setStep10Subsection}=ctx;
  const [subsection,setSubsectionLocal]=useState(step10Subsection||"collateral");
  const setSubsection=(value)=>{setSubsectionLocal(value); if(setStep10Subsection)setStep10Subsection(value);};
  const [data,setData]=useState(null); const [loading,setLoading]=useState(true); const [error,setError]=useState("");
  const [terms,setTerms]=useState(null); const [termsLoading,setTermsLoading]=useState(false); const [termsError,setTermsError]=useState("");
  const [editing,setEditing]=useState(false); const [saving,setSaving]=useState(false); const [draft,setDraft]=useState({});

  async function loadCollateral(refresh=false){
    if(!sessionId)return; setLoading(true);setError("");
    try{setData(await apiRequest(`/api/cam/collateral/${sessionId}${refresh?"?refresh=1":""}`));}
    catch(e){setError(e.message||"Unable to load collateral analysis");}
    finally{setLoading(false);}
  }
  async function loadTerms(refresh=false){
    if(!sessionId)return; setTermsLoading(true);setTermsError("");
    try{const x=await apiRequest(`/api/cam/loan-terms/${sessionId}${refresh?"?refresh=1":""}`);setTerms(x);}
    catch(e){setTermsError(e.message||"Unable to load loan terms");}
    finally{setTermsLoading(false);}
  }
  useEffect(()=>{loadCollateral(false)},[sessionId]);
  useEffect(()=>{if(step10Subsection && step10Subsection!==subsection)setSubsectionLocal(step10Subsection)},[step10Subsection]);
  useEffect(()=>{if(subsection==="terms"&&!terms)loadTerms(false)},[subsection,sessionId]);

  const initialDraft=useMemo(()=>terms?{
    facility_type:terms.facility?.facility_type||"",
    proposed_amount_cr:terms.facility?.proposed_amount_cr??"",
    tenor_months:terms.repayment?.tenor_months??"",
    moratorium_months:terms.repayment?.moratorium_months??"",
    interest_rate:terms.pricing?.indicative_rate??"",
    repayment:terms.repayment?.type||"",
  }: {},[terms]);
  function startEdit(){setDraft(initialDraft);setEditing(true)}
  function change(k,v){setDraft(d=>({...d,[k]:v}))}
  async function saveTerms(){
    setSaving(true);setTermsError("");
    try{
      const body={...draft};
      ["proposed_amount_cr","tenor_months","moratorium_months","interest_rate"].forEach(k=>{if(body[k]!==""&&body[k]!=null)body[k]=Number(body[k]);});
      const x=await apiRequest(`/api/cam/loan-terms/${sessionId}`,{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
      setTerms(x);setEditing(false);
    }catch(e){setTermsError(e.message||"Unable to save loan terms");}
    finally{setSaving(false);}
  }

  if(subsection==="terms") return <div className="lt18-page">
    <PageHeader number="8" title="Loan Terms & Conditions" subtitle="CAM Point 8: propose facility structure, pricing, repayment, security, covenants and conditions based on analysis and policy." action={<div className="lt18-actions"><button className="outline-btn" onClick={()=>loadTerms(true)}>↻ Refresh Data</button><button className="bob-btn" onClick={startEdit}>✎ Edit / Update</button></div>} />
    {termsLoading&&<section className="journey-card lt18-loading">Building Loan Terms & Conditions from proposal, financial, risk and collateral outputs…</section>}
    {termsError&&<section className="journey-card lt18-error"><strong>Unable to load Loan Terms & Conditions.</strong><span>{termsError}</span><button className="outline-btn" onClick={()=>loadTerms(true)}>Retry</button></section>}
    {terms&&<>
      <BorrowerStrip data={terms} companyData={companyData} mcaData={mcaData} camInfo={camInfo}/>
      <div className="lt18-title"><span>8</span><div><h2>Loan Terms & Conditions</h2><p>Proposed facility structure, pricing, repayment, security, covenants and conditions.</p></div></div>
      {editing&&<TermsEditor draft={draft} onChange={change} onSave={saveTerms} onCancel={()=>setEditing(false)} saving={saving}/>}      
      <TermsKpis data={terms}/>
      <div className="lt18-grid top"><FacilityStructure data={terms}/><ComparisonTable rows={terms.comparison}/><PricingDetails data={terms.pricing}/></div>
      <div className="lt18-grid middle"><RepaymentStructure data={terms.repayment}/><SecurityTerms data={terms.security}/><Covenants rows={terms.covenants}/></div>
      <div className="lt18-grid bottom"><Conditions title="Pre-Disbursement Conditions" items={terms.pre_disbursement_conditions}/><Conditions title="Post-Disbursement Conditions" items={terms.post_disbursement_conditions}/><Deviations rows={terms.deviations}/></div>
      <TermsCommentary data={terms.commentary}/>
      <div className="lt18-policy-note"><strong>Policy basis:</strong> {terms.policy_basis}<br/><span>{terms.decision_notice}</span></div>
      <div className="lt18-footer"><button className="outline-btn" onClick={()=>{if(ctx.setStep9Subsection)ctx.setStep9Subsection("mitigation");setJourneyStep(9)}}>← Previous: 6B Risk Mitigation</button><button className="bob-btn" onClick={()=>setJourneyStep(11)}>Next: 9 Regulatory & Compliance →</button></div>
    </>}
  </div>;

  return <div className="col17-page">
    <PageHeader number="7" title="Collateral Details" subtitle="CAM Point 7: review security, valuation, ownership, charge status, document completeness and coverage." action={<button className="outline-btn" onClick={()=>loadCollateral(true)}>↻ Refresh Data</button>} />
    {loading&&<section className="journey-card col17-loading">Building collateral analysis from proposal, valuation, title/legal, insurance and MCA evidence…</section>}
    {error&&<section className="journey-card col17-error"><strong>Unable to load Collateral Details.</strong><span>{error}</span><button className="outline-btn" onClick={()=>loadCollateral(true)}>Retry</button></section>}
    {data&&<>
      <BorrowerStrip data={data} companyData={companyData} mcaData={mcaData} camInfo={camInfo}/>
      <div className="col17-title"><span>7</span><div><h2>Collateral Details <small>(if applicable)</small></h2><p>Source-backed security, valuation, ownership, charge and coverage assessment.</p></div></div>
      <CollateralKpis data={data}/>
      <div className="col17-main"><SecurityTable rows={data.securities}/><CoveragePanel data={data.coverage}/></div>
      <div className="col17-main"><ValuationTable rows={data.valuations}/><ValidationChecks rows={data.validation_checks}/></div>
      <div className="col17-bottom"><DocumentChecklist rows={data.document_checks}/><Observations rows={data.observations}/><CollateralCommentary data={data.commentary}/></div>
      <CollateralSources items={data.sources} methodology={data.methodology} notice={data.decision_notice}/>
      <div className="col17-footer"><button className="outline-btn" onClick={()=>setJourneyStep(9)}>← Previous: 6A Risk Assessment</button><button className="bob-btn" onClick={()=>setJourneyStep(12)}>Next: Point 10 Industry & Peer Analysis →</button></div>
    </>}
  </div>;
}
