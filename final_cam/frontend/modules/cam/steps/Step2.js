export default function Step2(ctx) {
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

    return (
      <>
        <PageHeader
          number={2}
          title="Document Upload"
          subtitle={`Supporting documents for ${companyName}. Upload files for automatic classification, OCR and extraction.`}
          action={
            <button
              className="outline-btn"
              onClick={() => go(13)}
            >
              Policy Repository
            </button>
          }
        />

        <section className="borrower-banner">
          <div className="borrower-banner-icon">
            ▥
          </div>

          <div className="borrower-banner-main">
            <strong>
              {companyName || "Borrower"}
            </strong>

            <span>
              Active CAM borrower
            </span>

            <small>
              CIN:{" "}
              {mcaData?.cin ||
                "Not available"}{" "}
              | GSTIN: Not available |
              RM: Credit Officer
            </small>
          </div>

          <button
            className="bob-btn"
            onClick={() => go(3)}
            disabled={!docResults.length}
          >
            Proceed to Review & Mapping →
          </button>
        </section>

        <div className="doc-center-layout">
          <section className="journey-card doc-main-card">
            <div className="doc-tabs">
              <button className="doc-tab active">
                ⇧ &nbsp; Upload Documents
              </button>

              <button className="doc-tab">
                ◷ &nbsp; Upload History
              </button>
            </div>

            <div className="doc-summary-stats">
              <Stat
                label="Total Documents"
                value={docResults.length}
              />

              <Stat
                label="Processed"
                value={
                  docResults.filter(
                    (d) =>
                      documentUiStatus(
                        d
                      ) ===
                      "Auto Approved"
                  ).length
                }
              />

              <Stat
                label="Under Review"
                value={
                  docResults.filter(
                    (d) =>
                      documentUiStatus(
                        d
                      ) ===
                      "Under Review"
                  ).length
                }
              />

              <Stat
                label="New View"
                value={
                  docResults.filter(
                    (d) =>
                      documentUiStatus(
                        d
                      ) ===
                      "New View"
                  ).length
                }
              />

              <Stat
                label="Failed"
                value={
                  docResults.filter(
                    (d) =>
                      documentUiStatus(
                        d
                      ) === "Failed"
                  ).length
                }
              />
            </div>

            <div className="doc-toolbar">
              <div className="doc-search">
                <Icon name="search" />
                <input placeholder="Search documents..." />
              </div>

              <button className="outline-btn">
                ⌕ Filters
              </button>

              <select className="doc-filter">
                <option>
                  All Status
                </option>
                <option>
                  Auto Approved
                </option>
                <option>
                  New View
                </option>
                <option>
                  Under Review
                </option>
                <option>
                  Failed
                </option>
              </select>

              <button
                className="outline-btn"
                title="Refresh"
              >
                ↻
              </button>
            </div>

            <div className="upload-panel">
              <div className="upload-big">
                ↑
              </div>

              <div>
                <h2>
                  Upload Borrower Documents
                </h2>

                <p>
                  Upload audited financials,
                  ITR, GST, bank statements,
                  KYC and collateral
                  documents.
                </p>

                <small>
                  PDF, PNG, JPG, TIFF and
                  scanned documents supported
                </small>
              </div>

              <label className="bob-outline-upload">
                Browse Files

                <input
                  type="file"
                  multiple
                  accept={ACCEPT_DOCS}
                  onChange={(e) =>
                    setDocFiles([
                      ...e.target.files,
                    ])
                  }
                />
              </label>
            </div>

            {docFiles.length > 0 && (
              <div className="file-pills">
                {docFiles.map((f) => (
                  <span key={f.name}>
                    {f.name}
                  </span>
                ))}
              </div>
            )}

            <div className="upload-message">
              {docMsg}
            </div>

            <div className="doc-actions">
              <button
                className="bob-btn"
                onClick={uploadDocs}
                disabled={!sessionId}
              >
                Upload & Process Documents →
              </button>
            </div>

            <div className="panel-title doc-list-title">
              <h2>
                Processed Documents
              </h2>

              <span>
                {docResults.length} files
              </span>
            </div>

            {docResults.length ? (
              <div className="journey-table-wrap doc-table-wrap">
                <table className="journey-table doc-table">
                  <thead>
                    <tr>
                      <th>Sr. No.</th>
                      <th>
                        Document Name
                      </th>
                      <th>
                        Document Type
                      </th>
                      <th>
                        Confidence Score
                      </th>
                      <th>
                        Uploaded On
                      </th>
                      <th>Status</th>
                      <th>Actions</th>
                    </tr>
                  </thead>

                  <tbody>
                    {docResults.map(
                      (d, i) => {
                        const score =
                          documentConfidence(
                            d
                          );

                        const st =
                          documentUiStatus(
                            d
                          );

                        return (
                          <tr
                            key={
                              d.document_id ||
                              i
                            }
                          >
                            <td>
                              {i + 1}
                            </td>

                            <td>
                              <strong className="doc-name">
                                ▧{" "}
                                {d.filename ||
                                  d.file_name ||
                                  d.original_filename ||
                                  "Document"}
                              </strong>
                            </td>

                            <td>
                              <span className="doc-type-chip">
                                {humanize(
                                  d.doc_type ||
                                    d.document_type ||
                                    "Unknown"
                                )}
                              </span>
                            </td>

                            <td>
                              <ConfidenceScore
                                value={score}
                              />
                            </td>

                            <td>
                              {d.uploaded_on ||
                                d.created_at ||
                                "Just now"}
                            </td>

                            <td>
                              <span
                                className={`status-chip ${
                                  st ===
                                  "Auto Approved"
                                    ? "success"
                                    : st ===
                                      "Failed"
                                    ? "failed"
                                    : st ===
                                      "New View"
                                    ? "new-view"
                                    : "under-review"
                                }`}
                              >
                                {st}
                              </span>
                            </td>

                            <td>
                              <div className="doc-action-buttons">
                                <button
                                  title="View document"
                                  onClick={() =>
                                    setJourneyStep(
                                      3
                                    )
                                  }
                                >
                                  ◉
                                </button>

                                <button
                                  title="Delete document"
                                  className="delete-doc-btn"
                                  onClick={() =>
                                    deleteDoc(
                                      d.document_id
                                    )
                                  }
                                >
                                  ⌫
                                </button>

                                <button title="More">
                                  ⋮
                                </button>
                              </div>
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
                No documents uploaded yet.
              </div>
            )}

            {docResults.length > 0 && (
              <div className="doc-pagination">
                <span>
                  Showing 1 to{" "}
                  {docResults.length}{" "}
                  documents
                </span>

                <div>
                  <button>‹</button>
                  <button className="current">
                    1
                  </button>
                  <button>›</button>
                </div>

                <select>
                  <option>
                    10 / page
                  </option>
                </select>
              </div>
            )}
          </section>

          <aside className="doc-side-column">
            <section className="journey-card doc-side-card">
              <div className="panel-title">
                <h2>
                  Document Summary
                </h2>
              </div>

              <div className="doc-donut-wrap">
                <div className="doc-donut">
                  <strong>
                    {docResults.length}
                  </strong>
                  <span>Total</span>
                </div>

                <div className="doc-legend">
                  <Legend
                    color="green"
                    label="Auto Approved"
                    value={
                      docResults.filter(
                        (d) =>
                          documentUiStatus(
                            d
                          ) ===
                          "Auto Approved"
                      ).length
                    }
                  />

                  <Legend
                    color="orange"
                    label="New View"
                    value={
                      docResults.filter(
                        (d) =>
                          documentUiStatus(
                            d
                          ) ===
                          "New View"
                      ).length
                    }
                  />

                  <Legend
                    color="blue"
                    label="Under Review"
                    value={
                      docResults.filter(
                        (d) =>
                          documentUiStatus(
                            d
                          ) ===
                          "Under Review"
                      ).length
                    }
                  />

                  <Legend
                    color="red"
                    label="Failed"
                    value={
                      docResults.filter(
                        (d) =>
                          documentUiStatus(
                            d
                          ) === "Failed"
                      ).length
                    }
                  />
                </div>
              </div>
            </section>

            <section className="journey-card doc-side-card">
              <div className="panel-title">
                <h2>
                  Confidence Score Overview
                </h2>
              </div>

              <div className="confidence-overview">
                <div>
                  <span>
                    High ≥90%
                  </span>
                  <strong>
                    {
                      docResults.filter(
                        (d) =>
                          documentConfidence(
                            d
                          ) >= 90
                      ).length
                    }
                  </strong>
                </div>

                <div>
                  <span>
                    Medium 70–89%
                  </span>
                  <strong>
                    {
                      docResults.filter(
                        (d) => {
                          const x =
                            documentConfidence(
                              d
                            );

                          return (
                            x >= 70 &&
                            x < 90
                          );
                        }
                      ).length
                    }
                  </strong>
                </div>

                <div>
                  <span>
                    Low &lt;70%
                  </span>
                  <strong>
                    {
                      docResults.filter(
                        (d) =>
                          documentConfidence(
                            d
                          ) < 70
                      ).length
                    }
                  </strong>
                </div>
              </div>
            </section>

            <section className="journey-card doc-side-card">
              <div className="panel-title">
                <h2>
                  Recent Activity
                </h2>

                <span>
                  View All
                </span>
              </div>

              {docResults
                .slice(-5)
                .reverse()
                .map((d, i) => {
                  const status =
                    documentUiStatus(
                      d
                    );

                  return (
                    <div
                      className="recent-doc"
                      key={
                        d.document_id ||
                        i
                      }
                    >
                      <span
                        className={`recent-icon ${
                          status ===
                          "Failed"
                            ? "bad"
                            : status ===
                              "New View"
                            ? "warn"
                            : "good"
                        }`}
                      >
                        {status ===
                        "Failed"
                          ? "!"
                          : status ===
                            "New View"
                          ? "◷"
                          : "✓"}
                      </span>

                      <div>
                        <strong>
                          {d.filename ||
                            d.file_name ||
                            d.original_filename ||
                            "Document"}
                        </strong>

                        <small>
                          {status} with{" "}
                          {documentConfidence(
                            d
                          )}
                          % confidence
                        </small>
                      </div>
                    </div>
                  );
                })}

              <button
                className="go-upload-btn"
                onClick={() =>
                  document
                    .querySelector(
                      ".bob-outline-upload input"
                    )
                    ?.click()
                }
              >
                ⇧ &nbsp; Go to Upload
              </button>
            </section>
          </aside>
        </div>

        <FooterNav
          nextLabel="Review & Data Mapping"
          disabled={!docResults.length}
        />
      </>
    );
}
