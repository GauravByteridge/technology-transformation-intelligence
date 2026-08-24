import { useCallback } from 'react';
import { useAIQuery } from '@/hooks';
import { useChatSessionStore } from '../stores/chatSessionStore';
import type { AIResponse, ChatMessage } from '@/types';

/**
 * Main AI chat hook that wraps useAIQuery with conversation threading.
 * Manages message history via the session store and automatically
 * threads conversation_id across sequential exchanges.
 */
export function useAIChat(projectId?: string) {
  const aiQuery = useAIQuery();
  const {
    messages,
    activeConversationId,
    addMessage,
    startNewConversation: storeStartNewConversation,
    getActiveConversation,
    latestResponse,
    setLatestResponse,
  } = useChatSessionStore();

  const sendMessage = useCallback(
    async (question: string) => {
      // Ensure a conversation exists; start one if this is the first message
      let conversationId = activeConversationId;
      if (!conversationId) {
        conversationId = storeStartNewConversation(projectId);
      }

      // Add user message to the store
      const userMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'user',
        content: question,
        timestamp: new Date().toISOString(),
      };
      addMessage(userMessage);

      // Determine conversation_id from the most recent assistant response.
      // On the first message in a new conversation, omit conversation_id.
      const activeConversation = getActiveConversation();
      const lastAssistantMessage = activeConversation?.messages
        .filter((m) => m.role === 'assistant')
        .at(-1);

      // Build the AI query payload
      const payload: {
        question: string;
        project_id?: string;
        conversation_id?: string;
      } = { question };

      if (projectId) {
        payload.project_id = projectId;
      }

      // Only include conversation_id if we have one from a previous response
      if (lastAssistantMessage?.queryId) {
        // The queryId on the assistant message stores the conversation_id from the AI response
        payload.conversation_id = lastAssistantMessage.queryId;
      }

      try {
        const response = await aiQuery.mutateAsync(payload);

        // Store the latest full response for evidence/visualization rendering
        setLatestResponse(response);

        // Add assistant message to the store with conversation_id for threading
        const assistantMessage: ChatMessage = {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: response.answer,
          timestamp: new Date().toISOString(),
          queryId: response.conversation_id,
          visualizationSpec: response.visualization_spec,
          responseType: response.response_type,
        };
        addMessage(assistantMessage);
      } catch (error) {
        // Add error message to the store
        const errorContent =
          error instanceof Error
            ? error.message
            : 'An unexpected error occurred. Please try again.';

        const errorMessage: ChatMessage = {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: `Error: ${errorContent}`,
          timestamp: new Date().toISOString(),
        };
        addMessage(errorMessage);
      }
    },
    [
      activeConversationId,
      projectId,
      addMessage,
      storeStartNewConversation,
      getActiveConversation,
      aiQuery,
    ],
  );

  const startNewConversation = useCallback(() => {
    storeStartNewConversation(projectId);
    setLatestResponse(null);
  }, [storeStartNewConversation, projectId]);

  return {
    sendMessage,
    isLoading: aiQuery.isPending,
    messages,
    latestResponse,
    error: aiQuery.error,
    startNewConversation,
  };
}
