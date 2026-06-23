import { useState, useRef, useEffect } from "react";
import { FileTreeNode } from "../types";
import { apiClient } from "../api/client";
import { T } from "../constants";


// ─── TreeNode ─────────────────────────────────────────────────────────────────

function TreeNode({
  node,
  relativePath,
  onSelect,
  selected,
  onRefresh,
  depth = 0,
}: {
  node:         FileTreeNode;
  relativePath: string;
  onSelect:     (n: FileTreeNode) => void;
  selected?:    string;
  onRefresh:    () => void;
  depth?:       number;
}) {
  const [expanded,          setExpanded]          = useState(depth < 2);
  const [menuOpen,          setMenuOpen]          = useState(false);
  const [menuPos,           setMenuPos]           = useState({ top: 0, left: 0 });
  const [renaming,          setRenaming]          = useState(false);
  const [newName,           setNewName]           = useState(node.name);
  const [confirming,        setConfirming]        = useState(false);
  const [moving,            setMoving]            = useState(false);
  const [folders,           setFolders]           = useState<string[]>([]);
  const [moveStatus,        setMoveStatus]        = useState<"idle"|"loading"|"done"|"error">("idle");
  const [creatingFolder,    setCreatingFolder]    = useState(false);
  const [newFolderName,     setNewFolderName]     = useState("");
  const [folderCreateError, setFolderCreateError] = useState<string | null>(null);
  const btnRef = useRef<HTMLButtonElement>(null);
  const isFile   = node.type === "file";
  const hasChildren = !isFile && (node.children?.length ?? 0) > 0;

  // ── Outside-click closes menu ──────────────────────────────────────────────
  useEffect(() => {
    if (!menuOpen) return;
    const handler = () => {
      setMenuOpen(false);
      setConfirming(false);
      setMoving(false);
      setCreatingFolder(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [menuOpen]);

  const openMenu = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (btnRef.current) {
      const rect = btnRef.current.getBoundingClientRect();
      // Flip left if too close to right edge
      const left = Math.min(rect.right - 200, window.innerWidth - 210);
      setMenuPos({ top: rect.bottom + 4, left: Math.max(4, left) });
    }
    setMenuOpen(o => !o);
    setConfirming(false);
    setMoving(false);
    setCreatingFolder(false);
  };

  // ── Handlers ──────────────────────────────────────────────────────────────
  const handleDelete = async () => {
    if (!confirming) { setConfirming(true); return; }
    try {
      await apiClient.deleteDataset(relativePath);
      setMenuOpen(false);
      onRefresh();
    } catch (e) { console.error("Delete failed:", e); }
  };

  const handleRename = async () => {
    const dir     = relativePath.substring(0, relativePath.lastIndexOf("/") + 1);
    const newPath = dir + newName;
    try {
      await apiClient.renameItem(relativePath, newPath);
      setRenaming(false);
      onRefresh();
    } catch (e) { console.error("Rename failed:", e); setRenaming(false); }
  };

  const handleOpenMove = async () => {
    setMoving(true);
    setMoveStatus("loading");
    try {
      const list = await apiClient.listFolders();
      const currentFolder = relativePath.substring(0, relativePath.lastIndexOf("/"));
      setFolders(list.filter(f => f !== currentFolder && f !== ""));
      setMoveStatus("idle");
    } catch { setMoveStatus("error"); }
  };

  const handleMoveTo = async (destFolder: string) => {
    try {
      await apiClient.moveFile(node.name, relativePath, destFolder);
      setMenuOpen(false);
      setMoving(false);
      onRefresh();
    } catch (e) { console.error("Move failed:", e); }
  };

  const handleCreateFolder = async () => {
    if (!newFolderName.trim()) return;
    try {
      await apiClient.createFolder(`${relativePath}/${newFolderName.trim()}`);
      setCreatingFolder(false);
      setNewFolderName("");
      setFolderCreateError(null);
      setMenuOpen(false);
      onRefresh();
    } catch { setFolderCreateError("Failed to create folder"); }
  };

  // ── Row indent & chevron ──────────────────────────────────────────────────
  const indentPx = depth * 14;

  return (
    <div>
      {/* ── Row ── */}
      <div
        style={{
          display:        "flex",
          alignItems:     "center",
          paddingLeft:    indentPx,
          paddingRight:   4,
          paddingTop:     3,
          paddingBottom:  3,
          borderRadius:   4,
          background:     selected === node.name ? (T.bg2 ?? "#2a2a3e") : "transparent",
          cursor:         "pointer",
          minHeight:      32,
          userSelect:     "none",
        }}
        onClick={() => {
          if (renaming) return;
          if (!isFile) setExpanded(e => !e);
          else onSelect(node);
        }}
      >
        {/* Chevron for folders */}
        {!isFile && (
          <span style={{
            display:      "inline-block",
            width:        14,
            fontSize:     10,
            color:        T.muted,
            flexShrink:   0,
            transform:    expanded ? "rotate(90deg)" : "rotate(0deg)",
            transition:   "transform 0.15s ease",
            marginRight:  2,
          }}>
            ▶
          </span>
        )}

        {/* Icon */}
        <span style={{ fontSize: 13, marginRight: 6, flexShrink: 0 }}>
          {isFile ? "📄" : expanded ? "📂" : "📁"}
        </span>

        {/* Name / rename input */}
        {renaming ? (
          <input
            autoFocus
            value={newName}
            style={{
              background:   T.bg0,
              color:        T.textHi,
              border:       `1px solid ${T.blue}`,
              borderRadius: 3,
              fontSize:     12,
              padding:      "2px 6px",
              flex:         1,
              outline:      "none",
              minWidth:     0,
            }}
            onChange={e => setNewName(e.target.value)}
            onKeyDown={e => {
              if (e.key === "Enter")  handleRename();
              if (e.key === "Escape") { setRenaming(false); setNewName(node.name); }
            }}
            onClick={e => e.stopPropagation()}
          />
        ) : (
          <span style={{
            fontSize:      12,
            color:         isFile ? T.textDim : T.textHi,
            flex:          1,
            overflow:      "hidden",
            textOverflow:  "ellipsis",
            whiteSpace:    "nowrap",
            fontWeight:    isFile ? 400 : 500,
          }}>
            {node.name}
          </span>
        )}

        {/* ⋯ button */}
         <button
          ref={btnRef}
          className="btn btn-ghost btn-icon"
          style={{ opacity: 0.5, fontSize: 13, padding: "0 6px", marginLeft: 4, flexShrink: 0 }}
          onClick={openMenu}
          title="Options"
        >
          ⋯
        </button>
      </div>

      {/* ── Children (collapsible) ── */}
      {!isFile && expanded && node.children && node.children.length > 0 && (
        <div>
          {node.children.map(child => (
            <TreeNode
              key={child.name}
              node={child}
              relativePath={`${relativePath}/${child.name}`}
              onSelect={onSelect}
              selected={selected}
              onRefresh={onRefresh}
              depth={depth + 1}
            />
          ))}
        </div>
      )}

      {/* Empty folder hint */}
      {!isFile && expanded && (!node.children || node.children.length === 0) && (
        <div style={{
          paddingLeft: indentPx + 28,
          paddingTop:  2,
          paddingBottom: 4,
          fontSize:    11,
          color:       T.muted,
          fontStyle:   "italic",
        }}>
          empty folder
        </div>
      )}

      {/* ── Context menu (fixed to escape overflow) ── */}
      {menuOpen && (
        <div
          style={{
            position:     "fixed",
            top:          menuPos.top,
            left:         menuPos.left,
            zIndex:       9999,
            background:   T.bg1 ?? "#1a1a2e",
            border:       `1px solid ${T.border ?? "#444"}`,
            borderRadius: 8,
            minWidth:     200,
            maxWidth:     260,
            boxShadow:    "0 8px 24px rgba(0,0,0,0.6)",
            fontSize:     12,
            overflow:     "hidden",
          }}
          onMouseDown={e => e.stopPropagation()}
        >
          {/* Header */}
          <div style={{
            padding:      "8px 12px 6px",
            color:        T.muted,
            fontSize:     10,
            fontWeight:   600,
            letterSpacing: "0.05em",
            textTransform: "uppercase",
            borderBottom: `1px solid ${T.border ?? "#333"}`,
          }}>
            {isFile ? "📄" : "📁"} {node.name}
          </div>

          {/* ── Main menu ── */}
          {!moving && !creatingFolder && (
            <>
              <button
                className="btn btn-ghost"
                style={{ display: "flex", alignItems: "center", gap: 8, width: "100%", textAlign: "left", padding: "9px 12px" }}
                onMouseDown={() => { setRenaming(true); setMenuOpen(false); }}
              >
                <span>✏️</span> Rename
              </button>

              {isFile && (
                <button
                  className="btn btn-ghost"
                  style={{ display: "flex", alignItems: "center", gap: 8, width: "100%", textAlign: "left", padding: "9px 12px" }}
                  onMouseDown={e => { e.stopPropagation(); handleOpenMove(); }}
                >
                  <span>📂</span> Move to folder…
                </button>
              )}

              {!isFile && (
                <button
                  className="btn btn-ghost"
                  style={{ display: "flex", alignItems: "center", gap: 8, width: "100%", textAlign: "left", padding: "9px 12px" }}
                  onMouseDown={e => { e.stopPropagation(); setCreatingFolder(true); setNewFolderName(""); }}
                >
                  <span>📁</span> New subfolder
                </button>
              )}

              <div style={{ borderTop: `1px solid ${T.border ?? "#333"}`, margin: "4px 0" }} />

              <button
                className="btn btn-ghost"
                style={{
                  display: "flex", alignItems: "center", gap: 8,
                  width: "100%", textAlign: "left", padding: "9px 12px",
                  color: confirming ? (T.red ?? "#e05555") : T.amber,
                }}
                onMouseDown={e => { e.stopPropagation(); handleDelete(); }}
              >
                <span>{confirming ? "⚠️" : "🗑️"}</span>
                {confirming ? "Confirm delete" : "Delete"}
              </button>

              {confirming && (
                <button
                  className="btn btn-ghost"
                  style={{ display: "flex", alignItems: "center", gap: 8, width: "100%", textAlign: "left", padding: "9px 12px", color: T.muted }}
                  onMouseDown={e => { e.stopPropagation(); setConfirming(false); }}
                >
                  <span>✕</span> Cancel
                </button>
              )}
            </>
          )}

          {/* ── Move picker ── */}
          {moving && (
            <div>
              <div style={{ padding: "8px 12px 4px", color: T.textDim, fontSize: 11, fontWeight: 600 }}>
                Select destination:
              </div>
              {moveStatus === "loading" && (
                <div style={{ padding: "10px 12px", color: T.muted }}>Loading folders…</div>
              )}
              {moveStatus === "error" && (
                <div style={{ padding: "10px 12px", color: T.amber }}>Failed to load folders</div>
              )}
              {moveStatus === "idle" && folders.length === 0 && (
                <div style={{ padding: "10px 12px", color: T.muted, fontSize: 11 }}>No other folders available</div>
              )}
              <div style={{ maxHeight: 180, overflowY: "auto" }}>
                {moveStatus === "idle" && folders.map(f => (
                  <button
                    key={f}
                    className="btn btn-ghost"
                    style={{
                      display: "flex", alignItems: "center", gap: 8,
                      width: "100%", textAlign: "left", padding: "8px 12px",
                      color: T.textDim, fontFamily: T.mono, fontSize: 11,
                    }}
                    onMouseDown={e => { e.stopPropagation(); handleMoveTo(f); }}
                  >
                    <span>📁</span>
                    <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{f}</span>
                  </button>
                ))}
              </div>
              <div style={{ borderTop: `1px solid ${T.border ?? "#333"}`, margin: "4px 0" }} />
              <button
                className="btn btn-ghost"
                style={{ display: "flex", alignItems: "center", gap: 8, width: "100%", textAlign: "left", padding: "8px 12px", color: T.muted }}
                onMouseDown={e => { e.stopPropagation(); setMoving(false); }}
              >
                <span>←</span> Back
              </button>
            </div>
          )}

          {/* ── New subfolder inline input ── */}
          {creatingFolder && (
            <div style={{ padding: "8px 12px" }} onMouseDown={e => e.stopPropagation()}>
              <div style={{ color: T.textDim, fontSize: 11, marginBottom: 6, fontWeight: 600 }}>
                New subfolder in{" "}
                <span style={{ color: T.blue, fontFamily: T.mono }}>{node.name}/</span>
              </div>
              <input
                autoFocus
                value={newFolderName}
                placeholder="folder-name"
                style={{
                  width:        "100%",
                  background:   T.bg0,
                  color:        T.textHi,
                  border:       `1px solid ${folderCreateError ? (T.red ?? "#e05") : T.blue}`,
                  borderRadius: 4,
                  fontSize:     12,
                  padding:      "6px 8px",
                  outline:      "none",
                  boxSizing:    "border-box",
                  fontFamily:   T.mono,
                }}
                onChange={e => { setNewFolderName(e.target.value); setFolderCreateError(null); }}
                onKeyDown={e => {
                  if (e.key === "Enter")  handleCreateFolder();
                  if (e.key === "Escape") { setCreatingFolder(false); setNewFolderName(""); }
                }}
              />
              {folderCreateError && (
                <div style={{ color: T.red ?? "#e05", fontSize: 11, marginTop: 4 }}>
                  {folderCreateError}
                </div>
              )}
              <div style={{ display: "flex", gap: 6, marginTop: 8 }}>
                <button
                  className="btn btn-primary"
                  style={{ fontSize: 11, padding: "5px 12px", flex: 1 }}
                  onMouseDown={e => { e.stopPropagation(); handleCreateFolder(); }}
                >
                  Create
                </button>
                <button
                  className="btn btn-ghost"
                  style={{ fontSize: 11, padding: "5px 12px" }}
                  onMouseDown={e => { e.stopPropagation(); setCreatingFolder(false); setNewFolderName(""); setFolderCreateError(null); }}
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── FileTree (exported) ──────────────────────────────────────────────────────

interface FileTreeProps {
  node:       FileTreeNode;
  onSelect:   (n: FileTreeNode) => void;
  selected?:  string;
  onRefresh?: () => void;
}

export function FileTree({ node, onSelect, selected, onRefresh }: FileTreeProps) {
  if (node.children?.length) {
    return (
      <div style={{ width: "100%" }}>
        {node.children.map((child: FileTreeNode) => (
          <TreeNode
            key={child.name}
            node={child}
            relativePath={child.name}
            onSelect={onSelect}
            selected={selected}
            onRefresh={onRefresh ?? (() => {})}
            depth={0}
          />
        ))}
      </div>
    );
  }
  return (
    <div style={{ padding: 16, textAlign: "center", color: T.muted, fontSize: 12 }}>
      No files found
    </div>
  );
}