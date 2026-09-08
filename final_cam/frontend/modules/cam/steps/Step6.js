"use client";
import { useEffect, useMemo, useState } from "react";
import {
  BorrowerHeader,
  FieldRow,
  VerificationSummary,
  SourceInformation,
  PeopleCard,
  ConflictsCard,
  BorrowerOverview,
  CopilotDrawer,
} from "../borrower-information/components";

function money(value) {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "string" && /₹|cr|lakh/i.test(value)) return value;
  const n = Number(value);
  if (!Number.isFinite(n)) return String(value);
  if (Math.abs(n) < 1000) return `₹ ${n.toFixed(2)} Cr`;
  return `₹ ${n.toLocaleString("en-IN")}`;
}

export default function Step6(ctx) {
  const { sessionId, apiRequest, PageHeader, FooterNav, sendCamChat, chat, message, setMessage, assistantBusy, setJourneyStep } = ctx;
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [copilotOpen, setCopilotOpen] = useState(false);

  async function load(refresh = false) {
    if (!sessionId) return;
    setLoading(true); setError("");
    try {
      const d = await apiRequest(`/api/cam/borrower-information/${sessionId}${refresh ? "?refresh=1" : ""}`);
      setData(d);
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }

  useEffect(() => { load(false); }, [sessionId]);

  const c = data?.corporate_profile || {};
  const r = data?.registration || {};
  const bank = data?.bank_relationship || {};
  const publicInfo = data?.public_information || {};
  const latestNews = publicInfo.recent_developments?.[0];
  const rating = publicInfo.credit_rating || {};

  const corporateRows = useMemo(() => [
    ["Company Name", c.company_name], ["CIN", c.cin], ["Constitution", c.constitution], ["Company Status", c.company_status],
    ["Incorporation Date", c.incorporation_date], ["Business Vintage", c.business_vintage_years, v => `${v} Years`],
    ["Registered Office", c.registered_office], ["Authorized Capital", c.authorized_capital, money], ["Paid-up Capital", c.paid_up_capital, money],
    ["Industry / Line of Business", c.industry],
  ], [data]);

  return (
    <div className="biv12-page">
      <PageHeader number={6} title="Borrower Information" subtitle="Comprehensive borrower profile compiled from internal systems, uploaded documents, official/external sources and public information." action={<div className="biv12-header-actions"><button className="outline-btn" onClick={() => load(true)}>↻ Refresh Profile</button><button className="outline-btn" onClick={() => setCopilotOpen(true)}>✦ Ask Copilot</button></div>} />

      {loading && <section className="journey-card biv12-loading">Preparing borrower information and verifying sources…</section>}
      {error && <section className="journey-card biv12-alert warn">Unable to load Borrower Information: {error} <button className="outline-btn" onClick={() => load(true)}>Retry</button></section>}
      {data && <>
        <BorrowerHeader data={data} />
        <div className="biv12-tabs"><span className="active">Overview</span><span>Corporate Profile</span><span>Promoters & Management</span><span>Business & Operations</span><span>Financial & Banking</span><span>Public Information</span><span>Documents & Sources</span></div>
        <ConflictsCard conflicts={data.source_conflicts || []} />
        <div className="biv12-top-grid">
          <section className="journey-card biv12-card">
            <div className="biv12-title"><h2>Corporate Profile</h2><span>Source traceable</span></div>
            <div className="biv12-field-table">{corporateRows.map(([label, item, formatter]) => <FieldRow key={label} label={label} item={item} formatter={formatter} />)}</div>
          </section>
          <div className="biv12-stack"><SourceInformation sources={data.sources || []} />
            <section className="journey-card biv12-card"><div className="biv12-title"><h2>Registration & KYC</h2></div><div className="biv12-field-table"><FieldRow label="PAN" item={r.pan}/><FieldRow label="GSTIN" item={r.gstin}/><FieldRow label="GST Status" item={r.gst_status}/><FieldRow label="Udyam" item={r.udyam}/><FieldRow label="Udyam Status" item={r.udyam_status}/></div></section>
          </div>
          <div className="biv12-stack"><VerificationSummary summary={data.verification_summary}/><PeopleCard people={data.promoters_directors || []}/></div>
        </div>
        <div className="biv12-bottom-grid">
          <section className="journey-card biv12-card"><div className="biv12-title"><h2>Bank Relationship</h2><span>Internal / POC provider</span></div><div className="biv12-field-table"><FieldRow label="Existing Customer" item={bank.existing_customer} formatter={v => v ? "Yes" : "No"}/><FieldRow label="Relationship Since" item={bank.relationship_since}/><FieldRow label="Relationship Manager" item={bank.relationship_manager}/><FieldRow label="Account Conduct" item={bank.account_conduct}/><FieldRow label="Avg. Utilisation" item={bank.average_utilisation_pct} formatter={v => `${v}%`}/></div></section>
          <section className="journey-card biv12-card"><div className="biv12-title"><h2>Public Information</h2><span>{publicInfo.mode || "off"}</span></div><div className="biv12-public"><div><b>Credit Rating</b><span>{rating.rating || rating.current_rating || "Not available"}</span></div><div><b>Recent Development</b><span>{latestNews?.title || latestNews?.summary || "No material development available"}</span></div><div><b>Industry Observations</b><span>{publicInfo.industry_observations?.[0]?.title || publicInfo.industry_observations?.[0]?.summary || "Not available"}</span></div><div><b>Adverse News</b><span>{publicInfo.adverse_news?.length ? (publicInfo.adverse_news[0].title || publicInfo.adverse_news[0].summary) : "No material adverse item in current feed"}</span></div></div></section>
          <BorrowerOverview data={data} onAsk={() => setCopilotOpen(true)} />
        </div>
        <div className="biv12-footer"><button className="outline-btn" onClick={() => setJourneyStep(5)}>← Back</button><small>Source statuses distinguish fetched/official data from cross-verified data.</small><button className="bob-btn" onClick={() => setJourneyStep(7)}>Proceed to Business Overview →</button></div>
      </>}
      <CopilotDrawer open={copilotOpen} onClose={() => setCopilotOpen(false)} chat={chat} message={message} setMessage={setMessage} sendCamChat={sendCamChat} busy={assistantBusy}/>
    </div>
  );
}
