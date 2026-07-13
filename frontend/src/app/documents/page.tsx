'use client';
import { useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useDropzone } from 'react-dropzone';
import {
  FileText, Upload, Trash2, RefreshCw, Search, Filter,
  CheckCircle, Clock, XCircle, Loader2, FileUp, X, Eye
} from 'lucide-react';
import { documentApi } from '@/lib/api';
import { formatBytes, formatRelativeTime, cn } from '@/lib/utils';
import toast from 'react-hot-toast';

const STATUS_CONFIG: Record<string, { icon: any; color: string; label: string }> = {
  processed: { icon: CheckCircle, color: 'text-green-600 bg-green-50', label: 'Processed' },
  processing: { icon: Loader2, color: 'text-yellow-600 bg-yellow-50', label: 'Processing' },
  pending: { icon: Clock, color: 'text-blue-600 bg-blue-50', label: 'Pending' },
  failed: { icon: XCircle, color: 'text-red-600 bg-red-50', label: 'Failed' },
};

const FILE_TYPE_COLORS: Record<string, string> = {
  pdf: 'bg-red-100 text-red-700', docx: 'bg-blue-100 text-blue-700',
  txt: 'bg-gray-100 text-gray-700', csv: 'bg-green-100 text-green-700',
  md: 'bg-purple-100 text-purple-700',
};

