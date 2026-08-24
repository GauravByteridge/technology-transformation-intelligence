// ============================================================
// TypeScript interfaces aligned with backend Pydantic schemas
// ============================================================

// ---------------------------------------------------------------------------
// Portfolio & Health (schemas/health.py)
// ---------------------------------------------------------------------------

export interface PortfolioProjectSummary {
  project_id: string;
  overall_status: string;
  schedule_status: string;
  budget_total: number;
  budget_spent: number;
  budget_variance: number;
  budget_variance_percentage: number;
  progress_percentage: number;
  resource_utilization_percentage: number;
  open_issues_count: number;
  open_risks_count: number;
  open_audit_findings_count: number;
  open_remediation_items_count: number;
  it_control_compliance_percentage: number;
  last_calculated_at: string | null;
}

export interface PortfolioSummaryResponse {
  total_projects: number;
  on_track_count: number;
  at_risk_count: number;
  delayed_count: number;
  completed_count: number;
  projects: PortfolioProjectSummary[];
}

export interface ProjectHealthResponse {
  project_id: string;
  overall_status: string;
  schedule_status: string;
  budget_total: number;
  budget_spent: number;
  budget_variance: number;
  budget_variance_percentage: number;
  progress_percentage: number;
  resource_utilization_percentage: number;
  open_issues_count: number;
  open_risks_count: number;
  open_audit_findings_count: number;
  open_remediation_items_count: number;
  it_control_compliance_percentage: number;
  last_calculated_at: string | null;
}

// ---------------------------------------------------------------------------
// Projects (schemas/projects.py)
// ---------------------------------------------------------------------------

