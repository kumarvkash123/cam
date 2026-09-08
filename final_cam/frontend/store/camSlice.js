import { createSlice } from "@reduxjs/toolkit";

const initialState = {
  journeyStep: 1, company: "", sessionId: null, camInfo: null, chat: [],
  policyResults: [], policyIndexed: false, policyAnalysisComplete: false, policyMsg: "", policyChat: [],
  docResults: [], docMsg: "", documentChat: [],
  reviewApproved: false, mca: null, mcaMsg: "", mcaStatus: "not_fetched",
  analysis: null, analysisStarted: false, generated: null, error: "", step9Subsection: "credit", step10Subsection: "collateral"
};

const camSlice = createSlice({
  name: "cam", initialState, reducers: {
    setCamField: (state, action) => { const { key, value } = action.payload; state[key] = value; },
    resetCam: () => initialState,
  }
});
export const { setCamField, resetCam } = camSlice.actions;
export default camSlice.reducer;
