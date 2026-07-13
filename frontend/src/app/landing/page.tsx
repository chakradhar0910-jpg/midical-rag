'use client';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { Activity, Brain, Shield, Zap, FileText, Users, ChevronRight, CheckCircle } from 'lucide-react';

const features = [
  { icon: Brain, title: 'AI-Powered RAG', desc: 'Retrieval-Augmented Generation for accurate, source-cited medical answers' },
  { icon: Shield, title: 'HIPAA-Inspired Security', desc: 'End-to-end encryption, audit logs, RBAC, and MFA protection' },
  { icon: FileText, title: 'Multi-Format Docs', desc: 'Upload PDFs, DOCX, TXT, CSV and Markdown knowledge bases' },
  { icon: Zap, title: 'Real-Time Streaming', desc: 'Instant streaming responses with confidence scores and sources' },
  { icon: Activity, title: 'Emergency Detection', desc: 'Automatic emergency detection with immediate first-responder guidance' },
  { icon: Users, title: 'Team Collaboration', desc: 'Admin dashboard with user management, analytics and audit logs' },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-background">
      {/* Nav */}
      <nav className="border-b sticky top-0 z-50 bg-background/80 backdrop-blur-md">
        <div className="container mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
              <Activity className="w-5 h-5 text-white" />
            </div>
            <span className="font-bold text-lg">MedicalRAG</span>
          </div>
          <div className="hidden md:flex items-center gap-6 text-sm text-muted-foreground">
            <a href="#features" className="hover:text-foreground transition-colors">Features</a>
            <a href="#security" className="hover:text-foreground transition-colors">Security</a>
          </div>
          <div className="flex items-center gap-3">
            <Link href="/auth/login" className="text-sm font-medium hover:text-primary transition-colors">Sign In</Link>
            <Link href="/auth/register" className="bg-primary text-white text-sm font-medium px-4 py-2 rounded-lg hover:bg-primary/90 transition-colors">
              Get Started
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="container mx-auto px-4 pt-20 pb-16 text-center">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}>
          <div className="inline-flex items-center gap-2 bg-primary/10 text-primary text-sm font-medium px-4 py-2 rounded-full mb-6">
            <Activity className="w-4 h-4" />
            Enterprise Medical AI Platform
          </div>
          <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-6">
            Medical AI That
            <span className="text-primary"> Cites Its Sources</span>
          </h1>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto mb-10">
            MedicalRAG combines advanced RAG technology with curated medical knowledge to deliver
            accurate, source-cited answers with emergency detection and HIPAA-inspired security.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link href="/auth/register" className="flex items-center gap-2 bg-primary text-white font-semibold px-8 py-4 rounded-xl hover:bg-primary/90 transition-all hover:scale-105 shadow-lg shadow-primary/25">
              Start Free Trial <ChevronRight className="w-5 h-5" />
            </Link>
            <Link href="/auth/login" className="flex items-center gap-2 border border-border font-semibold px-8 py-4 rounded-xl hover:bg-muted transition-all">
              View Demo
            </Link>
          </div>
          <div className="flex items-center justify-center gap-8 mt-12 text-sm text-muted-foreground">
            {['1000+ Medical Entries', 'HIPAA-Inspired', '24/7 Available', 'Source Citations'].map((item) => (
              <div key={item} className="flex items-center gap-1">
                <CheckCircle className="w-4 h-4 text-primary" />
                {item}
              </div>
            ))}
          </div>
        </motion.div>
      </section>

      {/* Features */}
      <section id="features" className="container mx-auto px-4 py-20">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold mb-4">Everything You Need</h2>
          <p className="text-muted-foreground text-lg max-w-xl mx-auto">Built for healthcare teams that need fast, reliable, and secure AI medical assistance.</p>
        </div>
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
          {features.map((f, i) => (
            <motion.div key={f.title} initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.1 }} viewport={{ once: true }}
              className="p-6 rounded-2xl border bg-card hover:shadow-lg transition-shadow group">
              <div className="w-12 h-12 bg-primary/10 rounded-xl flex items-center justify-center mb-4 group-hover:bg-primary/20 transition-colors">
                <f.icon className="w-6 h-6 text-primary" />
              </div>
              <h3 className="font-semibold text-lg mb-2">{f.title}</h3>
              <p className="text-muted-foreground text-sm">{f.desc}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Security */}
      <section id="security" className="container mx-auto px-4 py-20">
        <div className="bg-gradient-to-r from-primary/10 to-blue-500/10 rounded-3xl p-12 text-center">
          <Shield className="w-16 h-16 text-primary mx-auto mb-6" />
          <h2 className="text-3xl font-bold mb-4">Enterprise-Grade Security</h2>
          <p className="text-muted-foreground max-w-xl mx-auto mb-8">JWT authentication, RBAC, bcrypt hashing, CSRF protection, rate limiting, audit logs, and encryption at rest and in transit.</p>
          <div className="flex flex-wrap justify-center gap-3">
            {['OWASP Top 10', 'JWT + MFA', 'RBAC', 'Audit Logs', 'Rate Limiting', 'Encrypted Storage'].map((tag) => (
              <span key={tag} className="bg-primary/10 text-primary text-sm font-medium px-4 py-1.5 rounded-full">{tag}</span>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="container mx-auto px-4 py-20 text-center">
        <h2 className="text-4xl font-bold mb-4">Ready to Transform Your Practice?</h2>
        <p className="text-muted-foreground text-lg mb-8">Join healthcare teams using MedicalRAG for smarter, faster clinical decisions.</p>
        <Link href="/auth/register" className="inline-flex items-center gap-2 bg-primary text-white font-semibold px-10 py-5 rounded-xl hover:bg-primary/90 transition-all hover:scale-105 shadow-lg shadow-primary/25 text-lg">
          Start for Free <ChevronRight className="w-5 h-5" />
        </Link>
      </section>

      {/* Footer */}
      <footer className="border-t py-8">
        <div className="container mx-auto px-4 flex flex-col md:flex-row items-center justify-between gap-4 text-sm text-muted-foreground">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-primary" />
            <span className="font-semibold text-foreground">MedicalRAG</span>
            <span>© 2024. All rights reserved.</span>
          </div>
          <div className="flex gap-6">
            <Link href="#" className="hover:text-foreground">Privacy</Link>
            <Link href="#" className="hover:text-foreground">Terms</Link>
            <Link href="#" className="hover:text-foreground">Contact</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
