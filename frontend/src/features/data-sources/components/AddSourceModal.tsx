import { useState } from 'react';
import { X, Database, FileText, CheckCircle2, Loader2 } from 'lucide-react';

type SourceType = 'postgresql' | 'mongodb' | 'jira' | 'files';
type Step = 'select-type' | 'configure' | 'connecting';

interface AddSourceModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

interface ConnectionForm {
  name: string;
  host: string;
  port: string;
  database: string;
  username: string;
  password: string;
}

const SOURCE_TYPES = [
  {
    type: 'postgresql' as const,
    label: 'PostgreSQL',
    icon: '/icons/postgresql.png',
    description: 'Connect to PostgreSQL databases',
  },
  {
    type: 'mongodb' as const,
    label: 'MongoDB',
    icon: '/icons/mongodb.png',
    description: 'Connect to MongoDB collections',
  },
  {
    type: 'jira' as const,
    label: 'Jira Cloud',
    icon: '/icons/jira.png',
    description: 'Connect to Jira for issue tracking data',
  },
  {
    type: 'files' as const,
    label: 'Files / Documents',
    icon: '/icons/document.png',
    description: 'Upload and index enterprise documents',
  },
];

const DISCOVERY_STEPS = [
  'Connecting...',
  '✓ Connection established',
  'Discovering schemas...',
  'Discovering tables...',
  'Discovering columns...',
  'Profiling metadata...',
  'Understanding datasets...',
  'Building semantic catalog...',
  '✓ Ready',
];

