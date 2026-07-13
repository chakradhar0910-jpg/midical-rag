'use client';
import { useEffect, useRef, useState, useCallback } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  Send, Plus, Trash2, Pin, Archive, Download, ThumbsUp, ThumbsDown,
  Search, MessageSquare, ChevronDown, AlertCircle, BookOpen, Loader2,
  Copy, Check, MoreVertical
} from 'lucide-react';
import { useChatStore, Message } from '@/store/chatStore';
import { chatApi } from '@/lib/api';
import { formatRelativeTime, cn } from '@/lib/utils';
import { ProviderSelector } from '@/components/chat/ProviderSelector';
import toast from 'react-hot-toast';

function TypingIndicator() {
  return (
    <div className="flex items-end gap-2 px-4 py-2 message-enter">
      <div className="w-7 h-7 bg-primary/20 rounded-full flex items-center justify-center flex-shrink-0">
        <span className="text-primary text-xs font-bold">AI</span>
      </div>
      <div className="bg-muted px-4 py-3 rounded-2xl rounded-bl-sm">
        <div className="flex gap-1 items-center h-4">
          {[0, 1, 2].map(i => (
            <div key={i} className="typing-dot" style={{ animationDelay: `${i * 0.2}s` }} />
          ))}
        </div>
      </div>
    </div>
  );
}

function SourceCard({ source }: { source: any }) {
  return (
    <div className="source-card">
      <div className="flex items-center gap-1 font-medium mb-1">
        <BookOpen className="w-3 h-3" />
        <span className="truncate">{source.title}</span>
        <span className="ml-auto text-muted-foreground">{Math.round(source.score * 100)}%</span>
      </div>
      <p className="text-muted-foreground line-clamp-2">{source.content}</p>
    </div>
  );
}

