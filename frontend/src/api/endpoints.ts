import { apiFetch, setTokens } from "./client";
import type {
  CatalogRole,
  Dashboard,
  Goal,
  LearningPath,
  RoleSuggestions,
  Step,
  Task,
  TokenPair,
  User,
} from "../types";

// ---- Auth ----
export function register(payload: {
  email: string;
  password: string;
  full_name: string;
}): Promise<User> {
  return apiFetch<User>("/api/register", {
    method: "POST",
    body: payload,
    auth: false,
  });
}

export async function login(
  email: string,
  password: string
): Promise<TokenPair> {
  const tokens = await apiFetch<TokenPair>("/api/login", {
    method: "POST",
    form: { username: email, password },
    auth: false,
  });
  setTokens(tokens.access_token, tokens.refresh_token);
  return tokens;
}

export function requestPasswordReset(
  email: string
): Promise<{ message: string }> {
  return apiFetch("/api/password-reset/request", {
    method: "POST",
    body: { email },
    auth: false,
  });
}

export function confirmPasswordReset(
  token: string,
  new_password: string
): Promise<{ message: string }> {
  return apiFetch("/api/password-reset/confirm", {
    method: "POST",
    body: { token, new_password },
    auth: false,
  });
}

// ---- AI coach ----
export interface ChatMsg {
  role: "user" | "assistant";
  content: string;
}
export function sendChat(messages: ChatMsg[]): Promise<{ reply: string }> {
  return apiFetch("/api/chat", { method: "POST", body: { messages } });
}

export function getMe(): Promise<User> {
  return apiFetch<User>("/api/users/me");
}

export function changePassword(
  current_password: string,
  new_password: string
): Promise<{ message: string }> {
  return apiFetch<{ message: string }>("/api/users/me/password", {
    method: "PUT",
    body: { current_password, new_password },
  });
}

export function resetProgress(): Promise<{ message: string }> {
  return apiFetch<{ message: string }>("/api/users/me/reset", { method: "POST" });
}

// ---- Dashboard ----
export function getDashboard(): Promise<Dashboard> {
  return apiFetch<Dashboard>("/dashboard/");
}

// ---- Goals ----
export function listGoals(): Promise<Goal[]> {
  return apiFetch<Goal[]>("/goals/");
}

export function getGoal(goalId: number): Promise<Goal> {
  return apiFetch<Goal>(`/goals/${goalId}`);
}

export function createGoal(payload: {
  role: string;
  hours_per_week: number;
  duration_weeks: number;
}): Promise<Goal> {
  return apiFetch<Goal>("/goals/", { method: "POST", body: payload });
}

export function updateGoal(
  goalId: number,
  payload: Partial<{
    role: string;
    hours_per_week: number;
    duration_weeks: number;
    is_active: boolean;
  }>
): Promise<Goal> {
  return apiFetch<Goal>(`/goals/${goalId}`, { method: "PUT", body: payload });
}

export function deleteGoal(goalId: number): Promise<void> {
  return apiFetch<void>(`/goals/${goalId}`, { method: "DELETE" });
}

export function resetGoal(goalId: number): Promise<{ message: string }> {
  return apiFetch<{ message: string }>(`/goals/${goalId}/reset`, { method: "POST" });
}

// ---- Paths ----
export function listPaths(goalId: number): Promise<LearningPath[]> {
  return apiFetch<LearningPath[]>(`/paths/goal/${goalId}`);
}

export function createPath(
  goalId: number,
  payload: { title: string; description?: string }
): Promise<LearningPath> {
  return apiFetch<LearningPath>(`/paths/${goalId}`, {
    method: "POST",
    body: payload,
  });
}

export function updatePath(
  pathId: number,
  payload: Partial<{ title: string; description: string }>
): Promise<LearningPath> {
  return apiFetch<LearningPath>(`/paths/${pathId}`, {
    method: "PUT",
    body: payload,
  });
}

export function deletePath(pathId: number): Promise<void> {
  return apiFetch<void>(`/paths/${pathId}`, { method: "DELETE" });
}

// ---- Steps ----
export function listSteps(pathId: number): Promise<Step[]> {
  return apiFetch<Step[]>(`/steps/path/${pathId}`);
}

export function createStep(
  pathId: number,
  payload: { title: string; description?: string; step_order?: number }
): Promise<Step> {
  return apiFetch<Step>(`/steps/path/${pathId}`, {
    method: "POST",
    body: payload,
  });
}

export function updateStep(
  stepId: number,
  payload: Partial<{
    title: string;
    description: string;
    step_order: number;
    is_done: boolean;
  }>
): Promise<Step> {
  return apiFetch<Step>(`/steps/${stepId}`, { method: "PATCH", body: payload });
}

export function deleteStep(stepId: number): Promise<void> {
  return apiFetch<void>(`/steps/${stepId}`, { method: "DELETE" });
}

// ---- Tasks ----
export function listTasks(stepId: number): Promise<Task[]> {
  return apiFetch<Task[]>(`/tasks/step/${stepId}`);
}

export function createTask(
  stepId: number,
  payload: { title: string; description?: string }
): Promise<Task> {
  return apiFetch<Task>(`/tasks/step/${stepId}`, {
    method: "POST",
    body: payload,
  });
}

export function updateTask(
  taskId: number,
  payload: Partial<{ title: string; description: string; is_done: boolean }>
): Promise<Task> {
  return apiFetch<Task>(`/tasks/${taskId}`, { method: "PATCH", body: payload });
}

export function deleteTask(taskId: number): Promise<void> {
  return apiFetch<void>(`/tasks/${taskId}`, { method: "DELETE" });
}

// ---- Catalog ----
export function listRoles(): Promise<CatalogRole[]> {
  return apiFetch<CatalogRole[]>("/catalog/roles");
}

export function getSuggestions(role: string): Promise<RoleSuggestions> {
  return apiFetch<RoleSuggestions>(
    `/catalog/suggestions?role=${encodeURIComponent(role)}`
  );
}
