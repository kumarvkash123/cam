"use client";

import { useEffect, useRef, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { setCamField } from "../../store/camSlice";
import {
  BOBMark,
  Icon,
  humanize,
  formatValue,
  AssistantText,
} from "../../shared/ui";
import ReportStep from "./ReportStep";
import { apiRequest } from "./api";
import { ACCEPT_POLICY, ACCEPT_DOCS } from "./constants";
import CAMSidebar from "./components/CAMSidebar";

import Step1 from "./steps/Step1";
import Step2 from "./steps/Step2";
import Step3 from "./steps/Step3";
import Step4 from "./steps/Step4";
import Step5 from "./steps/Step5";
import Step6 from "./steps/Step6";
import Step7 from "./steps/Step7";
import Step8 from "./steps/Step8";
import Step9 from "./steps/Step9";
import Step10 from "./steps/Step10";
import Step11 from "./steps/Step11";
import Step12 from "./steps/Step12";
import Step13 from "./steps/Step13";
import Step14 from "./steps/Step14";
import Step15 from "./steps/Step15";
import Step16 from "./steps/Step16";

/* =========================================================
   CHAT
========================================================= */

function Chat({ messages, onSend, placeholder }) {
  const [value, setValue] = useState("");

  const send = async () => {
    const v = value.trim();
    if (!v) return;

    setValue("");
    await onSend(v);
  };

  return (
    <>
      <div className="rag-box">
        {messages.map((m, i) => (
          <div
            key={i}
            className={`rag-msg ${m.who === "AI" ? "ai" : "user"}`}
          >
            <div className="rag-bubble">
              <AssistantText text={m.text} />

              {(m.citations || []).map((c, j) => (
                <div className="citation" key={j}>
                  <strong>{c.source_id || "Source"}</strong> ·{" "}
                  {c.filename || "Document"}
                  {c.page ? ` · Page ${c.page}` : ""}
                  {c.doc_type ? ` · ${c.doc_type}` : ""}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="chat-input-row">
        <input
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder={placeholder}
        />

        <button className="primary-btn" onClick={send}>
          Ask
        </button>
      </div>
    </>
  );
}

/* =========================================================
   STEP CARD
========================================================= */

function StepCard({
  number,
  title,
  subtitle,
  children,
  badge,
  hidden = false,
}) {
  if (hidden) return null;

  return (
    <section className="card">
      <div className="section-head">
        <div>
          <span className="step-number">
            {String(number).padStart(2, "0")}
          </span>

          <div className="section-title-wrap">
            <h2>{title}</h2>
            <p>{subtitle}</p>
          </div>
        </div>

        {badge}
      </div>

      {children}
    </section>
  );
}

/* =========================================================
   STAT
========================================================= */

function Stat({ label, value, kind = "" }) {
  return (
    <div className={`journey-stat ${kind}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

/* =========================================================
   LEGEND
   FIX FOR: ReferenceError: Legend is not defined
========================================================= */

function Legend({ color, label, value }) {
  return (
    <div className="doc-legend-item">
      <span
        className="doc-legend-dot"
        style={{ backgroundColor: color }}
      />

      <span>{label}</span>

      <strong>{value}</strong>
    </div>
  );
}

/* =========================================================
   CAM WORKSPACE
========================================================= */

function CAMWorkspace() {
  const dispatch = useDispatch();
  const cam = useSelector((state) => state.cam);

  const {
    journeyStep,
    step9Subsection,
    step10Subsection,
    company,
    sessionId,
    camInfo,
    chat,
    policyResults,
    policyIndexed,
    policyAnalysisComplete,
    policyMsg,
    policyChat,
    docResults,
    docMsg,
    documentChat,
    reviewApproved,
    mca,
    mcaMsg,
    mcaStatus,
    analysis,
    analysisStarted,
    generated,
    error,
  } = cam;

  /* =========================================================
     REDUX FIELD HELPERS
  ========================================================= */

  const setField = (key, value) =>
    dispatch(
      setCamField({
        key,
        value:
          typeof value === "function"
            ? value(cam[key])
            : value,
      })
    );

  const setJourneyStep = (v) => setField("journeyStep", v);
  const setStep9Subsection = (v) => setField("step9Subsection", v);
  const setStep10Subsection = (v) => setField("step10Subsection", v);
  const setCompany = (v) => setField("company", v);
  const setSessionId = (v) => setField("sessionId", v);
  const setCamInfo = (v) => setField("camInfo", v);
  const setChat = (v) => setField("chat", v);
  const setPolicyResults = (v) => setField("policyResults", v);
  const setPolicyIndexed = (v) => setField("policyIndexed", v);
  const setPolicyAnalysisComplete = (v) => setField("policyAnalysisComplete", v);
  const setPolicyMsg = (v) => setField("policyMsg", v);
  const setPolicyChat = (v) => setField("policyChat", v);
  const setDocResults = (v) => setField("docResults", v);
  const setDocMsg = (v) => setField("docMsg", v);
  const setDocumentChat = (v) => setField("documentChat", v);
  const setReviewApproved = (v) => setField("reviewApproved", v);
  const setMca = (v) => setField("mca", v);
  const setMcaMsg = (v) => setField("mcaMsg", v);
  const setMcaStatus = (v) => setField("mcaStatus", v);
  const setAnalysis = (v) => setField("analysis", v);
  const setAnalysisStarted = (v) =>
    setField("analysisStarted", v);
  const setGenerated = (v) => setField("generated", v);
  const setError = (v) => setField("error", v);

  /* =========================================================
     LOCAL STATE
  ========================================================= */

  const [journeyCollapsed, setJourneyCollapsed] =
    useState(false);

  const [message, setMessage] = useState("");
  const [assistantBusy, setAssistantBusy] = useState(false);

  const [policyFiles, setPolicyFiles] = useState([]);
  const [docFiles, setDocFiles] = useState([]);
  const [docUploadBusy, setDocUploadBusy] = useState(false);

  const [reviewDocIndex, setReviewDocIndex] = useState(0);
  const [mappingEdits, setMappingEdits] = useState({});
  const [reviewBusy, setReviewBusy] = useState(false);

  const [previewFullScreen, setPreviewFullScreen] =
    useState(false);

  const [mcaCin, setMcaCin] = useState("");

  const pollRef = useRef(null);

  useEffect(() => {
    return () => clearTimeout(pollRef.current);
  }, []);

  /* =========================================================
     START CAM
  ========================================================= */

  async function startCam(companyOverride) {
    const requestedCompany = String(companyOverride ?? company ?? "").trim();

    if (!requestedCompany) {
      return setError("Enter or select a company name");
    }

    setError("");
    // Keep the CAM session borrower in Redux, but allow Step 1 search and
    // create-new inputs to remain independent local UI state.
    setCompany(requestedCompany);

    try {
      const d = await apiRequest("/api/cam/start", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          company_name: requestedCompany,
        }),
      });

      setSessionId(d.session_id);
      setCamInfo(d);

      setChat([
        {
          who: "AI",
          text: d.message,
          sources: [],
        },
      ]);

      setJourneyStep(2);
    } catch (e) {
      setError(e.message);
    }
  }

  /* =========================================================
     CAM CHAT
  ========================================================= */

  async function sendCamChat(explicitMessage) {
    const v = (typeof explicitMessage === "string" ? explicitMessage : message).trim();

    if (!v || !sessionId || assistantBusy) return;

    setMessage("");

    setChat((x) => [
      ...x,
      {
        who: "You",
        text: v,
      },
    ]);

    setAssistantBusy(true);

    try {
      const d = await apiRequest(
        `/api/cam/chat/${sessionId}`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            message: v,
          }),
        }
      );

      setChat((x) => [
        ...x,
        {
          who: "AI",
          text: d.reply || d.error || "No reply",
          sources: d.sources || [],
          searchQuery: d.search_query,
        },
      ]);

      setCamInfo((prev) => ({
        ...(prev || {}),
        loan_type:
          d.loan_type ||
          prev?.loan_type ||
          "",
        loan_amount:
          d.loan_amount ||
          prev?.loan_amount ||
          "",
        loan_purpose:
          d.loan_purpose ||
          prev?.loan_purpose ||
          "",
        tenure:
          d.tenure ||
          prev?.tenure ||
          "",
        interest_rate:
          d.interest_rate ||
          prev?.interest_rate ||
          "",
        repayment:
          d.repayment ||
          prev?.repayment ||
          "",
      }));
    } catch (e) {
      setChat((x) => [
        ...x,
        {
          who: "AI",
          text: `Error: ${e.message}`,
        },
      ]);
    } finally {
      setAssistantBusy(false);
    }
  }

  /* =========================================================
     POLICY UPLOAD
  ========================================================= */

  async function uploadPolicies() {
    if (!policyFiles.length) {
      return setPolicyMsg("Select policy documents");
    }

    const fd = new FormData();

    policyFiles.forEach((f) => {
      fd.append("file", f);
    });

    setPolicyMsg("Indexing policy documents...");

    try {
      const d = await apiRequest(
        `/api/cam/policies/${sessionId}`,
        {
          method: "POST",
          body: fd,
        }
      );

      setPolicyMsg(
        d.message || "Policy documents indexed"
      );

      setPolicyIndexed(true);
      setPolicyAnalysisComplete(false);
      setPolicyResults(d.results || []);
      setPolicyFiles([]);
    } catch (e) {
      setPolicyMsg(`Error: ${e.message}`);
    }
  }

  /* =========================================================
     POLICY CHAT
  ========================================================= */

  async function askPolicy(q) {
    setPolicyChat((x) => [
      ...x,
      {
        who: "You",
        text: q,
      },
    ]);

    try {
      const d = await apiRequest(
        `/api/cam/policy-chat/${sessionId}`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            message: q,
          }),
        }
      );

      setPolicyChat((x) => [
        ...x,
        {
          who: "AI",
          text:
            d.answer ||
            d.error ||
            "No answer",
          citations: d.citations || [],
        },
      ]);
    } catch (e) {
      setPolicyChat((x) => [
        ...x,
        {
          who: "AI",
          text: `Error: ${e.message}`,
        },
      ]);
    }
  }

  /* =========================================================
     DELETE DOCUMENT
  ========================================================= */

  async function deleteDoc(documentId) {
    if (!documentId) return;

    if (
      !window.confirm(
        "Delete this document? This action cannot be undone."
      )
    ) {
      return;
    }

    try {
      await apiRequest(`/api/documents/${documentId}`, {
        method: "DELETE",
      });

      setDocResults((prev) =>
        prev.filter(
          (d) => d.document_id !== documentId
        )
      );

      setDocMsg("Document deleted successfully.");
    } catch (e) {
      setDocMsg(`Error: ${e.message}`);
    }
  }

  /* =========================================================
     DOCUMENT UPLOAD
  ========================================================= */

  async function uploadDocs() {
    if (!docFiles.length) {
      return setDocMsg(
        "Select supporting documents"
      );
    }

    const fd = new FormData();

    docFiles.forEach((f) => {
      fd.append("file", f);
    });

    setDocUploadBusy(true);
    setDocMsg(
      `Processing ${docFiles.length} document${docFiles.length === 1 ? "" : "s"} with OCR, classification and extraction...`
    );

    try {
      const d = await apiRequest(
        `/api/cam/documents/${sessionId}`,
        {
          method: "POST",
          body: fd,
        }
      );

      setDocMsg(
        d.message ||
          "Documents processed successfully"
      );

      setDocResults(d.results || []);
      setDocFiles([]);

      if (d.mca?.data) {
        setMca(d.mca);
        setMcaCin(d.mca.cin || "");
        setMcaStatus("completed");

        setMcaMsg(
          "FileSure MCA data fetched automatically."
        );
      } else {
        refreshMca();
      }

      setDocumentChat([
        {
          who: "AI",
          text:
            "Borrower documents are ready. Ask me about the submitted evidence. Answers will include file/page citations.",
        },
      ]);
    } catch (e) {
      setDocMsg(`Error: ${e.message}`);
    } finally {
      setDocUploadBusy(false);
    }
  }

  /* =========================================================
     DOCUMENT CHAT
  ========================================================= */

  async function askDocument(q) {
    setDocumentChat((x) => [
      ...x,
      {
        who: "You",
        text: q,
      },
    ]);

    try {
      const d = await apiRequest(
        `/api/cam/document-chat/${sessionId}`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            message: q,
          }),
        }
      );

      setDocumentChat((x) => [
        ...x,
        {
          who: "AI",
          text:
            d.answer ||
            d.error ||
            "No answer",
          citations: d.citations || [],
        },
      ]);
    } catch (e) {
      setDocumentChat((x) => [
        ...x,
        {
          who: "AI",
          text: `Error: ${e.message}`,
        },
      ]);
    }
  }

  /* =========================================================
     MCA
  ========================================================= */

  async function refreshMca() {
    if (!sessionId) return;

    try {
      const d = await apiRequest(
        `/api/cam/mca/${sessionId}`
      );

      if (
        d.status &&
        d.status !== "not_fetched"
      ) {
        setMcaStatus(d.status);
        setMcaCin(d.cin || "");

        if (d.data) {
          setMca(d.data);
        }
      }
    } catch {}
  }

  async function fetchMca() {
    setMcaStatus("fetching");
    setMcaMsg(
      "Fetching MCA through FileSure..."
    );

    try {
      const d = await apiRequest(
        `/api/cam/mca/${sessionId}`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(
            mcaCin
              ? { cin: mcaCin }
              : {}
          ),
        }
      );

      setMca(d);
      setMcaCin(d.cin || "");
      setMcaStatus("completed");

      setMcaMsg(
        d.message || "MCA data fetched"
      );
    } catch (e) {
      setMcaStatus("failed");
      setMcaMsg(
        `Error: ${e.message}`
      );
    }
  }

  /* =========================================================
     ANALYSIS
  ========================================================= */

  async function startAnalysis() {
    if (!sessionId) {
      setError("Start a CAM session before running analysis.");
      return false;
    }

    setError("");

    try {
      await apiRequest(
        `/api/cam/analyze/${sessionId}`,
        {
          method: "POST",
        }
      );

      setAnalysisStarted(true);
      pollStatus();
      return true;
    } catch (e) {
      setError(e.message);
      return false;
    }
  }

  async function pollStatus() {
    if (!sessionId) return;

    try {
      const d = await apiRequest(
        `/api/cam/status/${sessionId}`
      );

      setAnalysis(d);
      setPolicyAnalysisComplete(Boolean(d.policy_review_completed));

      if (
        d.status === "analysis_completed" ||
        d.status === "failed"
      ) {
        return;
      }

      pollRef.current = setTimeout(
        pollStatus,
        800
      );
    } catch (e) {
      setError(e.message);
    }
  }

  /* =========================================================
     GENERATE CAM
  ========================================================= */

  async function generateCam() {
    try {
      // Clear any stale generation error before re-checking readiness on the backend.
      setError("");
      const d = await apiRequest(
        `/api/cam/generate/${sessionId}`,
        {
          method: "POST",
        }
      );

      setGenerated(d);
      setError("");
    } catch (e) {
      setError(e.message);
    }
  }

  /* =========================================================
     DERIVED DATA
  ========================================================= */

  const hasSession = !!sessionId;
  const canDocs = hasSession;

  const analysisComplete =
    ["analysis_completed", "completed"].includes(analysis?.status) ||
    (analysis?.progress >= 100 && analysis?.analysis_stages?.remaining_cam === "completed");

  const finalCamReady =
    analysisComplete && policyAnalysisComplete;

  const mcaData =
    mca?.data || mca || {};

  const companyData =
    mcaData?.masterData?.companyData ||
    {};

  const mcaValues = [
    [
      "Company Name",
      companyData.companyName ||
        mcaData.company,
    ],
    [
      "CIN",
      mcaData.cin ||
        companyData.cin,
    ],
    [
      "Company Status",
      companyData.companyStatus,
    ],
    [
      "Date Of Incorporation",
      companyData.dateOfIncorporation,
    ],
    [
      "Authorised Capital",
      companyData.authorisedCapital,
    ],
    [
      "Paid-up Capital",
      companyData.paidupCapital,
    ],
  ].filter(
    (x) =>
      x[1] !== undefined &&
      x[1] !== null &&
      x[1] !== ""
  );

  const stepTitles = [
    "Borrower Details",
    "Document Upload",
    "Document Review & Mapping",
    "CAM Readiness & Start Analysis",
    "Loan Summary",
    "Borrower Information",
    "Business Overview",
    "Financial Analysis & Stress Testing",
    "Credit History & Risk Assessment",
    "Collateral & Loan Terms",
    "Compliance Checks",
    "Industry & Peer Analysis",
    "Policy Management",
    "CAM vs Policy Analysis",
    "Final CAM Review",
    "Generate CAM",
  ];

  // The bank requires 10 CAM report sections. Some UI screens intentionally
  // cover more than one report section (risk, collateral/terms). Keep this
  // list separate from workflow steps so Final Review tracks the actual CAM.
  const camSections = [
    "Loan Summary",
    "Borrower Information",
    "Business Overview",
    "Financial Analysis & Stress Testing",
    "Credit History & Repayment Track Record",
    "Risk Assessment & Mitigation",
    "Collateral Details",
    "Loan Terms & Conditions",
    "Regulatory & Compliance Checks",
    "Peer Benchmarking & Market / Industry Analysis",
  ];

  const camSectionStepMap = [5, 6, 7, 8, 9, 9, 10, 10, 11, 12];

  const go = (n) =>
    setJourneyStep(
      Math.max(
        1,
        Math.min(16, n)
      )
    );

  const next = () =>
    go(journeyStep + 1);

  const prev = () =>
    go(journeyStep - 1);

  const companyName =
    company ||
    companyData.companyName ||
    mcaData.company ||
    "New Borrower";

  const capturedLoanType =
    camInfo?.loan_type || "";

  const capturedLoanAmount =
    camInfo?.loan_amount || "";

  const docsProcessed =
    docResults.length;

  const extractedFields =
    docResults.reduce(
      (n, d) =>
        n +
        Object.keys(
          d.fields ||
            d.extracted_fields ||
            {}
        ).length,
      0
    );

  const analysisProgress = Number(
    analysis?.progress || 0
  );

  const readiness = [
    [
      "Borrower created",
      !!sessionId,
    ],
    [
      "Policy indexed",
      policyIndexed,
    ],
    [
      "Documents processed",
      docsProcessed > 0,
    ],
    [
      "MCA / external data",
      mcaStatus === "completed" ||
        !!mca,
    ],
    [
      "Analysis completed",
      analysisComplete,
    ],
  ];

  const statusText =
    analysisComplete
      ? "Analysis completed"
      : analysisStarted
      ? `${analysisProgress}% complete`
      : "Not started";

  /* =========================================================
     SIDEBAR
  ========================================================= */

  /* Sidebar moved to components/CAMSidebar.js. */

  /* =========================================================
     PAGE HEADER
  ========================================================= */

  function PageHeader({
    number,
    title,
    subtitle,
    action,
  }) {
    return (
      <div className="journey-header">
        <div className="journey-heading">
          <span className="journey-number">
            {String(number).padStart(
              2,
              "0"
            )}
          </span>

          <div>
            <div className="journey-kicker">
              CREDIT APPRAISAL MANAGEMENT
            </div>

            <h1>{title}</h1>
            <p>{subtitle}</p>
          </div>
        </div>

        <div className="journey-actions">
          <button className="journey-help">
            ? Help
          </button>

          {action}
        </div>
      </div>
    );
  }

  /* =========================================================
     FOOTER
  ========================================================= */

  function FooterNav({
    back = true,
    nextLabel = "Save & Continue",
    onNext = next,
    disabled = false,
  }) {
    return (
      <div className="journey-footer">
        <span>
          🔒 Secure & Confidential —
          Authorized Bank of Baroda
          users only
        </span>

        <div>
          {back && (
            <button
              className="outline-btn"
              onClick={prev}
              disabled={
                journeyStep === 1
              }
            >
              ← Back
            </button>
          )}

          <button
            className="bob-btn"
            onClick={onNext}
            disabled={disabled}
          >
            {nextLabel}
            <span>→</span>
          </button>
        </div>
      </div>
    );
  }

  /* =========================================================
     DATA TABLE
  ========================================================= */

  function DataTable({
    rows,
    columns = ["Field", "Value"],
  }) {
    return (
      <div className="journey-table-wrap">
        <table className="journey-table">
          <thead>
            <tr>
              {columns.map((c) => (
                <th key={c}>
                  {c}
                </th>
              ))}
            </tr>
          </thead>

          <tbody>
            {rows.map((r, i) => (
              <tr key={i}>
                {r.map((v, j) => (
                  <td key={j}>
                    {j === 0 ? (
                      <strong>
                        {formatValue(v)}
                      </strong>
                    ) : (
                      formatValue(v)
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  /* =========================================================
     DOCUMENT HELPERS
  ========================================================= */

  function documentConfidence(d) {
    const raw =
      d?.confidence_score ??
      d?.confidence ??
      d?.classification_confidence;

    if (
      raw === null ||
      raw === undefined ||
      raw === ""
    ) {
      return 0;
    }

    const n = Number(raw);

    if (!Number.isFinite(n)) {
      return 0;
    }

    return Math.round(
      n <= 1 ? n * 100 : n
    );
  }

  function documentUiStatus(d) {
    const raw = String(
      d?.status ||
        d?.classification_status ||
        "processed"
    ).toLowerCase();

    if (
      raw.includes("fail") ||
      raw.includes("error")
    ) {
      return "Failed";
    }

    if (
      raw === "auto_accepted" ||
      raw === "accepted" ||
      raw === "processed" ||
      raw === "confirmed"
    ) {
      return "Auto Approved";
    }

    if (
      raw === "llm_fallback" ||
      raw === "low_confidence" ||
      raw === "new_view"
    ) {
      return "New View";
    }

    return "Under Review";
  }

  function ConfidenceScore({ value }) {
    if (!value) {
      return (
        <span className="confidence-score empty">
          —
        </span>
      );
    }

    const cls =
      value >= 90
        ? "high"
        : value >= 70
        ? "medium"
        : "low";

    return (
      <div className="confidence-score">
        <span>{value}%</span>

        <i className={cls}>
          <b
            style={{
              width: `${Math.min(
                100,
                value
              )}%`,
            }}
          />
        </i>
      </div>
    );
  }

  /* =========================================================
     RENDER STEP
  ========================================================= */

  function renderStep() {
    const stepContext = {
      journeyStep,
      step9Subsection,
      step10Subsection,
      company,
      sessionId,
      camInfo,
      chat,
      policyResults,
      policyIndexed,
      policyAnalysisComplete,
      policyMsg,
      policyChat,
      docResults,
      docMsg,
      documentChat,
      reviewApproved,
      mca,
      mcaMsg,
      mcaStatus,
      analysis,
      analysisStarted,
      generated,
      error,
      setJourneyStep,
      setStep9Subsection,
      setStep10Subsection,
      setCompany,
      setSessionId,
      setCamInfo,
      setChat,
      setPolicyResults,
      setPolicyIndexed,
      setPolicyAnalysisComplete,
      setPolicyMsg,
      setPolicyChat,
      setDocResults,
      setDocMsg,
      setDocumentChat,
      setReviewApproved,
      setMca,
      setMcaMsg,
      setMcaStatus,
      setAnalysis,
      setAnalysisStarted,
      setGenerated,
      setError,
      startCam,
      sendCamChat,
      uploadPolicies,
      askPolicy,
      deleteDoc,
      uploadDocs,
      askDocument,
      refreshMca,
      fetchMca,
      startAnalysis,
      pollStatus,
      generateCam,
      hasSession,
      canDocs,
      analysisComplete,
      finalCamReady,
      mcaData,
      companyData,
      mcaValues,
      stepTitles,
      camSections,
      camSectionStepMap,
      go,
      next,
      prev,
      companyName,
      capturedLoanType,
      capturedLoanAmount,
      docsProcessed,
      extractedFields,
      analysisProgress,
      readiness,
      statusText,
      Chat,
      StepCard,
      Stat,
      Legend,
      BOBMark,
      Icon,
      humanize,
      formatValue,
      AssistantText,
      ReportStep,
      apiRequest,
      ACCEPT_POLICY,
      ACCEPT_DOCS,
      PageHeader,
      FooterNav,
      DataTable,
      documentConfidence,
      documentUiStatus,
      ConfidenceScore,
      journeyCollapsed,
      setJourneyCollapsed,
      message,
      setMessage,
      assistantBusy,
      setAssistantBusy,
      policyFiles,
      setPolicyFiles,
      docFiles,
      setDocFiles,
      docUploadBusy,
      reviewDocIndex,
      setReviewDocIndex,
      mappingEdits,
      setMappingEdits,
      reviewBusy,
      setReviewBusy,
      previewFullScreen,
      setPreviewFullScreen,
      mcaCin,
      setMcaCin,
      pollRef,
    };
    const StepComponent = [null, Step1, Step2, Step3, Step4, Step5, Step6, Step7, Step8, Step9, Step10, Step11, Step12, Step13, Step14, Step15, Step16][journeyStep];
    return StepComponent ? <StepComponent {...stepContext} /> : null;
  }

  /* =========================================================
     MAIN SHELL
  ========================================================= */

  return (
    <div
      className={`process-shell ${
        journeyCollapsed
          ? "sidebar-collapsed"
          : ""
      }`}
    >
      <CAMSidebar
        journeyStep={journeyStep}
        step9Subsection={step9Subsection}
        step10Subsection={step10Subsection}
        journeyCollapsed={journeyCollapsed}
        setJourneyCollapsed={setJourneyCollapsed}
        setJourneyStep={setJourneyStep}
        setStep9Subsection={setStep9Subsection}
        setStep10Subsection={setStep10Subsection}
      />

      <div className="process-main">
        <header className="process-topbar">
          <div className="process-title">
            <strong>
              CAM AI Platform
            </strong>

            <span>
              Credit Appraisal Management
            </span>
          </div>

          <div className="process-search">
            <Icon name="search" />

            <span>
              Search borrower, CAM ID, CIN,
              documents...
            </span>
          </div>

          <div className="process-actions">
            <button>
              🔔
            </button>

            <button>
              ?
            </button>

            <div className="process-profile">
              <span>
                CO
              </span>

              <div>
                <strong>
                  Credit Officer
                </strong>

                <small>
                  Bank of Baroda
                </small>
              </div>
            </div>
          </div>
        </header>

        <main className="journey-main">
          <div className="breadcrumb">
            <button
              onClick={() =>
                window.dispatchEvent(
                  new CustomEvent(
                    "bob-dashboard"
                  )
                )
              }
            >
              Dashboard
            </button>

            <span>›</span>

            <span>
              CAM Preparation
            </span>

            <span>›</span>

            <strong>
              {journeyStep}.{" "}
              {
                stepTitles[
                  journeyStep - 1
                ]
              }
            </strong>
          </div>

          {error && (
            <div className="error-banner">
              {error}

              <button
                onClick={() =>
                  setError("")
                }
              >
                ×
              </button>
            </div>
          )}

          {renderStep()}
        </main>
      </div>
    </div>
  );
}

export default CAMWorkspace;
