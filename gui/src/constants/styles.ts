import { T } from "../constants";

export const GLOBAL_CSS = `
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600;700&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html, body { height: 100%; background: ${T.bg0}; color: ${T.text}; font-family: ${T.sans}; font-size: 13px; overflow: hidden; }

::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: ${T.bg1}; }
::-webkit-scrollbar-thumb { background: ${T.dim}; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: ${T.muted}; }

button { font-family: ${T.sans}; cursor: pointer; }
input, select, textarea { font-family: ${T.sans}; }

/* ── Layout ── */
.app-shell { display: flex; height: 100vh; width: 100vw; overflow: hidden; }
.sidebar { width: 220px; min-width: 220px; background: ${T.bg1}; border-right: 1px solid ${T.border}; display: flex; flex-direction: column; overflow: hidden; }
.main-area { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
.topbar { height: 48px; min-height: 48px; background: ${T.bg1}; border-bottom: 1px solid ${T.border}; display: flex; align-items: center; padding: 0 20px; gap: 12px; }
.workspace { flex: 1; overflow-y: auto; padding: 24px; }

/* ── Navigation ── */
.nav-group { padding: 16px 10px 6px; font-size: 10px; font-weight: 700; color: ${T.muted}; letter-spacing: .12em; text-transform: uppercase; }
.nav-item { display: flex; align-items: center; gap: 10px; padding: 8px 14px; border-radius: 6px; cursor: pointer; color: ${T.textDim}; font-size: 13px; font-weight: 400; transition: all .12s; margin: 1px 6px; border: none; background: none; width: calc(100% - 12px); text-align: left; }
.nav-item:hover { background: ${T.bg2}; color: ${T.text}; }
.nav-item.active { background: ${T.blueDim}; color: ${T.blue}; font-weight: 500; }
.nav-item .badge { margin-left: auto; background: ${T.blue}; color: #000; font-size: 9px; font-weight: 700; padding: 1px 5px; border-radius: 8px; font-family: ${T.mono}; }

/* ── Panels ── */
.panel { background: ${T.panel}; border: 1px solid ${T.border}; border-radius: 10px; overflow: hidden; }
.panel-header { display: flex; align-items: center; justify-content: space-between; padding: 12px 16px; border-bottom: 1px solid ${T.border}; }
.panel-title { display: flex; align-items: center; gap: 8px; font-weight: 600; color: ${T.textHi}; font-size: 13px; }

/* ── Buttons ── */
.btn { display: inline-flex; align-items: center; gap: 6px; padding: 7px 14px; border-radius: 6px; border: 1px solid transparent; font-size: 12px; font-weight: 500; cursor: pointer; transition: all .12s; white-space: nowrap; }
.btn-primary { background: ${T.blue}; color: ${T.bg0}; font-weight: 600; border-color: ${T.blue}; }
.btn-primary:hover { background: #69b2ff; box-shadow: 0 0 0 3px ${T.blue}22; }
.btn-ghost { background: transparent; color: ${T.textDim}; border-color: ${T.border}; }
.btn-ghost:hover { background: ${T.bg2}; color: ${T.text}; border-color: ${T.borderHi}; }
.btn-teal { background: ${T.teal}; color: ${T.bg0}; font-weight: 600; border-color: ${T.teal}; }
.btn:disabled { opacity: .35; cursor: not-allowed; pointer-events: none; }
.btn-icon { padding: 6px; }

/* ── Inputs ── */
.input { background: ${T.bg1}; border: 1px solid ${T.border}; color: ${T.text}; border-radius: 6px; padding: 7px 10px; font-size: 12px; transition: border-color .12s; }
.input:focus { outline: none; border-color: ${T.blue}; }
.input::placeholder { color: ${T.muted}; }
.select { background: ${T.bg1}; border: 1px solid ${T.border}; color: ${T.text}; border-radius: 6px; padding: 7px 10px; font-size: 12px; cursor: pointer; appearance: none; }
.label { font-size: 10px; font-weight: 600; color: ${T.textDim}; letter-spacing: .09em; text-transform: uppercase; margin-bottom: 5px; display: block; }

/* ── Tags ── */
.tag { display: inline-flex; align-items: center; gap: 3px; padding: 2px 7px; border-radius: 4px; font-size: 10px; font-weight: 600; font-family: ${T.mono}; letter-spacing: .02em; }
.tag-blue   { background: ${T.blueDim};   color: ${T.blue}; }
.tag-teal   { background: ${T.tealDim};   color: ${T.teal}; }
.tag-amber  { background: ${T.amberDim};  color: ${T.amber}; }
.tag-red    { background: ${T.redDim};    color: ${T.red}; }
.tag-green  { background: ${T.greenDim};  color: ${T.green}; }
.tag-violet { background: ${T.violetDim}; color: ${T.violet}; }
.tag-muted  { background: ${T.dim};       color: ${T.muted}; }

/* ── Stats ── */
.stat { background: ${T.bg2}; border: 1px solid ${T.border}; border-radius: 8px; padding: 12px 14px; }
.stat-val { font-family: ${T.mono}; font-size: 20px; font-weight: 700; color: ${T.textHi}; line-height: 1; }
.stat-lbl { font-size: 10px; color: ${T.textDim}; text-transform: uppercase; letter-spacing: .09em; margin-top: 5px; }

/* ── Tables ── */
.data-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.data-table th { padding: 8px 12px; text-align: left; font-size: 10px; font-weight: 700; color: ${T.textDim}; text-transform: uppercase; letter-spacing: .09em; border-bottom: 1px solid ${T.border}; white-space: nowrap; }
.data-table td { padding: 9px 12px; border-bottom: 1px solid ${T.border}20; font-family: ${T.mono}; vertical-align: middle; }
.data-table tr:hover td { background: ${T.bg1}; }
.data-table tr:last-child td { border-bottom: none; }

/* ── File tree ── */
.ftree-item { display: flex; align-items: center; gap: 7px; padding: 4px 6px; border-radius: 4px; cursor: pointer; font-size: 12px; transition: background .1s; }
.ftree-item:hover { background: ${T.bg2}; }
.ftree-item.selected { background: ${T.blueDim}; color: ${T.blue}; }

/* ── Drop zone ── */
.drop-zone { border: 2px dashed ${T.border}; border-radius: 10px; padding: 40px 32px; text-align: center; cursor: pointer; transition: all .2s; }
.drop-zone:hover, .drop-zone.drag { border-color: ${T.blue}; background: ${T.blueDim}20; }
.drop-zone.filled { border-color: ${T.teal}; border-style: solid; background: ${T.tealDim}20; }

/* ── Progress ── */
.prog-bar { height: 2px; background: ${T.border}; border-radius: 1px; overflow: hidden; }
.prog-fill { height: 100%; background: linear-gradient(90deg, ${T.blue}, ${T.teal}); transition: width .3s ease; }

/* ── Heat map cells ── */
.heat-cell { border-radius: 4px; display: flex; align-items: center; justify-content: center; font-family: ${T.mono}; font-size: 11px; font-weight: 600; cursor: default; transition: transform .1s; }
.heat-cell:hover { transform: scale(1.08); z-index: 1; }

/* ── Pipeline steps ── */
.pipe-step { display: flex; align-items: center; gap: 8px; padding: 10px 14px; border-radius: 8px; border: 1px solid ${T.border}; background: ${T.bg2}; font-size: 12px; }
.pipe-step.done    { border-color: ${T.teal}40; }
.pipe-step.running { border-color: ${T.blue}40; background: ${T.blueDim}20; }
.pipe-step.error   { border-color: ${T.red}40; background: ${T.redDim}20; }

/* ── Code / misc ── */
.code-block { background: ${T.bg0}; border: 1px solid ${T.border}; border-radius: 6px; padding: 12px 16px; font-family: ${T.mono}; font-size: 11px; color: ${T.green}; line-height: 1.8; overflow-x: auto; }
.api-banner { padding: 10px 16px; border-radius: 8px; display: flex; align-items: center; gap: 10px; font-size: 12px; margin-bottom: 16px; }
.api-banner.ok  { background: ${T.tealDim}; border: 1px solid ${T.teal}40; color: ${T.teal}; }
.api-banner.err { background: ${T.redDim};  border: 1px solid ${T.red}40;  color: ${T.red};  }
.search-bar { display: flex; align-items: center; gap: 8px; background: ${T.bg2}; border: 1px solid ${T.border}; border-radius: 6px; padding: 6px 10px; flex: 1; max-width: 380px; }
.search-bar input { background: none; border: none; color: ${T.text}; font-size: 12px; outline: none; flex: 1; }
.search-bar input::placeholder { color: ${T.muted}; }

/* ── Grid helpers ── */
.split { display: grid; gap: 16px; }
.split-2 { grid-template-columns: 1fr 1fr; }
.split-3 { grid-template-columns: 1fr 1fr 1fr; }
.split-4 { grid-template-columns: repeat(4, 1fr); }
.split-5 { grid-template-columns: repeat(5, 1fr); }

/* ── Animations ── */
.fade-in { animation: fadeIn .25s ease; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: none; } }
.spin-anim { animation: spin 2s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* ── Interpretation section ── */
.narrative-block { padding: 16px 20px; line-height: 1.9; font-size: 13px; }
.narrative-block p { margin-bottom: 12px; }
.narrative-block p:last-child { margin-bottom: 0; }
.flag-row { transition: background .1s; }
.flag-row:hover { background: ${T.bg2}; }

/* ── Provenance section ── */
.dataset-drawer td { padding: 0 !important; border-bottom: none !important; }
.lambda-bar-track { position: relative; height: 8px; background: ${T.border}30; border-radius: 4px; }
.lambda-bar-fill  { position: absolute; height: 100%; background: ${T.blue}; border-radius: 4px; min-width: 3px; }

/* ── Coverage section ── */
.gantt-track  { position: relative; flex: 1; height: 24px; background: ${T.border}30; border-radius: 3px; }
.gantt-bar    { position: absolute; height: 100%; border-radius: 3px; opacity: .85; }
.overlap-band { position: absolute; top: 0; bottom: 0; background: ${T.teal}18; border: 1px solid ${T.teal}40; border-radius: 2px; pointer-events: none; }

/* ── Recharts overrides ── */
.recharts-default-legend { font-size: 10px !important; }
.recharts-legend-item-text { color: ${T.textDim} !important; font-size: 10px !important; }
`;