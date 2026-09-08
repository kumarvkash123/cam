"use client";

import { Icon, BOBMark } from "../ui";

const menuItems = [
  ["Dashboard", "home"],
  ["CAM Proposals", "file"],
  ["Borrowers", "users"],
  ["Documents", "file"],
  ["MCA & External Data", "building"],
  ["Policy & Compliance", "shield"],
  ["AI Assistant", "spark"],
  ["Reports & Analytics", "chart"],
  ["Notifications", "bell"],
  ["Audit Trail", "file"],
  ["User Management", "users"],
  ["Settings", "settings"],
];

function Sidebar({ collapsed, setCollapsed, onNavigate, active }) {
  return (
    <aside className={`app-sidebar ${collapsed ? "collapsed" : ""}`}>
      <div className="sidebar-brand">
        <BOBMark small />

        <div className="sidebar-brand-copy">
          <strong>Bank of Baroda</strong>
          <span>CAM AI Platform</span>
        </div>
      </div>

      <button
        className="sidebar-toggle"
        onClick={() => setCollapsed(!collapsed)}
        title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
      >
        <Icon name="menu" />
      </button>

      <nav>
        {menuItems.map(([label, icon]) => (
          <button
            key={label}
            className={active === label ? "active" : ""}
            onClick={() => onNavigate(label)}
            title={collapsed ? label : ""}
          >
            <Icon name={icon} />

            <span>{label}</span>

            {label === "Notifications" && (
              <b className="nav-count">3</b>
            )}

            {["CAM Proposals", "Borrowers"].includes(label) &&
              !collapsed && <small>›</small>}
          </button>
        ))}
      </nav>

      <div className="sidebar-bottom">
        <button
          onClick={() => onNavigate("logout")}
          title={collapsed ? "Logout" : ""}
        >
          <Icon name="logout" />
          <span>Logout</span>
        </button>
      </div>
    </aside>
  );
}

export default Sidebar;