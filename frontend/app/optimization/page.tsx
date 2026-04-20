'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { optimizationApi } from '@/lib/api';
import type { OptimizationProject } from '@/types';
import {
  FlaskConical, Plus, ChevronRight, BookOpen,
  Beaker, TrendingUp, AlertTriangle,
} from 'lucide-react';

export default function OptimizationPage() {
  const [projects, setProjects] = useState<OptimizationProject[]>([]);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    optimizationApi.listProjects()
      .then(setProjects)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
            <FlaskConical className="w-8 h-8 text-indigo-600" />
            Bayesian Optimization
          </h1>
          <p className="text-gray-500 mt-1 max-w-2xl">
            Use your PDF literature database as prior knowledge. Enter your real lab results.
            The system recommends the next best experiment using Gaussian Process + Expected Improvement.
          </p>
        </div>
        <Link href="/optimization/projects/new" className="btn-primary">
          <Plus className="w-4 h-4" />
          New Project
        </Link>
      </div>

      {/* How it works */}
      <div className="card p-5 bg-indigo-50 border-indigo-200">
        <h2 className="font-semibold text-indigo-800 mb-3">How it works</h2>
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
          {[
            { step: '1', icon: BookOpen, title: 'Literature Prior', desc: 'Your scanned PDFs provide prior knowledge about which conditions work.' },
            { step: '2', icon: Beaker, title: 'Your Experiments', desc: 'Enter your actual lab results. They are the highest-trust data.' },
            { step: '3', icon: TrendingUp, title: 'GP + EI', desc: 'Gaussian Process fits a surrogate model. Expected Improvement finds next best point.' },
            { step: '4', icon: FlaskConical, title: 'Iterate', desc: 'Run recommended experiment, enter results, get next recommendation.' },
          ].map(({ step, icon: Icon, title, desc }) => (
            <div key={step} className="flex gap-3">
              <div className="w-7 h-7 rounded-full bg-indigo-600 text-white text-xs font-bold flex items-center justify-center flex-shrink-0">
                {step}
              </div>
              <div>
                <p className="text-sm font-semibold text-indigo-900 flex items-center gap-1">
                  <Icon className="w-3.5 h-3.5" /> {title}
                </p>
                <p className="text-xs text-indigo-700 mt-0.5">{desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="card p-4 border-red-300 bg-red-50 flex gap-2">
          <AlertTriangle className="w-5 h-5 text-red-500 flex-shrink-0" />
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {/* Project list */}
      {loading ? (
        <p className="text-gray-400 text-sm">Loading projects…</p>
      ) : projects.length === 0 ? (
        <div className="card p-10 text-center">
          <FlaskConical className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500 font-medium">No projects yet</p>
          <p className="text-sm text-gray-400 mt-1 mb-4">
            Create a project to start a Bayesian optimization campaign.
          </p>
          <Link href="/optimization/projects/new" className="btn-primary inline-flex">
            <Plus className="w-4 h-4" /> Create First Project
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {projects.map(p => (
            <ProjectCard key={p.id} project={p} />
          ))}
        </div>
      )}
    </div>
  );
}

function ProjectCard({ project: p }: { project: OptimizationProject }) {
  return (
    <Link
      href={`/optimization/projects/${p.id}`}
      className="card p-5 flex items-start justify-between hover:border-indigo-300 hover:bg-indigo-50/30 transition-colors group"
    >
      <div className="flex-1">
        <div className="flex items-center gap-2">
          <h3 className="font-semibold text-gray-900 group-hover:text-indigo-700">
            {p.name}
          </h3>
          {p.objective_variable && (
            <span className="badge bg-indigo-100 text-indigo-700">
              {p.objective_direction === 'maximize' ? '↑' : '↓'} {p.objective_variable}
            </span>
          )}
        </div>
        {p.material_system && (
          <p className="text-xs text-gray-500 mt-0.5">Material: {p.material_system}</p>
        )}
        {p.description && (
          <p className="text-sm text-gray-600 mt-1 line-clamp-1">{p.description}</p>
        )}
        <div className="flex gap-4 mt-3">
          <Chip label={`${p.n_literature_points} literature`} color="blue" />
          <Chip label={`${p.n_user_experiments} experiments`} color="green" />
          <Chip label={`${p.n_recommendations} runs`} color="purple" />
        </div>
      </div>
      <ChevronRight className="w-5 h-5 text-gray-400 group-hover:text-indigo-500 flex-shrink-0 mt-1" />
    </Link>
  );
}

function Chip({ label, color }: { label: string; color: string }) {
  const colors: Record<string, string> = {
    blue:   'bg-blue-100 text-blue-700',
    green:  'bg-green-100 text-green-700',
    purple: 'bg-purple-100 text-purple-700',
  };
  return (
    <span className={`badge ${colors[color] || 'bg-gray-100 text-gray-700'}`}>
      {label}
    </span>
  );
}
