"use client";

import { useEffect, useRef } from "react";

export const na = (value) =>
  value === undefined || value === null || value === "" ? "Not available" : value;

export const cr = (value) => {
  if (value === undefined || value === null || value === "") return "Not available";
  const n = Number(value);
  return Number.isFinite(n) ? `₹ ${n.toFixed(2)} Cr` : "Not available";
};

export const ratio = (value, suffix = "x") => {
  if (value === undefined || value === null || value === "") return "Not available";
  const n = Number(value);
  return Number.isFinite(n) ? `${n.toFixed(2)}${suffix}` : "Not available";
};

export function InfoRows({ rows, compact = false }) {
  return (
    <div className={`lsv9-info-list ${compact ? "is-compact" : ""}`}>
      {rows.map(([label, value]) => (
        <div key={label}>
          <span>{label}</span>
          <strong>{na(value)}</strong>
        </div>
      ))}
    </div>
  );
}

export function BulletList({ items, empty = "No material observations available." }) {
  if (!items?.length) return <div className="lsv9-empty">{empty}</div>;
  return (
    <ul className="lsv9-bullets">
      {items.map((item, index) => {
        const text = typeof item === "string" ? item : item?.title || item?.summary || JSON.stringify(item);
        return (
          <li key={`${index}-${text}`}>
            <span>{text}</span>
            {typeof item === "object" && item?.title && item?.summary ? <small>{item.summary}</small> : null}
          </li>
        );
      })}
    </ul>
  );
}

export function SectionTitle({ title, badge, action }) {
  return (
    <div className="lsv9-section-title">
      <h2>{title}</h2>
      <div className="lsv9-title-actions">
        {badge ? <span className="lsv9-soft-badge">{badge}</span> : null}
        {action}
      </div>
    </div>
  );
}

export function BorrowerHeader({ borrower, companyName, onProfile }) {
  const status = borrower.mca_status || "Active";
  return (
    <section className="lsv9-borrower-card">
      <div className="lsv9-company-mark">▥</div>
      <div className="lsv9-borrower-main">
        <div className="lsv9-name-line">
          <h2>{borrower.name || companyName || "Borrower"}</h2>
          <span className="lsv9-status-badge">{status}</span>
          {borrower.existing_customer ? <span className="lsv9-customer-badge">Existing Customer</span> : null}
        </div>
        <div className="lsv9-meta-row">
          {borrower.cin ? <span>CIN: {borrower.cin}</span> : null}
          {borrower.gstin ? <span>GSTIN: {borrower.gstin}</span> : null}
          {borrower.pan ? <span>PAN: {borrower.pan}</span> : null}
        </div>
        <div className="lsv9-meta-row">
          {borrower.industry ? <span>Industry: {borrower.industry}</span> : null}
          {borrower.location ? <span>Location: {borrower.location}</span> : null}
        </div>
      </div>
      <button className="outline-btn lsv9-profile-btn" onClick={onProfile}>♙ View Borrower Profile</button>
    </section>
  );
}

export function ReadinessCard({ readiness = {}, onDetails }) {
  const score = Math.max(0, Math.min(100, Number(readiness.score || 0)));
  const total = Number(readiness.total || 0) || 1;
  const pct = (v) => Math.round((Number(v || 0) / total) * 100);
  const missing = readiness.missing_items || [];
  return (
    <section className="journey-card lsv9-card lsv9-readiness-card">
      <SectionTitle title="CAM Readiness Overview" action={<button className="lsv9-link-btn" onClick={onDetails}>View Details →</button>} />
      <div className="lsv9-readiness-body">
        <div className="lsv9-donut" style={{ "--readiness": `${score * 3.6}deg` }}>
          <div><strong>{score}%</strong><span>CAM Readiness<br />Score</span></div>
        </div>
        <div className="lsv9-readiness-legend">
          <div><i className="is-complete" /><span>Completed</span><strong>{readiness.completed || 0} ({pct(readiness.completed)}%)</strong></div>
          <div><i className="is-progress" /><span>In Progress</span><strong>{readiness.in_progress || 0} ({pct(readiness.in_progress)}%)</strong></div>
          <div><i className="is-pending" /><span>Pending</span><strong>{readiness.pending || 0} ({pct(readiness.pending)}%)</strong></div>
        </div>
      </div>
      <div className="lsv9-missing-box">
        <strong>⚠ Key Missing / In Progress Items</strong>
        {missing.length ? (
          <ul>{missing.slice(0, 3).map((item) => <li key={item}>{String(item).replaceAll("_", " ")}</li>)}</ul>
        ) : (
          <span>No mandatory readiness gaps identified.</span>
        )}
      </div>
    </section>
  );
}

function toCrore(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return null;
  // Existing loan_summary.py trends are stored in rupees when extracted from
  // "in crore" documents, while mock/context values are already in crores.
  return Math.abs(n) > 100000 ? n / 10000000 : n;
}

export function normalizeTrend(summary) {
  const trends = summary?.financial_trend || {};
  const years = summary?.financial_years || [];
  const revenue = Array.isArray(trends?.Revenue) ? trends.Revenue : [];
  const pat = Array.isArray(trends?.PAT) ? trends.PAT : [];
  const count = Math.min(Math.max(revenue.length, pat.length), 3);
  if (!count) return [];

  const startR = Math.max(0, revenue.length - count);
  const startP = Math.max(0, pat.length - count);
  const visibleYears = years.length >= count ? years.slice(-count) : [];
  return Array.from({ length: count }, (_, i) => ({
    year: visibleYears[i] || `FY ${i + 1}`,
    revenue: toCrore(revenue[startR + i]),
    pat: toCrore(pat[startP + i]),
  }));
}

