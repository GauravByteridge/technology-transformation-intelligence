import { create } from 'zustand';
import { persist } from 'zustand/middleware';

type AppMode = 'demo' | 'real';
type LlmProvider = 'azure_openai' | 'azure_ai_foundry' | 'groq';

interface EnvironmentState {
  mode: AppMode;
  provider: LlmProvider;
  setMode: (mode: AppMode) => void;
  setProvider: (provider: LlmProvider) => void;
}

export const useEnvironmentStore = create<EnvironmentState>()(
  persist(
    (set) => ({
      mode: 'real',
      provider: 'azure_openai',
      setMode: (mode) => set({ mode }),
      setProvider: (provider) => set({ provider }),
    }),
    {
      name: 'environment-settings',
    }
  )
);