export function AddSourceModal({ isOpen, onClose, onSuccess }: AddSourceModalProps) {
  const [step, setStep] = useState<Step>('select-type');
  const [sourceType, setSourceType] = useState<SourceType | null>(null);
  const [form, setForm] = useState<ConnectionForm>({
    name: '',
    host: '',
    port: '5432',
    database: '',
    username: '',
    password: '',
  });
  const [discoveryStep, setDiscoveryStep] = useState(0);
  const [testStatus, setTestStatus] = useState<'idle' | 'testing' | 'success' | 'error'>('idle');

  if (!isOpen) return null;

  const handleSelectType = (type: SourceType) => {
    setSourceType(type);
    if (type === 'files') {
      onClose();
      window.location.href = '/upload';
      return;
    }
    if (type === 'jira') {
      setForm({ name: 'Jira Cloud', host: 'https://your-site.atlassian.net', port: '', database: '', username: '', password: '' });
    } else {
      setForm({ name: '', host: '', port: type === 'postgresql' ? '5432' : '27017', database: '', username: '', password: '' });
    }
    setStep('configure');
  };

  const handleTestConnection = () => {
    setTestStatus('testing');
    setTimeout(() => setTestStatus('success'), 1500);
  };

  const handleConnect = () => {
    setStep('connecting');
    setDiscoveryStep(0);

    // Simulate discovery progress
    let currentStep = 0;
    const interval = setInterval(() => {
      currentStep++;
      setDiscoveryStep(currentStep);
      if (currentStep >= DISCOVERY_STEPS.length - 1) {
        clearInterval(interval);
        setTimeout(() => {
          onSuccess();
          resetModal();
        }, 1000);
      }
    }, 800);
  };

  const resetModal = () => {
    setStep('select-type');
    setSourceType(null);
    setForm({ name: '', host: '', port: '5432', database: '', username: '', password: '' });
    setDiscoveryStep(0);
    setTestStatus('idle');
  };

  const handleClose = () => {
    resetModal();
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Overlay */}
      <div className="absolute inset-0 bg-black/60" onClick={handleClose} aria-hidden="true" />

      {/* Modal */}
      <div className="relative w-full max-w-lg mx-4 bg-gray-900 border border-gray-700 rounded-xl shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-700">
          <h2 className="text-lg font-semibold text-white">
            {step === 'select-type' && 'Add Data Source'}
            {step === 'configure' && `Connect ${sourceType === 'postgresql' ? 'PostgreSQL' : sourceType === 'jira' ? 'Jira Cloud' : 'MongoDB'}`}
            {step === 'connecting' && 'Discovering...'}
          </h2>
          <button
            onClick={handleClose}
            className="p-1 rounded hover:bg-gray-700 text-gray-400 hover:text-white transition-colors"
            aria-label="Close"
          >
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        <div className="px-6 py-5">
          {step === 'select-type' && (
            <div className="space-y-3">
              <p className="text-sm text-gray-400 mb-4">Select source type</p>
              {SOURCE_TYPES.map(({ type, label, icon, description }) => (
                <button
                  key={type}
                  onClick={() => handleSelectType(type)}
                  className="w-full flex items-center gap-4 p-4 rounded-lg border border-gray-700 hover:border-teal-500/50 hover:bg-teal-500/5 transition-colors text-left"
                >
                  <img src={icon} alt={label} className="w-8 h-8 object-contain" />
                  <div>
                    <p className="text-sm font-medium text-white">{label}</p>
                    <p className="text-xs text-gray-400">{description}</p>
                  </div>
                </button>
              ))}
            </div>
          )}

          {step === 'configure' && (
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-gray-400 mb-1">Connection Name</label>
                <input
                  type="text"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder="Client PostgreSQL"
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-teal-500"
                />
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div className="col-span-2">
                  <label className="block text-xs font-medium text-gray-400 mb-1">Host</label>
                  <input
                    type="text"
                    value={form.host}
                    onChange={(e) => setForm({ ...form, host: e.target.value })}
                    placeholder="db.company.com"
                    className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-teal-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-400 mb-1">Port</label>
                  <input
                    type="text"
                    value={form.port}
                    onChange={(e) => setForm({ ...form, port: e.target.value })}
                    className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-teal-500"
                  />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-400 mb-1">Database</label>
                <input
                  type="text"
                  value={form.database}
                  onChange={(e) => setForm({ ...form, database: e.target.value })}
                  placeholder="TechnologyTransformation"
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-teal-500"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-400 mb-1">Username</label>
                  <input
                    type="text"
                    value={form.username}
                    onChange={(e) => setForm({ ...form, username: e.target.value })}
                    className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-teal-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-400 mb-1">Password</label>
                  <input
                    type="password"
                    value={form.password}
                    onChange={(e) => setForm({ ...form, password: e.target.value })}
                    className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-teal-500"
                  />
                </div>
              </div>

              {/* Actions */}
              <div className="flex items-center justify-between pt-3">
                <button
                  onClick={handleTestConnection}
                  disabled={testStatus === 'testing'}
                  className="px-4 py-2 text-sm rounded-lg border border-gray-600 text-gray-300 hover:bg-gray-800 disabled:opacity-50 transition-colors"
                >
                  {testStatus === 'testing' ? 'Testing...' : testStatus === 'success' ? '✓ Connected' : 'Test Connection'}
                </button>
                <button
                  onClick={handleConnect}
                  className="px-4 py-2 text-sm font-medium rounded-lg bg-teal-600 text-white hover:bg-teal-500 transition-colors"
                >
                  Connect & Discover
                </button>
              </div>
            </div>
          )}

          {step === 'connecting' && (
            <div className="space-y-3 py-4">
              {DISCOVERY_STEPS.map((stepLabel, idx) => (
                <div
                  key={idx}
                  className={`flex items-center gap-3 text-sm transition-opacity duration-300 ${
                    idx <= discoveryStep ? 'opacity-100' : 'opacity-0'
                  }`}
                >
                  {idx < discoveryStep ? (
                    <CheckCircle2 size={16} className="text-green-400 shrink-0" />
                  ) : idx === discoveryStep ? (
                    <Loader2 size={16} className="text-teal-400 shrink-0 animate-spin" />
                  ) : (
                    <div className="w-4 h-4 shrink-0" />
                  )}
                  <span className={idx <= discoveryStep ? 'text-gray-200' : 'text-gray-600'}>
                    {stepLabel}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