export function FinancialTrendChart({ data }) {
  if (!data?.length) {
    return <div className="lsv9-chart-empty">Revenue & PAT trend will appear when multi-year financial data is extracted.</div>;
  }
  const max = Math.max(1, ...data.flatMap((d) => [Number(d.revenue || 0), Number(d.pat || 0)]));
  const chartHeight = 160;
  return (
    <div className="lsv9-chart-wrap">
      <div className="lsv9-chart-legend"><span><i className="revenue" />Revenue (₹ Cr)</span><span><i className="pat" />PAT (₹ Cr)</span></div>
      <svg className="lsv9-chart" viewBox="0 0 520 230" role="img" aria-label="Revenue and PAT trend">
        {[0, 0.25, 0.5, 0.75, 1].map((p) => {
          const y = 185 - chartHeight * p;
          return <line key={p} x1="42" x2="505" y1={y} y2={y} className="lsv9-grid-line" />;
        })}
        {data.map((d, index) => {
          const groupX = 82 + index * (390 / Math.max(data.length - 1, 1));
          const rh = (Number(d.revenue || 0) / max) * chartHeight;
          const ph = (Number(d.pat || 0) / max) * chartHeight;
          return (
            <g key={`${d.year}-${index}`}>
              <rect x={groupX - 24} y={185 - rh} width="34" height={rh} rx="4" className="lsv9-revenue-bar" />
              <rect x={groupX + 14} y={185 - ph} width="28" height={ph} rx="4" className="lsv9-pat-bar" />
              <text x={groupX - 7} y={Math.max(15, 179 - rh)} textAnchor="middle" className="lsv9-chart-value">{d.revenue != null ? d.revenue.toFixed(2) : "—"}</text>
              <text x={groupX + 28} y={Math.max(15, 179 - ph)} textAnchor="middle" className="lsv9-chart-value">{d.pat != null ? d.pat.toFixed(2) : "—"}</text>
              <text x={groupX + 5} y="210" textAnchor="middle" className="lsv9-chart-year">{d.year}</text>
            </g>
          );
        })}
      </svg>
      <small>All amounts in INR Crore</small>
    </div>
  );
}

export function RecentActivities({ activities = [] }) {
  if (!activities.length) return <div className="lsv9-empty">No recent CAM activity captured.</div>;
  return (
    <div className="lsv9-activities">
      {activities.slice(0, 6).map((item, index) => {
        const status = item.status || "pending";
        return (
          <div key={`${item.label}-${index}`}>
            <span className={`lsv9-activity-icon is-${status}`}>{status === "completed" ? "✓" : status === "pending" ? "!" : "•"}</span>
            <div><strong>{item.label}</strong>{item.detail ? <small>{item.detail}</small> : null}</div>
          </div>
        );
      })}
    </div>
  );
}

export function CopilotDrawer({ open, onClose, borrowerName, chat, message, setMessage, sendCamChat, assistantBusy }) {
  const endRef = useRef(null);
  useEffect(() => {
    if (open) endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [open, chat?.length, assistantBusy]);
  if (!open) return null;

  const suggestions = [
    "Why is this risk rating assigned?",
    "Explain the financial performance",
    "What are the key risks?",
    "What is the collateral coverage?",
    "Why is CAM readiness not 100%?",
    "Summarise recent public information",
  ];

  return (
    <aside className="lsv9-copilot-drawer" aria-label="CAM Assistant">
      <div className="lsv9-copilot-head">
        <div><strong>◉ CAM Assistant</strong><span>Your AI partner for deeper CAM insights</span></div>
        <button onClick={onClose} aria-label="Close CAM Assistant">×</button>
      </div>
      <div className="lsv9-copilot-borrower"><strong>{borrowerName}</strong><span>Current Loan Summary context</span></div>
      <div className="lsv9-suggestions">
        <strong>Suggested Questions</strong>
        <div>{suggestions.map((q) => <button key={q} onClick={() => sendCamChat(q)} disabled={assistantBusy}>{q}</button>)}</div>
      </div>
      <div className="lsv9-chat-scroll">
        {!chat?.length ? <div className="lsv9-ai-message">Hello! Ask me to explain financials, risks, collateral, readiness, policy or public information for this CAM.</div> : null}
        {(chat || []).map((m, i) => (
          <div key={i} className={m.who === "AI" ? "lsv9-ai-message" : "lsv9-user-message"}>
            <strong>{m.who === "AI" ? "CAM Assistant" : "You"}</strong>
            <p>{m.text}</p>
            {m.sources?.length ? (
              <div className="lsv9-chat-sources"><b>Sources</b>{m.sources.slice(0, 6).map((src, j) => src.url ? <a href={src.url} target="_blank" rel="noreferrer" key={j}>{j + 1}. {src.title || "Public source"}</a> : <span key={j}>{j + 1}. {src.title || src.filename || "CAM evidence"}</span>)}</div>
            ) : null}
          </div>
        ))}
        {assistantBusy ? <div className="lsv9-ai-message">Working on the current CAM evidence…</div> : null}
        <div ref={endRef} />
      </div>
      <div className="lsv9-copilot-input">
        <input value={message} onChange={(e) => setMessage(e.target.value)} onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && sendCamChat()} placeholder="Ask a follow-up question…" disabled={assistantBusy} />
        <button className="bob-btn" onClick={() => sendCamChat()} disabled={assistantBusy || !message?.trim()}>➤</button>
      </div>
      <small className="lsv9-copilot-note">AI-generated response. Verify evidence before taking any credit action.</small>
    </aside>
  );
}
