"use client";

import { useMemo, useState } from "react";

const RECENT_BORROWERS = [
  { name: "Apex Manufacturing Pvt. Ltd.", cin: "Available", status: "Active" },
  { name: "ABC Textiles Pvt. Ltd.", cin: "Available", status: "Active" },
  { name: "Sunrise Engineering Pvt. Ltd.", cin: "Available", status: "Active" },
  { name: "Global Traders Pvt. Ltd.", cin: "Not available", status: "Prospect" },
  { name: "Metro Infrastructure Ltd.", cin: "Available", status: "Active" },
];

export default function Step1(ctx) {
  const {
    camInfo,
    mcaCin,
    setMcaCin,
    startCam,
    PageHeader,
    Icon,
  } = ctx;

  // IMPORTANT: search, selected-existing borrower and create-new form are
  // independent UI state. They no longer share Redux `company` while typing.
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedBorrower, setSelectedBorrower] = useState(null);
  const [newBorrower, setNewBorrower] = useState({
    companyName: "",
    constitution: "",
    gstin: "",
    state: "",
    industry: "",
    rm: "",
  });

  const filteredBorrowers = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return RECENT_BORROWERS;
    return RECENT_BORROWERS.filter((borrower) =>
      `${borrower.name} ${borrower.cin} ${borrower.status}`.toLowerCase().includes(q)
    );
  }, [searchQuery]);

  const updateNewBorrower = (key, value) =>
    setNewBorrower((current) => ({ ...current, [key]: value }));

  const continueExisting = async () => {
    if (!selectedBorrower?.name) return;
    await startCam(selectedBorrower.name);
  };

  const saveNewBorrower = async () => {
    await startCam(newBorrower.companyName);
  };

  return (
    <>
      <PageHeader
        number={1}
        title="Borrower Details"
        subtitle="Search an existing borrower or capture a new borrower profile to begin the credit appraisal."
      />

      <div className="two-pane borrower-step-grid">
        <section className="journey-card borrower-search-card">
          <div className="card-title">
            <Icon name="search" />
            <div>
              <h2>Search Existing Borrower</h2>
              <p>Search by Company Name, CIN, GSTIN or Loan ID</p>
            </div>
          </div>

          <div className="search-row">
            <input
              placeholder="Search by Company Name, CIN, GSTIN, or Loan ID"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              aria-label="Search existing borrower"
            />
            <button className="outline-btn" type="button">⌕ Filters</button>
          </div>

          <h3 className="sub-title">Recent Borrowers</h3>

          <div className="borrower-list">
            {filteredBorrowers.map((borrower) => {
              const selected = selectedBorrower?.name === borrower.name;
              return (
                <button
                  className={`borrower-item ${selected ? "selected" : ""}`}
                  key={borrower.name}
                  type="button"
                  onClick={() => setSelectedBorrower(borrower)}
                  aria-pressed={selected}
                >
                  <span className="borrower-icon">▥</span>
                  <div>
                    <strong>{borrower.name}</strong>
                    <small>CIN: {borrower.cin}</small>
                  </div>
                  <b className={borrower.status === "Prospect" ? "prospect" : ""}>
                    {borrower.status}
                  </b>
                  <span>{selected ? "✓" : "›"}</span>
                </button>
              );
            })}
          </div>

          {selectedBorrower && (
            <div className="selected-borrower-panel">
              <div>
                <span>Selected existing borrower</span>
                <strong>{selectedBorrower.name}</strong>
                <small>This selection does not modify the Create New Borrower form.</small>
              </div>
              <button className="bob-btn" type="button" onClick={continueExisting}>
                Continue →
              </button>
            </div>
          )}
        </section>

        <section className="journey-card create-borrower-card">
          <div className="card-title">
            <Icon name="users" />
            <div>
              <h2>Create New Borrower</h2>
              <p>Add a new borrower to initiate CAM process</p>
            </div>
          </div>

          <div className="form-grid">
            <label>
              Company / Borrower Name <em>*</em>
              <input
                value={newBorrower.companyName}
                onChange={(e) => updateNewBorrower("companyName", e.target.value)}
                placeholder="Enter Company or Borrower Name"
              />
            </label>

            <label>
              Constitution / Entity Type <em>*</em>
              <select
                value={newBorrower.constitution}
                onChange={(e) => updateNewBorrower("constitution", e.target.value)}
              >
                <option value="">Select Entity Type</option>
                <option>Private Limited</option>
                <option>Public Limited</option>
                <option>LLP</option>
                <option>Partnership</option>
              </select>
            </label>

            <label>
              CIN (If applicable)
              <input
                value={mcaCin}
                onChange={(e) => setMcaCin(e.target.value)}
                placeholder="Enter CIN Number"
              />
            </label>

            <label>
              GSTIN (If applicable)
              <input
                value={newBorrower.gstin}
                onChange={(e) => updateNewBorrower("gstin", e.target.value)}
                placeholder="Enter GSTIN"
              />
            </label>

            <label>
              Registered Office State <em>*</em>
              <select
                value={newBorrower.state}
                onChange={(e) => updateNewBorrower("state", e.target.value)}
              >
                <option value="">Select State</option>
                <option>Maharashtra</option>
                <option>Delhi</option>
                <option>Karnataka</option>
                <option>Gujarat</option>
              </select>
            </label>

            <label>
              Primary Industry / Business Type <em>*</em>
              <select
                value={newBorrower.industry}
                onChange={(e) => updateNewBorrower("industry", e.target.value)}
              >
                <option value="">Select Industry</option>
                <option>Manufacturing</option>
                <option>Trading</option>
                <option>Services</option>
                <option>Infrastructure</option>
              </select>
            </label>

            <label>
              Relationship Manager (RM) <em>*</em>
              <select
                value={newBorrower.rm}
                onChange={(e) => updateNewBorrower("rm", e.target.value)}
              >
                <option value="">Select RM</option>
                <option>RM - Mumbai</option>
                <option>RM - Delhi</option>
                <option>RM - Bengaluru</option>
              </select>
            </label>
          </div>

          <p className="mandatory-note">ⓘ All fields marked with * are mandatory</p>

          <button
            className="bob-btn full"
            type="button"
            onClick={saveNewBorrower}
            disabled={!newBorrower.companyName.trim()}
          >
            Save & Continue →
          </button>

          {camInfo && (
            <div className="success-strip">CAM session created successfully.</div>
          )}
        </section>
      </div>
    </>
  );
}
