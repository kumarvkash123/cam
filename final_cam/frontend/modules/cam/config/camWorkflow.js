export const CAM_ANALYSIS_FLOW = [
  { id: "loan-summary", section: "1", label: "Loan Summary", step: 5 },
  { id: "borrower-information", section: "2", label: "Borrower Information", step: 6 },
  { id: "business-overview", section: "3", label: "Business Overview", step: 7 },
  { id: "financial-analysis", section: "4", label: "Financial Analysis", step: 8 },
  { id: "credit-history", section: "5", label: "Credit History & Repayment", step: 9, step9Subsection: "credit" },
  { id: "risk-assessment", section: "6A", label: "Risk Assessment", step: 9, step9Subsection: "risk" },
  { id: "collateral", section: "7", label: "Collateral Details", step: 10, step10Subsection: "collateral" },
  { id: "peer-benchmarking", section: "10", label: "Peer Benchmarking", step: 12 },
  { id: "risk-mitigation", section: "6B", label: "Risk Mitigation", step: 9, step9Subsection: "mitigation" },
  { id: "loan-terms", section: "8", label: "Loan Terms & Conditions", step: 10, step10Subsection: "terms" },
  { id: "compliance", section: "9", label: "Regulatory & Compliance", step: 11 },
];

export function analysisFlowItemForState({ journeyStep, step9Subsection, step10Subsection }) {
  if (journeyStep === 9) {
    return CAM_ANALYSIS_FLOW.find(
      (item) => item.step === 9 && item.step9Subsection === (step9Subsection || "credit")
    );
  }
  if (journeyStep === 10) {
    return CAM_ANALYSIS_FLOW.find(
      (item) => item.step === 10 && item.step10Subsection === (step10Subsection || "collateral")
    );
  }
  return CAM_ANALYSIS_FLOW.find((item) => item.step === journeyStep);
}
