// ============================================================
// TypeScript interfaces matching backend Pydantic schemas
// ============================================================

// --- Enums ---

export type ProjectStatus = 'on_track' | 'at_risk' | 'delayed' | 'completed';
export type RiskLevel = 'high' | 'medium' | 'low';
export type ConfidenceLevel = 'high' | 'medium' | 'low';
export type Severity = 'critical' | 'high' | 'medium' | 'low';
export type ComplianceStatus = 'compliant' | 'non_compliant' | 'not_assessed';
export type IssueStatus = 'open' | 'in_progress' | 'resolved' | 'closed';
export type IssuePriority = 'critical' | 'high' | 'medium' | 'low';
export type RemediationStatus = 'open' | 'in_progress' | 'completed' | 'overdue';
export type DataSourceStatusValue = 'Connected' | 'Syncing' | 'Error';
export type SourceType = 'database' | 'document' | 'notes';

// --- Dashboard ---

export interface DashboardKPIs {
  total_projects: number;
  projects_at_risk: number;
  total_budget: number;
  budget_variance: number;
  open_audit_findings: number;
  open_remediation_items: number;
  it_control_compliance: number;
  resource_utilization: number;
}

export interface ProjectHealthDistribution {
  on_track: number;
  at_risk: number;
  delayed: number;
  completed: number;
}

export interface BudgetChartItem {
  project_id: string;
  project_name: string;
  planned_budget: number;
  actual_cost: number;
}

export interface BurndownPoint {
  date: string;
  planned_progress: number;
  actual_progress: number;
}

export interface AuditChart {
  open_findings: number;
  critical_findings: number;
  remediated_items: number;
  overdue_items: number;
}

export interface ResourceForecastPoint {
  month: string;
  demand: number;
  capacity: number;
}

// --- Projects ---

export interface ProjectSummary {
  id: string;
  name: string;
  project_manager: string;
  status: ProjectStatus;
  budget: number;
  actual_cost: number;
  variance: number;
  progress: number;
  risk: RiskLevel;
  resource_utilization: number;
  open_issues: number;
}

export interface ProjectDetail {
  id: string;
  name: string;
  project_manager: string;
  status: ProjectStatus;
  total_budget: number;
  actual_cost: number;
  budget_variance: number;
  schedule_status: string;
  progress: number;
  resource_utilization: number;
  open_issues: number;
  risk: RiskLevel;
}

export interface ProjectFilters {
  status?: ProjectStatus[];
  risk?: RiskLevel[];
  project_manager?: string[];
  search?: string;
}

// --- Financials ---

export interface Financial {
  id: string;
  project_id: string;
  category: string;
  planned_amount: number;
  actual_amount: number;
  variance: number;
  month: string;
}

// --- JIRA ---

export interface JIRAIssue {
  id: string;
  project_id: string;
  issue_key: string;
  summary: string;
  status: IssueStatus;
  priority: IssuePriority;
  assignee: string;
  due_date: string;
  created_date: string;
}

// --- Resources ---

export interface Resource {
  id: string;
  project_id: string;
  team_member: string;
  role: string;
  allocation_percent: number;
  utilization_percent: number;
}

export interface ResourceForecast {
  id: string;
  project_id: string;
  month: string;
  demand: number;
  capacity: number;
}

// --- Audit ---

export interface AuditFinding {
  id: string;
  project_id: string;
  title: string;
  description: string;
  severity: Severity;
  status: 'open' | 'in_progress' | 'closed';
  target_remediation_date: string;
}

// --- IT Controls ---

export interface ITControl {
  id: string;
  project_id: string;
  control_name: string;
  description: string;
  compliance_status: ComplianceStatus;
  last_assessment_date: string;
}

// --- Remediation ---

export interface RemediationItem {
  id: string;
  project_id: string;
  title: string;
  description: string;
  status: RemediationStatus;
  priority: IssuePriority;
  due_date: string;
  assigned_to: string;
}

// --- Documents ---

export interface ProjectDocument {
  id: string;
  project_id: string;
  title: string;
  document_type: string;
  content: string;
  file_path: string;
}

// --- AI Response ---

export interface SourceEvidence {
  source_name: string;
  source_type: SourceType;
  display_name: string;
  data_items: Record<string, unknown>[];
}

export interface AIResponse {
  answer: string;
  findings: string[];
  metrics: Record<string, unknown>[];
  sources: string[];
  evidence: SourceEvidence[];
  confidence: number;
  partial_sources: boolean;
  unavailable_sources: string[];
}

export interface AIQuestionRequest {
  question: string;
  project_id?: string;
}

// --- Executive Brief ---

export interface ExecutiveBrief {
  executive_summary: string;
  overall_health: string;
  financial_position: string;
  schedule: string;
  resource_position: string;
  top_risks: string;
  audit_and_controls: string;
  recommended_actions: string;
  supporting_sources: string[];
  generated_at: string;
}

// --- Data Sources ---

export interface DataSourceStatus {
  name: string;
  type: string;
  records_count: number;
  last_updated: string;
  status: DataSourceStatusValue;
}

// --- API Error ---

export interface APIError {
  error_code: string;
  message: string;
}
