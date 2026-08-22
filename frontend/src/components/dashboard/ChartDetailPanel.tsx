import { X } from 'lucide-react';

export interface ChartDetailData {
  label: string;
  value: number | string;
  category: string;
}

interface ChartDetailPanelProps {
  data: ChartDetailData | null;
  onClose: () => void;
}

export function ChartDetailPanel({ data, onClose }: ChartDetailPanelProps) {
  if (!data) return null;

  return (
    <div className="absolute top-4 right-4 z-10 bg-white border border-gray-200 rounded-lg shadow-lg p-4 min-w-[200px]">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-semibold text-gray-700">Detail</h4>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-gray-600 transition-colors"
          aria-label="Close detail panel"
        >
          <X size={16} />
        </button>
      </div>
      <div className="space-y-2">
        <div>
          <span className="text-xs text-gray-500">Label</span>
          <p className="text-sm font-medium text-gray-900">{data.label}</p>
        </div>
        <div>
          <span className="text-xs text-gray-500">Value</span>
          <p className="text-sm font-medium text-gray-900">{data.value}</p>
        </div>
        <div>
          <span className="text-xs text-gray-500">Category</span>
          <p className="text-sm font-medium text-gray-900">{data.category}</p>
        </div>
      </div>
    </div>
  );
}