function MessageBubble({ message, chatId, onReact }: { message: Message; chatId: string; onReact: (id: string, r: string) => void }) {
  const [copied, setCopied] = useState(false);
  const [showSources, setShowSources] = useState(false);
  const isUser = message.role === 'user';

  const copyText = async () => {
    await navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className={cn('flex items-end gap-2 px-4 py-1.5 message-enter group', isUser && 'flex-row-reverse')}>
      {/* Avatar */}
      <div className={cn('w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 text-xs font-bold',
        isUser ? 'bg-primary text-white' : 'bg-primary/20 text-primary')}>
        {isUser ? 'Me' : 'AI'}
      </div>

      <div className={cn('max-w-[75%] space-y-1', isUser && 'items-end flex flex-col')}>
        {/* Bubble */}
        <div className={cn('px-4 py-3 rounded-2xl text-sm',
          isUser ? 'bg-primary text-white rounded-br-sm' : 'bg-muted rounded-bl-sm')}>
          {isUser ? (
            <p className="whitespace-pre-wrap">{message.content}</p>
          ) : (
            <div className="prose prose-sm dark:prose-invert max-w-none">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
            </div>
          )}
        </div>

        {/* Sources */}
        {!isUser && message.sources && message.sources.length > 0 && (
          <div className="w-full">
            <button onClick={() => setShowSources(!showSources)}
              className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors">
              <BookOpen className="w-3 h-3" />
              {message.sources.length} source{message.sources.length > 1 ? 's' : ''}
              <ChevronDown className={cn('w-3 h-3 transition-transform', showSources && 'rotate-180')} />
              {message.confidence_score && (
                <span className="ml-2 text-primary">{Math.round(message.confidence_score * 100)}% confidence</span>
              )}
            </button>
            {showSources && (
              <div className="mt-2 space-y-2">
                {message.sources.map((s, i) => <SourceCard key={i} source={s} />)}
              </div>
            )}
          </div>
        )}

        {/* Emergency banner */}
        {!isUser && message.content.includes('EMERGENCY DETECTED') && (
          <div className="flex items-center gap-2 bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded-lg text-xs">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span className="font-medium">Emergency detected — please call emergency services immediately</span>
          </div>
        )}

        {/* Actions */}
        <div className={cn('flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity', isUser && 'flex-row-reverse')}>
          {!isUser && message.model_used && (
            <span className="text-xs text-muted-foreground/70 font-mono mr-1">{message.model_used}</span>
          )}
          <span className="text-xs text-muted-foreground">{formatRelativeTime(message.created_at)}</span>
          <button onClick={copyText} className="p-1 rounded hover:bg-muted transition-colors text-muted-foreground hover:text-foreground">
            {copied ? <Check className="w-3 h-3 text-green-500" /> : <Copy className="w-3 h-3" />}
          </button>
          {!isUser && (
            <>
              <button onClick={() => onReact(message.id, 'like')}
                className={cn('p-1 rounded hover:bg-muted transition-colors', message.reaction === 'like' ? 'text-green-600' : 'text-muted-foreground hover:text-foreground')}>
                <ThumbsUp className="w-3 h-3" />
              </button>
              <button onClick={() => onReact(message.id, 'dislike')}
                className={cn('p-1 rounded hover:bg-muted transition-colors', message.reaction === 'dislike' ? 'text-red-500' : 'text-muted-foreground hover:text-foreground')}>
                <ThumbsDown className="w-3 h-3" />
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function ChatContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const chatIdParam = searchParams.get('id');
  const {
    chats, activeChat, messages, isLoading, isSending,
    fetchChats, createChat, selectChat, deleteChat, updateChat,
    sendMessage, reactToMessage, setActiveChat, clearMessages
  } = useChatStore();
  const [input, setInput] = useState('');
  const [search, setSearch] = useState('');
  const [editingTitle, setEditingTitle] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const titleInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => { fetchChats(); }, []);

  useEffect(() => {
    if (chatIdParam) selectChat(chatIdParam);
    else clearMessages();
  }, [chatIdParam]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isSending]);

  const handleNewChat = async () => {
    const chat = await createChat('New Chat');
    router.push(`/chat?id=${chat.id}`);
  };

  const handleSend = async () => {
    if (!input.trim() || isSending || !activeChat) return;
    const content = input.trim();
    setInput('');
    try {
      await sendMessage(activeChat.id, content);
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      toast.error(detail || 'Failed to send message', { duration: 6000 });
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleDelete = async (chatId: string) => {
    if (!confirm('Delete this chat?')) return;
    await deleteChat(chatId);
    if (chatIdParam === chatId) router.push('/chat');
    toast.success('Chat deleted');
  };

  const handlePin = async (chatId: string, pinned: boolean) => {
    await updateChat(chatId, { is_pinned: !pinned });
  };

  const handleRename = async (chatId: string, title: string) => {
    await updateChat(chatId, { title });
    setEditingTitle(null);
  };

  const handleExport = async (format: string) => {
    if (!activeChat) return;
    try {
      const { data } = await chatApi.export(activeChat.id, format);
      const url = URL.createObjectURL(new Blob([data]));
      const a = document.createElement('a');
      a.href = url;
      a.download = `chat-${activeChat.id}.${format}`;
      a.click();
    } catch { toast.error('Export failed'); }
  };

  const filteredChats = chats.filter(c => c.title.toLowerCase().includes(search.toLowerCase()));
  const pinnedChats = filteredChats.filter(c => c.is_pinned);
  const unpinnedChats = filteredChats.filter(c => !c.is_pinned);

  const ChatItem = ({ chat }: { chat: any }) => (
    <div className={cn('group flex items-center gap-2 px-3 py-2.5 rounded-lg cursor-pointer transition-all hover:bg-muted',
      chatIdParam === chat.id && 'bg-primary/10 border border-primary/20')}>
      {editingTitle === chat.id ? (
        <input ref={titleInputRef} defaultValue={chat.title} autoFocus
          className="flex-1 bg-transparent text-sm outline-none"
          onBlur={(e) => handleRename(chat.id, e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') handleRename(chat.id, (e.target as HTMLInputElement).value); }} />
      ) : (
        <button onClick={() => router.push(`/chat?id=${chat.id}`)} className="flex-1 text-left min-w-0">
          <p className="text-sm truncate">{chat.title}</p>
          <p className="text-xs text-muted-foreground">{formatRelativeTime(chat.updated_at)}</p>
        </button>
      )}
      <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
        <button onClick={(e) => { e.stopPropagation(); handlePin(chat.id, chat.is_pinned); }}
          className="p-1 rounded hover:bg-background" title={chat.is_pinned ? 'Unpin' : 'Pin'}>
          <Pin className={cn('w-3 h-3', chat.is_pinned && 'text-primary fill-primary')} />
        </button>
        <button onClick={(e) => { e.stopPropagation(); setEditingTitle(chat.id); }}
          className="p-1 rounded hover:bg-background" title="Rename">
          <MoreVertical className="w-3 h-3" />
        </button>
        <button onClick={(e) => { e.stopPropagation(); handleDelete(chat.id); }}
          className="p-1 rounded hover:bg-background text-destructive" title="Delete">
          <Trash2 className="w-3 h-3" />
        </button>
      </div>
    </div>
  );

  return (
    <div className="flex h-full">
      {/* Chat list sidebar */}
      <div className="w-64 flex-shrink-0 border-r bg-card flex flex-col">
        <div className="p-3 border-b space-y-2">
          <button onClick={handleNewChat}
            className="w-full flex items-center gap-2 justify-center bg-primary text-white text-sm font-medium py-2.5 rounded-lg hover:bg-primary/90 transition-colors">
            <Plus className="w-4 h-4" /> New Chat
          </button>
          <div className="relative">
            <Search className="w-4 h-4 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search chats..."
              className="w-full pl-8 pr-3 py-2 rounded-lg border bg-background text-sm focus:outline-none focus:ring-1 focus:ring-primary/30" />
          </div>
        </div>
        <div className="flex-1 overflow-y-auto p-2 space-y-0.5">
          {pinnedChats.length > 0 && (
            <>
              <p className="text-xs text-muted-foreground px-2 py-1 font-medium">📌 Pinned</p>
              {pinnedChats.map(c => <ChatItem key={c.id} chat={c} />)}
              <div className="my-2 border-t" />
            </>
          )}
          {unpinnedChats.map(c => <ChatItem key={c.id} chat={c} />)}
          {filteredChats.length === 0 && (
            <div className="text-center py-8 text-muted-foreground">
              <MessageSquare className="w-8 h-8 mx-auto mb-2 opacity-40" />
              <p className="text-sm">No chats found</p>
            </div>
          )}
        </div>
      </div>

      {/* Chat area */}
      <div className="flex-1 flex flex-col min-w-0">
        {activeChat ? (
          <>
            {/* Chat header */}
            <div className="border-b px-4 py-3 flex items-center justify-between bg-card">
              <div>
                <h2 className="font-semibold text-sm">{activeChat.title}</h2>
                <p className="text-xs text-muted-foreground">{activeChat.message_count} messages</p>
              </div>
              <div className="flex items-center gap-2">
                <ProviderSelector />
                {['json', 'csv'].map(fmt => (
                  <button key={fmt} onClick={() => handleExport(fmt)}
                    className="flex items-center gap-1 px-2 py-1.5 text-xs rounded hover:bg-muted transition-colors text-muted-foreground">
                    <Download className="w-3 h-3" /> {fmt.toUpperCase()}
                  </button>
                ))}
                <button onClick={() => handlePin(activeChat.id, activeChat.is_pinned)}
                  className={cn('p-1.5 rounded hover:bg-muted', activeChat.is_pinned && 'text-primary')}>
                  <Pin className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto py-4 space-y-1">
              {messages.length === 0 && (
                <div className="flex flex-col items-center justify-center h-full text-center px-4">
                  <div className="w-16 h-16 bg-primary/10 rounded-2xl flex items-center justify-center mb-4">
                    <MessageSquare className="w-8 h-8 text-primary" />
                  </div>
                  <h3 className="text-lg font-semibold mb-2">Start a Medical Conversation</h3>
                  <p className="text-muted-foreground text-sm max-w-md mb-6">Ask about symptoms, diseases, treatments, medications, or any medical topic. I'll provide evidence-based answers with source citations.</p>
                  <div className="grid grid-cols-2 gap-2 w-full max-w-sm">
                    {['What are symptoms of diabetes?', 'How to manage hypertension?', 'COVID-19 treatment protocols', 'Dengue fever warning signs'].map(q => (
                      <button key={q} onClick={() => { setInput(q); inputRef.current?.focus(); }}
                        className="text-left text-xs p-2.5 border rounded-lg hover:bg-muted transition-colors text-muted-foreground hover:text-foreground">
                        {q}
                      </button>
                    ))}
                  </div>
                </div>
              )}
              {messages.map((msg) => (
                <MessageBubble key={msg.id} message={msg} chatId={activeChat.id}
                  onReact={(id, r) => reactToMessage(activeChat.id, id, r)} />
              ))}
              {isSending && <TypingIndicator />}
              <div ref={messagesEndRef} />
            </div>

            {/* Input area */}
            <div className="border-t p-4 bg-card">
              <div className="flex items-end gap-2 bg-background border rounded-xl p-2">
                <textarea ref={inputRef} value={input} onChange={e => setInput(e.target.value)}
                  onKeyDown={handleKeyDown} placeholder="Ask a medical question..."
                  className="flex-1 resize-none bg-transparent text-sm outline-none max-h-32 min-h-[2.5rem] px-2 py-1.5"
                  rows={1}
                  onInput={e => {
                    const el = e.target as HTMLTextAreaElement;
                    el.style.height = 'auto';
                    el.style.height = Math.min(el.scrollHeight, 128) + 'px';
                  }}
                />
                <button onClick={handleSend} disabled={!input.trim() || isSending}
                  className="w-9 h-9 bg-primary text-white rounded-lg flex items-center justify-center hover:bg-primary/90 transition-colors disabled:opacity-40 flex-shrink-0">
                  {isSending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                </button>
              </div>
              <p className="text-xs text-muted-foreground mt-2 text-center">
                ⚕️ For medical emergencies, call 911 immediately. AI responses are for informational purposes only.
              </p>
            </div>
          </>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-center px-4">
            <div className="w-20 h-20 bg-primary/10 rounded-3xl flex items-center justify-center mb-6">
              <MessageSquare className="w-10 h-10 text-primary" />
            </div>
            <h2 className="text-2xl font-bold mb-2">MedicalRAG Chat</h2>
            <p className="text-muted-foreground max-w-md mb-8">
              Select a conversation from the sidebar or start a new one to get evidence-based medical answers.
            </p>
            <button onClick={handleNewChat} className="flex items-center gap-2 bg-primary text-white font-semibold px-6 py-3 rounded-xl hover:bg-primary/90 transition-colors">
              <Plus className="w-5 h-5" /> Start New Chat
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

import { Suspense } from 'react';
export default function ChatPage() {
  return (
    <Suspense fallback={<div className="flex h-full items-center justify-center"><div className="animate-spin w-8 h-8 border-4 border-primary border-t-transparent rounded-full" /></div>}>
      <ChatContent />
    </Suspense>
  );
}
