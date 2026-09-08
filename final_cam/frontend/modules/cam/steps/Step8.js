"use client";
import { useEffect, useState } from "react";
import { BorrowerStrip, KpiRow, RatioTable, TrendChart, MovementTable, StressTable, Commentary, Sources } from "../financial-analysis/components";

export default function Step8(ctx) {
  const { sessionId, apiRequest, PageHeader, companyData, mcaData, camInfo, setJourneyStep } = ctx;
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load(refresh=false) {
    if (!sessionId) return;
    setLoading(true); setError("");
    try {
      const payload = await apiRequest(`/api/cam/financial-analysis/${sessionId}${refresh ? "?refresh=1" : ""}`);
      setData(payload);
    } catch (e) { setError(e.message || "Unable to load financial analysis"); }
    finally { setLoading(false); }
  }

  useEffect(()=>{ load(false); }, [sessionId]);

  return <div className="fa14-page">
    <PageHeader number={8} title="Financial Analysis & Stress Testing" subtitle="Point 4 of the CAM: financial performance, ratios, material movements and repayment-capacity stress testing." action={<button className="outline-btn" onClick={()=>load(true)}>↻ Refresh Analysis</button>} />
    {loading && <section className="journey-card fa14-loading">Calculating ratios, trends and stress scenarios from extracted financial evidence…</section>}
    {error && <section className="journey-card fa14-error"><strong>Unable to load Financial Analysis.</strong><span>{error}</span><button className="outline-btn" onClick={()=>load(true)}>Retry</button></section>}
    {data && <>
      <BorrowerStrip data={data} companyData={companyData} mcaData={mcaData} camInfo={camInfo}/>
      <div className="fa14-section-title"><div><span>4</span><div><h2>Financial Analysis & Stress Testing</h2><p>Calculated from the borrower&apos;s available financial statements and supporting evidence.</p></div></div><div className="fa14-year">{data.latest_year}</div></div>
      <KpiRow items={data.kpis}/>
      <div className="fa14-grid top"><RatioTable rows={data.ratios}/><TrendChart series={data.trends}/></div>
      <div className="fa14-grid bottom"><MovementTable rows={data.material_movements}/><StressTable rows={data.stress_testing}/></div>
      <Commentary commentary={data.commentary}/>
      <Sources items={data.sources}/>
      <div className="fa14-method">ⓘ {data.methodology}</div>
      <div className="fa14-footer"><button className="outline-btn" onClick={()=>setJourneyStep(7)}>← Previous: Business Overview</button><button className="bob-btn" onClick={()=>setJourneyStep(9)}>Next: Credit History & Risk →</button></div>
    </>}
  </div>;
}
