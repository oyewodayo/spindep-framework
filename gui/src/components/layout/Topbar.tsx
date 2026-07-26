import React from "react";
import { T, NAV_ITEMS } from "../../constants";
import { Icon } from "../ui/Icon";
import type { NavSection } from "../../types";

interface TopbarProps {
  activePage: NavSection;
  apiOnline: boolean;
  resultsReady: boolean;
  totalPairs: number;
  significantPairs: number;
  onMenuClick: () => void;
}

export const Topbar: React.FC<TopbarProps> = ({
  activePage,
  apiOnline,
  resultsReady,
  totalPairs,
  significantPairs,
  onMenuClick,
}) => {
  const pageLabel = NAV_ITEMS.find(n => n.id === activePage)?.label ?? "";

  return (
    <div className="topbar">
      <button className="menu-btn" onClick={onMenuClick} aria-label="Toggle navigation">
        <Icon name="menu" size={16} />
      </button>
      <div style={{ fontWeight: 600, color: T.textHi, fontSize: 14, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
        {pageLabel}
      </div>
      <div style={{ flex: 1 }} />

      {resultsReady && (
        <>
          <span className="tag tag-blue" style={{ fontFamily: T.mono }}>
            {totalPairs} pairs
          </span>
          <span className="tag tag-red" style={{ fontFamily: T.mono }}>
            {significantPairs} significant
          </span>
          <span className="tag tag-teal">Ready</span>
        </>
      )}

      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 6,
          fontSize: 10,
          color: apiOnline ? T.teal : T.red,
          fontFamily: T.mono,
        }}
      >
        <Icon name={apiOnline ? "wifi" : "wifiOff"} size={12} />
        {apiOnline ? "API :8001" : "API offline"}
      </div>
    </div>
  );
};