export interface ProjectResponse {
  id: string;
  project_code: string | null;
  name: string;
  description: string | null;
  status: string;
  created_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectListResponse {
  items: ProjectResponse[];
  total: number;
}

// ---------------------------------------------------------------------------
// Finance (schemas/project_domain.py)
// ---------------------------------------------------------------------------

export interface BudgetLineItemResponse {
  id: string;
  budget_id: string;
  cost_category_id: string;
  planned_amount: number;
}

export interface ProjectBudgetResponse {
  id: string;
  project_id: string;
  fiscal_year: number;
  total_budget: number;
  approved_date: string | null;
  status: string;
  line_items: BudgetLineItemResponse[];
}

export interface ActualCostResponse {
  id: string;
  project_id: string;
  cost_category_id: string;
  amount: number;
  incurred_date: string;
  description: string | null;
}

export interface MonthlyCostTrendResponse {
  id: string;
  project_id: string;
  year_month: string;
  planned_spend: number;
  actual_spend: number;
  cumulative_planned: number;
  cumulative_actual: number;
}

export interface ProjectFinanceResponse {
  budget: ProjectBudgetResponse | null;
  actual_costs: ActualCostResponse[];
  total_spent: number;
  budget_variance: number;
  variance_percentage: number;
  monthly_trends: MonthlyCostTrendResponse[];
}

// ---------------------------------------------------------------------------
// JIRA (schemas/project_domain.py)
// ---------------------------------------------------------------------------

export interface SprintResponse {
  id: string;
  project_id: string;
  name: string;
  sprint_number: number;
  start_date: string;
  end_date: string;
  status: string;
  goal: string | null;
  velocity: number | null;
}

export interface JiraIssueResponse {
  id: string;
  project_id: string;
  sprint_id: string | null;
  issue_key: string;
  issue_type: string;
  summary: string;
  description: string | null;
  status: string;
  priority: string;
  assignee: string | null;
  reporter: string | null;
  story_points: number | null;
  due_date: string | null;
  resolved_date: string | null;
}

export interface ProjectJiraResponse {
  sprints: SprintResponse[];
  issues: JiraIssueResponse[];
  open_issues_count: number;
  overdue_issues_count: number;
  completion_percentage: number;
}

// ---------------------------------------------------------------------------
// Resources (schemas/project_domain.py)
// ---------------------------------------------------------------------------

export interface ResourceAllocationResponse {
  id: string;
  project_id: string;
  team_member_id: string;
  allocation_percentage: number;
  start_date: string;
  end_date: string | null;
  role_on_project: string | null;
}

export interface ResourceForecastResponse {
  id: string;
  project_id: string;
  year_month: string;
  demand_fte: number;
  capacity_fte: number;
  gap_fte: number;
}

export interface ProjectResourceResponse {
  allocations: ResourceAllocationResponse[];
  utilization_percentage: number | null;
  capacity_gap: number;
  forecasts: ResourceForecastResponse[];
}

// ---------------------------------------------------------------------------
// SDLC (schemas/project_domain.py)
// ---------------------------------------------------------------------------

export interface SdlcDeliverableResponse {
  id: string;
  name: string;
  description: string | null;
  status: string;
  owner: string | null;
  due_date: string | null;
  completion_date: string | null;
}

export interface SdlcMilestoneResponse {
  id: string;
  name: string;
  description: string | null;
  planned_date: string | null;
  actual_date: string | null;
  status: string;
  deliverables: SdlcDeliverableResponse[];
}

export interface SdlcPhaseResponse {
  id: string;
  phase_name: string;
  sequence_order: number;
  status: string;
  planned_start_date: string | null;
  planned_end_date: string | null;
  actual_start_date: string | null;
  actual_end_date: string | null;
  milestones: SdlcMilestoneResponse[];
}

export interface ProjectSdlcResponse {
  project_id: string;
  phases: SdlcPhaseResponse[];
}

// ---------------------------------------------------------------------------
// Risks (schemas/project_domain.py)
// ---------------------------------------------------------------------------

export interface ProjectRiskResponse {
  id: string;
  project_id: string;
  risk_reference: string;
  title: string;
  description: string | null;
  severity: string;
  status: string;
  owner: string | null;
  identified_date: string | null;
  target_date: string | null;
}

export interface ProjectRisksResponse {
  risks: ProjectRiskResponse[];
  open_risks_count: number;
}

// ---------------------------------------------------------------------------
// Progress (schemas/project_domain.py)
// ---------------------------------------------------------------------------

export interface ProgressSnapshotResponse {
  id: string;
  snapshot_date: string;
  planned_progress_percentage: number;
  actual_progress_percentage: number;
}

export interface ProjectProgressResponse {
  project_id: string;
  snapshots: ProgressSnapshotResponse[];
  progress_percentage: number;
}

// ---------------------------------------------------------------------------
// Audit (schemas/project_domain.py)
// ---------------------------------------------------------------------------

export interface AuditFindingResponse {
  id: string;
  project_id: string;
  finding_reference: string;
  title: string;
  description: string | null;
  severity: string;
  status: string;
  identified_date: string | null;
  target_remediation_date: string | null;
  actual_remediation_date: string | null;
  auditor: string | null;
}

export interface ProjectAuditResponse {
  findings: AuditFindingResponse[];
  overdue_count: number;
}

// ---------------------------------------------------------------------------
// IT Controls (schemas/project_domain.py)
// ---------------------------------------------------------------------------

export interface ControlAssessmentResponse {
  id: string;
  control_id: string;
  project_id: string;
  compliance_status: string;
  assessed_date: string | null;
  assessor: string | null;
  notes: string | null;
  next_assessment_date: string | null;
}

export interface ProjectControlsResponse {
  assessments: ControlAssessmentResponse[];
  compliance_percentage: number;
}

// ---------------------------------------------------------------------------
// Remediation (schemas/project_domain.py)
// ---------------------------------------------------------------------------

export interface RemediationItemResponse {
  id: string;
  finding_id: string;
  project_id: string;
  title: string;
  description: string | null;
  owner: string | null;
  status: string;
  priority: string;
  due_date: string;
  completion_date: string | null;
}

export interface ProjectRemediationResponse {
  items: RemediationItemResponse[];
  overdue_count: number;
}

// ---------------------------------------------------------------------------
// AI (schemas/ai.py)
// ---------------------------------------------------------------------------

export interface AIQueryRequest {
  question: string;
  project_id?: string;
  conversation_id?: string;
}

export interface AIResponse {
  answer: string;
  response_type: 'text' | 'table' | 'chart';
  sources: Record<string, unknown>[];
  evidence: Record<string, unknown>[];
  query_id: string;
  conversation_id: string;
  is_partial: boolean;
  failed_sources: Record<string, unknown>[];
  visualization_spec: Record<string, unknown> | null;
  lineage_trace: Record<string, unknown> | null;
}

// ---------------------------------------------------------------------------
// File Upload (schemas/dataset.py)
// ---------------------------------------------------------------------------

export interface FileUploadResponse {
  file_id: string;
  file_name: string;
  file_type: string;
  processing_status: string;
  datasets_created: Record<string, unknown>[];
  documents_indexed: number;
}

// ---------------------------------------------------------------------------
// Datasets (schemas/dataset.py)
// ---------------------------------------------------------------------------

export interface DatasetResponse {
  id: string;
  file_id: string;
  project_id: string | null;
  name: string;
  source_type: string;
  sheet_name: string | null;
  classification: string;
  record_count: number;
  confidence: number;
  status: string;
  created_at: string | null;
}

export interface DatasetDetailResponse extends DatasetResponse {
  description: string | null;
  domain: string | null;
  columns: Record<string, unknown>[];
  regions: Record<string, unknown>[];
}

export interface DatasetPreviewResponse {
  dataset: DatasetResponse;
  columns: Record<string, unknown>[];
  records: Record<string, unknown>[];
  total_count: number;
}

export interface DatasetQueryRequest {
  filters?: Record<string, unknown>;
  sort?: Record<string, unknown>[];
  limit?: number;
  offset?: number;
  columns?: string[];
  aggregations?: Record<string, unknown>[];
}

export interface DatasetQueryResponse {
  records: Record<string, unknown>[];
  total_count: number;
  aggregations?: Record<string, unknown>[];
}

export interface DatasetConfirmRequest {
  name?: string;
  description?: string;
  classification?: string;
  domain?: string;
}

// ---------------------------------------------------------------------------
// Documents (schemas/document.py)
// ---------------------------------------------------------------------------

export interface DocumentResponse {
  id: string;
  project_id: string;
  file_name: string;
  file_type: string;
  file_size: number;
  processing_status: string;
  created_at: string | null;
}

export interface DocumentSearchRequest {
  project_id: string;
  query: string;
  limit?: number;
}

export interface DocumentSearchResponse {
  results: Record<string, unknown>[];
  total_count: number;
  query: string;
  project_id: string;
}

// ---------------------------------------------------------------------------
// Data Sources (schemas/data_source.py)
// ---------------------------------------------------------------------------

export interface DataSourceResponse {
  id: string;
  name: string;
  source_type: string;
  display_label: string;
  connection_config: Record<string, unknown>;
  connection_status: string;
  last_connected_at: string | null;
  created_at: string;
  updated_at: string;
  // Discovery tracking fields (Phase 8)
  last_discovery_at: string | null;
  discovery_status: string;
  objects_discovered: number;
  fields_discovered: number;
}

// ---------------------------------------------------------------------------
// AI Chat Session (design document — frontend-only types)
// ---------------------------------------------------------------------------

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  queryId?: string;
}

