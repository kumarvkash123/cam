"use client";

import { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Provider } from "react-redux";
import { store } from "../store";
import { setUser, clearUser } from "../store/authSlice";
import { BOBMark } from "../shared/ui";
import LoginPage from "../modules/auth/LoginPage";
import Dashboard from "../modules/dashboard/Dashboard";
import CAMWorkspace from "../modules/cam/CAMWorkspace";

function Home() {
  const [screen, setScreen] = useState("loading");
  const dispatch = useDispatch();
  const user = useSelector(state => state.auth.user);
  useEffect(() => {
    const goDashboard = () => setScreen("dashboard");
    window.addEventListener("bob-dashboard", goDashboard);
    try {
      const raw = localStorage.getItem("bob_cam_user") || sessionStorage.getItem("bob_cam_user");
      if (raw) { dispatch(setUser(JSON.parse(raw))); setScreen("dashboard"); } else setScreen("login");
    } catch { setScreen("login"); }
    return () => window.removeEventListener("bob-dashboard", goDashboard);
  }, []);
  function logout() { localStorage.removeItem("bob_cam_user"); sessionStorage.removeItem("bob_cam_user"); dispatch(clearUser()); setScreen("login"); }
  if (screen === "loading") return <div className="app-loading"><div className="loading-mark"><BOBMark small/></div><strong>CAM AI Platform</strong><span>Loading secure workspace…</span></div>;
  if (screen === "login") return <LoginPage onLogin={(u)=>{dispatch(setUser(u));setScreen("dashboard")}}/>;
  if (screen === "workspace") return <CAMWorkspace/>;
  return <Dashboard user={user} onNewCam={()=>setScreen("workspace")} onLogout={logout}/>;
}

export default function Page() { return <Provider store={store}><Home/></Provider>; }
