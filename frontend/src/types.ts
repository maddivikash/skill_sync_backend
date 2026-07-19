export interface User {
  id: number;
  email: string;
  full_name: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface Progress {
  total_tasks: number;
  done_tasks: number;
  percent: number;
}

export interface Goal {
  id: number;
  role: string;
  hours_per_week: number;
  duration_weeks: number;
  is_active: boolean;
  created_at: string;
}

export interface DashboardGoal extends Goal {
  paths_count: number;
  progress: Progress;
}

export interface Dashboard {
  overall: Progress;
  goals: DashboardGoal[];
}

export interface LearningPath {
  id: number;
  goal_id: number;
  title: string;
  description: string | null;
  created_at: string;
}

export interface Step {
  id: number;
  path_id: number;
  title: string;
  description: string | null;
  step_order: number;
  is_done: boolean;
  created_at: string;
}

export interface Task {
  id: number;
  step_id: number;
  title: string;
  description: string | null;
  is_done: boolean;
  created_at: string;
}

// ---- Catalog (suggestions live in the DB) ----
export interface CatalogRole {
  id: number;
  slug: string;
  name: string;
}

export type CatalogCategory = "skill" | "course" | "tool" | "project";

export interface CatalogItem {
  id: number;
  category: CatalogCategory;
  name: string;
  description: string | null;
  provider: string | null;
  url: string | null;
  estimated_hours: number | null;
  steps: string[] | null;
}

export interface RoleSuggestions {
  matched: boolean;
  label: string;
  role: CatalogRole | null;
  items: {
    skill: CatalogItem[];
    course: CatalogItem[];
    tool: CatalogItem[];
    project: CatalogItem[];
  };
}
