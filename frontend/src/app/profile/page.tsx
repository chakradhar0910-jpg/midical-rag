'use client';
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { User, Shield, Bell, Key, Settings, Loader2, CheckCircle, QrCode, Eye, EyeOff } from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { userApi, authApi } from '@/lib/api';
import toast from 'react-hot-toast';
import { cn } from '@/lib/utils';

const tabs = [
  { id: 'profile', label: 'Profile', icon: User },
  { id: 'security', label: 'Security', icon: Shield },
  { id: 'settings', label: 'Settings', icon: Settings },
  { id: 'notifications', label: 'Notifications', icon: Bell },
];

export default function ProfilePage() {
  const { user, fetchProfile } = useAuthStore();
  const qc = useQueryClient();
  const [activeTab, setActiveTab] = useState('profile');
  const [mfaStep, setMfaStep] = useState<'idle' | 'setup' | 'enable'>('idle');
  const [mfaData, setMfaData] = useState<{ secret: string; qr_uri: string } | null>(null);
  const [mfaToken, setMfaToken] = useState('');
  const [disableMfaToken, setDisableMfaToken] = useState('');
  const [showCurrentPwd, setShowCurrentPwd] = useState(false);

  const { data: settingsData } = useQuery({ queryKey: ['settings'], queryFn: userApi.getSettings });
  const { data: notifsData } = useQuery({ queryKey: ['notifications'], queryFn: () => userApi.getNotifications() });

  const profileForm = useForm({ defaultValues: { full_name: user?.full_name || '', bio: '', phone: '' } });
  const pwdForm = useForm();
  const settingsForm = useForm({
    values: settingsData?.data || { theme: 'light', language: 'en', notifications_enabled: true, email_notifications: true, max_tokens: 1000, temperature: 0.7 }
  });

  const updateProfile = useMutation({
    mutationFn: (data: any) => userApi.updateProfile(data),
    onSuccess: () => { toast.success('Profile updated'); fetchProfile(); },
    onError: () => toast.error('Update failed'),
  });

  const changePwd = useMutation({
    mutationFn: (data: any) => authApi.changePassword(data),
    onSuccess: () => { toast.success('Password changed'); pwdForm.reset(); },
    onError: (err: any) => toast.error(err?.response?.data?.detail || 'Failed'),
  });

  const updateSettings = useMutation({
    mutationFn: (data: any) => userApi.updateSettings(data),
    onSuccess: () => { toast.success('Settings saved'); qc.invalidateQueries({ queryKey: ['settings'] }); },
  });

  const setupMFA = async () => {
    const { data } = await authApi.setupMFA();
    setMfaData(data);
    setMfaStep('setup');
  };

  const enableMFA = async () => {
    try {
      await authApi.enableMFA(mfaToken);
      toast.success('MFA enabled');
      setMfaStep('idle');
      fetchProfile();
    } catch { toast.error('Invalid MFA token'); }
  };

  const disableMFA = async () => {
    try {
      await authApi.disableMFA(disableMfaToken);
      toast.success('MFA disabled');
      fetchProfile();
      setDisableMfaToken('');
    } catch { toast.error('Invalid MFA token'); }
  };

  const markAllRead = async () => {
    await userApi.markAllRead();
    qc.invalidateQueries({ queryKey: ['notifications'] });
    toast.success('All notifications marked as read');
  };

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="mb-6">
        <div className="flex items-center gap-4">
          <div className="w-16 h-16 bg-primary/20 rounded-2xl flex items-center justify-center">
            <span className="text-primary font-bold text-2xl">{user?.username?.[0]?.toUpperCase()}</span>
          </div>
          <div>
            <h1 className="text-2xl font-bold">{user?.full_name || user?.username}</h1>
            <p className="text-muted-foreground">{user?.email} · <span className="capitalize">{user?.role}</span></p>
          </div>
        </div>
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

      {/* Profile Tab */}
      {activeTab === 'profile' && (
        <div className="bg-card border rounded-xl p-6">
          <h2 className="font-semibold text-lg mb-5">Profile Information</h2>
          <form onSubmit={profileForm.handleSubmit(d => updateProfile.mutate(d))} className="space-y-4 max-w-lg">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium mb-1.5 block">Username</label>
                <input value={user?.username} disabled className="w-full px-3 py-2.5 rounded-lg border bg-muted text-sm text-muted-foreground" />
              </div>
              <div>
                <label className="text-sm font-medium mb-1.5 block">Email</label>
                <input value={user?.email} disabled className="w-full px-3 py-2.5 rounded-lg border bg-muted text-sm text-muted-foreground" />
              </div>
            </div>
            <div>
              <label className="text-sm font-medium mb-1.5 block">Full Name</label>
              <input {...profileForm.register('full_name')} className="w-full px-3 py-2.5 rounded-lg border bg-background text-sm focus:outline-none focus:ring-1 focus:ring-primary/30" />
            </div>
            <div>
              <label className="text-sm font-medium mb-1.5 block">Phone</label>
              <input {...profileForm.register('phone')} placeholder="+1 234 567 8900" className="w-full px-3 py-2.5 rounded-lg border bg-background text-sm focus:outline-none focus:ring-1 focus:ring-primary/30" />
            </div>
            <div>
              <label className="text-sm font-medium mb-1.5 block">Bio</label>
              <textarea {...profileForm.register('bio')} rows={3} placeholder="Tell us about yourself..." className="w-full px-3 py-2.5 rounded-lg border bg-background text-sm focus:outline-none focus:ring-1 focus:ring-primary/30 resize-none" />
            </div>
            <div className="flex items-center gap-2">
              <span className={cn('text-xs px-2 py-0.5 rounded-full font-medium', user?.is_email_verified ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700')}>
                {user?.is_email_verified ? '✓ Email Verified' : '⚠ Email Not Verified'}
              </span>
            </div>
            <button type="submit" disabled={updateProfile.isPending}
              className="flex items-center gap-2 bg-primary text-white px-6 py-2.5 rounded-lg text-sm font-medium hover:bg-primary/90 disabled:opacity-60">
              {updateProfile.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
              Save Profile
            </button>
          </form>
        </div>
      )}

      {/* Security Tab */}
      {activeTab === 'security' && (
        <div className="space-y-6">
          {/* Change password */}
          <div className="bg-card border rounded-xl p-6">
            <h2 className="font-semibold text-lg mb-5">Change Password</h2>
            <form onSubmit={pwdForm.handleSubmit(d => changePwd.mutate(d))} className="space-y-4 max-w-lg">
              <div>
                <label className="text-sm font-medium mb-1.5 block">Current Password</label>
                <div className="relative">
                  <input {...pwdForm.register('current_password')} type={showCurrentPwd ? 'text' : 'password'} placeholder="••••••••"
                    className="w-full px-3 py-2.5 rounded-lg border bg-background text-sm focus:outline-none focus:ring-1 focus:ring-primary/30 pr-10" />
                  <button type="button" onClick={() => setShowCurrentPwd(p => !p)} className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground">
                    {showCurrentPwd ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>
              <div>
                <label className="text-sm font-medium mb-1.5 block">New Password</label>
                <input {...pwdForm.register('new_password')} type="password" placeholder="••••••••"
                  className="w-full px-3 py-2.5 rounded-lg border bg-background text-sm focus:outline-none focus:ring-1 focus:ring-primary/30" />
              </div>
              <button type="submit" disabled={changePwd.isPending}
                className="flex items-center gap-2 bg-primary text-white px-6 py-2.5 rounded-lg text-sm font-medium hover:bg-primary/90 disabled:opacity-60">
                {changePwd.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Shield className="w-4 h-4" />}
                Change Password
              </button>
            </form>
          </div>

          {/* MFA */}
          <div className="bg-card border rounded-xl p-6">
            <h2 className="font-semibold text-lg mb-2">Multi-Factor Authentication</h2>
            <p className="text-muted-foreground text-sm mb-5">Add an extra layer of security to your account with TOTP-based MFA.</p>
            {user?.is_mfa_enabled ? (
              <div className="space-y-4">
                <div className="flex items-center gap-2 text-green-600 bg-green-50 px-4 py-2.5 rounded-lg text-sm">
                  <CheckCircle className="w-4 h-4" /> MFA is enabled on your account
                </div>
                <div>
                  <label className="text-sm font-medium mb-1.5 block">Enter MFA code to disable:</label>
                  <div className="flex gap-2">
                    <input value={disableMfaToken} onChange={e => setDisableMfaToken(e.target.value)} maxLength={6}
                      placeholder="123456" className="px-3 py-2 rounded-lg border bg-background text-sm w-36 text-center tracking-widest" />
                    <button onClick={disableMFA} className="px-4 py-2 border border-destructive text-destructive rounded-lg text-sm hover:bg-destructive/10">Disable MFA</button>
                  </div>
                </div>
              </div>
            ) : mfaStep === 'idle' ? (
              <button onClick={setupMFA} className="flex items-center gap-2 bg-primary text-white px-6 py-2.5 rounded-lg text-sm font-medium hover:bg-primary/90">
                <QrCode className="w-4 h-4" /> Enable MFA
              </button>
            ) : mfaStep === 'setup' && mfaData ? (
              <div className="space-y-4">
                <p className="text-sm">Scan this QR code with your authenticator app (Google Authenticator, Authy, etc.):</p>
                <div className="bg-white p-4 rounded-xl w-fit">
                  <img src={`https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(mfaData.qr_uri)}`} alt="MFA QR Code" className="w-48 h-48" />
                </div>
                <p className="text-sm text-muted-foreground">Or enter this secret manually: <code className="bg-muted px-2 py-0.5 rounded text-xs">{mfaData.secret}</code></p>
                <div>
                  <label className="text-sm font-medium mb-1.5 block">Enter the 6-digit code from your app:</label>
                  <div className="flex gap-2">
                    <input value={mfaToken} onChange={e => setMfaToken(e.target.value)} maxLength={6}
                      placeholder="123456" className="px-3 py-2 rounded-lg border bg-background text-sm w-36 text-center tracking-widest" />
                    <button onClick={enableMFA} className="px-4 py-2 bg-primary text-white rounded-lg text-sm hover:bg-primary/90">Verify & Enable</button>
                    <button onClick={() => setMfaStep('idle')} className="px-4 py-2 border rounded-lg text-sm hover:bg-muted">Cancel</button>
                  </div>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      )}

      {/* Settings Tab */}
      {activeTab === 'settings' && (
        <div className="bg-card border rounded-xl p-6">
          <h2 className="font-semibold text-lg mb-5">Preferences</h2>
          <form onSubmit={settingsForm.handleSubmit(d => updateSettings.mutate(d))} className="space-y-5 max-w-lg">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium mb-1.5 block">Theme</label>
                <select {...settingsForm.register('theme')} className="w-full px-3 py-2.5 rounded-lg border bg-background text-sm">
                  <option value="light">Light</option>
                  <option value="dark">Dark</option>
                  <option value="system">System</option>
                </select>
              </div>
              <div>
                <label className="text-sm font-medium mb-1.5 block">Language</label>
                <select {...settingsForm.register('language')} className="w-full px-3 py-2.5 rounded-lg border bg-background text-sm">
                  <option value="en">English</option>
                  <option value="es">Spanish</option>
                  <option value="fr">French</option>
                </select>
              </div>
            </div>
            <div>
              <label className="text-sm font-medium mb-1.5 block">Max Tokens: {settingsForm.watch('max_tokens')}</label>
              <input type="range" min={100} max={4000} step={100} {...settingsForm.register('max_tokens', { valueAsNumber: true })} className="w-full" />
            </div>
            <div>
              <label className="text-sm font-medium mb-1.5 block">Temperature: {settingsForm.watch('temperature')}</label>
              <input type="range" min={0} max={1} step={0.1} {...settingsForm.register('temperature', { valueAsNumber: true })} className="w-full" />
              <div className="flex justify-between text-xs text-muted-foreground mt-1"><span>Precise</span><span>Creative</span></div>
            </div>
            <div className="space-y-3">
              {[['notifications_enabled', 'Enable Notifications'], ['email_notifications', 'Email Notifications'], ['chat_history_enabled', 'Save Chat History']].map(([key, label]) => (
                <div key={key} className="flex items-center justify-between">
                  <label className="text-sm">{label}</label>
                  <input type="checkbox" {...settingsForm.register(key as any)} className="w-4 h-4 rounded border-border accent-primary" />
                </div>
              ))}
            </div>
            <button type="submit" disabled={updateSettings.isPending}
              className="flex items-center gap-2 bg-primary text-white px-6 py-2.5 rounded-lg text-sm font-medium hover:bg-primary/90 disabled:opacity-60">
              {updateSettings.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Settings className="w-4 h-4" />}
              Save Settings
            </button>
          </form>
        </div>
      )}

      {/* Notifications Tab */}
      {activeTab === 'notifications' && (
        <div className="bg-card border rounded-xl p-6">
          <div className="flex items-center justify-between mb-5">
            <h2 className="font-semibold text-lg">Notifications</h2>
            <button onClick={markAllRead} className="text-sm text-primary hover:underline">Mark all read</button>
          </div>
          <div className="space-y-3">
            {(notifsData?.data || []).length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <Bell className="w-10 h-10 mx-auto mb-2 opacity-40" /><p>No notifications</p>
              </div>
            ) : (notifsData?.data || []).map((n: any) => (
              <div key={n.id} className={cn('flex gap-3 p-3 rounded-lg', !n.is_read && 'bg-primary/5 border border-primary/10')}>
                <div className={cn('w-2 h-2 rounded-full mt-2 flex-shrink-0', !n.is_read ? 'bg-primary' : 'bg-transparent')} />
                <div>
                  <p className="text-sm font-medium">{n.title}</p>
                  <p className="text-sm text-muted-foreground">{n.message}</p>
                  <p className="text-xs text-muted-foreground mt-1">{new Date(n.created_at).toLocaleString()}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
