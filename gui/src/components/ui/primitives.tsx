import React from "react";
import { T } from "../../constants";
import { Icon } from "./Icon";
import type { TooltipPayloadItem } from "../../types";

// Stat

interface StatProps {
  label: string;
  value: React.ReactNode;
  unit?: string;
  color?: string;
  sub?: string;
}

export const Stat: React.FC<StatProps> = ({ label, value, unit, color, sub }) => (
  <div className="stat">
    <div className="stat-val" style={color ? { color } : undefined}>
      {value}
      {unit && (
        <span style={{ fontSize: 11, fontWeight: 400, color: T.textDim, marginLeft: 3 }}>
          {unit}
        </span>
      )}
    </div>
    <div className="stat-lbl">{label}</div>
    {sub && <div style={{ fontSize: 10, color: T.muted, marginTop: 3 }}>{sub}</div>}
  </div>
);

// PanelHeader

interface PanelHeaderProps {
  title: string;
  icon?: string;
  right?: React.ReactNode;
  sub?: string;
}

export const PanelHeader: React.FC<PanelHeaderProps> = ({ title, icon, right, sub }) => (
  <div className="panel-header">
    <div style={{ minWidth: 0, flex: "1 1 auto" }}>
      <div className="panel-title">
        {icon && (
          <span style={{ color: T.blue, flexShrink: 0 }}>
            <Icon name={icon as any} size={14} />
          </span>
        )}
        {title}
      </div>
      {sub && <div style={{ fontSize: 10, color: T.textDim, marginTop: 2 }}>{sub}</div>}
    </div>
    {right}
  </div>
);

// ChartTooltip

interface ChartTooltipProps {
  active?: boolean;
  payload?: TooltipPayloadItem[];
  label?: number;
  fmt?: (v: number) => string;
}

export const ChartTooltip: React.FC<ChartTooltipProps> = ({ active, payload, label, fmt }) => {
  if (!active || !payload?.length) return null;
  return (
    <div
      style={{
        background: T.bg1,
        border: `1px solid ${T.border}`,
        borderRadius: 8,
        padding: "8px 12px",
        fontSize: 11,
        fontFamily: T.mono,
      }}
    >
      {label !== undefined && (
        <div style={{ color: T.textDim, marginBottom: 5 }}>
          λ = 10<sup>{Number(label).toFixed(1)}</sup> m
        </div>
      )}
      {payload.map(p => (
        <div key={p.name} style={{ color: p.color ?? T.text, marginBottom: 2 }}>
          {p.name}: {fmt ? fmt(p.value) : p.value}
        </div>
      ))}
    </div>
  );
};

// SigTag

export const SigTag: React.FC<{ pval: number }> = ({ pval }) => {
  if (pval < 0.001) return <span className="tag tag-red">✦✦✦ p &lt; 0.001</span>;
  if (pval < 0.05)  return <span className="tag tag-amber">✦ p &lt; 0.05</span>;
  return <span className="tag tag-teal">ns</span>;
};

// ApiBanner

export const ApiBanner: React.FC<{ online: boolean }> = ({ online }) => (
  <div className={`api-banner ${online ? "ok" : "err"}`}>
    <Icon name={online ? "wifi" : "wifiOff"} size={14} />
    {online
      ? "API connected — pipeline will use real data from ~/spindep_framework/datasets"
      : "API offline — start the server: python3 app_server.py (from ~/spindep_framework)"}
  </div>
);

// ProgressBar

export const ProgressBar: React.FC<{ value: number; height?: number }> = ({
  value,
  height = 2,
}) => (
  <div className="prog-bar" style={{ height }}>
    <div className="prog-fill" style={{ width: `${value}%` }} />
  </div>
);

// SearchBar

interface SearchBarProps {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
}

export const SearchBar: React.FC<SearchBarProps> = ({ value, onChange, placeholder }) => (
  <div className="search-bar">
    <Icon name="search" size={13} />
    <input
      placeholder={placeholder ?? "Search…"}
      value={value}
      onChange={e => onChange(e.target.value)}
    />
  </div>
);