// AI Chat feature module barrel export
export { useChatSessionStore } from './stores/chatSessionStore';
export { useAIChat } from './hooks/useAIChat';
export { useQueryHistory } from './hooks/useQueryHistory';

// Components
export { ChatThread } from './components/ChatThread';
export { ChatInput } from './components/ChatInput';
export { MessageBubble } from './components/MessageBubble';
export { QueryHistory } from './components/QueryHistory';
export { EvidencePanel } from './components/EvidencePanel';
export { VisualizationRenderer } from './components/VisualizationRenderer';
export { SourcesUsedPanel } from './components/SourcesUsedPanel';
export { PartialFailureWarning } from './components/PartialFailureWarning';
export { DataLineagePanel } from './components/DataLineagePanel';

export type {
  AIQueryRequest,
  AIResponse,
  ChatMessage,
  Conversation,
  QueryHistoryEntry,
  SourceEvidence,
  SourceType,
} from './types';
