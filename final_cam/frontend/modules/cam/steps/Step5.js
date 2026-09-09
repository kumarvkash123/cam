"use client";

import { useEffect, useMemo, useState } from "react";
import {
  BorrowerHeader,
  BulletList,
  CopilotDrawer,
  FinancialTrendChart,
  InfoRows,
  ReadinessCard,
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
  const presentation = summary?.presentation || {};
  const strengths = presentation.strengths || [];
  const attentionItems = presentation.attention_items || [];
  const pendingItems = presentation.pending_items || [];
  const verificationStatus = presentation.verification_status || summary?.activities || [];
  const complianceStatus = presentation.compliance_status || [];
  const dataReadiness = presentation.data_readiness || {};
  const readinessForCard = {
    ...(summary?.readiness || {}),
    score: dataReadiness.score ?? summary?.readiness?.score,
    completed: dataReadiness.completed ?? summary?.readiness?.completed,
    total: dataReadiness.total ?? summary?.readiness?.total,
    pending: dataReadiness.total != null && dataReadiness.completed != null ? Math.max(0, dataReadiness.total - dataReadiness.completed) : summary?.readiness?.pending,
    missing_items: pendingItems.map((x) => x.title || x.label).filter(Boolean),
  };

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

  function ObservationPanel({ tone, title, items }) {
    if (!items?.length) return null;
    return (
      <div className={`lsv32-observation is-${tone}`}>
        <strong>{tone === "positive" ? "✓" : tone === "attention" ? "!" : "⚠"} {title}</strong>
        <ul>{items.slice(0, 6).map((item, i) => <li key={i}><b>{item.title || item.label || item}</b>{item.detail ? <span>{item.detail}</span> : null}</li>)}</ul>
      </div>
    );
  }

  function VerificationList({ items }) {
    return (
      <div className="lsv32-verification-list">
        {(items || []).slice(0, 8).map((item, index) => (
          <div key={`${item.label}-${index}`}>
            <span className={`lsv32-status-icon is-${item.status || "pending"}`}>{item.status === "completed" ? "✓" : item.status === "exception" ? "×" : "!"}</span>
            <div><strong>{item.label}</strong><small>{item.detail || "Status not available"}</small></div>
            <em className={`lsv32-status-pill is-${item.status || "pending"}`}>{item.status === "completed" ? "Completed" : item.status === "exception" ? "Exception" : "Pending"}</em>
          </div>
        ))}
      </div>
    );
  }

  function ComplianceList({ items }) {
    return (
      <div className="lsv32-compliance-list">
        {(items || []).map((item) => <div key={item.label}><span>{item.label}</span><strong className={`is-${item.status || "pending"}`}>{item.status === "verified" ? "✓ " : item.status === "exception" ? "⚠ " : "! "}{item.value}</strong></div>)}
      </div>
    );
  }

  const trendInsight = financialTrend?.length >= 2 ? (() => {
    const first = financialTrend[0], last = financialTrend[financialTrend.length - 1];
    const prev = financialTrend[financialTrend.length - 2];
    const revenueDirection = Number(last.revenue || 0) > Number(prev.revenue || 0) ? "increased" : "declined";
    const patDirection = Number(last.pat || 0) > Number(prev.pat || 0) ? "recovered" : "declined";
    const versusFirst = Number(last.pat || 0) < Number(first.pat || 0) ? " but remains below the first period shown" : " and is above the first period shown";
    return `Revenue ${revenueDirection} in ${last.year}; PAT ${patDirection} versus ${prev.year}${versusFirst}.`;
  })() : null;

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

        <ReadinessCard readiness={readinessForCard} onDetails={() => go(4)} />
      </div>

      <div className="lsv9-mid-grid">
        <section className="journey-card lsv9-card lsv9-executive-card">
          <SectionTitle title="Executive Credit Summary" badge={summary?.summary_source === "ai_generated" ? "AI-Assisted Summary" : "AI Summary Pending"} />
          <div className="lsv32-exec-identity">
            <strong>{borrowerName}</strong>
            <span>{borrower.constitution || "Company"}{borrower.cin ? ` • CIN ${borrower.cin}` : ""}</span>
            <small>MCA Status: <b className="is-verified">● {borrower.mca_status || "Pending"}</b></small>
          </div>
          <div className="lsv32-proposal-strip">
            <strong>{requestedAmount} <span>•</span> {facility}</strong>
            <p>{proposal.purpose || "Purpose pending"}</p>
            <div><span>Tenure <b>{proposal.tenure_months ? `${proposal.tenure_months} Months` : "Pending"}</b></span><span>Moratorium <b>{proposal.moratorium_months != null ? `${proposal.moratorium_months} Months` : "Pending"}</b></span><span>Pricing <b>{proposal.pricing || (proposal.interest_rate_pct != null ? `${proposal.interest_rate_pct}% p.a.` : "Pending")}</b></span></div>
          </div>
          {summary?.summary_source === "ai_generated" && summary?.executive_summary ? (
            <p className="lsv9-executive-text lsv32-ai-brief">{summary.executive_summary}</p>
          ) : loading ? (
            <p className="lsv9-executive-text">Generating Executive Credit Summary with Groq…</p>
          ) : (
            <div className="loan-summary-llm-debug"><strong>AI summary unavailable.</strong><span>Status: {na(summary?.llm_status?.status)}</span>{summary?.llm_status?.error ? <span>{summary.llm_status.error}</span> : null}<button className="outline-btn" onClick={() => loadSummary(true)} disabled={loading}>Retry Groq</button></div>
          )}
          <div className="lsv32-observation-grid">
            <ObservationPanel tone="positive" title="Key Strengths" items={strengths} />
            <ObservationPanel tone="attention" title="Areas to Monitor" items={attentionItems} />
            <ObservationPanel tone="pending" title="Information Pending" items={pendingItems} />
          </div>
          <div className="lsv32-source-badges">{(presentation.sources || []).slice(0, 5).map((src, i) => <span key={i}>✓ {src.label || src.type}</span>)}</div>
          <button className="outline-btn lsv9-copilot-btn" onClick={() => setCopilotOpen(true)}>◯ Ask Copilot</button>
        </section>

        <section className="journey-card lsv9-card">
          <SectionTitle title="Revenue & PAT Trend" badge="Last 3 Years" />
          <FinancialTrendChart data={financialTrend} />
          {trendInsight ? <div className="lsv32-trend-insight"><strong>↗ Trend Insight</strong><span>{trendInsight}</span></div> : null}
        </section>

        <section className="journey-card lsv9-card">
          <SectionTitle title="Verification & Data Status" badge="Current CAM" />
          <VerificationList items={verificationStatus} />
          <div className="lsv32-data-readiness"><strong>{dataReadiness.score ?? 0}%</strong><span>CAM Data Readiness</span><small>{dataReadiness.completed ?? 0} of {dataReadiness.total ?? 0} key categories completed</small></div>
        </section>
      </div>

      <div className="lsv9-three-grid">
        <section className="journey-card lsv9-card">
          <SectionTitle title="Credit & Banking" badge={credit.synthetic ? "Synthetic POC Data" : "Verified / API"} />
          <InfoRows rows={[
            ["Bureau Score", credit.bureau_score],
            ["PD", credit.pd_pct != null ? `${credit.pd_pct}%` : null],
            ["Repayment Conduct", credit.repayment_conduct],
            ["Overdue", credit.overdue_cr != null ? cr(credit.overdue_cr) : null],
            ["Avg. Utilisation", credit.average_utilisation_pct != null ? `${credit.average_utilisation_pct}%` : null],
            ["Max. Utilisation", credit.maximum_utilisation_pct != null ? `${credit.maximum_utilisation_pct}%` : null],
            ["SMA Status", credit.sma_status],
            ["Cheque Returns", credit.cheque_returns != null ? String(credit.cheque_returns) : null],
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
          <SectionTitle title="Collateral Highlights" badge={collateral.synthetic ? "Synthetic POC Valuation" : ratio(collateral.coverage_ratio)} />
          <InfoRows rows={[
            ["Gross Value", cr(collateral.gross_value_cr)],
            ["Eligible / Net Value", cr(collateral.net_value_cr)],
            ["Coverage", ratio(collateral.coverage_ratio)],
            ["Title Status", collateral.title_status],
            ["Valuation Status", collateral.valuation_status],
          ]} compact />
          <h4 className="lsv9-mini-title">KEY COLLATERAL</h4>
          <BulletList items={(collateral.securities || []).slice(0, 5).map((item) => item.type ? `${item.type}: ${cr(item.net_value_cr ?? item.gross_value_cr)}` : `${item.label || item.field || "Security"}: ${item.value || "Captured"}`)} empty="Collateral information is not yet available." />
        </section>
      </div>

      <div className="lsv9-bottom-grid">
        <section className="journey-card lsv9-card">
          <SectionTitle title="Compliance Snapshot" badge="Review" />
          <ComplianceList items={complianceStatus} />
        </section>

        <section className="journey-card lsv9-card">
          <SectionTitle title="Public Information" badge={publicInfo.mode === "public_reference_poc" ? "Public Sources" : (publicInfo.mode || "off")} />
          <InfoRows rows={[
            ["Credit Rating", ratingData.rating ? `${ratingData.agency || ""} ${ratingData.rating}${ratingData.outlook ? ` / ${ratingData.outlook}` : ""}` : null],
            ["Rated Facilities", publicInfo.rated_facilities_cr != null ? cr(publicInfo.rated_facilities_cr) : null],
            ["Listed Status", publicInfo.listed_status],
            ["Recent Developments", observationText(publicInfo.recent_developments?.[0])],
            ["Industry Observations", observationText(publicInfo.industry_observations?.[0])],
            ["Adverse Media", publicInfo.adverse_news?.length ? observationText(publicInfo.adverse_news?.[0]) : (publicInfo.mode === "off" ? "Not checked" : "No material issue identified in sources checked")],
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
