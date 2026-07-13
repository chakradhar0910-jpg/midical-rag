'use client';
import { useQuery } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { MessageSquare, FileText, Brain, ArrowRight, Clock, TrendingUp, Activity, Plus } from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { useI18n } from '@/i18n/context';
import { chatApi, documentApi } from '@/lib/api';
import { formatRelativeTime, formatBytes } from '@/lib/utils';

function StatCard({ icon: Icon, label, value, color }: any) {
  return (
    <div className="bg-card border rounded-xl p-5">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-muted-foreground">{label}</p>
          <p className="text-3xl font-bold mt-1">{value}</p>
        </div>
        <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${color}`}>
          <Icon className="w-5 h-5" />
        </div>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const router = useRouter();
  const { user } = useAuthStore();
  const { t } = useI18n();
  const { data: chatsData } = useQuery({ queryKey: ['chats'], queryFn: () => chatApi.list({ page_size: 5 }) });
  const { data: docsData } = useQuery({ queryKey: ['documents'], queryFn: () => documentApi.list({ page_size: 5 }) });

  const recentChats = chatsData?.data?.chats || [];
  const recentDocs = docsData?.data?.documents || [];

  const hour = new Date().getHours();
  const greeting = hour < 12 ? t('dashboard.greeting.morning') : hour < 18 ? t('dashboard.greeting.afternoon') : t('dashboard.greeting.evening');

  const handleNewChat = async () => {
    const { data } = await chatApi.create({ title: 'New Chat' });
    router.push(`/chat?id=${data.id}`);
  };

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold">
          {greeting}, <span className="text-primary">{user?.full_name?.split(' ')[0] || user?.username}</span> 👋
        </h1>
        <p className="text-muted-foreground mt-1">{t('dashboard.overview')}</p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard icon={MessageSquare} label={t('dashboard.stats.totalChats')} value={chatsData?.data?.total || 0} color="bg-blue-500/10 text-blue-600" />
        <StatCard icon={FileText} label={t('dashboard.stats.documents')} value={docsData?.data?.total || 0} color="bg-green-500/10 text-green-600" />
        <StatCard icon={Brain} label={t('dashboard.stats.aiQueries')} value={recentChats.reduce((a: number, c: any) => a + (c.message_count || 0), 0)} color="bg-purple-500/10 text-purple-600" />
        <StatCard icon={Activity} label={t('dashboard.stats.activeToday')} value={recentChats.filter((c: any) => new Date(c.updated_at).toDateString() === new Date().toDateString()).length} color="bg-primary/10 text-primary" />
      </div>

      <div className="grid md:grid-cols-3 gap-4 mb-8">
        <button onClick={handleNewChat} className="flex items-center gap-4 p-5 bg-primary text-white rounded-xl hover:bg-primary/90 transition-all hover:scale-[1.02] shadow-lg shadow-primary/20">
          <Plus className="w-8 h-8" />
          <div className="text-left">
            <p className="font-semibold">{t('dashboard.quickActions.newChat')}</p>
            <p className="text-primary-foreground/70 text-sm">{t('dashboard.quickActions.newChatDesc')}</p>
          </div>
        </button>
        <Link href="/documents" className="flex items-center gap-4 p-5 bg-card border rounded-xl hover:bg-muted transition-all hover:scale-[1.02]">
          <FileText className="w-8 h-8 text-primary" />
          <div>
            <p className="font-semibold">{t('dashboard.quickActions.uploadDoc')}</p>
            <p className="text-muted-foreground text-sm">{t('dashboard.quickActions.uploadDocDesc')}</p>
          </div>
        </Link>
        <Link href="/profile" className="flex items-center gap-4 p-5 bg-card border rounded-xl hover:bg-muted transition-all hover:scale-[1.02]">
          <TrendingUp className="w-8 h-8 text-primary" />
          <div>
            <p className="font-semibold">{t('dashboard.quickActions.viewProfile')}</p>
            <p className="text-muted-foreground text-sm">{t('dashboard.quickActions.viewProfileDesc')}</p>
          </div>
        </Link>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        <div className="bg-card border rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold">{t('dashboard.recentChats')}</h2>
            <Link href="/chat" className="text-sm text-primary hover:underline flex items-center gap-1">
              {t('dashboard.viewAll')} <ArrowRight className="w-3 h-3" />
            </Link>
          </div>
          <div className="space-y-3">
            {recentChats.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <MessageSquare className="w-10 h-10 mx-auto mb-2 opacity-40" />
                <p className="text-sm">{t('dashboard.noChats')}</p>
                <button onClick={handleNewChat} className="text-primary text-sm mt-2 hover:underline">{t('chat.startNewChat')}</button>
              </div>
            ) : recentChats.map((chat: any) => (
              <Link href={`/chat?id=${chat.id}`} key={chat.id} className="flex items-start gap-3 p-3 rounded-lg hover:bg-muted transition-colors">
                <div className="w-8 h-8 bg-primary/10 rounded-lg flex items-center justify-center flex-shrink-0">
                  <MessageSquare className="w-4 h-4 text-primary" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium truncate">{chat.title}</p>
                  <div className="flex items-center gap-2 mt-0.5">
                    <Clock className="w-3 h-3 text-muted-foreground" />
                    <p className="text-xs text-muted-foreground">{formatRelativeTime(chat.updated_at)}</p>
                    <span className="text-xs text-muted-foreground">· {chat.message_count} {t('chat.messages')}</span>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </div>

        <div className="bg-card border rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold">{t('dashboard.recentDocuments')}</h2>
            <Link href="/documents" className="text-sm text-primary hover:underline flex items-center gap-1">
              {t('dashboard.viewAll')} <ArrowRight className="w-3 h-3" />
            </Link>
          </div>
          <div className="space-y-3">
            {recentDocs.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <FileText className="w-10 h-10 mx-auto mb-2 opacity-40" />
                <p className="text-sm">{t('dashboard.noDocs')}</p>
                <Link href="/documents" className="text-primary text-sm mt-2 hover:underline block">{t('documents.uploadFirst')}</Link>
              </div>
            ) : recentDocs.map((doc: any) => (
              <div key={doc.id} className="flex items-start gap-3 p-3 rounded-lg hover:bg-muted transition-colors">
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 text-xs font-bold ${
                  doc.file_type === 'pdf' ? 'bg-red-100 text-red-600' :
                  doc.file_type === 'docx' ? 'bg-blue-100 text-blue-600' : 'bg-gray-100 text-gray-600'}`}>
                  {doc.file_type?.toUpperCase()}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium truncate">{doc.title}</p>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className={`text-xs px-1.5 py-0.5 rounded-full ${
                      doc.status === 'processed' ? 'bg-green-100 text-green-700' :
                      doc.status === 'processing' ? 'bg-yellow-100 text-yellow-700' :
                      doc.status === 'failed' ? 'bg-red-100 text-red-700' : 'bg-gray-100 text-gray-600'
                    }`}>{t(`documents.status.${doc.status}`) || doc.status}</span>
                    <span className="text-xs text-muted-foreground">{formatBytes(doc.file_size)}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
