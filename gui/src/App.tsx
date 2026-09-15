import React, { useEffect, useState, useCallback } from "react";
import { GLOBAL_CSS } from "./constants/styles";
import { useApiHealth, usePipeline, useRunHistory } from "./hooks";
import { SIG } from "./constants";

import { Sidebar }  from "./components/layout/Sidebar";
import { Topbar }   from "./components/layout/Topbar";

import { IngestSection }          from "./components/sections/IngestSection";
import { PipelineSection }        from "./components/sections/PipelineSection";
import { BatchResultsSection }    from "./components/sections/BatchResultsSection";
import { AtlasSection }           from "./components/sections/AtlasSection";
import { GapAnalysisSection }     from "./components/sections/GapAnalysisSection";
import { ExportSection }          from "./components/sections/ExportSection";
import { InterpretationSection }  from "./components/sections/InterpretationSection";
import { ProvenanceSection }      from "./components/sections/ProvenanceSection";
import { CoverageSection }        from "./components/sections/CoverageSection";
import { HistorySection }         from "./components/sections/HistorySection";
import { NullTestSection }        from "./components/sections/NullTestSection";

import type { NavSection, PipelineMode, AnalysisPair } from "./types";

function useGlobalStyles() {
   useEffect(() => {
        const el = document.createElement("style");

        el.textContent = GLOBAL_CSS;

        document.head.appendChild(el);

        return () => {
            document.head.removeChild(el);
        };
    }, []);
}

export default function App() {
  useGlobalStyles();

  const [page, setPage] = useState<NavSection>("ingest");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const apiOnline = useApiHealth();

  const {
    jobId, mode, pairs: pipelinePairs, resultsReady,
    lastLog, startRun, handleComplete,
  } = usePipeline();

  const {
    history, activeRunId, addRun, restoreRun, deleteRun, renameRun, clearHistory,
  } = useRunHistory();

  // "Active" pairs — either the latest pipeline run or a restored history record
  const [activePairs, setActivePairs] = useState<AnalysisPair[]>([]);

  // Keep activePairs in sync with the latest pipeline run
  useEffect(() => {
    if (pipelinePairs.length > 0) setActivePairs(pipelinePairs);
  }, [pipelinePairs]);

  const significantPairs = activePairs.filter(p => p.pval < SIG.STANDARD).length;

  const handleStartRun = useCallback(
    async (m: PipelineMode) => {
      setPage("pipeline");
      await startRun(m);
    },
    [startRun]
  );

  // saves the run to history and switches to the results page once it's done
  const handlePipelineComplete = useCallback(async () => {
    const result = await handleComplete();
    if (result && jobId) {
      const record = addRun(jobId, mode, result.pairs, result.log);
      setActivePairs(result.pairs);
      setTimeout(() => setPage("batch"), 800);
    }
  }, [handleComplete, jobId, mode, addRun]);

  const handleRestore = useCallback((pairs: AnalysisPair[]) => {
    setActivePairs(pairs);
    setPage("batch");
  }, []);

  const renderPage = () => {
    switch (page) {
      case "ingest":
        return <IngestSection onStartRun={handleStartRun} apiOnline={apiOnline} />;
      case "pipeline":
        return <PipelineSection mode={mode} jobId={jobId} onComplete={handlePipelineComplete} />;
      case "batch":
      case "pairs":
        return <BatchResultsSection pairs={activePairs} />;
      case "interpretation":
        return <InterpretationSection pairs={activePairs} />;
      case "provenance":
        return <ProvenanceSection pairs={activePairs} />;
      case "coverage":
        return <CoverageSection pairs={activePairs} />;
      case "atlas":
        return <AtlasSection pairs={activePairs} />;
      case "gaps":
        return <GapAnalysisSection />;
      case "history":
        return (
          <HistorySection
            history={history}
            activeRunId={activeRunId}
            onRestore={handleRestore}
            onDelete={deleteRun}
            onRename={renameRun}
            onClear={clearHistory}
          />
        );
      case "nulltest":
        return <NullTestSection pairs={activePairs} />;
      case "export":
        return <ExportSection pairs={activePairs} />;
      default:
        return null;
    }
  };

  const isResultsReady = resultsReady || activePairs.length > 0;

  return (
    <div className="app-shell">
      <Sidebar
        activePage={page}
        onNavigate={setPage}
        apiOnline={apiOnline}
        resultsReady={isResultsReady}
        totalPairs={activePairs.length}
        significantPairs={significantPairs}
        historyCount={history.length}
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />
      <div className="main-area">
        <Topbar
          activePage={page}
          apiOnline={apiOnline}
          resultsReady={isResultsReady}
          totalPairs={activePairs.length}
          significantPairs={significantPairs}
          onMenuClick={() => setSidebarOpen(o => !o)}
        />
        <div className="workspace">{renderPage()}</div>
      </div>
    </div>
  );
}