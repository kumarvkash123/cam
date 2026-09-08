"use client";
import { useEffect, useState } from "react";
import { BorrowerStrip } from "../financial-analysis/components";
import { Point10Kpis, IndustryOverview, PeerBenchmarkTable, MarketFactors, StrengthsRisks, IndustryDevelopments, IndustryCommentary, IndustrySources } from "../industry-peer/components";

export default function Step12(ctx) {
  const { sessionId, apiRequest, PageHeader, setJourneyStep, companyData, mcaData, camInfo, setStep10Subsection, setStep9Subsection } = ctx;
  const [data,setData]=useState(null);
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState("");

  async function load(refresh=false){
    if(!sessionId)return;
    setLoading(true); setError("");
    try{setData(await apiRequest(`/api/cam/industry-peer/${sessionId}${refresh?"?refresh=1":""}`));}
    catch(e){setError(e.message||"Unable to load Industry & Peer Analysis");}
    finally{setLoading(false);}
  }
  useEffect(()=>{load(false)},[sessionId]);

  function goToFinalMitigation(){
    if(setStep9Subsection) setStep9Subsection("mitigation");
    setJourneyStep(9);
  }

  return <div className="ip19-page">
    <PageHeader number="10" title="Industry, Market & Peer Analysis" subtitle="CAM Point 10: place the borrower in sector context using available industry trends, market conditions and peer benchmarks." action={<button className="outline-btn" onClick={()=>load(true)}>↻ Refresh Data</button>} />
    {loading&&<section className="journey-card ip19-loading">Building Point 10 from Business Overview, Financial Analysis and configured market/public evidence…</section>}
    {error&&<section className="journey-card ip19-error"><strong>Unable to load Industry & Peer Analysis.</strong><span>{error}</span><button className="outline-btn" onClick={()=>load(true)}>Retry</button></section>}
    {data&&<>
      <BorrowerStrip data={data} companyData={companyData} mcaData={mcaData} camInfo={camInfo}/>
      <div className="ip19-title"><span>10</span><div><h2>Peer Benchmarking & Market / Industry Overview</h2><p>Computed after Point 7 and before final risk refresh / Point 8 loan structuring.</p></div><b>ANALYTICAL PICTURE COMPLETE</b></div>
      <Point10Kpis data={data}/>
      <div className="ip19-main"><IndustryOverview data={data}/><PeerBenchmarkTable rows={data.peer_comparison}/></div>
      <div className="ip19-main lower"><MarketFactors rows={data.market_factors}/><IndustryDevelopments rows={data.industry_developments}/></div>
      <StrengthsRisks strengths={data.strengths} risks={data.risks}/>
      <IndustryCommentary data={data}/>
      <IndustrySources data={data}/>
      <div className="ip19-flow-note"><strong>Processing order:</strong> 1 → 2 → 3 → 4 → 5 → 6A → 7 → <b>10</b> → 6B final risk → 8 loan terms → 9 final compliance.</div>
      <div className="ip19-footer"><button className="outline-btn" onClick={()=>{if(setStep10Subsection)setStep10Subsection("collateral");setJourneyStep(10)}}>← Previous: Collateral Details</button><button className="bob-btn" onClick={goToFinalMitigation}>Next: 6B Risk Mitigation →</button></div>
    </>}
  </div>;
}
