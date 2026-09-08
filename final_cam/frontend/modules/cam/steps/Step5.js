"use client";

import { useEffect, useMemo, useState } from "react";
import {
  BorrowerHeader,
  BulletList,
  CopilotDrawer,
  FinancialTrendChart,
  InfoRows,
  ReadinessCard,
  RecentActivities,
  SectionTitle,
  cr,
  na,
  normalizeTrend,
  ratio,
} from "../loan-summary/components";

export default function Step5(ctx) {
  const {
    sessionId,
    companyName,
    camInfo,
    chat,
    message,
    setMessage,
    assistantBusy,
    sendCamChat,
    apiRequest,
    PageHeader,
    go,
  } = ctx;

  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [summaryError, setSummaryError] = useState("");
  const [copilotOpen, setCopilotOpen] = useState(false);

  async function loadSummary(force = false) {
    if (!sessionId || loading) return;
    setLoading(true);
    setSummaryError("");
    try {
      const data = await apiRequest(`/api/cam/loan-summary/${sessionId}${force ? "?refresh=1" : ""}`);
      setSummary(data);
    } catch (error) {
      setSummaryError(error.message || "Unable to load Loan Summary");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (sessionId) loadSummary(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  const context = summary?.context || {};
  const borrower = context.borrower || summary?.company || {};
  const proposal = context.proposal || {};
  const financials = context.financials || {};
  const ratios = context.ratios || {};
  const credit = summary?.credit || context.credit || {};
  const risk = summary?.risk || context.risk || {};
  const collateral = summary?.collateral || context.collateral || {};
  const compliance = summary?.compliance || context.compliance || {};
  const publicInfo = summary?.public_information || context.public_information || {};
  const ratingData = publicInfo.credit_rating || {};
  const financialTrend = useMemo(() => normalizeTrend(summary), [summary]);

  const requestedAmount = summary?.loan_details?.requested_amount || cr(proposal.requested_amount_cr);
  const facility = proposal.facility_type || camInfo?.loan_type || "Not available";
  const borrowerName = borrower.name || companyName || "Borrower";

  function exportSummary() {
    if (typeof window !== "undefined") window.print();
  }

  function observationText(item) {
    if (!item) return null;
    if (typeof item === "string") return item;
    return item.title || item.summary || item.observation || item.name || null;
  }

  return (
    <div className={`lsv9-page ${copilotOpen ? "has-copilot" : ""}`}>
      <PageHeader
        number={5}
        title="Loan Summary"
        subtitle="AI-assisted insights with verified CAM evidence. Final credit decision remains with the authorised credit officer / committee."
        action={
          <div className="lsv9-header-actions">
            <button className="outline-btn" onClick={() => loadSummary(true)} disabled={loading || !sessionId}>{loading ? "Refreshing…" : "↻ Refresh Summary"}</button>
            <button className="bob-btn" onClick={exportSummary}>⇩ Export Summary</button>
          </div>
        }
      />

      {summaryError ? <div className="error-box">{summaryError}</div> : null}

      <BorrowerHeader borrower={borrower} companyName={companyName} onProfile={() => go(6)} />

      <div className="lsv9-top-grid">
        <section className="journey-card lsv9-card">
          <SectionTitle title="Loan Details" action={<button className="lsv9-link-btn" onClick={() => go(1)}>✎ Edit</button>} />
          <InfoRows rows={[
            ["Requested Amount", requestedAmount],
            ["Facility Type", facility],
            ["Purpose of Loan", proposal.purpose],
            ["Tenure", proposal.tenure_months ? `${proposal.tenure_months} Months` : null],
            ["Interest Rate / Pricing", proposal.interest_rate_pct != null ? `${proposal.interest_rate_pct}% p.a.` : null],
            ["Repayment Structure", proposal.repayment],
            ["Existing Exposure", credit.existing_exposure_cr != null ? cr(credit.existing_exposure_cr) : null],
            ["DSCR (Projected)", ratio(ratios.dscr)],
            ["Interest Coverage Ratio", ratio(ratios.icr)],
          ]} compact />
        </section>

        <section className="journey-card lsv9-card">
          <SectionTitle title={`Key Financial Indicators${financials.latest_fy ? ` (${financials.latest_fy})` : ""}`} action={<button className="lsv9-link-btn" onClick={() => go(3)}>✎ Edit / Review</button>} />
          <InfoRows rows={[
            ["Total Revenue", cr(financials.revenue_cr)],
            ["EBITDA", cr(financials.ebitda_cr)],
            ["PAT", cr(financials.pat_cr)],
            ["Net Worth", cr(financials.net_worth_cr)],
            ["Total Debt", cr(financials.total_debt_cr)],
            ["Debt / Equity", ratio(ratios.debt_equity)],
            ["Current Ratio", ratio(ratios.current_ratio)],
            ["Quick Ratio", ratio(ratios.quick_ratio)],
            ["EBITDA Margin", ratio(ratios.ebitda_margin_pct, "%")],
            ["PAT Margin", ratio(ratios.pat_margin_pct, "%")],
          ]} compact />
        </section>

        <ReadinessCard readiness={summary?.readiness || {}} onDetails={() => go(4)} />
      </div>

      <div className="lsv9-mid-grid">
        <section className="journey-card lsv9-card lsv9-executive-card">
          <SectionTitle title="Executive Credit Summary" badge={summary?.summary_source === "ai_generated" ? "Groq AI Draft" : "Groq Required"} />
          {summary?.summary_source === "ai_generated" && summary?.executive_summary ? (
            <ul className="lsv9-bullets lsv9-executive-bullets">{String(summary.executive_summary).replace(/\b(Pvt|Ltd|Mr|Mrs|Ms|Dr|Prof|No|Cr)\./g,"$1§").split(/(?<=[.!?])\s+(?=[A-Z0-9₹])/).filter(Boolean).map((item,i)=><li key={i}><span>{item.replace(/§/g,".")}</span></li>)}</ul>
          ) : loading ? (
            <p className="lsv9-executive-text">Generating Executive Credit Summary with Groq…</p>
          ) : (
            <div className="loan-summary-llm-debug">
              <strong>Groq did not generate the Executive Credit Summary.</strong>
              <span>Status: {na(summary?.llm_status?.status)}</span>
              <span>Model: {na(summary?.llm_status?.model)}</span>
              {summary?.llm_status?.error ? <span>{summary.llm_status.error}</span> : null}
              <button className="outline-btn" onClick={() => loadSummary(true)} disabled={loading}>{loading ? "Retrying…" : "Retry Groq"}</button>
            </div>
          )}
          <div className="lsv9-review-note">AI-assisted draft. Credit calculations, policy checks and final credit decision remain subject to authorised human review.</div>
          <button className="outline-btn lsv9-copilot-btn" onClick={() => setCopilotOpen(true)}>◯ Ask Copilot</button>
        </section>

        <section className="journey-card lsv9-card">
          <SectionTitle title="Revenue & PAT Trend" badge="Last 3 Years" />
          <FinancialTrendChart data={financialTrend} />
        </section>

        <section className="journey-card lsv9-card">
          <SectionTitle title="Recent Activities" badge="Current CAM" />
          <RecentActivities activities={summary?.activities || []} />
        </section>
      </div>

      <div className="lsv9-three-grid">
        <section className="journey-card lsv9-card">
          <SectionTitle title="Credit & Banking" badge="Verified / API" />
          <InfoRows rows={[
            ["Bureau Score", credit.bureau_score],
            ["PD", credit.pd_pct != null ? `${credit.pd_pct}%` : null],
            ["Repayment Conduct", credit.repayment_conduct],
            ["Overdue", credit.overdue_cr != null ? cr(credit.overdue_cr) : null],
            ["Avg. Utilisation", credit.average_utilisation_pct != null ? `${credit.average_utilisation_pct}%` : null],
          ]} compact />
        </section>

        <section className="journey-card lsv9-card">
          <SectionTitle title="Major Risks & Mitigants" badge={risk.rating || "Review"} />
          <h4 className="lsv9-mini-title">RISKS</h4>
          <BulletList items={risk.major_risks} />
          <h4 className="lsv9-mini-title">MITIGANTS</h4>
          <BulletList items={risk.mitigants} empty="No mitigants captured yet." />
        </section>

        <section className="journey-card lsv9-card">
          <SectionTitle title="Collateral Highlights" badge={ratio(collateral.coverage_ratio)} />
          <InfoRows rows={[
            ["Gross Value", cr(collateral.gross_value_cr)],
            ["Eligible / Net Value", cr(collateral.net_value_cr)],
            ["Coverage", ratio(collateral.coverage_ratio)],
          ]} compact />
          <h4 className="lsv9-mini-title">KEY COLLATERAL</h4>
          <BulletList items={(collateral.securities || []).slice(0, 5).map((item) => item.type ? `${item.type}: ${cr(item.net_value_cr ?? item.gross_value_cr)}` : `${item.label || item.field || "Security"}: ${item.value || "Captured"}`)} empty="Collateral information is not yet available." />
        </section>
      </div>

      <div className="lsv9-bottom-grid">
        <section className="journey-card lsv9-card">
          <SectionTitle title="Compliance Snapshot" badge={compliance.sanctions === "Clear" ? "Clear" : "Review"} />
          <InfoRows rows={[
            ["KYC", compliance.kyc],
            ["Sanctions", compliance.sanctions],
            ["PEP", compliance.pep],
            ["Adverse Media", compliance.adverse_media],
            ["Policy Compliance", compliance.policy_observations?.length ? "Review observations" : "Pending / no exception captured"],
          ]} compact />
        </section>

        <section className="journey-card lsv9-card">
          <SectionTitle title="Public Information" badge={publicInfo.mode || "off"} />
          <InfoRows rows={[
            ["Credit Rating", ratingData.rating ? `${ratingData.agency || ""} ${ratingData.rating}${ratingData.outlook ? ` (${ratingData.outlook})` : ""}` : null],
            ["Recent Developments", observationText(publicInfo.recent_developments?.[0])],
            ["Industry Observations", observationText(publicInfo.industry_observations?.[0])],
            ["Adverse Media", observationText(publicInfo.adverse_news?.[0]) || "No material adverse news captured"],
          ]} compact />
        </section>

      </div>

      <div className="lsv9-page-footer">
        <button className="outline-btn" onClick={() => go(4)}>← Back to Start CAM Preparation</button>
        <div><small>CAM ID: {sessionId || "—"}</small></div>
        <button className="bob-btn" onClick={() => go(6)}>Proceed to Borrower Information →</button>
      </div>

      <CopilotDrawer
        open={copilotOpen}
        onClose={() => setCopilotOpen(false)}
        borrowerName={borrowerName}
        chat={chat}
        message={message}
        setMessage={setMessage}
        sendCamChat={sendCamChat}
        assistantBusy={assistantBusy}
      />
    </div>
  );
}
