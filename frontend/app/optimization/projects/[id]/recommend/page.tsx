'use client';

import { useEffect, useState, useCallback } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { optimizationApi } from '@/lib/api';
import type { OptimizationProject, ProjectVariable, RecommendationRun, RecommendedCandidate } from '@/types';
import {
  ArrowLeft, TrendingUp, Sparkles, AlertTriangle, BookOpen,
  ChevronDown, ChevronUp, CheckCircle, RefreshCw, Beaker,
} from 'lucide-react';

export default function RecommendPage() {
  const { id } = useParams<{ id: string }>();
  const [project, setProject]     = useState<OptimizationProject | null>(null);
  const [variables, setVariables] = useState<ProjectVariable[]>([]);
  const [runs, setRuns]           = useState<RecommendationRun[]>([]);
  const [latestRun, setLatestRun] = useState<RecommendationRun | null>(null);
  const [loading, setLoading]     = useState(true);
  const [recommending, setRecommending] = useState(false);
  const [nCandidates, setNCandidates]   = useState(5);
  const [error, setError]         = useState<string | null>(null);
  const [expandedCandidate, setExpandedCandidate] = useState<string | null>(null);
  const [executingId, setExecutingId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [proj, vars, runList] = await Promise.all([
        optimizationApi.getProject(id),
        optimizationApi.listVariables(id),
        optimizationApi.listRuns(id),
      ]);
      setProject(proj);
      setVariables(vars);
      setRuns(runList);
      if (runList.length > 0) {
        const full = await optimizationApi.getRun(runList[0].id);
        setLatestRun(full);
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { load(); }, [load]);

  const handleRecommend = async () => {
    setRecommending(true); setError(null);
    try {
      const run = await optimizationApi.recommend(id, nCandidates);
      setLatestRun(run);
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Recommendation failed. Check that you have at least one input and one output variable defined.');
    } finally {
      setRecommending(false);
    }
  };

  const handleExecute = async (cand: RecommendedCandidate) => {
    setExecutingId(cand.id);
    try {
      await optimizationApi.markExecuted(cand.id);
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to mark as executed');
    } finally {
      setExecutingId(null);
    }
  };

  const inputVarMap  = Object.fromEntries(variables.filter(v => v.role === 'input').map(v => [v.name, v]));

  if (loading) return <p className="text-gray-400 text-sm">Loading recommendations…</p>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link href={`/optimization/projects/${id}`} className="btn-secondary px-2 py-1">
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-indigo-600" />
              Recommendations
            </h1>
            {project && <p className="text-sm text-gray-500">{project.name}</p>}
          </div>
        </div>
        <button className="btn-secondary" onClick={load} title="Refresh">
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {error && (
        <div className="card p-3 bg-red-50 border-red-300 flex gap-2">
          <AlertTriangle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {/* BO trigger */}
      <div className="card p-5 bg-indigo-50 border-indigo-200">
        <h2 className="font-semibold text-indigo-800 mb-2 flex items-center gap-2">
          <Sparkles className="w-4 h-4" />
          Run Bayesian Optimisation
        </h2>
        {project?.objective_variable ? (
          <p className="text-sm text-indigo-700 mb-4">
            Objective: <strong>{project.objective_direction === 'maximize' ? 'Maximize' : 'Minimize'}{' '}</strong>
            <code className="bg-indigo-100 px-1 rounded">{project.objective_variable}</code>.{' '}
            Data: {project.n_literature_points} literature + {project.n_user_experiments} experiments.
          </p>
        ) : (
          <p className="text-sm text-amber-700 mb-4">
            ⚠ No objective variable set.{' '}
            <Link href={`/optimization/projects/${id}/variables`} className="underline">
              Set one in Variables →
            </Link>
          </p>
        )}

        <div className="flex items-center gap-3">
          <div>
            <label className="label text-xs">Candidates to generate</label>
            <select className="input w-24 text-sm"
              value={nCandidates}
              onChange={e => setNCandidates(Number(e.target.value))}>
              {[3, 5, 7, 10].map(n => <option key={n} value={n}>{n}</option>)}
            </select>
          </div>
          <div className="mt-5">
            <button
              className="btn-primary bg-indigo-600 hover:bg-indigo-700"
              onClick={handleRecommend}
              disabled={recommending}
            >
              <Sparkles className="w-4 h-4" />
              {recommending
                ? 'Running… (may take 30s for large datasets)'
                : 'Recommend Next Experiments'}
            </button>
          </div>
        </div>

        {recommending && (
          <div className="mt-3 text-xs text-indigo-600 animate-pulse">
            Fitting Gaussian Process on literature + user data… evaluating {nCandidates * 200}+ candidate points with Expected Improvement…
          </div>
        )}
      </div>

      {/* Latest run result */}
      {latestRun && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-gray-800 flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-indigo-500" />
              Latest Run — {latestRun.created_at.split('T')[0]}
            </h2>
            <div className="flex gap-2">
              <span className={`badge ${
                latestRun.status === 'completed' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
              }`}>{latestRun.status}</span>
              {latestRun.model_type && (
                <span className="badge bg-indigo-100 text-indigo-700">{latestRun.model_type}</span>
              )}
              {latestRun.acquisition_fn && (
                <span className="badge bg-blue-100 text-blue-700">{latestRun.acquisition_fn}</span>
              )}
            </div>
          </div>

          <div className="card p-3 bg-gray-50 text-xs text-gray-600">
            <div className="grid grid-cols-3 gap-4">
              <div><span className="text-gray-400">Literature data</span><br /><strong>{latestRun.n_literature_points}</strong> points</div>
              <div><span className="text-gray-400">User experiments</span><br /><strong>{latestRun.n_user_points}</strong> points (2× weight)</div>
              <div><span className="text-gray-400">Candidates</span><br /><strong>{latestRun.n_candidates}</strong> proposed</div>
            </div>
            {latestRun.message && (
              <p className="mt-2 text-gray-500">{latestRun.message}</p>
            )}
          </div>

          {/* Candidates */}
          {latestRun.candidates && latestRun.candidates.length > 0 ? (
            <div className="space-y-3">
              {latestRun.candidates.map(cand => (
                <CandidateCard
                  key={cand.id}
                  candidate={cand}
                  inputVarMap={inputVarMap}
                  project={project}
                  projectId={id}
                  expanded={expandedCandidate === cand.id}
                  onToggle={() => setExpandedCandidate(expandedCandidate === cand.id ? null : cand.id)}
                  onExecute={() => handleExecute(cand)}
                  executing={executingId === cand.id}
                />
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-400 text-center py-4">No candidates in this run.</p>
          )}
        </div>
      )}

      {/* Run history */}
      {runs.length > 1 && (
        <div className="card overflow-hidden">
          <div className="px-4 py-2 bg-gray-50 text-xs font-semibold text-gray-500 uppercase tracking-wide">
            Previous Runs ({runs.length - 1})
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100">
                <th className="px-4 py-2 text-left text-xs text-gray-500">Date</th>
                <th className="px-4 py-2 text-left text-xs text-gray-500">Model</th>
                <th className="px-4 py-2 text-left text-xs text-gray-500">Data</th>
                <th className="px-4 py-2 text-left text-xs text-gray-500">Status</th>
                <th className="px-4 py-2" />
              </tr>
            </thead>
            <tbody>
              {runs.slice(1).map(r => (
                <tr key={r.id} className="border-b border-gray-50 hover:bg-gray-50">
                  <td className="px-4 py-2 text-xs text-gray-600">{r.created_at.split('T')[0]}</td>
                  <td className="px-4 py-2 text-xs font-mono text-gray-700">{r.model_type || '—'}</td>
                  <td className="px-4 py-2 text-xs text-gray-500">
                    {r.n_literature_points}L + {r.n_user_points}U
                  </td>
                  <td className="px-4 py-2">
                    <span className={`badge text-xs ${
                      r.status === 'completed' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'
                    }`}>{r.status}</span>
                  </td>
                  <td className="px-4 py-2">
                    <button
                      className="text-xs text-indigo-600 hover:underline"
                      onClick={async () => {
                        const full = await optimizationApi.getRun(r.id);
                        setLatestRun(full);
                      }}
                    >
                      Load →
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {!latestRun && !recommending && (
        <div className="card p-10 text-center">
          <TrendingUp className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500 font-medium">No recommendations yet</p>
          <p className="text-xs text-gray-400 mt-1 mb-4">
            Click <strong>Recommend Next Experiments</strong> to run Bayesian optimisation.
          </p>
        </div>
      )}
    </div>
  );
}

function CandidateCard({ candidate: cand, inputVarMap, project, projectId, expanded, onToggle, onExecute, executing }: {
  candidate: RecommendedCandidate;
  inputVarMap: Record<string, ProjectVariable>;
  project: OptimizationProject | null;
  projectId: string;
  expanded: boolean;
  onToggle: () => void;
  onExecute: () => void;
  executing: boolean;
}) {
  const getRankColor = (rank: number) => {
    if (rank === 1) return 'bg-amber-100 text-amber-800 border-amber-300';
    if (rank === 2) return 'bg-gray-100 text-gray-700 border-gray-300';
    if (rank === 3) return 'bg-orange-50 text-orange-700 border-orange-200';
    return 'bg-white text-gray-600';
  };

  const rankLabel = ['', '🥇 #1 Best', '🥈 #2', '🥉 #3', '#4', '#5'][cand.rank] || `#${cand.rank}`;

  return (
    <div className={`card overflow-hidden border ${getRankColor(cand.rank)}`}>
      <button className="w-full px-5 py-4 flex items-start justify-between hover:bg-white/50 transition-colors text-left"
        onClick={onToggle}>
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-2">
            <span className="font-bold text-sm">{rankLabel}</span>
            {cand.was_executed && (
              <span className="badge bg-green-100 text-green-700 flex items-center gap-1">
                <CheckCircle className="w-3 h-3" /> Executed
              </span>
            )}
            {cand.predicted_mean != null && project?.objective_variable && (
              <span className="badge bg-indigo-100 text-indigo-700 font-mono text-xs">
                {project.objective_variable} ≈ {cand.predicted_mean}
                {cand.predicted_std != null && ` ± ${cand.predicted_std}`}
              </span>
            )}
            {cand.acquisition_score != null && (
              <span className="badge bg-blue-100 text-blue-700 text-xs">
                EI = {cand.acquisition_score.toFixed(4)}
              </span>
            )}
          </div>
          {/* Top 3 proposed inputs preview */}
          {cand.proposed_inputs && (
            <div className="flex flex-wrap gap-2">
              {Object.entries(cand.proposed_inputs).slice(0, 4).map(([k, v]) => {
                const varDef = inputVarMap[k];
                return (
                  <span key={k} className="text-xs bg-white/70 border rounded px-2 py-0.5">
                    <span className="text-gray-500">{varDef?.label || k}:</span>{' '}
                    <span className="font-mono">{String(v)}</span>
                    {varDef?.unit && <span className="text-gray-400"> {varDef.unit}</span>}
                  </span>
                );
              })}
              {Object.keys(cand.proposed_inputs).length > 4 && (
                <span className="text-xs text-gray-400">+{Object.keys(cand.proposed_inputs).length - 4} more</span>
              )}
            </div>
          )}
        </div>
        <div className="ml-3 flex-shrink-0">
          {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </div>
      </button>

      {expanded && (
        <div className="px-5 py-4 border-t border-gray-200 space-y-4 bg-white/80">
          {/* All proposed conditions */}
          {cand.proposed_inputs && Object.keys(cand.proposed_inputs).length > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-blue-700 uppercase tracking-wide mb-2">
                Proposed Experimental Conditions
              </h4>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                {Object.entries(cand.proposed_inputs).map(([k, v]) => {
                  const varDef = inputVarMap[k];
                  return (
                    <div key={k} className="text-xs">
                      <span className="text-gray-500">{varDef?.label || k}</span>
                      {varDef?.unit && <span className="text-gray-400 ml-1">[{varDef.unit}]</span>}
                      <div className="font-mono font-semibold text-gray-900">{String(v)}</div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Model prediction */}
          <div>
            <h4 className="text-xs font-semibold text-indigo-700 uppercase tracking-wide mb-2">
              Model Prediction
            </h4>
            <div className="grid grid-cols-3 gap-3 text-xs">
              <div>
                <span className="text-gray-400">Predicted value</span>
                <div className="font-mono font-bold text-indigo-800">
                  {cand.predicted_mean != null ? cand.predicted_mean : '—'}
                  {project?.objective_variable ? ` (${project.objective_variable})` : ''}
                </div>
              </div>
              <div>
                <span className="text-gray-400">Uncertainty (σ)</span>
                <div className="font-mono font-bold text-gray-700">
                  {cand.predicted_std != null ? `± ${cand.predicted_std}` : '—'}
                </div>
              </div>
              <div>
                <span className="text-gray-400">EI score</span>
                <div className="font-mono font-bold text-blue-700">
                  {cand.acquisition_score != null ? cand.acquisition_score.toFixed(6) : '—'}
                </div>
              </div>
            </div>
          </div>

          {/* Explanation */}
          {cand.explanation && (
            <div>
              <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
                Why recommended
              </h4>
              <p className="text-xs text-gray-700 leading-relaxed">{cand.explanation}</p>
            </div>
          )}

          {/* Supporting literature */}
          {cand.supporting_paper_ids && cand.supporting_paper_ids.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-blue-600 uppercase tracking-wide mb-1 flex items-center gap-1">
                <BookOpen className="w-3 h-3" /> Supporting Literature
              </h4>
              <div className="flex flex-wrap gap-1">
                {cand.supporting_paper_ids.map(pid => (
                  <Link
                    key={pid}
                    href={`/papers/${pid}`}
                    className="text-xs text-indigo-600 hover:underline bg-blue-50 px-2 py-0.5 rounded"
                  >
                    {pid.slice(0, 8)}…
                  </Link>
                ))}
              </div>
            </div>
          )}

          {/* Action */}
          {!cand.was_executed ? (
            <div className="flex items-center gap-3 pt-2 border-t border-gray-100">
              <button
                className="btn-primary bg-green-600 hover:bg-green-700 text-sm"
                onClick={onExecute}
                disabled={executing}
              >
                <Beaker className="w-4 h-4" />
                {executing ? 'Marking…' : 'I ran this experiment'}
              </button>
              <Link
                href={`/optimization/projects/${projectId}/experiments`}
                className="text-xs text-gray-500 hover:underline"
              >
                Or log full results →
              </Link>
            </div>
          ) : (
            <div className="flex items-center gap-2 pt-2 border-t border-gray-100 text-xs text-green-700">
              <CheckCircle className="w-4 h-4" />
              Experiment executed.{' '}
              <Link href={`/optimization/projects/${projectId}/experiments`}
                className="underline">
                Log the results →
              </Link>
              {' '}then run a new recommendation.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
