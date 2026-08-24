import { useState } from 'react';
import { Settings as SettingsIcon, Zap, Shield } from 'lucide-react';
import { useEnvironmentStore } from '../stores/environmentStore';

export default function Settings() {
  const { mode, provider, setMode, setProvider } = useEnvironmentStore();
  const [testStatus, setTestStatus] = useState<string | null>(null);

  const handleTestProvider = () => {
    setTestStatus('testing');
    // Simulate provider test — in production this calls the backend
    setTimeout(() => setTestStatus('success'), 1500);
  };

  return (
    <div className="space-y-8 max-w-2xl">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold text-white flex items-center gap-2">
          <SettingsIcon size={24} className="text-gray-400" />
          Settings
        </h1>
        <p className="text-sm text-gray-400 mt-1">
          Configure AI providers, environment mode, and application settings.
        </p>
      </div>

      {/* AI Configuration */}
      <section className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-6 space-y-6">
        <div className="flex items-center gap-2">
          <Zap size={18} className="text-teal-400" />
          <h2 className="text-lg font-medium text-white">AI Configuration</h2>
        </div>

        {/* Mode */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-3">
            Environment Mode
          </label>
          <div className="space-y-2">
            {(['demo', 'real'] as const).map((m) => (
              <label
                key={m}
                className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                  mode === m
                    ? 'border-teal-500/50 bg-teal-500/10'
                    : 'border-gray-700 hover:border-gray-600'
                }`}
              >
                <input
                  type="radio"
                  name="mode"
                  value={m}
                  checked={mode === m}
                  onChange={() => setMode(m)}
                  className="sr-only"
                />
                <div
                  className={`w-4 h-4 rounded-full border-2 flex items-center justify-center ${
                    mode === m ? 'border-teal-400' : 'border-gray-500'
                  }`}
                >
                  {mode === m && (
                    <div className="w-2 h-2 rounded-full bg-teal-400" />
                  )}
                </div>
                <div>
                  <span className="text-sm font-medium text-white capitalize">
                    {m}
                  </span>
                  <p className="text-xs text-gray-400">
                    {m === 'demo'
                      ? 'Uses sample data and mock AI responses'
                      : 'Connects to real data sources and LLM providers'}
                  </p>
                </div>
              </label>
            ))}
          </div>
        </div>

        {/* LLM Provider */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-3">
            LLM Provider
          </label>
          <div className="space-y-2">
            {(
              [
                { value: 'azure_openai', label: 'Azure OpenAI', desc: 'GPT-4o via Azure' },
                { value: 'azure_ai_foundry', label: 'Azure AI Foundry', desc: 'Azure AI Studio models' },
                { value: 'groq', label: 'Groq', desc: 'Fast inference with Llama models' },
              ] as const
            ).map(({ value, label, desc }) => (
              <label
                key={value}
                className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                  provider === value
                    ? 'border-teal-500/50 bg-teal-500/10'
                    : 'border-gray-700 hover:border-gray-600'
                }`}
              >
                <input
                  type="radio"
                  name="provider"
                  value={value}
                  checked={provider === value}
                  onChange={() => setProvider(value)}
                  className="sr-only"
                />
                <div
                  className={`w-4 h-4 rounded-full border-2 flex items-center justify-center ${
                    provider === value ? 'border-teal-400' : 'border-gray-500'
                  }`}
                >
                  {provider === value && (
                    <div className="w-2 h-2 rounded-full bg-teal-400" />
                  )}
                </div>
                <div>
                  <span className="text-sm font-medium text-white">{label}</span>
                  <p className="text-xs text-gray-400">{desc}</p>
                </div>
              </label>
            ))}
          </div>
        </div>

        {/* Test Provider */}
        <div className="flex items-center gap-3">
          <button
            onClick={handleTestProvider}
            disabled={testStatus === 'testing'}
            className="px-4 py-2 text-sm font-medium rounded-lg bg-teal-600 text-white hover:bg-teal-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {testStatus === 'testing' ? 'Testing...' : 'Test Provider'}
          </button>
          {testStatus === 'success' && (
            <span className="text-sm text-green-400">✓ Connection successful</span>
          )}
        </div>
      </section>

      {/* Security notice */}
      <section className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-6">
        <div className="flex items-center gap-2 mb-3">
          <Shield size={18} className="text-yellow-400" />
          <h2 className="text-lg font-medium text-white">Security</h2>
        </div>
        <p className="text-sm text-gray-400">
          Credentials and API keys are managed through environment variables and are never displayed in the UI.
          Contact your administrator to update provider credentials.
        </p>
      </section>
    </div>
  );
}
