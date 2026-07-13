'use client';
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, BarChart, Bar, Legend
} from 'recharts';
import {
  Users, MessageSquare, FileText, Brain, TrendingUp, Activity,
  Shield, Search, ChevronDown, Loader2, Trash2, Edit2, Ban, CheckCircle,
  Cpu, Cloud, CircleCheck, CircleX
} from 'lucide-react';
import { adminApi, aiApi } from '@/lib/api';
import { formatRelativeTime, cn } from '@/lib/utils';
import toast from 'react-hot-toast';

const COLORS = ['#00c8d0', '#3b82f6', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444'];

const tabs = [
  { id: 'overview', label: 'Overview', icon: Activity },
  { id: 'users', label: 'Users', icon: Users },
  { id: 'documents', label: 'Documents', icon: FileText },
  { id: 'ai', label: 'AI Providers', icon: Cpu },
  { id: 'logs', label: 'Audit Logs', icon: Shield },
];

function StatCard({ icon: Icon, label, value, sub, color }: any) {
  return (
    <div className="bg-card border rounded-xl p-5">
      <div className="flex items-start justify-between mb-3">
        <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${color}`}>
          <Icon className="w-5 h-5" />
        </div>
      </div>
      <p className="text-3xl font-bold">{typeof value === 'number' ? value.toLocaleString() : value}</p>
      <p className="text-sm text-muted-foreground mt-1">{label}</p>
      {sub && <p className="text-xs text-primary mt-0.5">{sub}</p>}
    </div>
  );
}

export default function AdminPage() {
  const qc = useQueryClient();
  const [activeTab, setActiveTab] = useState('overview');
  const [userSearch, setUserSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [userPage, setUserPage] = useState(1);
  const [logPage, setLogPage] = useState(1);
  const [editUser, setEditUser] = useState<any>(null);
  const [days, setDays] = useState(30);

  const { data: statsData } = useQuery({ queryKey: ['admin-stats'], queryFn: adminApi.getStats });
  const { data: usersData, isLoading: usersLoading } = useQuery({
    queryKey: ['admin-users', userSearch, roleFilter, statusFilter, userPage],
    queryFn: () => adminApi.getUsers({ search: userSearch, role: roleFilter || undefined, status: statusFilter || undefined, page: userPage }),
    enabled: activeTab === 'users',
  });
  const { data: logsData } = useQuery({
    queryKey: ['admin-logs', logPage],
    queryFn: () => adminApi.getLogs({ page: logPage }),
    enabled: activeTab === 'logs',
  });
  const { data: usersAnalytics } = useQuery({
    queryKey: ['analytics-users', days],
    queryFn: () => adminApi.getUsersAnalytics(days),
    enabled: activeTab === 'overview',
  });
  const { data: chatsAnalytics } = useQuery({
    queryKey: ['analytics-chats', days],
    queryFn: () => adminApi.getChatsAnalytics(days),
    enabled: activeTab === 'overview',
  });
  const { data: adminDocsData } = useQuery({
    queryKey: ['admin-documents'],
    queryFn: () => adminApi.getDocuments({ page_size: 20 }),
    enabled: activeTab === 'documents',
  });
  const { data: aiHealth, refetch: refetchAiHealth, isFetching: aiHealthLoading } = useQuery({
    queryKey: ['admin-ai-health'],
    queryFn: () => aiApi.health(),
    enabled: activeTab === 'ai',
    refetchInterval: activeTab === 'ai' ? 15000 : false,
    retry: false,
  });

  const updateUserMut = useMutation({
    mutationFn: ({ id, data }: any) => adminApi.updateUser(id, data),
    onSuccess: () => { toast.success('User updated'); qc.invalidateQueries({ queryKey: ['admin-users'] }); setEditUser(null); },
    onError: () => toast.error('Update failed'),
  });

  const deleteUserMut = useMutation({
    mutationFn: (id: string) => adminApi.deleteUser(id),
    onSuccess: () => { toast.success('User deleted'); qc.invalidateQueries({ queryKey: ['admin-users'] }); },
    onError: (err: any) => toast.error(err?.response?.data?.detail || 'Delete failed'),
  });

  const stats = statsData?.data;
  const usersList = usersData?.data?.users || [];
  const logsArr = logsData?.data?.logs || [];
  const userChartData = (usersAnalytics?.data?.data || []).map((d: any) => ({
    date: new Date(d.date).toLocaleDateString('en', { month: 'short', day: 'numeric' }),
    value: d.value,
  }));
  const chatChartData = (chatsAnalytics?.data?.data || []).map((d: any) => ({
    date: new Date(d.date).toLocaleDateString('en', { month: 'short', day: 'numeric' }),
    value: d.value,
  }));

  const roleDist = usersList.length ? [
    { name: 'Admin', value: usersList.filter((u: any) => u.role === 'admin').length },
    { name: 'Doctor', value: usersList.filter((u: any) => u.role === 'doctor').length },
    { name: 'User', value: usersList.filter((u: any) => u.role === 'user').length },
  ].filter(d => d.value > 0) : [];

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">Admin Dashboard</h1>
        <p className="text-muted-foreground text-sm">Platform management and analytics</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-muted p-1 rounded-xl mb-6 w-fit">
        {tabs.map(tab => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)}
            className={cn('flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all',
              activeTab === tab.id ? 'bg-card shadow-sm' : 'text-muted-foreground hover:text-foreground')}>
            <tab.icon className="w-4 h-4" />{tab.label}
          </button>
        ))}
      </div>

      {/* Overview */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Stats grid */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard icon={Users} label="Total Users" value={stats?.total_users || 0} sub={`${stats?.new_users_today || 0} new today`} color="bg-blue-500/10 text-blue-600" />
            <StatCard icon={MessageSquare} label="Total Chats" value={stats?.total_chats || 0} color="bg-green-500/10 text-green-600" />
            <StatCard icon={FileText} label="Documents" value={stats?.total_documents || 0} sub={`${stats?.processed_documents || 0} processed`} color="bg-purple-500/10 text-purple-600" />
            <StatCard icon={Brain} label="AI Queries Today" value={stats?.ai_requests_today || 0} color="bg-primary/10 text-primary" />
          </div>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard icon={Activity} label="Active Users" value={stats?.active_users || 0} color="bg-yellow-500/10 text-yellow-600" />
            <StatCard icon={MessageSquare} label="Total Messages" value={stats?.total_messages || 0} color="bg-indigo-500/10 text-indigo-600" />
            <StatCard icon={Brain} label="Tokens Used" value={stats?.total_tokens_used?.toLocaleString() || 0} color="bg-pink-500/10 text-pink-600" />
            <StatCard icon={TrendingUp} label="Processed Docs" value={stats?.processed_documents || 0} color="bg-cyan-500/10 text-cyan-600" />
          </div>

          {/* Charts */}
          <div className="flex items-center gap-4 mb-2">
            <span className="text-sm font-medium">Time range:</span>
            {[7, 30, 90].map(d => (
              <button key={d} onClick={() => setDays(d)}
                className={cn('text-sm px-3 py-1 rounded-lg', days === d ? 'bg-primary text-white' : 'bg-muted hover:bg-muted/80')}>
                {d}d
              </button>
            ))}
          </div>
          <div className="grid lg:grid-cols-2 gap-6">
            <div className="bg-card border rounded-xl p-5">
              <h3 className="font-semibold mb-4">User Registrations</h3>
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={userChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip contentStyle={{ background: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: 8 }} />
                  <Line type="monotone" dataKey="value" stroke="#00c8d0" strokeWidth={2} dot={false} name="Users" />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <div className="bg-card border rounded-xl p-5">
              <h3 className="font-semibold mb-4">AI Queries</h3>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={chatChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip contentStyle={{ background: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: 8 }} />
                  <Bar dataKey="value" fill="#00c8d0" radius={[4, 4, 0, 0]} name="Queries" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}

      {/* Users Tab */}
      {activeTab === 'users' && (
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <div className="relative flex-1 max-w-sm">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <input value={userSearch} onChange={e => setUserSearch(e.target.value)} placeholder="Search users..."
                className="w-full pl-9 pr-3 py-2 rounded-lg border bg-background text-sm focus:outline-none focus:ring-1 focus:ring-primary/30" />
            </div>
            <select value={roleFilter} onChange={e => setRoleFilter(e.target.value)} className="px-3 py-2 rounded-lg border bg-background text-sm">
              <option value="">All Roles</option>
              {['admin', 'doctor', 'user', 'viewer'].map(r => <option key={r} value={r} className="capitalize">{r}</option>)}
            </select>
            <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} className="px-3 py-2 rounded-lg border bg-background text-sm">
              <option value="">All Status</option>
              {['active', 'pending', 'inactive', 'suspended'].map(s => <option key={s} value={s} className="capitalize">{s}</option>)}
            </select>
          </div>

          <div className="bg-card border rounded-xl overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-muted/50 border-b">
                <tr>
                  {['User', 'Role', 'Status', 'Joined', 'Actions'].map(h => (
                    <th key={h} className="text-left px-4 py-3 font-medium text-muted-foreground">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y">
                {usersLoading ? (
                  <tr><td colSpan={5} className="text-center py-8"><Loader2 className="w-6 h-6 animate-spin mx-auto text-primary" /></td></tr>
                ) : usersList.map((u: any) => (
                  <tr key={u.id} className="hover:bg-muted/30 transition-colors">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <div className="w-8 h-8 bg-primary/20 rounded-full flex items-center justify-center text-primary font-semibold text-xs">
                          {u.username?.[0]?.toUpperCase()}
                        </div>
                        <div>
                          <p className="font-medium">{u.full_name || u.username}</p>
                          <p className="text-xs text-muted-foreground">{u.email}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className={cn('text-xs px-2 py-0.5 rounded-full font-medium capitalize',
                        u.role === 'admin' ? 'bg-purple-100 text-purple-700' :
                        u.role === 'doctor' ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-700')}>
                        {u.role}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={cn('text-xs px-2 py-0.5 rounded-full font-medium capitalize',
                        u.status === 'active' ? 'bg-green-100 text-green-700' :
                        u.status === 'suspended' ? 'bg-red-100 text-red-700' : 'bg-yellow-100 text-yellow-700')}>
                        {u.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-muted-foreground text-xs">{formatRelativeTime(u.created_at)}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1">
                        <button onClick={() => setEditUser(u)} className="p-1.5 rounded hover:bg-muted" title="Edit">
                          <Edit2 className="w-3.5 h-3.5 text-muted-foreground" />
                        </button>
                        <button onClick={() => updateUserMut.mutate({ id: u.id, data: { status: u.status === 'active' ? 'suspended' : 'active' } })}
                          className="p-1.5 rounded hover:bg-muted" title={u.status === 'active' ? 'Suspend' : 'Activate'}>
                          {u.status === 'active' ? <Ban className="w-3.5 h-3.5 text-yellow-600" /> : <CheckCircle className="w-3.5 h-3.5 text-green-600" />}
                        </button>
                        <button onClick={() => { if (confirm(`Delete ${u.email}?`)) deleteUserMut.mutate(u.id); }}
                          className="p-1.5 rounded hover:bg-muted" title="Delete">
                          <Trash2 className="w-3.5 h-3.5 text-destructive" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Edit User Modal */}
          {editUser && (
            <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
              <div className="bg-card rounded-2xl border shadow-xl w-80 p-6">
                <h3 className="font-semibold mb-4">Edit User: {editUser.username}</h3>
                <div className="space-y-3">
                  <div>
                    <label className="text-sm font-medium mb-1 block">Role</label>
                    <select defaultValue={editUser.role} id="edit-role" className="w-full px-3 py-2 rounded-lg border bg-background text-sm">
                      {['admin', 'doctor', 'user', 'viewer'].map(r => <option key={r} value={r}>{r}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="text-sm font-medium mb-1 block">Status</label>
                    <select defaultValue={editUser.status} id="edit-status" className="w-full px-3 py-2 rounded-lg border bg-background text-sm">
                      {['active', 'inactive', 'suspended', 'pending'].map(s => <option key={s} value={s}>{s}</option>)}
                    </select>
                  </div>
                </div>
                <div className="flex gap-2 mt-5">
                  <button onClick={() => setEditUser(null)} className="flex-1 py-2 border rounded-lg text-sm hover:bg-muted">Cancel</button>
                  <button onClick={() => {
                    const role = (document.getElementById('edit-role') as HTMLSelectElement).value;
                    const status = (document.getElementById('edit-status') as HTMLSelectElement).value;
                    updateUserMut.mutate({ id: editUser.id, data: { role, status } });
                  }} className="flex-1 py-2 bg-primary text-white rounded-lg text-sm hover:bg-primary/90">Save</button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Documents Tab */}
      {activeTab === 'documents' && (
        <div className="bg-card border rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-muted/50 border-b">
              <tr>
                {['Document', 'Type', 'User', 'Status', 'Chunks', 'Uploaded'].map(h => (
                  <th key={h} className="text-left px-4 py-3 font-medium text-muted-foreground">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y">
              {(adminDocsData?.data?.documents || []).map((doc: any) => (
                <tr key={doc.id} className="hover:bg-muted/30">
                  <td className="px-4 py-3 font-medium max-w-[200px] truncate">{doc.title}</td>
                  <td className="px-4 py-3"><span className="text-xs bg-muted px-2 py-0.5 rounded font-mono">{doc.file_type}</span></td>
                  <td className="px-4 py-3 text-muted-foreground text-xs">{doc.user_id?.slice(0, 8)}...</td>
                  <td className="px-4 py-3">
                    <span className={cn('text-xs px-2 py-0.5 rounded-full font-medium',
                      doc.status === 'processed' ? 'bg-green-100 text-green-700' :
                      doc.status === 'failed' ? 'bg-red-100 text-red-700' : 'bg-yellow-100 text-yellow-700')}>
                      {doc.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">{doc.chunk_count}</td>
                  <td className="px-4 py-3 text-muted-foreground text-xs">{formatRelativeTime(doc.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* AI Providers Tab */}
      {activeTab === 'ai' && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">
              Real-time status of configured AI inference providers. Auto-refreshes every 15s.
            </p>
            <button onClick={() => refetchAiHealth()} disabled={aiHealthLoading}
              className="flex items-center gap-2 text-sm px-3 py-1.5 border rounded-lg hover:bg-muted transition-colors disabled:opacity-60">
              {aiHealthLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Cpu className="w-3.5 h-3.5" />}
              Refresh
            </button>
          </div>

          <div className="grid md:grid-cols-2 gap-6">
            {/* Ollama card */}
            <div className="bg-card border rounded-xl p-5">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <div className="w-10 h-10 bg-blue-500/10 rounded-xl flex items-center justify-center">
                    <Cpu className="w-5 h-5 text-blue-600" />
                  </div>
                  <div>
                    <h3 className="font-semibold">Ollama (Local)</h3>
                    <p className="text-xs text-muted-foreground">Strict local inference — never falls back silently</p>
                  </div>
                </div>
                <span className={cn('flex items-center gap-1 text-xs px-2.5 py-1 rounded-full font-medium',
                  aiHealth?.data?.ollama_running ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700')}>
                  {aiHealth?.data?.ollama_running ? <CircleCheck className="w-3 h-3" /> : <CircleX className="w-3 h-3" />}
                  {aiHealth?.data?.ollama_running ? 'Running' : 'Offline'}
                </span>
              </div>
              <div className="text-sm">
                <p className="text-muted-foreground mb-1">Installed models:</p>
                {(aiHealth?.data?.available_models || []).length > 0 ? (
                  <div className="flex flex-wrap gap-1.5">
                    {(aiHealth?.data?.available_models || []).map((m: string) => (
                      <span key={m} className="text-xs bg-muted px-2 py-1 rounded font-mono">{m}</span>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-muted-foreground italic">
                    {aiHealth?.data?.ollama_running ? 'No models installed' : 'Ollama not reachable'}
                  </p>
                )}
              </div>
            </div>

            {/* Gemini card */}
            <div className="bg-card border rounded-xl p-5">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <div className="w-10 h-10 bg-purple-500/10 rounded-xl flex items-center justify-center">
                    <Cloud className="w-5 h-5 text-purple-600" />
                  </div>
                  <div>
                    <h3 className="font-semibold">Gemini (Cloud)</h3>
                    <p className="text-xs text-muted-foreground">Strict cloud inference — never falls back silently</p>
                  </div>
                </div>
                <span className={cn('flex items-center gap-1 text-xs px-2.5 py-1 rounded-full font-medium',
                  aiHealth?.data?.gemini_available ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700')}>
                  {aiHealth?.data?.gemini_available ? <CircleCheck className="w-3 h-3" /> : <CircleX className="w-3 h-3" />}
                  {aiHealth?.data?.gemini_available ? 'Configured' : 'Not Configured'}
                </span>
              </div>
              <p className="text-sm text-muted-foreground">
                {aiHealth?.data?.gemini_available
                  ? 'GEMINI_API_KEY is set. Ready to receive requests.'
                  : 'Set GEMINI_API_KEY in backend/.env to enable.'}
              </p>
            </div>
          </div>

          {/* Default provider + routing info */}
          <div className="bg-card border rounded-xl p-5">
            <h3 className="font-semibold mb-3">Routing Configuration</h3>
            <div className="flex items-center gap-2 mb-4">
              <span className="text-sm text-muted-foreground">Default provider (when client sends no header):</span>
              <span className="text-xs bg-primary/10 text-primary px-2.5 py-1 rounded-full font-mono font-medium">
                {aiHealth?.data?.default_provider || '—'}
              </span>
            </div>
            <div className="space-y-2 text-sm text-muted-foreground">
              <p>• <code className="bg-muted px-1.5 py-0.5 rounded text-xs">X-AI-Provider: ollama</code> → strict local, errors if Ollama unavailable, never touches Gemini</p>
              <p>• <code className="bg-muted px-1.5 py-0.5 rounded text-xs">X-AI-Provider: gemini</code> → strict cloud, errors if Gemini unavailable, never touches Ollama</p>
              <p>• <code className="bg-muted px-1.5 py-0.5 rounded text-xs">X-AI-Provider: auto</code> → tries Ollama first, falls back to Gemini only if Ollama is down (explicitly logged)</p>
            </div>
          </div>
        </div>
      )}


      {/* Logs Tab */}
      {activeTab === 'logs' && (
        <div className="space-y-4">
          <div className="bg-card border rounded-xl overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-muted/50 border-b">
                <tr>
                  {['Time', 'User', 'Action', 'Resource', 'IP', 'Status'].map(h => (
                    <th key={h} className="text-left px-4 py-3 font-medium text-muted-foreground">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y">
                {logsArr.map((log: any) => (
                  <tr key={log.id} className="hover:bg-muted/30">
                    <td className="px-4 py-2.5 text-xs text-muted-foreground whitespace-nowrap">{new Date(log.created_at).toLocaleString()}</td>
                    <td className="px-4 py-2.5 text-xs">{log.username || log.user_id?.slice(0, 8) || 'System'}</td>
                    <td className="px-4 py-2.5"><span className="text-xs bg-muted px-2 py-0.5 rounded font-mono">{log.action}</span></td>
                    <td className="px-4 py-2.5 text-xs text-muted-foreground">{log.resource_type || '—'}</td>
                    <td className="px-4 py-2.5 text-xs text-muted-foreground font-mono">{log.ip_address || '—'}</td>
                    <td className="px-4 py-2.5">
                      <span className={cn('text-xs px-2 py-0.5 rounded-full font-medium', log.status === 'success' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700')}>
                        {log.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Total: {logsData?.data?.total || 0} logs</span>
            <div className="flex gap-2">
              <button disabled={logPage === 1} onClick={() => setLogPage(p => p - 1)} className="px-3 py-1.5 border rounded-lg text-sm disabled:opacity-40">Prev</button>
              <button disabled={logsArr.length < 50} onClick={() => setLogPage(p => p + 1)} className="px-3 py-1.5 border rounded-lg text-sm disabled:opacity-40">Next</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
