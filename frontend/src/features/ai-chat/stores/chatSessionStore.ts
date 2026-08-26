import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { ChatMessage, Conversation, AIResponse } from '@/types';

interface ChatSessionState {
  activeConversationId: string | null;
  activeProjectId: string | null;
  messages: ChatMessage[];
  conversations: Conversation[];
  latestResponse: AIResponse | null;
}

interface ChatSessionActions {
  addMessage: (message: ChatMessage) => void;
  startNewConversation: (projectId?: string) => string;
  setActiveConversation: (id: string) => void;
  setActiveProject: (projectId: string | null) => void;
  getActiveConversation: () => Conversation | undefined;
  getConversationsForProject: (projectId: string | null) => Conversation[];
  setLatestResponse: (response: AIResponse | null) => void;
}

type ChatSessionStore = ChatSessionState & ChatSessionActions;

export const useChatSessionStore = create<ChatSessionStore>()(
  persist(
    (set, get) => ({
      activeConversationId: null,
      activeProjectId: null,
      messages: [],
      conversations: [],
      latestResponse: null,

      addMessage: (message: ChatMessage) => {
        const { activeConversationId } = get();

        set((state) => {
          const updatedConversations = state.conversations.map((conv) => {
            if (conv.id === activeConversationId) {
              return {
                ...conv,
                messages: [...conv.messages, message],
                last_message_at: message.timestamp,
              };
            }
            return conv;
          });

          return {
            messages: [...state.messages, message],
            conversations: updatedConversations,
          };
        });
      },

      startNewConversation: (projectId?: string): string => {
        const conversationId = crypto.randomUUID();
        const now = new Date().toISOString();

        const newConversation: Conversation = {
          id: conversationId,
          project_id: projectId,
          messages: [],
          created_at: now,
          last_message_at: now,
        };

        set((state) => ({
          conversations: [...state.conversations, newConversation],
          activeConversationId: conversationId,
          activeProjectId: projectId || state.activeProjectId,
          messages: [],
          latestResponse: null,
        }));

        return conversationId;
      },

      setActiveConversation: (id: string) => {
        const conversation = get().conversations.find((conv) => conv.id === id);

        set({
          activeConversationId: id,
          messages: conversation?.messages ?? [],
          latestResponse: null,
        });
      },

      setActiveProject: (projectId: string | null) => {
        const { conversations, activeProjectId } = get();

        // If same project, no-op
        if (projectId === activeProjectId) return;

        // Find the most recent conversation for this project
        const projectConversations = conversations
          .filter((c) => c.project_id === projectId)
          .sort((a, b) => (b.last_message_at || '').localeCompare(a.last_message_at || ''));

        const latestConv = projectConversations[0];

        if (latestConv) {
          // Switch to existing conversation for this project
          set({
            activeProjectId: projectId,
            activeConversationId: latestConv.id,
            messages: latestConv.messages,
            latestResponse: null,
          });
        } else {
          // No conversation exists for this project — start fresh
          set({
            activeProjectId: projectId,
            activeConversationId: null,
            messages: [],
            latestResponse: null,
          });
        }
      },

      getActiveConversation: (): Conversation | undefined => {
        const { activeConversationId, conversations } = get();
        if (!activeConversationId) return undefined;
        return conversations.find((conv) => conv.id === activeConversationId);
      },

      getConversationsForProject: (projectId: string | null): Conversation[] => {
        const { conversations } = get();
        return conversations
          .filter((c) => c.project_id === projectId)
          .sort((a, b) => (b.last_message_at || '').localeCompare(a.last_message_at || ''));
      },

      setLatestResponse: (response: AIResponse | null) => {
        set({ latestResponse: response });
      },
    }),
    {
      name: 'chat-session-store',
    }
  )
);
