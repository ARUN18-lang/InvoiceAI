const LS_KEY = "smartinvoice_workspace_id";

let activeWorkspaceId: string | null =
  typeof localStorage !== "undefined" ? localStorage.getItem(LS_KEY) : null;

export function getStoredWorkspaceId(): string | null {
  return activeWorkspaceId;
}

export function setActiveWorkspaceId(id: string | null): void {
  activeWorkspaceId = id;
  if (typeof localStorage === "undefined") return;
  if (id) localStorage.setItem(LS_KEY, id);
  else localStorage.removeItem(LS_KEY);
}

export function workspaceHeaders(): HeadersInit {
  const id = activeWorkspaceId;
  if (!id?.trim()) return {};
  return { "X-Workspace-Id": id.trim() };
}
