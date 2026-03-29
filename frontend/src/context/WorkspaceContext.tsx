import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { createWorkspace, fetchWorkspaces, type WorkspaceRecord } from "@/lib/api";
import { getStoredWorkspaceId, setActiveWorkspaceId } from "@/lib/workspaceStore";

type WorkspaceContextValue = {
  workspaces: WorkspaceRecord[];
  current: WorkspaceRecord | null;
  loading: boolean;
  error: string | null;
  selectWorkspace: (id: string) => void;
  refresh: () => Promise<void>;
  createNew: (name: string) => Promise<void>;
};

const WorkspaceContext = createContext<WorkspaceContextValue | null>(null);

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const [workspaces, setWorkspaces] = useState<WorkspaceRecord[]>([]);
  const [currentId, setCurrentId] = useState<string | null>(() => getStoredWorkspaceId());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setError(null);
    const list = await fetchWorkspaces();
    setWorkspaces(list);
    const stored = getStoredWorkspaceId();
    const valid = stored && list.some((w) => w.id === stored);
    const pick = valid ? stored! : list[0]?.id ?? null;
    setCurrentId(pick);
    setActiveWorkspaceId(pick);
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        await refresh();
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Failed to load workspaces");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [refresh]);

  const selectWorkspace = useCallback((id: string) => {
    setCurrentId(id);
    setActiveWorkspaceId(id);
  }, []);

  const createNew = useCallback(
    async (name: string) => {
      const w = await createWorkspace(name);
      await refresh();
      selectWorkspace(w.id);
    },
    [refresh, selectWorkspace],
  );

  const current = useMemo(
    () => workspaces.find((w) => w.id === currentId) ?? null,
    [workspaces, currentId],
  );

  const value = useMemo<WorkspaceContextValue>(
    () => ({
      workspaces,
      current,
      loading,
      error,
      selectWorkspace,
      refresh,
      createNew,
    }),
    [workspaces, current, loading, error, selectWorkspace, refresh, createNew],
  );

  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>;
}

export function useWorkspace(): WorkspaceContextValue {
  const ctx = useContext(WorkspaceContext);
  if (!ctx) throw new Error("useWorkspace must be used within WorkspaceProvider");
  return ctx;
}
