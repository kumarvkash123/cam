"use client";
import { useEffect, useState } from "react";
import {
  BusinessModelCard, ListCard, FootprintCard, RevenueProfile, MarketPosition,
  StrengthRiskCard, RecentDevelopments, AIOverview, SourcesStrip, BusinessCopilotDrawer,
} from "../business-overview/components";

export default function Step7(ctx) {
  const { sessionId, apiRequest, PageHeader, setJourneyStep, sendCamChat, chat, message, setMessage, assistantBusy } = ctx;
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [copilotOpen, setCopilotOpen] = useState(false);

  async function load(refresh = false) {
    if (!sessionId) return;
    setLoading(true); setError("");
    try {
      const d = await apiRequest(`/api/cam/business-overview/${sessionId}${refresh ? "?refresh=1" : ""}`);
      setData(d);
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }
  useEffect(() => { load(false); }, [sessionId]);

  return <div className="bov13-page">
    <PageHeader number={7} title="Business Overview" subtitle="Source-grounded view of the borrower’s business model, products, customers, operations, revenue profile and market context." action={<div className="bov13-actions"><button className="outline-btn" onClick={()=>load(true)}>↻ Refresh Overview</button><button className="outline-btn" onClick={()=>setCopilotOpen(true)}>✦ Ask Copilot</button></div>} />

    {loading && <section className="journey-card bov13-loading">Preparing Business Overview from borrower data, documents, financial evidence and public information…</section>}
    {error && <section className="journey-card bov13-error">Unable to load Business Overview: {error} <button className="outline-btn" onClick={()=>load(true)}>Retry</button></section>}
    {data && <>
      <section className="bov13-hero"><div><span>BUSINESS OVERVIEW</span><h2>{data.company_name || "Borrower"}</h2><p>{data.business_model?.industry || "Industry not available"}</p></div><div className="bov13-hero-badge">Source Grounded</div></section>
      <div className="bov13-grid two"><BusinessModelCard data={data.business_model}/><ListCard title="Key Products / Services" subtitle="Documents / disclosures" items={data.products_services || []}/></div>
      <div className="bov13-grid two"><ListCard title="Customer Profile" subtitle="Segments / concentration" items={data.customer_profile?.segments || []} getText={x=>x.segment || x.name}/><FootprintCard data={data.operating_footprint}/></div>
      <RevenueProfile data={data.revenue_profile}/>
      <div className="bov13-grid two"><MarketPosition data={data.market_position}/><StrengthRiskCard strengths={data.strengths || []} risks={data.business_risks || []}/></div>
      <div className="bov13-grid two"><RecentDevelopments items={data.recent_developments || []} industryItems={data.industry_observations || []}/><AIOverview data={data} onAsk={()=>setCopilotOpen(true)}/></div>
      <SourcesStrip sources={data.sources || []}/>
      <div className="bov13-footer"><button className="outline-btn" onClick={()=>setJourneyStep(6)}>← Back to Borrower Information</button><small>{data.data_note}</small><button className="bob-btn" onClick={()=>setJourneyStep(8)}>Proceed to Financial Analysis →</button></div>
    </>}
    <BusinessCopilotDrawer open={copilotOpen} onClose={()=>setCopilotOpen(false)} chat={chat} message={message} setMessage={setMessage} sendCamChat={sendCamChat} busy={assistantBusy}/>
  </div>;
}
