// Project Intelligence Hub - TypeScript Interfaces
// Field names match the backend API responses (snake_case from Python/Pydantic)

export interface Project {
  id: number;
  name: string;
  description: string;
  created_at: string;
}

export interface ProjectFile {
  id: number;
  file_name: string;
  file_type: 'pdf' | 'xlsx' | 'xls' | 'csv' | 'json';
  category: FileCategory;
  uploaded_at: string;
  chunk_count: number;
}

export type FileCategory =
  | 'Project Costs'
  | 'Burndown'
  | 'Audit'
  | 'IT Controls'
  | 'Remediation'
  | 'Business Intelligence'
  | 'Internal Data'
  | 'Other';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: string[];
  timestamp: string;
}

export interface DashboardStats {
  project_name: string;
  project_description: string;
  total_files: number;
  files_by_type: { type: string; count: number }[];
  files_by_category: { category: string; count: number }[];
  recent_files: ProjectFile[];
}

export interface ChartConfig {
  type: 'bar' | 'line' | 'pie';
  title: string;
  data: Record<string, unknown>[];
  x_key?: string;
  y_key?: string;
  data_key?: string;
  name_key?: string;
}