export interface Conversation {
  id: string;
  project_id?: string;
  messages: ChatMessage[];
  created_at: string;
  last_message_at: string;
}

export interface QueryHistoryEntry {
  question: string;
  timestamp: string;
  conversation_id: string;
}

// ---------------------------------------------------------------------------
// Evidence / Source Attribution (used by EvidencePanel and AI components)
// ---------------------------------------------------------------------------

export type SourceType = 'database' | 'document' | 'notes';

export interface SourceEvidence {
  source_name: string;
  source_type: SourceType;
  display_name: string;
  data_items: Record<string, unknown>[];
}

// ---------------------------------------------------------------------------
// Data Source Status (used by StatusBadge)
// ---------------------------------------------------------------------------

export type DataSourceStatusValue = 'Connected' | 'Syncing' | 'Error';

// ---------------------------------------------------------------------------
// Executive Brief (backend-dependent — endpoint does not yet exist)
// ---------------------------------------------------------------------------

export interface ExecutiveBrief {
  executive_summary: string;
  overall_health: string;
  financial_position: string;
  schedule: string;
  resource_position: string;
  top_risks: string;
  audit_and_controls: string;
  recommended_actions: string;
  generated_at: string;
  supporting_sources: string[];
}

// ---------------------------------------------------------------------------
// Client-side Filtering (retained for Project Portfolio page)
// ---------------------------------------------------------------------------

export interface ProjectFilters {
  status?: string[];
  risk?: string[];
  search?: string;
}
