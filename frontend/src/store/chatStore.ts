import { create } from 'zustand';
import { chatApi } from '@/lib/api';

export interface Message {
  id: string;
  chat_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  sources?: Source[];
  confidence_score?: number;
  tokens_used?: number;
  reaction?: string;
  is_flagged: boolean;
  processing_time_ms?: number;
  model_used?: string;
  created_at: string;
}

export interface Source {
  document_id: string;
  title: string;
  content: string;
  score: number;
  page?: number;
}

export interface Chat {
  id: string;
  user_id: string;
  title: string;
  is_pinned: boolean;
  is_archived: boolean;
  message_count: number;
  last_message_at?: string;
  created_at: string;
  updated_at: string;
  messages?: Message[];
}

interface ChatState {
  chats: Chat[];
  activeChat: Chat | null;
  messages: Message[];
  isLoading: boolean;
  isSending: boolean;
  streamingContent: string;
  isStreaming: boolean;
  total: number;
  page: number;
  aiProvider: 'ollama' | 'gemini' | 'auto';

  fetchChats: (params?: any) => Promise<void>;
  createChat: (title?: string) => Promise<Chat>;
  selectChat: (chatId: string) => Promise<void>;
  deleteChat: (chatId: string) => Promise<void>;
  updateChat: (chatId: string, data: any) => Promise<void>;
  sendMessage: (chatId: string, content: string) => Promise<void>;
  reactToMessage: (chatId: string, messageId: string, reaction: string) => Promise<void>;
  setActiveChat: (chat: Chat | null) => void;
  clearMessages: () => void;
  setAIProvider: (provider: 'ollama' | 'gemini' | 'auto') => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  chats: [],
  activeChat: null,
  messages: [],
  isLoading: false,
  isSending: false,
  streamingContent: '',
  isStreaming: false,
  total: 0,
  page: 1,
  aiProvider: (typeof window !== 'undefined'
    ? (localStorage.getItem('medrag_ai_provider') as 'ollama' | 'gemini' | 'auto')
    : null) || 'auto',

  setAIProvider: (provider) => {
    if (typeof window !== 'undefined') localStorage.setItem('medrag_ai_provider', provider);
    set({ aiProvider: provider });
  },

  fetchChats: async (params) => {
    set({ isLoading: true });
    try {
      const { data } = await chatApi.list(params);
      set({ chats: data.chats, total: data.total, isLoading: false });
    } catch {
      set({ isLoading: false });
    }
  },

  createChat: async (title = 'New Chat') => {
    const { data } = await chatApi.create({ title });
    set((state) => ({ chats: [data, ...state.chats] }));
    return data;
  },

  selectChat: async (chatId) => {
    set({ isLoading: true });
    try {
      const { data } = await chatApi.get(chatId);
      set({ activeChat: data, messages: data.messages || [], isLoading: false });
    } catch {
      set({ isLoading: false });
    }
  },

  deleteChat: async (chatId) => {
    await chatApi.delete(chatId);
    set((state) => ({
      chats: state.chats.filter((c) => c.id !== chatId),
      activeChat: state.activeChat?.id === chatId ? null : state.activeChat,
      messages: state.activeChat?.id === chatId ? [] : state.messages,
    }));
  },

  updateChat: async (chatId, data) => {
    const { data: updated } = await chatApi.update(chatId, data);
    set((state) => ({
      chats: state.chats.map((c) => (c.id === chatId ? updated : c)),
      activeChat: state.activeChat?.id === chatId ? updated : state.activeChat,
    }));
  },

  sendMessage: async (chatId, content) => {
    const userMsg: Message = {
      id: `temp-${Date.now()}`,
      chat_id: chatId,
      role: 'user',
      content,
      is_flagged: false,
      created_at: new Date().toISOString(),
    };
    set((state) => ({ messages: [...state.messages, userMsg], isSending: true }));

    try {
      const { data } = await chatApi.sendMessage(chatId, content, get().aiProvider);
      set((state) => ({
        messages: [...state.messages, data],
        isSending: false,
        chats: state.chats.map((c) =>
          c.id === chatId
            ? { ...c, message_count: c.message_count + 2, last_message_at: new Date().toISOString() }
            : c
        ),
      }));
    } catch (err) {
      set((state) => ({
        messages: state.messages.filter((m) => m.id !== userMsg.id),
        isSending: false,
      }));
      throw err;
    }
  },

  reactToMessage: async (chatId, messageId, reaction) => {
    await chatApi.react(chatId, messageId, reaction);
    set((state) => ({
      messages: state.messages.map((m) => (m.id === messageId ? { ...m, reaction } : m)),
    }));
  },

  setActiveChat: (chat) => set({ activeChat: chat }),
  clearMessages: () => set({ messages: [], activeChat: null }),
}));