function UploadModal({ onClose, onSuccess }: { onClose: () => void; onSuccess: () => void }) {
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [category, setCategory] = useState('');

  const onDrop = useCallback((accepted: File[]) => {
    setFiles(prev => [...prev, ...accepted]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop, accept: { 'application/pdf': ['.pdf'], 'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'text/plain': ['.txt'], 'text/csv': ['.csv'], 'text/markdown': ['.md'] },
    maxSize: 50 * 1024 * 1024,
  });

  const uploadAll = async () => {
    if (!files.length) return;
    setUploading(true);
    let successCount = 0;
    for (const file of files) {
      try {
        const fd = new FormData();
        fd.append('file', file);
        fd.append('title', file.name.replace(/\.[^.]+$/, ''));
        if (category) fd.append('category', category);
        await documentApi.upload(fd);
        successCount++;
      } catch (err: any) {
        toast.error(`Failed to upload ${file.name}: ${err?.response?.data?.detail || 'error'}`);
      }
    }
    setUploading(false);
    if (successCount > 0) {
      toast.success(`${successCount} document(s) uploaded successfully`);
      onSuccess();
      onClose();
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-card rounded-2xl border shadow-xl w-full max-w-lg">
        <div className="flex items-center justify-between p-5 border-b">
          <h2 className="font-semibold text-lg">Upload Documents</h2>
          <button onClick={onClose} className="p-1.5 rounded hover:bg-muted"><X className="w-4 h-4" /></button>
        </div>
        <div className="p-5 space-y-4">
          <div {...getRootProps()} className={cn('border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors',
            isDragActive ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/50 hover:bg-muted/50')}>
            <input {...getInputProps()} />
            <FileUp className="w-10 h-10 text-muted-foreground mx-auto mb-3" />
            <p className="font-medium mb-1">{isDragActive ? 'Drop files here' : 'Drag & drop files here'}</p>
            <p className="text-sm text-muted-foreground">or click to browse</p>
            <p className="text-xs text-muted-foreground mt-2">PDF, DOCX, TXT, CSV, MD · Max 50MB each</p>
          </div>

          <div>
            <label className="text-sm font-medium mb-1.5 block">Category (optional)</label>
            <select value={category} onChange={e => setCategory(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border bg-background text-sm focus:outline-none focus:ring-1 focus:ring-primary/30">
              <option value="">Select category</option>
              {['WHO Guidelines', 'CDC Guidelines', 'Clinical Protocols', 'Drug Reference', 'Research Papers', 'Emergency Care', 'Patient Education'].map(c => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>

          {files.length > 0 && (
            <div className="space-y-2 max-h-40 overflow-y-auto">
              {files.map((f, i) => (
                <div key={i} className="flex items-center gap-2 p-2 bg-muted rounded-lg text-sm">
                  <FileText className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                  <span className="truncate flex-1">{f.name}</span>
                  <span className="text-muted-foreground text-xs">{formatBytes(f.size)}</span>
                  <button onClick={() => setFiles(prev => prev.filter((_, j) => j !== i))}
                    className="text-muted-foreground hover:text-destructive flex-shrink-0">
                    <X className="w-3 h-3" />
                  </button>
                </div>
              ))}
            </div>
          )}

          <div className="flex gap-3">
            <button onClick={onClose} className="flex-1 py-2.5 border rounded-lg text-sm font-medium hover:bg-muted">Cancel</button>
            <button onClick={uploadAll} disabled={!files.length || uploading}
              className="flex-1 bg-primary text-white py-2.5 rounded-lg text-sm font-medium hover:bg-primary/90 disabled:opacity-60 flex items-center justify-center gap-2">
              {uploading ? <><Loader2 className="w-4 h-4 animate-spin" />Uploading...</> : `Upload ${files.length} file${files.length !== 1 ? 's' : ''}`}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function DocumentsPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [showUpload, setShowUpload] = useState(false);
  const [page, setPage] = useState(1);

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['documents', search, statusFilter, page],
    queryFn: () => documentApi.list({ search, status: statusFilter || undefined, page, page_size: 20 }),
    refetchInterval: 10000, // auto-refresh for processing status
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => documentApi.delete(id),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['documents'] }); toast.success('Document deleted'); },
    onError: () => toast.error('Delete failed'),
  });

  const reprocessMutation = useMutation({
    mutationFn: (id: string) => documentApi.reprocess(id),
    onSuccess: () => { toast.success('Reprocessing started'); refetch(); },
  });

  const docs = data?.data?.documents || [];
  const total = data?.data?.total || 0;
  const pageSize = 20;
  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="p-6 max-w-6xl mx-auto">
      {showUpload && (
        <UploadModal onClose={() => setShowUpload(false)} onSuccess={() => { queryClient.invalidateQueries({ queryKey: ['documents'] }); }} />
      )}

      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Documents</h1>
          <p className="text-muted-foreground text-sm">{total} documents in your knowledge base</p>
        </div>
        <button onClick={() => setShowUpload(true)}
          className="flex items-center gap-2 bg-primary text-white font-medium px-4 py-2.5 rounded-xl hover:bg-primary/90 transition-colors">
          <Upload className="w-4 h-4" /> Upload
        </button>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 mb-6">
        <div className="relative flex-1 max-w-sm">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <input value={search} onChange={e => { setSearch(e.target.value); setPage(1); }} placeholder="Search documents..."
            className="w-full pl-9 pr-3 py-2 rounded-lg border bg-background text-sm focus:outline-none focus:ring-1 focus:ring-primary/30" />
        </div>
        <select value={statusFilter} onChange={e => { setStatusFilter(e.target.value); setPage(1); }}
          className="px-3 py-2 rounded-lg border bg-background text-sm focus:outline-none focus:ring-1 focus:ring-primary/30">
          <option value="">All Status</option>
          {Object.keys(STATUS_CONFIG).map(s => <option key={s} value={s}>{STATUS_CONFIG[s].label}</option>)}
        </select>
      </div>

      {/* Documents grid */}
      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
        </div>
      ) : docs.length === 0 ? (
        <div className="text-center py-20">
          <FileText className="w-16 h-16 mx-auto mb-4 text-muted-foreground/40" />
          <h3 className="text-lg font-semibold mb-2">No documents found</h3>
          <p className="text-muted-foreground mb-6">Upload medical documents to build your AI knowledge base.</p>
          <button onClick={() => setShowUpload(true)} className="bg-primary text-white font-medium px-6 py-2.5 rounded-xl hover:bg-primary/90">
            Upload First Document
          </button>
        </div>
      ) : (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {docs.map((doc: any) => {
            const status = STATUS_CONFIG[doc.status] || STATUS_CONFIG.pending;
            const StatusIcon = status.icon;
            return (
              <div key={doc.id} className="bg-card border rounded-xl p-4 hover:shadow-md transition-shadow">
                <div className="flex items-start gap-3 mb-3">
                  <div className={cn('w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 text-xs font-bold',
                    FILE_TYPE_COLORS[doc.file_type] || 'bg-gray-100 text-gray-700')}>
                    {doc.file_type?.toUpperCase()}
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="font-medium text-sm truncate">{doc.title}</h3>
                    <p className="text-xs text-muted-foreground">{doc.file_name}</p>
                  </div>
                </div>

                <div className="flex items-center gap-2 mb-3">
                  <span className={cn('flex items-center gap-1 text-xs px-2 py-0.5 rounded-full font-medium', status.color)}>
                    <StatusIcon className={cn('w-3 h-3', doc.status === 'processing' && 'animate-spin')} />
                    {status.label}
                  </span>
                  {doc.chunk_count > 0 && (
                    <span className="text-xs text-muted-foreground">{doc.chunk_count} chunks</span>
                  )}
                </div>

                <div className="flex items-center justify-between text-xs text-muted-foreground mb-3">
                  <span>{formatBytes(doc.file_size)}</span>
                  <span>{formatRelativeTime(doc.created_at)}</span>
                </div>

                {doc.category && (
                  <span className="inline-block bg-muted text-xs px-2 py-0.5 rounded-full mb-3">{doc.category}</span>
                )}

                <div className="flex items-center gap-1 border-t pt-3">
                  {doc.status === 'failed' && (
                    <button onClick={() => reprocessMutation.mutate(doc.id)}
                      className="flex-1 flex items-center justify-center gap-1 text-xs py-1.5 border rounded hover:bg-muted transition-colors">
                      <RefreshCw className="w-3 h-3" /> Retry
                    </button>
                  )}
                  <button onClick={() => { if (confirm('Delete this document?')) deleteMutation.mutate(doc.id); }}
                    className="flex items-center justify-center gap-1 text-xs py-1.5 px-3 border border-destructive/20 text-destructive rounded hover:bg-destructive/10 transition-colors ml-auto">
                    <Trash2 className="w-3 h-3" /> Delete
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 mt-8">
          <button disabled={page === 1} onClick={() => setPage(p => p - 1)}
            className="px-4 py-2 border rounded-lg text-sm disabled:opacity-40 hover:bg-muted">Previous</button>
          <span className="text-sm text-muted-foreground">Page {page} of {totalPages}</span>
          <button disabled={page === totalPages} onClick={() => setPage(p => p + 1)}
            className="px-4 py-2 border rounded-lg text-sm disabled:opacity-40 hover:bg-muted">Next</button>
        </div>
      )}
    </div>
  );
}
