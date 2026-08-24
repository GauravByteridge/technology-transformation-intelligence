import { useState, useMemo } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ScatterChart, Scatter, LineChart, Line, AreaChart, Area, PieChart, Pie, Cell } from 'recharts';
import { RefreshCw, Share2, MoreVertical } from 'lucide-react';
import { ProjectSelector } from '@/components/common';
import { useProjectHealth, useProjects } from '@/hooks';

// ---------------------------------------------------------------------------
// Demo data generators (simulated project-specific data)
// ---------------------------------------------------------------------------

function generateBudgetData(projectName: string) {
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug'];
  const base = projectName === 'Project Alpha' ? 120000 : 80000;
  return months.map((month, i) => ({
    month,
    planned: base + i * 15000,
    actual: base + i * 15000 + (Math.random() - 0.3) * 20000,
  }));
}

function generateVelocityData(projectName: string) {
  const sprints = ['Sprint 1', 'Sprint 2', 'Sprint 3', 'Sprint 4', 'Sprint 5', 'Sprint 6', 'Sprint 7', 'Sprint 8'];
  const base = projectName === 'Project Alpha' ? 28 : 35;
  return sprints.map((sprint, i) => ({
    sprint,
    planned: base + Math.floor(Math.random() * 8),
    completed: base - 5 + Math.floor(Math.random() * 12),
    carryover: Math.floor(Math.random() * 6),
  }));
}

function generateRiskDistribution(projectName: string) {
  if (projectName === 'Project Alpha') {
    return [
      { name: 'High', value: 3, color: '#ef4444' },
      { name: 'Medium', value: 5, color: '#f59e0b' },
      { name: 'Low', value: 4, color: '#22c55e' },
    ];
  }
  return [
    { name: 'High', value: 1, color: '#ef4444' },
    { name: 'Medium', value: 2, color: '#f59e0b' },
    { name: 'Low', value: 6, color: '#22c55e' },
  ];
}

function generateResourceData(projectName: string) {
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug'];
  const base = projectName === 'Project Alpha' ? 8 : 5;
  return months.map((month, i) => ({
    month,
    demand: base + (i > 3 ? 2 : 0) + Math.random() * 1.5,
    capacity: base + 1,
  }));
}

