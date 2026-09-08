import { configureStore } from "@reduxjs/toolkit";
import authReducer from "./authSlice";
import camReducer from "./camSlice";
export const store = configureStore({ reducer: { auth: authReducer, cam: camReducer } });
