'use client';

import { useEffect, useState, useCallback } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { optimizationApi } from '@/lib/api';
import type { OptimizationProject, ProjectVariable, UserExperiment, RecommendationRun, LiteraturePreview } from '@/types';
import {
  ArrowLeft, FlaskConical, BookOpen, Beaker, TrendingUp,
  ChevronRight, Settings, AlertTriangle, RefreshCw, Sparkles,
} from 'lucide-react';

export default function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [project, setProject]     = useState<OptimizationProject | null>(null);
  const [variables, setVariables] = useState<ProjectVariable[]>([]);
  const [experiments, setExps]    = useState<UserExperiment[]>([]);
  const [runs, setRuns]           = useState<RecommendationRun[]>([]);
  const [litPreview, setLitPreview] = useState<LiteraturePreview | null>(null);
  const [loading, setLoading]     = useState(true);
  const [recommending, setRecommending] = useState(false);
  const [error, setError]         = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [proj, vars, exps, runList, litPrev] = await Promise.all([
        optimizationApi.getProject(id),
        optimizationApi.listVariables(id),
        optimizationApi.listExperiments(id),
        optimizationApi.listRuns(id),
        optimizationApi.getLiteraturePreview(id).catch(() => null),
      ]);
      setProject(proj);
      setVariables(vars);
      setExps(exps);
      setRuns(runList);
      if (litPrev) setLitPreview(litPrev);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load project');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { load(); }, [load]);

  const handleRecommend = async () => {
    setRecommending(true);
    setError(null);
    try {
      await optimizationApi.recommend(id, 5);
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Recommendation failed');
    } finally {
      setRecommending(false);
    }
  };

  if (loading) return <p className="text-gray-400 text-sm">Loading project…</p>;
  if (!project) return (
    <div className="card p-6 text-center text-red-600">
      {error || 'Project not found'}
    </div>
  );

  const inputVars  = variables.filter(v => v.role === 'input');
  const outputVars = variables.filter(v => v.role === 'output');
  const latestRun  = runs[0] ?? null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <Link href="/optimization" className="btn-secondary px-2 py-1">
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
              <FlaskConical className="w-6 h-6 text-indigo-600" />
              {project.name}
            </h1>
            {project.material_system && (
              <p className="text-sm text-gray-500">Material: {project.material_system}</p>
            )}
          </div>
        </div>
        <div className="flex gap-2">
          <button
            className="btn-secondary"
            onClick={load}
            title="Refresh"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            className="btn-primary bg-indigo-600 hover:bg-indigo-700"
            onClick={handleRecommend}
            disabled={recommending || variables.length === 0}
          >
            <Sparkles className="w-4 h-4" />
            {recommending ? 'Running BO…' : 'Recommend Experiment'}
          </button>
        </div>
      </div>

      {error && (
        <div className="card p-3 bg-red-50 border-red-300 flex gap-2">
          <AlertTriangle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {/* Objective */}
      {project.objective_variable && (
        <div className="card p-4 bg-indigo-50 border-indigo-200">
          <p className="text-sm text-indigo-800">
            <strong>Objective:</strong>{' '}
            {project.objective_direction === 'maximize' ? 'Maximize' : 'Minimize'}{' '}
            <code className="bg-indigo-100 px-1 rounded">{project.objective_variable}</code>
          </p>
          {project.description && (
            <p className="text-xs text-indigo-700 mt-1">{project.description}</p>
          )}
        </div>
      )}

      {/* Stats row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <StatCard icon={<BookOpen className="w-4 h-4 text-blue-500" />}
          label="Literature Points" value={project.n_literature_points}
          href={`/optimization/projects/${id}/recommend`} linkLabel="View" />
        <StatCard icon={<Beaker className="w-4 h-4 text-green-500" />}
          label="Your Experiments" value={project.n_user_experiments}
          href={`/optimization/projects/${id}/experiments`} linkLabel="Add" />
        <StatCard icon={<TrendingUp className="w-4 h-4 text-indigo-500" />}
          label="BO Runs" value={project.n_recommendations}
          href={`/optimization/projects/${id}/recommend`} linkLabel="History" />
        <StatCard icon={<Settings className="w-4 h-4 text-gray-500" />}
          label="Variables" value={variables.length}
          href={`/optimization/projects/${id}/variables`} linkLabel="Edit" />
      </div>

      {/* Latest recommendation */}
      {latestRun && (
        <div className="card p-5">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold text-gray-800 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-indigo-500" />
              Latest Recommendation
            </h2>
            <Link href={`/optimization/projects/${id}/recommend`}
              className="text-xs text-indigo-600 hover:underline flex items-center gap-1">
              All runs <ChevronRight className="w-3 h-3" />
            </Link>
          </div>
          <div className="flex gap-3 flex-wrap mb-3">
            <Badge label={latestRun.status} color={latestRun.status === 'completed' ? 'green' : 'gray'} />
            <Badge label={latestRun.model_type || 'N/A'} color="indigo" />
            <Badge label={`${latestRun.n_literature_points} lit + ${latestRun.n_user_points} user`} color="blue" />
          </div>
          {latestRun.message && (
            <p className="text-xs text-gray-500 mb-3">{latestRun.message}</p>
          )}
          <Link href={`/optimization/projects/${id}/recommend`}
            className="btn-secondary text-sm">
            View Candidates <ChevronRight className="w-4 h-4" />
          </Link>
        </div>
      )}

      {/* Variable summary */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="card p-4">
          <div className="flex items-center justify-between mb-2">
            <h3 className="font-semibold text-gray-700 text-sm">Input Variables ({inputVars.length})</h3>
            <Link href={`/optimization/projects/${id}/variables`}
              className="text-xs text-indigo-600 hover:underline">Edit →</Link>
          </div>
          {inputVars.length === 0 ? (
            <p className="text-xs text-gray-400">No input variables. <Link href={`/optimization/projects/${id}/variables`} className="underline text-indigo-600">Add some →</Link></p>
          ) : (
            <ul className="space-y-1">
              {inputVars.slice(0, 6).map(v => (
                <li key={v.id} className="text-xs flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-blue-400 flex-shrink-0" />
                  <span className="text-gray-700 font-medium">{v.label || v.name}</span>
                  {v.unit && <span className="text-gray-400">[{v.unit}]</span>}
                </li>
              ))}
              {inputVars.length > 6 && <li className="text-xs text-gray-400">+ {inputVars.length - 6} more</li>}
            </ul>
          )}
        </div>

        <div className="card p-4">
          <div className="flex items-center justify-between mb-2">
            <h3 className="font-semibold text-gray-700 text-sm">Output Variables ({outputVars.length})</h3>
            <Link href={`/optimization/projects/${id}/variables`}
              className="text-xs text-indigo-600 hover:underline">Edit →</Link>
          </div>
          {outputVars.length === 0 ? (
            <p className="text-xs text-gray-400">No output variables defined.</p>
          ) : (
            <ul className="space-y-1">
              {outputVars.map(v => (
                <li key={v.id} className="text-xs flex items-center gap-1.5">
                  <span className={`w-2 h-2 rounded-full flex-shrink-0 ${v.is_objective ? 'bg-indigo-500' : 'bg-green-400'}`} />
                  <span className="text-gray-700 font-medium">{v.label || v.name}</span>
                  {v.unit && <span className="text-gray-400">[{v.unit}]</span>}
                  {v.is_objective && <span className="badge bg-indigo-100 text-indigo-700 text-[10px] px-1">objective</span>}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {/* Literature preview */}
      {litPreview && litPreview.n_papers > 0 && (
        <div className="card p-4">
          <h3 className="font-semibold text-gray-700 text-sm mb-2 flex items-center gap-2">
            <BookOpen className="w-4 h-4 text-blue-500" />
            Matching Literature ({litPreview.n_papers} papers with data)
          </h3>
          <div className="space-y-1.5">
            {litPreview.papers.slice(0, 5).map(p => (
              <div key={p.paper_id} className="flex items-center gap-2 text-xs">
                <span className="badge bg-blue-100 text-blue-700 flex-shrink-0">
                  {p.n_variables} vars
                </span>
                <span className="text-gray-700 line-clamp-1">{p.paper_title}</span>
                {p.paper_year && <span className="text-gray-400 flex-shrink-0">{p.paper_year}</span>}
              </div>
            ))}
            {litPreview.n_papers > 5 && (
              <p className="text-xs text-gray-400">+ {litPreview.n_papers - 5} more papers</p>
            )}
          </div>
        </div>
      )}

      {/* Recent experiments */}
      {experiments.length > 0 && (
        <div className="card p-4">
          <div className="flex items-center justify-between mb-2">
            <h3 className="font-semibold text-gray-700 text-sm flex items-center gap-2">
              <Beaker className="w-4 h-4 text-green-500" />
              Recent Experiments ({experiments.length})
            </h3>
            <Link href={`/optimization/projects/${id}/experiments`}
              className="text-xs text-indigo-600 hover:underline">View all →</Link>
          </div>
          <div className="space-y-1.5">
            {experiments.slice(0, 4).map(e => (
              <div key={e.id} className="flex items-center gap-3 text-xs">
                <span className={`badge ${e.status === 'completed' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'}`}>
                  {e.status}
                </span>
                <span className="text-gray-700">{e.name || `Run ${e.id.slice(0, 8)}`}</span>
                {e.objective_value != null && (
                  <span className="font-mono text-indigo-700 ml-auto">
                    {project.objective_variable} = {e.objective_value}
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Quick actions */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <QuickLink href={`/optimization/projects/${id}/variables`}
          icon={<Settings className="w-4 h-4" />}
          title="Variables" desc="Define inputs, outputs, ranges" color="gray" />
        <QuickLink href={`/optimization/projects/${id}/experiments`}
          icon={<Beaker className="w-4 h-4" />}
          title="My Experiments" desc="Enter lab results" color="green" />
        <QuickLink href={`/optimization/projects/${id}/recommend`}
          icon={<TrendingUp className="w-4 h-4" />}
          title="Recommendations" desc="View and act on BO suggestions" color="indigo" />
      </div>
    </div>
  );
}

function StatCard({ icon, label, value, href, linkLabel }: {
  icon: React.ReactNode; label: string; value: number;
  href: string; linkLabel: string;
}) {
  return (
    <div className="card p-4">
      <div className="flex items-center gap-2 mb-1">
        {icon}
        <span className="text-xs text-gray-500">{label}</span>
      </div>
      <p className="text-2xl font-bold text-gray-900">{value}</p>
      <Link href={href} className="text-xs text-indigo-600 hover:underline mt-1 inline-block">
        {linkLabel} →
      </Link>
    </div>
  );
}

function Badge({ label, color }: { label: string; color: string }) {
  const colors: Record<string, string> = {
    green: 'bg-green-100 text-green-700',
    gray:  'bg-gray-100 text-gray-700',
    indigo:'bg-indigo-100 text-indigo-700',
    blue:  'bg-blue-100 text-blue-700',
  };
  return <span className={`badge ${colors[color] || 'bg-gray-100 text-gray-700'}`}>{label}</span>;
}

function QuickLink({ href, icon, title, desc, color }: {
  href: string; icon: React.ReactNode; title: string; desc: string;
  color: string;
}) {
  const colors: Record<string, string> = {
    gray:  'hover:border-gray-400 hover:bg-gray-50',
    green: 'hover:border-green-400 hover:bg-green-50',
    indigo:'hover:border-indigo-400 hover:bg-indigo-50',
  };
  return (
    <Link href={href}
      className={`card p-4 flex items-start gap-3 transition-colors cursor-pointer ${colors[color]}`}>
      <span className="mt-0.5 text-gray-500">{icon}</span>
      <div>
        <p className="font-semibold text-gray-800 text-sm">{title}</p>
        <p className="text-xs text-gray-500 mt-0.5">{desc}</p>
      </div>
    </Link>
  );
}
