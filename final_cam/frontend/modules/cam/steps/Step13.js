"use client";
import { useEffect, useState } from "react";

export default function Step13(ctx) {
  const { sessionId, policyFiles, setPolicyFiles, uploadPolicies, policyMsg, policyResults, policyChat, askPolicy,
    setPolicyIndexed, setPolicyAnalysisComplete, apiRequest, ACCEPT_POLICY, PageHeader, FooterNav, Chat, go, companyName } = ctx;
  const [active, setActive] = useState(null);
  const [loading, setLoading] = useState(true);

  async function loadPolicy() {
    if (!sessionId) return;
    setLoading(true);
    try {
      const d = await apiRequest(`/api/cam/policy-readiness/${sessionId}`);
      setActive(d.policy || null);
      setPolicyIndexed(Boolean(d.policy_available));
      setPolicyAnalysisComplete(Boolean(d.analysis_complete));
    } finally { setLoading(false); }
  }
  useEffect(() => { loadPolicy(); }, [sessionId]);

  async function uploadAndRefresh() { await uploadPolicies(); setTimeout(loadPolicy, 250); }

  return <>
    <PageHeader number={13} title="Policy Documents" subtitle="Manage the policy set used to validate CAM proposals. Synthetic MSME policy data is active for this POC; uploaded policies can replace it." action={<button className="outline-btn" onClick={() => go(14)}>CAM vs Policy Analysis →</button>} />

    <div className="policy-doc-grid">
      <section className="journey-card policy-active-card">
        <div className="panel-title"><h2>Active Policy Set</h2><span className="status-chip success">{active?.status || (loading ? "Loading" : "ACTIVE")}</span></div>
        <div className="policy-doc-icon">▤</div>
        <h3>{active?.policy_name || "Synthetic MSME Credit Policy 2026"}</h3>
        <div className="policy-meta-grid">
          <span>Version</span><strong>{active?.version || "2026.09"}</strong>
          <span>Effective Date</span><strong>{active?.effective_date || "01-Sep-2026"}</strong>
          <span>Last Updated</span><strong>{active?.updated_at ? new Date(active.updated_at).toLocaleString() : "06-Sep-2026"}</strong>
          <span>Rules</span><strong>{active?.total_rules || 44}</strong>
          <span>Source</span><strong>{active?.source === "uploaded" ? "Uploaded policy" : "Synthetic POC data"}</strong>
          <span>Applies To</span><strong>{active?.loan_type || "MSME"}</strong>
        </div>
        <div className="mapping-note">✓ This active policy is used for CAM vs Policy Analysis for {companyName}.</div>
      </section>

      <section className="journey-card">
        <div className="panel-title"><h2>Upload Policy Documents</h2><span>PDF / DOCX / TXT</span></div>
        <div className="upload-panel compact-policy-upload">
          <div className="upload-big">⇧</div><div><h3>Upload approved policy</h3><p>Uploading a changed policy invalidates the previous policy analysis and requires a re-run.</p></div>
          <label className="bob-outline-upload">Browse<input type="file" multiple accept={ACCEPT_POLICY} onChange={e => setPolicyFiles([...e.target.files])}/></label>
        </div>
        {policyFiles.length > 0 && <div className="file-pills">{policyFiles.map(f => <span key={f.name}>{f.name}</span>)}</div>}
        <button className="bob-btn" disabled={!policyFiles.length} onClick={uploadAndRefresh}>Upload & Activate Policy →</button>
        <div className="upload-message">{policyMsg}</div>
        {policyResults.length > 0 && <div className="policy-upload-list">{policyResults.map((r,i)=><div key={i}><strong>{r.filename}</strong><span className="status-chip success">{r.status}</span></div>)}</div>}
      </section>
    </div>

    <section className="journey-card policy-copilot-card">
      <div className="panel-title"><h2>AI Policy Copilot</h2><span>Source-grounded Q&A</span></div>
      <Chat messages={policyChat.length ? policyChat : [{who:"AI",text:"The synthetic policy set is available for CAM policy analysis. Upload a real policy document to ask source-grounded questions with page citations."}]} onSend={askPolicy} placeholder="Ask about eligibility, exposure limits, collateral, DSCR, covenants or deviations..." />
    </section>
    <FooterNav nextLabel="Go to CAM vs Policy Analysis" onNext={() => go(14)} disabled={!active}/>
  </>;
}
