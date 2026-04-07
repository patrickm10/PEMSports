import { useWorkspaceState } from '../../hooks/v3/useWorkspaceState';
import { V3WorkspaceLayout } from '../../components/v3/layout/V3WorkspaceLayout';
import { V3AnalysisGrid } from '../../components/v3/grid/V3AnalysisGrid';
import { V3DeltaDrawer } from '../../components/v3/analysis/V3DeltaDrawer';

export function V3Workspace() {
  const { state, updateState } = useWorkspaceState();

  return (
    <V3WorkspaceLayout 
      drawer={
        <V3DeltaDrawer 
          id={state.focusId} 
          onClose={() => updateState({ focusId: undefined })} 
        />
      }
    >
      <div className="h-full flex flex-col">
        <V3AnalysisGrid 
          state={state} 
          onRowClick={(id) => updateState({ focusId: id })} 
        />
      </div>
    </V3WorkspaceLayout>
  );
}
