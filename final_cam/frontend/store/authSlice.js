import { createSlice } from "@reduxjs/toolkit";
const authSlice=createSlice({name:"auth",initialState:{user:null},reducers:{setUser:(s,a)=>{s.user=a.payload},clearUser:s=>{s.user=null}}});
export const {setUser,clearUser}=authSlice.actions; export default authSlice.reducer;
