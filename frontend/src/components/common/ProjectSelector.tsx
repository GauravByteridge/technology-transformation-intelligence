import { useState } from 'react';
import { ChevronDown } from 'lucide-react';
import { useProjects } from '@/hooks';

interface ProjectSelectorProps {
  /** Currently selected project ID (null = all projects) */
  value: string | null;
  /** Callback when a project is selected */
  onChange: (projectId: string | null) => void;
  /** Label prefix shown before the project name */
  label?: string;
  /** Whether to show "All Projects" option */
  showAllOption?: boolean;
  /** Placeholder when no project is selected and showAllOption is false */
  placeholder?: string;
  /** Whether the selector is disabled */
  disabled?: boolean;
  /** Visual variant */
  variant?: 'button' | 'select';
}

/**
 * Reusable project selector dropdown.
 * Displays projects by their code + name (e.g. "ALPHA — Project Alpha").
 * Internally passes the project UUID to the parent via onChange.
 */
export function ProjectSelector({
  value,
  onChange,
  label = 'Project:',
  showAllOption = true,
  placeholder = 'Select Project',
  disabled = false,
  variant = 'button',
}: ProjectSelectorProps) {
  const { data: projects } = useProjects();
  const [open, setOpen] = useState(false);

  const selectedProject = projects?.items.find((p) => p.id === value);
  const selectedLabel = selectedProject
    ? formatProjectLabel(selectedProject.project_code, selectedProject.name)
    : showAllOption
      ? 'All Projects'
      : placeholder;

  if (variant === 'select') {
    return (
      <select
        value={value ?? ''}
        onChange={(e) => onChange(e.target.value || null)}
        disabled={disabled}
        className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-white focus:outline-none focus:ring-1 focus:ring-teal-500 disabled:opacity-50"
      >
        {showAllOption && <option value="">— All Projects —</option>}
        {!showAllOption && <option value="">— {placeholder} —</option>}
        {projects?.items.map((p) => (
          <option key={p.id} value={p.id}>
            {formatProjectLabel(p.project_code, p.name)}
          </option>
        ))}
      </select>
    );
  }

  return (
    <div className="relative">
      <button
        onClick={() => !disabled && setOpen(!open)}
        disabled={disabled}
        className="inline-flex items-center gap-2 px-3 py-1.5 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-300 hover:border-gray-600 transition-colors disabled:opacity-50"
      >
        {label} <span className="text-white font-medium">{selectedLabel}</span>
        <ChevronDown size={14} />
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute left-0 top-full mt-1 z-20 w-72 bg-gray-800 border border-gray-700 rounded-lg shadow-xl py-1 max-h-64 overflow-y-auto">
            {showAllOption && (
              <button
                onClick={() => { onChange(null); setOpen(false); }}
                className={`w-full text-left px-4 py-2 text-sm hover:bg-gray-700 transition-colors ${
                  !value ? 'text-teal-400' : 'text-gray-300'
                }`}
              >
                All Projects
              </button>
            )}
            {projects?.items.map((p) => (
              <button
                key={p.id}
                onClick={() => { onChange(p.id); setOpen(false); }}
                className={`w-full text-left px-4 py-2 text-sm hover:bg-gray-700 transition-colors ${
                  value === p.id ? 'text-teal-400' : 'text-gray-300'
                }`}
              >
                {formatProjectLabel(p.project_code, p.name)}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

/** Format a project label showing code + name */
function formatProjectLabel(code: string | null, name: string): string {
  if (code) return `${code} — ${name}`;
  return name;
}
