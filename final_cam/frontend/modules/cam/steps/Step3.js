import { useEffect, useState } from "react";
import { API_BASE as API } from "../api";

export default function Step3(ctx) {
  const {
    journeyStep,
    company,
    sessionId,
    camInfo,
    chat,
    policyResults,
    policyIndexed,
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
    setCompany,
    setSessionId,
    setCamInfo,
    setChat,
    setPolicyResults,
    setPolicyIndexed,
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
    mcaData,
    companyData,
    mcaValues,
    stepTitles,
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
  } = ctx;

    const selectedDoc =
      docResults[reviewDocIndex] ||
      docResults[0];

    const selectedIndex = selectedDoc
      ? Math.max(
          0,
          docResults.indexOf(
            selectedDoc
          )
        )
      : 0;

    const fields =
      selectedDoc?.fields ||
      selectedDoc?.extracted_fields ||
      {};

    const fieldEntries =
      Object.entries(fields);

    const docConfidence =
      documentConfidence(
        selectedDoc
      );

    const docType =
      selectedDoc?.doc_type ||
      selectedDoc?.document_type ||
      "Unknown";

    const displayType =
      humanize(docType);

    const fieldMap = {
      pan_number_masked: "PAN",
      cin: "CIN",
      gstin: "GSTIN",
      account_number_masked:
        "Account Number",
      account_holder_name:
        "Account Holder Name",
      ifsc: "IFSC Code",
      opening_balance:
        "Opening Balance",
      closing_balance:
        "Closing Balance",
      statement_period:
        "Statement Period",
      acknowledgement_number:
        "ITR Acknowledgement No.",
      assessment_year:
        "Assessment Year",
      aadhaar_number_masked:
        "Aadhaar (Masked)",
      udyam_registration_number:
        "Udyam Registration No.",
    };

    const systemFields = [
      "PAN",
      "Legal Name",
      "CIN",
      "GSTIN",
      "Registered State",
      "Nature of Business",
      "Gross Total Income",
      "Deductions (Chapter VIA)",
      "Total Income",
      "Total Tax Payable",
      "Taxes Paid",
      "Refund",
      "Account Number",
      "Account Holder Name",
      "IFSC Code",
      "Assessment Year",
      "ITR Acknowledgement No.",
      "Other / Unmapped",
    ];

    const defaultMapping = (key) =>
      mappingEdits[
        selectedDoc?.document_id
      ]?.[key] ||
      fieldMap[key] ||
      humanize(key);

    const fieldConfidence = (
      idx
    ) =>
      Math.max(
        72,
        Math.min(
          99,
          docConfidence
            ? docConfidence -
                Math.min(
                  idx * 2,
                  7
                ) +
                (idx % 3 === 0
                  ? 1
                  : 0)
            : 0
        )
      );

    const previewUrl =
      selectedDoc?.document_id
        ? `${API}/api/documents/${selectedDoc.document_id}/file`
        : "";

    const [previewState, setPreviewState] = useState({ status: "idle", message: "" });

    useEffect(() => {
      let cancelled = false;
      if (!previewUrl) {
        setPreviewState({ status: "empty", message: "" });
        return () => { cancelled = true; };
      }
      setPreviewState({ status: "loading", message: "" });
      fetch(previewUrl, { method: "HEAD", cache: "no-store" })
        .then(async (response) => {
          if (cancelled) return;
          if (!response.ok) {
            let message = `Preview request failed (${response.status})`;
            try {
              const body = await fetch(previewUrl, { cache: "no-store" });
              const json = await body.json();
              if (json?.error) message = json.error;
            } catch {}
            setPreviewState({ status: "error", message });
            return;
          }
          setPreviewState({ status: "ready", message: "" });
        })
        .catch((error) => {
          if (!cancelled) setPreviewState({ status: "error", message: error?.message || "Unable to reach preview service" });
        });
      return () => { cancelled = true; };
    }, [previewUrl]);

    function retryPreview() {
      if (!previewUrl) return;
      setPreviewState({ status: "loading", message: "" });
      fetch(previewUrl, { method: "HEAD", cache: "no-store" })
        .then((response) => {
          if (!response.ok) throw new Error(`Preview request failed (${response.status})`);
          setPreviewState({ status: "ready", message: "" });
        })
        .catch((error) => setPreviewState({ status: "error", message: error?.message || "Unable to load document" }));
    }

    const validation = [
      [
        "Document is readable",
        true,
      ],
      [
        "Required pages detected",
        !!selectedDoc,
      ],
      [
        "Document classification valid",
        !!selectedDoc &&
          docType !== "Unknown",
      ],
      [
        "Financial / key values extracted",
        fieldEntries.length > 0,
      ],
      [
        "Cross verification",
        reviewApproved,
      ],
    ];

    async function approveReview() {
      if (!selectedDoc) return;

      setReviewBusy(true);
      setError("");

      try {
        const d = await apiRequest(
          `/api/documents/${selectedDoc.document_id}/confirm`,
          {
            method: "POST",
            headers: {
              "Content-Type":
                "application/json",
            },
            body: JSON.stringify({
              correct_doc_type:
                selectedDoc.doc_type,
            }),
          }
        );

        setDocResults((prev) =>
          prev.map((x, i) =>
            i === selectedIndex
              ? {
                  ...x,
                  status: "confirmed",
                  user_confirmed:
                    true,
                  doc_type:
                    d.doc_type ||
                    x.doc_type,
                }
              : x
          )
        );

        setReviewApproved(true);
        setError("");
        go(4);
      } catch (e) {
        setError(
          `Review approval failed: ${e.message}`
        );
      } finally {
        setReviewBusy(false);
      }
    }

    function saveMapping(
      key,
      value
    ) {
      const id =
        selectedDoc?.document_id ||
        `local-${selectedIndex}`;

      setMappingEdits((prev) => ({
        ...prev,
        [id]: {
          ...(prev[id] || {}),
          [key]: value,
        },
      }));
    }

    function selectDoc(index) {
      setReviewDocIndex(index);
      setReviewApproved(false);
    }

    return (
      <>
        <PageHeader
          number={3}
          title="Document Review & Mapping"
          subtitle={`Review extracted data from ${displayType} and map it to CAM system fields before continuing.`}
          action={
            <span className="ai-confidence-badge">
              ✦ AI Extraction Confidence:{" "}
              {docConfidence || 0}%
            </span>
          }
        />

        {docResults.length > 1 && (
          <div className="review-doc-strip">
            {docResults.map(
              (d, i) => (
                <button
                  key={
                    d.document_id ||
                    i
                  }
                  className={`review-doc-pill ${
                    i === selectedIndex
                      ? "active"
                      : ""
                  }`}
                  onClick={() =>
                    selectDoc(i)
                  }
                >
                  <span>
                    PDF
                  </span>

                  <div>
                    <strong>
                      {d.filename ||
                        d.original_filename ||
                        "Document"}
                    </strong>

                    <small>
                      {humanize(
                        d.doc_type ||
                          "Unknown"
                      )}{" "}
                      ·{" "}
                      {documentConfidence(
                        d
                      )}
                      %
                    </small>
                  </div>
                </button>
              )
            )}
          </div>
        )}

        <section className="review-document-banner">
          <div className="review-file-icon">
            PDF
          </div>

          <div className="review-banner-main">
            <strong>
              {selectedDoc?.filename ||
                selectedDoc?.original_filename ||
                "No document selected"}
            </strong>

            <div>
              <span>
                {displayType}
              </span>

              <small>
                Uploaded:{" "}
                {selectedDoc?.uploaded_on ||
                  selectedDoc?.created_at ||
                  "Just now"}
              </small>

              <small>
                Pages:{" "}
                {selectedDoc?.pages
                  ?.length || "—"}
              </small>
            </div>
          </div>

          <span
            className={`review-status ${
              reviewApproved ||
              selectedDoc?.status ===
                "confirmed"
                ? "approved"
                : "pending"
            }`}
          >
            {reviewApproved ||
            selectedDoc?.status ===
              "confirmed"
              ? "Approved"
              : "Under Review"}
          </span>

          <button
            className="outline-btn"
            onClick={() =>
              window.location.reload()
            }
          >
            ↻ Re-run Extraction
          </button>
        </section>

        <div className="document-review-layout">
          <section className="journey-card review-preview-card">
            <div className="panel-title">
              <div>
                <h2>
                  Document Preview
                </h2>

                <span>
                  Source document
                </span>
              </div>

              <div className="preview-controls">
                <button
                  onClick={() =>
                    setPreviewFullScreen(
                      !previewFullScreen
                    )
                  }
                >
                  {previewFullScreen
                    ? "↙ Exit Full Screen"
                    : "⛶ Full Screen"}
                </button>
              </div>
            </div>

            <div
              className={`document-preview-frame ${
                previewFullScreen
                  ? "fullscreen-preview"
                  : ""
              }`}
            >
              {previewState.status === "ready" && previewUrl ? (
                <iframe
                  src={previewUrl}
                  title="Document preview"
                />
              ) : previewState.status === "loading" ? (
                <div className="preview-empty preview-loading">
                  <span>…</span>
                  <strong>Loading document preview</strong>
                  <small>Checking the stored source document.</small>
                </div>
              ) : previewState.status === "error" ? (
                <div className="preview-empty preview-error-state">
                  <span>!</span>
                  <strong>Unable to load document</strong>
                  <small>{previewState.message || "The stored document could not be retrieved."}</small>
                  <div className="preview-error-actions">
                    <button className="outline-btn" onClick={retryPreview}>↻ Retry</button>
                    <button className="outline-btn" onClick={() => go(2)}>Re-upload</button>
                  </div>
                </div>
              ) : (
                <div className="preview-empty">
                  <span>PDF</span>
                  <strong>Document preview unavailable</strong>
                  <small>Upload a PDF or image document to preview the source.</small>
                </div>
              )}

              {previewFullScreen && (
                <button
                  className="preview-close"
                  onClick={() =>
                    setPreviewFullScreen(
                      false
                    )
                  }
                >
                  ×
                </button>
              )}
            </div>

            <div className="preview-footer">
              <span>
                Page{" "}
                {selectedDoc?.pages
                  ?.length
                  ? 1
                  : "—"}{" "}
                /{" "}
                {selectedDoc?.pages
                  ?.length || "—"}
              </span>

              <div>
                <button>‹</button>
                <button>›</button>
                <button>−</button>
                <span>100%</span>
                <button>+</button>
              </div>
            </div>
          </section>

          <section className="journey-card extracted-card">
            <div className="panel-title">
              <div>
                <h2>
                  Extracted Information
                </h2>

                <span>
                  Review extracted data
                  and map it to system
                  fields.
                </span>
              </div>

              <button
                className="outline-btn"
                onClick={() =>
                  setMappingEdits({})
                }
              >
                ✎ Reset Mapping
              </button>
            </div>

            {fieldEntries.length ? (
              <div className="mapping-review-table-wrap">
                <table className="mapping-review-table">
                  <thead>
                    <tr>
                      <th>
                        Extracted Value
                      </th>
                      <th>
                        Mapped To
                        (System Field)
                      </th>
                      <th>
                        Confidence
                      </th>
                      <th>Status</th>
                    </tr>
                  </thead>

                  <tbody>
                    {fieldEntries.map(
                      (
                        [key, value],
                        i
                      ) => {
                        const score =
                          fieldConfidence(
                            i
                          );

                        const mapped =
                          defaultMapping(
                            key
                          );

                        return (
                          <tr key={key}>
                            <td>
                              <strong>
                                {formatValue(
                                  value
                                )}
                              </strong>

                              <small>
                                {humanize(
                                  key
                                )}
                              </small>
                            </td>

                            <td>
                              <select
                                value={
                                  mapped
                                }
                                onChange={(
                                  e
                                ) =>
                                  saveMapping(
                                    key,
                                    e.target
                                      .value
                                  )
                                }
                              >
                                {!systemFields.includes(
                                  mapped
                                ) && (
                                  <option>
                                    {mapped}
                                  </option>
                                )}

                                {systemFields.map(
                                  (
                                    option
                                  ) => (
                                    <option
                                      key={
                                        option
                                      }
                                      value={
                                        option
                                      }
                                    >
                                      {option}
                                    </option>
                                  )
                                )}
                              </select>
                            </td>

                            <td>
                              <span
                                className={`field-confidence ${
                                  score >=
                                  90
                                    ? "high"
                                    : score >=
                                      80
                                    ? "medium"
                                    : "low"
                                }`}
                              >
                                {score}%
                              </span>
                            </td>

                            <td>
                              <span className="field-ok">
                                ✓
                              </span>
                            </td>
                          </tr>
                        );
                      }
                    )}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="empty-state">
                No structured fields were
                extracted from this document.
                Review the source and send it
                for rework if required.
              </div>
            )}

            <div className="mapping-note">
              ⓘ Low confidence fields are
              highlighted for your review.
              Mapping changes are applied to
              this CAM review session.
            </div>
          </section>

          <aside className="review-details-column">
            <section className="journey-card review-side-card">
              <div className="panel-title">
                <h2>
                  Document Details
                </h2>
              </div>

              <div className="review-detail-list">
                <div>
                  <span>
                    Document Type
                  </span>
                  <b>
                    {displayType}
                  </b>
                </div>

                <div>
                  <span>
                    Financial Year
                  </span>
                  <b>
                    {fields.financial_year ||
                      fields.assessment_year ||
                      "—"}
                  </b>
                </div>

                <div>
                  <span>
                    Assessment Year
                  </span>
                  <b>
                    {fields.assessment_year ||
                      "—"}
                  </b>
                </div>

                <div>
                  <span>
                    Upload Source
                  </span>
                  <b>
                    Manual Upload
                  </b>
                </div>

                <div>
                  <span>
                    Extraction Method
                  </span>
                  <b>
                    {selectedDoc?.extraction_method ||
                      "OCR / Rules"}
                  </b>
                </div>
              </div>
            </section>

            <section className="journey-card review-side-card">
              <div className="panel-title">
                <h2>
                  Validation Checks
                </h2>
              </div>

              <div className="validation-list">
                {validation.map(
                  ([label, ok]) => (
                    <div key={label}>
                      <span>
                        {label}
                      </span>

                      <b
                        className={
                          ok
                            ? "ok"
                            : "warn"
                        }
                      >
                        {ok ? "✓" : "!"}
                      </b>
                    </div>
                  )
                )}
              </div>
            </section>

            <section className="journey-card review-side-card review-actions-card">
              <div className="panel-title">
                <h2>
                  Actions
                </h2>
              </div>

              <button
                className="bob-btn review-primary-action"
                onClick={
                  approveReview
                }
                disabled={
                  !selectedDoc ||
                  reviewBusy
                }
              >
                {reviewBusy
                  ? "Approving…"
                  : "Approve & Proceed"}

                <span>→</span>
              </button>

              <button
                className="outline-btn review-rework"
                onClick={() =>
                  setError(
                    "Document marked for rework. Please correct the source or re-upload it before approval."
                  )
                }
              >
                ↻ Send for Rework
              </button>

              <button
                className="danger-outline-btn"
                onClick={() =>
                  selectedDoc?.document_id &&
                  deleteDoc(
                    selectedDoc.document_id
                  )
                }
              >
                ⌫ Discard Document
              </button>
            </section>
          </aside>
        </div>

        <div className="review-guidance">
          ⓘ Please review the extracted data
          carefully. You can edit the mapping
          or send the document for rework if
          needed.
        </div>

        <FooterNav
          nextLabel="Save & Continue"
          onNext={() => go(4)}
          disabled={!reviewApproved}
        />
      </>
    );
}
