import { useState, useEffect } from 'react';
import { X, Database, FileText, CheckCircle2, Loader2 } from 'lucide-react';

type SourceType = 'postgresql' | 'mongodb' | 'jira' | 'files' | 'gmail';
type Step = 'select-type' | 'configure' | 'connecting' | 'gmail-fetch' | 'gmail-results';

interface AddSourceModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  initialSourceType?: 'postgresql' | 'mongodb' | 'jira' | 'files' | 'gmail';
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
    type: 'gmail' as const,
    label: 'Gmail',
    icon: '/icons/gmail.png',
    description: 'Fetch emails and attachments into RAG',
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

export function AddSourceModal({ isOpen, onClose, onSuccess, initialSourceType }: AddSourceModalProps) {
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

  // Gmail state
  const [gmailKeywords, setGmailKeywords] = useState('');
  const [gmailCount, setGmailCount] = useState(10);
  const [gmailEmails, setGmailEmails] = useState<any[]>([]);
  const [gmailLoading, setGmailLoading] = useState(false);
  const [gmailStatus, setGmailStatus] = useState<{ connected: boolean; email?: string } | null>(null);
  const [addingToRag, setAddingToRag] = useState<string | null>(null);
  const [ragResults, setRagResults] = useState<Record<string, string>>({});
  const [selectedProjectId, setSelectedProjectId] = useState<string>('');
  const [projects, setProjects] = useState<{ id: string; name: string; project_code: string | null }[]>([]);
  const [gmailSearchMode, setGmailSearchMode] = useState<'keywords' | 'project'>('project');
  const [addAllLoading, setAddAllLoading] = useState(false);
  const [addAllResult, setAddAllResult] = useState<string | null>(null);

  // Fetch projects when Gmail step is shown
  useEffect(() => {
    if (step === 'gmail-fetch' && projects.length === 0) {
      fetch('http://localhost:8000/api/v1/projects')
        .then(res => res.json())
        .then(data => {
          const items = data.items || data || [];
          setProjects(items.map((p: any) => ({ id: p.id, name: p.name, project_code: p.project_code })));
          if (items.length > 0 && !selectedProjectId) {
            setSelectedProjectId(items[0].id);
          }
        })
        .catch(() => {});
    }
  }, [step]);

  // Handle initialSourceType when modal opens
  useEffect(() => {
    if (isOpen && initialSourceType) {
      setSourceType(initialSourceType);
      if (initialSourceType === 'gmail') {
        checkGmailStatus();
        setStep('gmail-fetch');
      }
    }
  }, [isOpen, initialSourceType]);

  if (!isOpen) return null;

  const handleSelectType = (type: SourceType) => {
    setSourceType(type);
    if (type === 'files') {
      onClose();
      window.location.href = '/upload';
      return;
    }
    if (type === 'gmail') {
      // Check Gmail connection status
      checkGmailStatus();
      setStep('gmail-fetch');
      return;
    }
    if (type === 'jira') {
      setForm({ name: 'Jira Cloud', host: 'https://your-site.atlassian.net', port: '', database: '', username: '', password: '' });
    } else {
      setForm({ name: '', host: '', port: type === 'postgresql' ? '5432' : '27017', database: '', username: '', password: '' });
    }
    setStep('configure');
  };

  const checkGmailStatus = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/v1/gmail/status');
      const data = await res.json();
      setGmailStatus(data);
    } catch {
      setGmailStatus({ connected: false });
    }
  };

  const handleGmailAuth = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/v1/gmail/auth/url');
      const data = await res.json();
      window.open(data.auth_url, '_blank');
    } catch (e) {
      console.error('Failed to get auth URL', e);
    }
  };

  const handleGmailFetch = async () => {
    setGmailLoading(true);
    try {
      // Build search keywords based on mode
      let searchQuery = '';
      if (gmailSearchMode === 'keywords') {
        searchQuery = gmailKeywords;
      } else {
        // "Search by Project" — use project name and code as keywords
        const project = projects.find(p => p.id === selectedProjectId);
        if (project) {
          const parts: string[] = [];
          if (project.name) parts.push(project.name);
          if (project.project_code) parts.push(project.project_code);
          searchQuery = parts.join(' OR ');
        }
      }

      const res = await fetch('http://localhost:8000/api/v1/gmail/fetch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ keywords: searchQuery, max_results: gmailCount }),
      });
      const data = await res.json();
      setGmailEmails(data.emails || []);
      setStep('gmail-results');
    } catch (e) {
      console.error('Failed to fetch emails', e);
    } finally {
      setGmailLoading(false);
    }
  };

  const handleAddAllToRag = async () => {
    setAddAllLoading(true);
    setAddAllResult(null);
    try {
      const emailPayloads = gmailEmails.map(email => ({
        message_id: email.message_id,
        subject: email.subject,
        body: email.body_preview,
        attachments: email.attachments || [],
      }));

      const res = await fetch('http://localhost:8000/api/v1/gmail/add-all-to-rag', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          emails: emailPayloads,
          project_id: selectedProjectId || null,
        }),
      });
      const data = await res.json();
      setAddAllResult(data.message);
    } catch (e) {
      setAddAllResult('Failed to add emails to RAG');
    } finally {
      setAddAllLoading(false);
    }
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
    setGmailKeywords('');
    setGmailCount(10);
    setGmailEmails([]);
    setGmailStatus(null);
    setRagResults({});
    setSelectedProjectId('');
    setGmailSearchMode('project');
    setAddAllLoading(false);
    setAddAllResult(null);
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
      <div className="relative w-full max-w-2xl mx-4 bg-gray-900 border border-gray-700 rounded-xl shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-700">
          <h2 className="text-lg font-semibold text-white">
            {step === 'select-type' && 'Add Data Source'}
            {step === 'configure' && `Connect ${sourceType === 'postgresql' ? 'PostgreSQL' : sourceType === 'jira' ? 'Jira Cloud' : 'MongoDB'}`}
            {step === 'connecting' && 'Discovering...'}
            {step === 'gmail-fetch' && 'Gmail — Fetch Emails'}
            {step === 'gmail-results' && 'Gmail — Search Results'}
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

          {step === 'gmail-fetch' && (
            <div className="space-y-4">
              {/* Connection status */}
              {gmailStatus && (
                <div className={`p-3 rounded-lg text-sm ${gmailStatus.connected ? 'bg-green-500/10 border border-green-500/30 text-green-300' : 'bg-yellow-500/10 border border-yellow-500/30 text-yellow-300'}`}>
                  {gmailStatus.connected ? (
                    <span>✓ Connected as <strong>{gmailStatus.email}</strong></span>
                  ) : (
                    <div className="space-y-2">
                      <p>Not connected to Gmail. Authorize to continue.</p>
                      <button onClick={handleGmailAuth} className="px-3 py-1.5 bg-teal-600 text-white text-xs rounded-lg hover:bg-teal-500">
                        Authorize Gmail
                      </button>
                    </div>
                  )}
                </div>
              )}

              {/* Project selector */}
              <div>
                <label className="block text-xs font-medium text-gray-400 mb-1">Project</label>
                <select
                  value={selectedProjectId}
                  onChange={(e) => setSelectedProjectId(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-white focus:outline-none focus:ring-1 focus:ring-teal-500"
                >
                  <option value="">— Select a project —</option>
                  {projects.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.project_code ? `${p.project_code} — ${p.name}` : p.name}
                    </option>
                  ))}
                </select>
              </div>

              {/* Search mode toggle */}
              {selectedProjectId && (
                <>
                  <div>
                    <label className="block text-xs font-medium text-gray-400 mb-2">Search Mode</label>
                    <div className="flex gap-2">
                      <button
                        onClick={() => setGmailSearchMode('project')}
                        className={`px-3 py-1.5 text-xs rounded-lg border transition-colors ${gmailSearchMode === 'project' ? 'border-teal-500 bg-teal-500/10 text-teal-300' : 'border-gray-600 text-gray-400 hover:border-gray-500'}`}
                      >
                        Search by Project
                      </button>
                      <button
                        onClick={() => setGmailSearchMode('keywords')}
                        className={`px-3 py-1.5 text-xs rounded-lg border transition-colors ${gmailSearchMode === 'keywords' ? 'border-teal-500 bg-teal-500/10 text-teal-300' : 'border-gray-600 text-gray-400 hover:border-gray-500'}`}
                      >
                        Search by Keywords
                      </button>
                    </div>
                  </div>

                  {gmailSearchMode === 'project' && (
                    <div className="p-3 bg-gray-800/50 rounded-lg border border-gray-700">
                      <p className="text-xs text-gray-400 mb-1">Will search Gmail for:</p>
                      <p className="text-sm text-white">
                        {(() => {
                          const project = projects.find(p => p.id === selectedProjectId);
                          if (!project) return '—';
                          const parts: string[] = [];
                          if (project.name) parts.push(`"${project.name}"`);
                          if (project.project_code) parts.push(`"${project.project_code}"`);
                          return parts.join(' OR ');
                        })()}
                      </p>
                    </div>
                  )}

                  {gmailSearchMode === 'keywords' && (
                    <div>
                      <label className="block text-xs font-medium text-gray-400 mb-1">Keywords</label>
                      <input
                        type="text"
                        value={gmailKeywords}
                        onChange={(e) => setGmailKeywords(e.target.value)}
                        placeholder="e.g. quarterly report, budget review"
                        className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-teal-500"
                      />
                    </div>
                  )}

                  <div>
                    <label className="block text-xs font-medium text-gray-400 mb-1">Max Results</label>
                    <input
                      type="number"
                      value={gmailCount}
                      onChange={(e) => setGmailCount(Math.min(50, Math.max(1, parseInt(e.target.value) || 10)))}
                      min={1}
                      max={50}
                      className="w-24 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-white focus:outline-none focus:ring-1 focus:ring-teal-500"
                    />
                  </div>

                  <div className="flex justify-end pt-2">
                    <button
                      onClick={handleGmailFetch}
                      disabled={gmailLoading || !gmailStatus?.connected || (gmailSearchMode === 'keywords' && !gmailKeywords.trim())}
                      className="px-4 py-2 text-sm font-medium rounded-lg bg-teal-600 text-white hover:bg-teal-500 disabled:opacity-50 transition-colors"
                    >
                      {gmailLoading ? 'Fetching...' : 'Fetch Emails'}
                    </button>
                  </div>
                </>
              )}
            </div>
          )}

          {step === 'gmail-results' && (
            <div className="space-y-3 max-h-96 overflow-y-auto">
              <div className="flex items-center justify-between">
                <p className="text-xs text-gray-400">{gmailEmails.length} email(s) found</p>
                {selectedProjectId && (
                  <p className="text-xs text-teal-400">
                    → {projects.find(p => p.id === selectedProjectId)?.project_code || ''} — {projects.find(p => p.id === selectedProjectId)?.name}
                  </p>
                )}
              </div>
              {gmailEmails.map((email) => (
                <div key={email.message_id} className="p-3 rounded-lg border border-gray-700 bg-gray-800/50 space-y-2">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-white truncate">{email.subject}</p>
                      <p className="text-xs text-gray-400 truncate">{email.sender}</p>
                      <p className="text-xs text-gray-500">{email.date}</p>
                    </div>
                    {email.has_attachments && (
                      <span className="text-xs bg-blue-500/20 text-blue-300 px-2 py-0.5 rounded shrink-0">
                        📎 {email.attachments?.length || 0}
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-gray-400 line-clamp-2">{email.body_preview}</p>
                  {email.attachments?.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {email.attachments.map((att: any, i: number) => (
                        <span key={i} className="text-xs bg-gray-700 text-gray-300 px-2 py-0.5 rounded">
                          {att.filename}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))}

              {/* Add All to RAG / Result */}
              {addAllResult ? (
                <div className="p-3 rounded-lg bg-green-500/10 border border-green-500/30 text-green-300 text-sm">
                  ✓ {addAllResult}
                </div>
              ) : (
                <div className="flex justify-between items-center pt-3 border-t border-gray-700">
                  <button
                    onClick={() => setStep('gmail-fetch')}
                    className="px-3 py-1.5 text-xs rounded-md border border-gray-600 text-gray-300 hover:bg-gray-800"
                  >
                    ← Back to Search
                  </button>
                  <button
                    onClick={handleAddAllToRag}
                    disabled={addAllLoading || gmailEmails.length === 0}
                    className="px-4 py-2 text-sm font-medium rounded-lg bg-teal-600 text-white hover:bg-teal-500 disabled:opacity-50 transition-colors"
                  >
                    {addAllLoading ? 'Adding all to RAG...' : `Add All ${gmailEmails.length} Email(s) to RAG`}
                  </button>
                </div>
              )}

              {addAllResult && (
                <div className="flex justify-end pt-2">
                  <button
                    onClick={handleClose}
                    className="px-3 py-1.5 text-xs rounded-md bg-gray-700 text-gray-300 hover:bg-gray-600"
                  >
                    Done
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
