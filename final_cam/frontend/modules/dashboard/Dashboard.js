"use client";
import { useEffect, useState } from "react";
import { Icon } from "../../shared/ui";
import Sidebar from "../../shared/layout/Sidebar";
import { KPI, Panel, Legend, Status, Activity, InfoLine } from "../../shared/dashboard/widgets";

const API = (process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "");
function Dashboard({ user, onNewCam, onLogout }) {
  const [collapsed, setCollapsed] = useState(true);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [active, setActive] = useState("Dashboard");

  async function load() {
    try { const r=await fetch(`${API}/api/dashboard`); const d=await r.json(); if(r.ok) setData(d); }
    catch {} finally { setLoading(false); }
  }
  useEffect(()=>{load(); const t=setInterval(load,30000); return ()=>clearInterval(t)},[]);

  function navigate(label) {
    if(label === "logout") return onLogout();
    if(label === "CAM Proposals") return onNewCam();
    setActive(label);
  }

  const m = data?.metrics || {};
  const recent = data?.recent_proposals || [];
  const types = Object.entries(data?.loan_type_distribution || {});
  const total = Math.max(Number(m.total_proposals||0), 1);
  const pct = n => `${Math.round((Number(n||0)/total)*100)}%`;

  return <div className={`app-shell ${collapsed ? "sidebar-collapsed" : ""}`}>
    <Sidebar collapsed={collapsed} setCollapsed={setCollapsed} onNavigate={navigate} active={active}/>
    <div className="app-main">
      <header className="topbar"><button className="mobile-menu" onClick={()=>setCollapsed(!collapsed)}><Icon name="menu"/></button><div className="top-title"><strong>CAM AI Platform</strong><span>Credit Appraisal Management</span></div><div className="global-search"><Icon name="search"/><input placeholder="Search borrower, proposal, CAM ID, CIN, customer..."/></div><div className="top-actions"><button title="Notifications"><Icon name="bell"/><b>3</b></button><button title="Help">?</button><div className="profile"><span>{(user?.name||"CO").split(" ").map(x=>x[0]).slice(0,2).join("")}</span><div><strong>{user?.name||"Credit Officer"}</strong><small>{user?.role||"Credit Officer"}</small></div><i>⌄</i></div></div></header>
      <main className="dashboard-main">
        <div className="dashboard-heading"><div><div className="dash-eyebrow">OVERVIEW</div><h1>Dashboard</h1><p>Central view of CAM activities, applications, documents, compliance and AI insights.</p></div><button className="new-cam-btn" onClick={onNewCam}>＋ Start New CAM</button></div>
        <section className="welcome-banner"><div><strong>Welcome back, {user?.name?.split(" ")[0] || "Credit Officer"}!</strong><span>AI-powered Credit Appraisal & CAM Platform</span><small>Smarter Insights &nbsp; | &nbsp; Faster Analysis &nbsp; | &nbsp; Stronger Risk Decisions</small></div><div className="welcome-art"><span></span><span></span><span></span></div></section>
        <section className="kpi-grid">
          <KPI icon="file" label="Total CAM Proposals" value={loading?"—":m.total_proposals??0} trend="Live from CAM database" />
          <KPI icon="clock" label="In Progress" value={loading?"—":m.in_progress??0} trend="Applications currently open" />
          <KPI icon="shield" label="Under Review" value={loading?"—":m.under_review??0} trend="Awaiting review" />
          <KPI icon="spark" label="Completed" value={loading?"—":m.completed??0} trend="Generated / completed" />
          <KPI icon="upload" label="Documents Processed" value={loading?"—":m.documents_processed??0} trend={`${m.documents_review||0} need review`} />
        </section>
        <section className="dashboard-grid dashboard-grid-top">
          <Panel title="CAM Pipeline" className="pipeline-panel"><div className="donut-wrap"><div className="donut" style={{"--p1":pct(m.completed),"--p2":`${Number(pct(m.completed).replace('%',''))+Number(pct(m.in_progress).replace('%',''))}%`}}><strong>{m.total_proposals??0}</strong><span>Total</span></div><div className="legend"><Legend color="green" label="Completed" value={m.completed||0}/><Legend color="blue" label="In Progress" value={m.in_progress||0}/><Legend color="orange" label="Under Review" value={m.under_review||0}/><Legend color="gray" label="Pending / Other" value={Math.max(0,(m.total_proposals||0)-(m.completed||0)-(m.in_progress||0)-(m.under_review||0))}/></div></div></Panel>
          <Panel title="Loan Type Distribution"><div className="bar-chart">{(types.length?types:[["No data",0]]).slice(0,6).map(([name,count])=><div className="bar-row" key={name}><span>{name}</span><div><i style={{width:`${Math.max(3,(Number(count)/total)*100)}%`}}></i></div><b>{count}</b></div>)}</div></Panel>
          <Panel title="Risk & Compliance Overview"><div className="risk-empty"><div className="risk-ring"><strong>—</strong><span>Risk score</span></div><div><b>Risk engine</b><p>Risk rating becomes available after CAM analysis is completed.</p><div className="mini-status"><span>Policy checks</span><b>Available in CAM</b></div></div></div></Panel>
        </section>
        <section className="dashboard-grid dashboard-grid-bottom">
          <Panel title="Recent CAM Proposals" wide action={<button onClick={()=>setActive("CAM Proposals")}>View All <Icon name="arrow"/></button>}><div className="table-scroll"><table><thead><tr><th>CAM ID</th><th>Company / Borrower</th><th>Loan Type</th><th>Status</th><th>Created On</th><th></th></tr></thead><tbody>{recent.length?recent.map((r,i)=><tr key={r.application_id||i}><td><strong>{r.cam_id}</strong></td><td>{r.company}</td><td>{r.loan_type}</td><td><Status value={r.status}/></td><td>{r.created_at?new Date(r.created_at).toLocaleDateString("en-IN"):"—"}</td><td>•••</td></tr>):<tr><td colSpan="6" className="empty-table">No CAM proposals yet. Start your first CAM proposal.</td></tr>}</tbody></table></div></Panel>
          <Panel title="Activity Feed" action={<button onClick={()=>setActive("Audit Trail")}>View All <Icon name="arrow"/></button>}><div className="activity-feed"><Activity title="Dashboard ready" detail="CAM platform is ready for your next appraisal."/><Activity title={`${m.documents_processed||0} documents processed`} detail="Live document count from the CAM database."/><Activity title="Policy repository" detail="RAG-based policy checks are available during CAM preparation."/><Activity title="AI Assistant" detail="Source-grounded borrower and policy chat is available."/></div></Panel>
        </section>
        <section className="insight-grid"><Panel title="Document Processing"><InfoLine label="Documents processed" value={m.documents_processed||0}/><InfoLine label="Needs review" value={m.documents_review||0}/><InfoLine label="Active CAM sessions" value={data?.active_sessions||0}/></Panel><Panel title="Policy & Compliance"><InfoLine label="Policy repository" value="RAG enabled" good/><InfoLine label="Source citations" value="Page-level" good/><InfoLine label="Final decision" value="Human controlled"/></Panel><Panel title="AI Platform Capabilities"><div className="capability-list"><span>✦ Document classification & extraction</span><span>✦ MCA / external data enrichment</span><span>✦ Policy RAG & compliance checks</span><span>✦ Financial analysis & stress testing</span><span>✦ Risk analysis & peer benchmarking</span><span>✦ Auto CAM draft generation</span></div></Panel></section>
        <footer className="dashboard-footer"><span>⌕ Secure & Confidential — For Authorized Bank of Baroda Users Only</span><span>© 2026 Bank of Baroda. All rights reserved.</span></footer>
      </main>
    </div>
  </div>;
}


export default Dashboard;