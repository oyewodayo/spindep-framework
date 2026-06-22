import React from "react";
import { T, NAV_ITEMS, NAV_GROUPS } from "../../constants";
import { Icon } from "../ui/Icon";
import type { NavSection } from "../../types";

interface SidebarProps {
  activePage: NavSection;
  onNavigate: (page: NavSection) => void;
  apiOnline: boolean;
  resultsReady: boolean;
  totalPairs: number;
  significantPairs: number;
  historyCount: number;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activePage,
  onNavigate,
  apiOnline,
  resultsReady,
  totalPairs,
  significantPairs,
  historyCount,
}) => (
  <div className="sidebar">
    {/* Wordmark */}
    <div
      style={{
        padding: "14px 14px 12px",
        borderBottom: `1px solid ${T.border}`,
        display: "flex",
        alignItems: "center",
        gap: 10,
      }}
    >
      <div
        style={{
          width: 28,
          height: 28,
          borderRadius: 7,
          background: `linear-gradient(135deg, ${T.blue}, #1a6ac8)`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "#fff",
          flexShrink: 0,
        }}
      >
        <Icon name="atom" size={15} />
      </div>
      <div>
        <div
          style={{
            fontFamily: T.mono,
            fontWeight: 700,
            color: T.textHi,
            fontSize: 13,
            letterSpacing: ".06em",
          }}
        >
          SPINDEP
        </div>
        <div
          style={{
            fontSize: 9,
            color: T.muted,
            letterSpacing: ".08em",
            marginTop: -1,
          }}
        >
          CPT ANALYSIS PLATFORM
        </div>
      </div>
    </div>

    {/* Navigation */}
    <div style={{ flex: 1, overflowY: "auto", padding: "8px 0" }}>
      {NAV_GROUPS.map(group => (
        <div key={group}>
          <div className="nav-group">{group}</div>
          {NAV_ITEMS.filter(n => n.group === group).map(item => {
            const badge =
              item.id === "batch"   && resultsReady  ? totalPairs
              : item.id === "history" && historyCount > 0 ? historyCount
              : null;
            return (
              <button
                key={item.id}
                className={`nav-item${activePage === item.id ? " active" : ""}`}
                onClick={() => onNavigate(item.id)}
              >
                <Icon name={item.icon as any} size={14} />
                {item.label}
                {badge != null && (
                  <span className="badge">{badge}</span>
                )}
              </button>
            );
          })}
        </div>
      ))}
    </div>

    {/* Footer */}
    <div
      style={{
        padding: "12px 14px",
        borderTop: `1px solid ${T.border}`,
        fontSize: 11,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 6,
          marginBottom: 8,
        }}
      >
        <span style={{ color: apiOnline ? T.teal : T.red }}>
          <Icon name={apiOnline ? "wifi" : "wifiOff"} size={11} />
        </span>
        <span style={{ color: apiOnline ? T.teal : T.red, fontSize: 10 }}>
          API {apiOnline ? "online" : "offline"}
        </span>
      </div>

      {resultsReady ? (
        <>
          <div style={{ color: T.teal, fontWeight: 600, marginBottom: 4 }}>
            <Icon name="check" size={11} /> Analysis complete
          </div>
          <div style={{ color: T.textDim }}>
            {totalPairs} pairs · {significantPairs} significant
          </div>
        </>
      ) : (
        <div style={{ color: T.muted }}>No active analysis</div>
      )}
      <div style={{ marginTop: 8, fontSize: 10, color: T.dim }}>
        spin CLI v2.0 · Python 3.9+
      </div>
    </div>
  </div>
);