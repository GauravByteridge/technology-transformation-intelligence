import { create } from 'zustand';
import type { ChatMessage, Conversation } from '@/types';

interface ChatSessionState {
  activeConversationId: string | null;
  messages: ChatMessage[];
  conversations: Conversation[];
}

interface ChatSessionActions {
  addMessage: (message: ChatMessage) => void;
  startNewConversation: (projectId?: string) => string;
  setActiveConversation: (id: string) => void;
  getActiveConversation: () => Conversation | undefined;
}

type ChatSessionStore = ChatSessionState & ChatSessionActions;

export const useChatSessionStore = create<ChatSessionStore>((set, get) => ({
  activeConversationId: null,
  messages: [],
  conversations: [],

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
      messages: [],
    }));

    return conversationId;
  },

  setActiveConversation: (id: string) => {
    const conversation = get().conversations.find((conv) => conv.id === id);

    set({
      activeConversationId: id,
      messages: conversation?.messages ?? [],
    });
  },

  getActiveConversation: (): Conversation | undefined => {
    const { activeConversationId, conversations } = get();
    if (!activeConversationId) return undefined;
    return conversations.find((conv) => conv.id === activeConversationId);
  },
}));
