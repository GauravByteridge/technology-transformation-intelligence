import { ProjectTable } from '../components/project';

/**
 * ProjectPortfolio — displays the full project portfolio with search,
 * filter controls, and a sortable table. All search/filter/data-fetching
 * logic lives inside ProjectTable which uses the useProjects React Query hook.
 */
export default function ProjectPortfolio() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-gray-900">
        Project Portfolio
      </h1>

      <ProjectTable />
    </div>
  );
}