function generateProgressScatter(projectName: string) {
  const tasks = [];
  const count = projectName === 'Project Alpha' ? 30 : 20;
  for (let i = 0; i < count; i++) {
    tasks.push({
      effort: Math.random() * 10,
      completion: Math.random() * 100,
      priority: ['high', 'medium', 'low'][Math.floor(Math.random() * 3)],
    });
  }
  return tasks;
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function AnalyticsDashboard() {
  const [selectedProject, setSelectedProject] = useState<string | null>(null);
  const { data: projects } = useProjects();
  const { data: health } = useProjectHealth(selectedProject ?? '');

  const currentProject = projects?.items.find((p) => p.id === selectedProject);
  const projectName = currentProject?.name ?? 'All Projects';

  // Generate project-specific demo data
  const budgetData = useMemo(() => generateBudgetData(projectName), [projectName]);
  const velocityData = useMemo(() => generateVelocityData(projectName), [projectName]);
  const riskData = useMemo(() => generateRiskDistribution(projectName), [projectName]);
  const resourceData = useMemo(() => generateResourceData(projectName), [projectName]);
  const scatterData = useMemo(() => generateProgressScatter(projectName), [projectName]);

  return (
    <div className="space-y-6">
      {/* Top bar — Databricks-style with filters */}
      <div className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-4">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div className="flex items-center gap-4">
            <h1 className="text-lg font-semibold text-white">Analytics Dashboard</h1>
            <ProjectSelector
              value={selectedProject}
              onChange={setSelectedProject}
              label="Project:"
              showAllOption={true}
            />
          </div>
          <div className="flex items-center gap-2">
            <button className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md bg-gray-700 text-gray-300 hover:bg-gray-600 transition-colors">
              <RefreshCw size={12} />
              Refresh
            </button>
            <button className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md bg-gray-700 text-gray-300 hover:bg-gray-600 transition-colors">
              <Share2 size={12} />
              Share
            </button>
            <button className="p-1.5 rounded-md text-gray-400 hover:bg-gray-700 hover:text-white transition-colors">
              <MoreVertical size={14} />
            </button>
          </div>
        </div>

        {/* KPI Strip */}
        {health && (
          <div className="flex items-center gap-6 mt-4 pt-4 border-t border-gray-700/50 text-sm">
            <KPIStrip label="Status" value={health.overall_status} />
            <KPIStrip label="Progress" value={`${Number(health.progress_percentage) || 0}%`} />
            <KPIStrip label="Budget Variance" value={`${Number(health.budget_variance_percentage) || 0}%`} />
            <KPIStrip label="Open Issues" value={String(health.open_issues_count)} />
            <KPIStrip label="Open Risks" value={String(health.open_risks_count)} />
            <KPIStrip label="Utilization" value={`${Number(health.resource_utilization_percentage) || 0}%`} />
          </div>
        )}
      </div>

      {/* Charts Grid — Databricks canvas-style */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Progress Burndown — Line Chart (FIRST) */}
        <ChartCard title="Progress Burndown">
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={budgetData.map((d, i) => ({
              month: d.month,
              planned: 100 - i * 12,
              actual: 100 - i * 12 + (Math.random() - 0.5) * 10,
            }))} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="month" tick={{ fill: '#9ca3af', fontSize: 11 }} />
              <YAxis tick={{ fill: '#9ca3af', fontSize: 11 }} />
              <Tooltip
                contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }}
                labelStyle={{ color: '#fff' }}
              />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Line type="monotone" dataKey="planned" stroke="#3b82f6" name="Planned" strokeDasharray="5 5" dot={false} />
              <Line type="monotone" dataKey="actual" stroke="#10b981" name="Actual" dot={{ r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>

        {/* Budget vs Actual — Bar Chart */}
        <ChartCard title="Budget vs Actual (Monthly)">
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={budgetData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="month" tick={{ fill: '#9ca3af', fontSize: 11 }} />
              <YAxis tick={{ fill: '#9ca3af', fontSize: 11 }} tickFormatter={(v) => `$${(v / 1000).toFixed(0)}K`} />
              <Tooltip
                contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }}
                labelStyle={{ color: '#fff' }}
                formatter={(value: number) => [`$${(value / 1000).toFixed(1)}K`, '']}
              />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Bar dataKey="planned" fill="#3b82f6" name="Planned" radius={[2, 2, 0, 0]} />
              <Bar dataKey="actual" fill="#f59e0b" name="Actual" radius={[2, 2, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        {/* Sprint Velocity — Bar Chart */}
        <ChartCard title="Sprint Velocity">
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={velocityData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="sprint" tick={{ fill: '#9ca3af', fontSize: 10 }} />
              <YAxis tick={{ fill: '#9ca3af', fontSize: 11 }} />
              <Tooltip
                contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }}
                labelStyle={{ color: '#fff' }}
              />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Bar dataKey="completed" fill="#10b981" name="Completed" stackId="a" radius={[0, 0, 0, 0]} />
              <Bar dataKey="carryover" fill="#ef4444" name="Carryover" stackId="a" radius={[2, 2, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        {/* Resource Demand vs Capacity — Area Chart */}
        <ChartCard title="Resource Demand vs Capacity (FTE)">
          <ResponsiveContainer width="100%" height={250}>
            <AreaChart data={resourceData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="month" tick={{ fill: '#9ca3af', fontSize: 11 }} />
              <YAxis tick={{ fill: '#9ca3af', fontSize: 11 }} />
              <Tooltip
                contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }}
                labelStyle={{ color: '#fff' }}
              />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Area type="monotone" dataKey="capacity" fill="#3b82f6" fillOpacity={0.2} stroke="#3b82f6" name="Capacity" />
              <Area type="monotone" dataKey="demand" fill="#f59e0b" fillOpacity={0.3} stroke="#f59e0b" name="Demand" />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>

        {/* Task Effort vs Completion — Scatter Chart */}
        <ChartCard title="Task Effort vs Completion">
          <ResponsiveContainer width="100%" height={250}>
            <ScatterChart margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="effort" name="Effort (days)" tick={{ fill: '#9ca3af', fontSize: 11 }} label={{ value: 'Effort (days)', position: 'bottom', fill: '#6b7280', fontSize: 10 }} />
              <YAxis dataKey="completion" name="Completion %" tick={{ fill: '#9ca3af', fontSize: 11 }} label={{ value: 'Completion %', angle: -90, position: 'insideLeft', fill: '#6b7280', fontSize: 10 }} />
              <Tooltip
                contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }}
                labelStyle={{ color: '#fff' }}
                formatter={(value: number) => [value.toFixed(1), '']}
              />
              <Scatter data={scatterData.filter(d => d.priority === 'high')} fill="#ef4444" name="High Priority" />
              <Scatter data={scatterData.filter(d => d.priority === 'medium')} fill="#f59e0b" name="Medium" />
              <Scatter data={scatterData.filter(d => d.priority === 'low')} fill="#22c55e" name="Low" />
            </ScatterChart>
          </ResponsiveContainer>
        </ChartCard>

        {/* Risk Distribution — Pie Chart */}
        <ChartCard title="Risk Distribution by Severity">
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie
                data={riskData}
                cx="50%"
                cy="50%"
                outerRadius={80}
                dataKey="value"
                label={({ name, value }) => `${name}: ${value}`}
                labelLine={{ stroke: '#6b7280' }}
              >
                {riskData.map((entry, idx) => (
                  <Cell key={idx} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }}
              />
              <Legend wrapperStyle={{ fontSize: 11 }} />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function ChartCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-gray-800/50 border border-gray-700/50 rounded-lg overflow-hidden">
      <div className="px-4 py-3 border-b border-gray-700/50 flex items-center justify-between">
        <h3 className="text-sm font-medium text-white">{title}</h3>
      </div>
      <div className="p-4">
        {children}
      </div>
    </div>
  );
}

function KPIStrip({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-gray-500">{label}</p>
      <p className="text-sm font-medium text-white">{value}</p>
    </div>
  );
}
