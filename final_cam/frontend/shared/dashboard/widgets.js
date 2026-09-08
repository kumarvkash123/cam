"use client";
import { Icon } from "../ui";
function KPI({icon,label,value,trend}) { return <article className="kpi-card"><div className="kpi-icon"><Icon name={icon}/></div><span>{label}</span><strong>{value}</strong><small>{trend}</small></article>; }
function Panel({title,children,action,wide,className=""}) { return <section className={`dash-panel ${wide?"wide":""} ${className}`}><div className="panel-head"><h2>{title}</h2>{action}</div>{children}</section>; }
function Legend({color,label,value}) { return <div className="legend-row"><i className={`legend-dot ${color}`}></i><span>{label}</span><b>{value}</b></div>; }
function Status({value}) { const v=String(value||"").replace(/_/g," "); return <span className={`table-status ${value}`}>{v.replace(/\b\w/g,c=>c.toUpperCase())}</span>; }
function Activity({title,detail}) { return <div className="activity-item"><i></i><div><strong>{title}</strong><span>{detail}</span></div></div>; }
function InfoLine({label,value,good}) { return <div className="info-line"><span>{label}</span><b className={good?"good":""}>{value}</b></div>; }


export { KPI, Panel, Legend, Status, Activity, InfoLine };