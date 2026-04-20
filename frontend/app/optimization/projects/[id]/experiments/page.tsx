'use client';

import { useEffect, useState, useCallback } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { optimizationApi } from '@/lib/api';
import type { OptimizationProject, ProjectVariable, UserExperiment } from '@/types';
import { ArrowLeft, Plus, Trash2, AlertTriangle, Beaker, ChevronDown, ChevronUp } from 'lucide-react';

export default function ExperimentsPage() {
  const { id } = useParams<{ id: string }>();
  const [project, setProject]         = useState<OptimizationProject | null>(null);
  const [variables, setVariables]     = useState<ProjectVariable[]>([]);
  const [experiments, setExperiments] = useState<UserExperiment[]>([]);
  const [showForm, setShowForm]       = useState(false);
  const [saving, setSaving]           = useState(false);
  const [error, setError]             = useState<string | null>(null);
  const [expandedId, setExpandedId]   = useState<string | null>(null);

  // Form state
  const [form, setForm] = useState({
    name: '', notes: '', status: 'completed', run_date: '',
    inputs: {} as Record<string, string>,
    outputs: {} as Record<string, string>,
  });

  const load = useCallback(async () => {
    try {
      const [proj, vars, exps] = await Promise.all([
        optimizationApi.getProject(id),
        optimizationApi.listVariables(id),
        optimizationApi.listExperiments(id),
      ]);
      setProject(proj);
      setVariables(vars);
      setExperiments(exps);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load');
    }
  }, [id]);

  useEffect(() => { load(); }, [load]);

  const inputVars  = variables.filter(v => v.role === 'input');
  const outputVars = variables.filter(v => v.role === 'output');

  const submit = async () => {
    setSaving(true); setError(null);
    try {
      // Build input_values / output_values dicts
      const input_values: Record<string, { value: number | string; unit?: string }> = {};
      for (const v of inputVars) {
        const val = form.inputs[v.name];
        if (val !== undefined && val !== '') {
          input_values[v.name] = {
            value: isNaN(Number(val)) ? val : Number(val),
            unit: v.unit || undefined,
          };
        }
      }
      const output_values: Record<string, { value: number | string; unit?: string }> = {};
      for (const v of outputVars) {
        const val = form.outputs[v.name];
        if (val !== undefined && val !== '') {
          output_values[v.name] = {
            value: isNaN(Number(val)) ? val : Number(val),
            unit: v.unit || undefined,
          };
        }
      }

      await optimizationApi.createExperiment(id, {
        name: form.name || undefined,
        notes: form.notes || undefined,
        status: form.status,
        run_date: form.run_date || undefined,
        input_values,
        output_values,
      });

      setShowForm(false);
      setForm({ name: '', notes: '', status: 'completed', run_date: '', inputs: {}, outputs: {} });
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to save experiment');
    } finally {
      setSaving(false);
    }
  };

  const deleteExp = async (expId: string) => {
    if (!confirm('Delete this experiment? This cannot be undone.')) return;
    try {
      await optimizationApi.deleteExperiment(expId);
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to delete');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link href={`/optimization/projects/${id}`} className="btn-secondary px-2 py-1">
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
              <Beaker className="w-5 h-5 text-green-600" /> My Experiments
            </h1>
            {project && <p className="text-sm text-gray-500">{project.name}</p>}
          </div>
        </div>
        <button className="btn-primary" onClick={() => { setShowForm(true); setError(null); }}>
          <Plus className="w-4 h-4" /> Log Experiment
        </button>
      </div>

      {error && (
        <div className="card p-3 bg-red-50 border-red-300 flex gap-2">
          <AlertTriangle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {/* Add experiment form */}
      {showForm && (
        <div className="card p-5 border-green-300 bg-green-50/20">
          <h3 className="font-semibold text-gray-800 mb-4">Log New Experiment</h3>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-4">
            <div>
              <label className="label">Run Name / Label</label>
              <input className="input" value={form.name}
                onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                placeholder="e.g. Run 004 — high power" />
            </div>
            <div>
              <label className="label">Status</label>
              <select className="input" value={form.status}
                onChange={e => setForm(f => ({ ...f, status: e.target.value }))}>
                <option value="completed">Completed</option>
                <option value="failed">Failed</option>
                <option value="planned">Planned</option>
              </select>
            </div>
            <div>
              <label className="label">Run Date</label>
              <input type="date" className="input" value={form.run_date}
                onChange={e => setForm(f => ({ ...f, run_date: e.target.value }))} />
            </div>
          </div>

          {/* Input conditions */}
          {inputVars.length > 0 && (
            <div className="mb-4">
              <h4 className="text-sm font-semibold text-blue-700 mb-2">
                Input Conditions
              </h4>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                {inputVars.map(v => (
                  <div key={v.name}>
                    <label className="label text-xs">
                      {v.label || v.name}
                      {v.unit && <span className="text-gray-400 ml-1">[{v.unit}]</span>}
                    </label>
                    <input
                      type={v.var_type === 'categorical' ? 'text' : 'number'}
                      step="any"
                      className="input"
                      value={form.inputs[v.name] || ''}
                      onChange={e => setForm(f => ({
                        ...f, inputs: { ...f.inputs, [v.name]: e.target.value }
                      }))}
                      placeholder={v.var_type === 'categorical' ? 'text value' : 'numeric'}
                    />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Output results */}
          {outputVars.length > 0 && (
            <div className="mb-4">
              <h4 className="text-sm font-semibold text-green-700 mb-2">
                Measured Results
                {project?.objective_variable && (
                  <span className="ml-2 text-indigo-600 font-normal text-xs">
                    ★ {project.objective_variable} is the objective
                  </span>
                )}
              </h4>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                {outputVars.map(v => (
                  <div key={v.name}>
                    <label className={`label text-xs ${v.is_objective ? 'text-indigo-700' : ''}`}>
                      {v.is_objective && '★ '}
                      {v.label || v.name}
                      {v.unit && <span className="text-gray-400 ml-1">[{v.unit}]</span>}
                    </label>
                    <input
                      type="number" step="any"
                      className={`input ${v.is_objective ? 'border-indigo-400 ring-1 ring-indigo-300' : ''}`}
                      value={form.outputs[v.name] || ''}
                      onChange={e => setForm(f => ({
                        ...f, outputs: { ...f.outputs, [v.name]: e.target.value }
                      }))}
                    />
                  </div>
                ))}
              </div>
            </div>
          )}

          {variables.length === 0 && (
            <div className="mb-4 p-3 bg-amber-50 border border-amber-200 rounded-md text-xs text-amber-700">
              No variables defined. <Link href={`/optimization/projects/${id}/variables`}
                className="underline">Add variables first →</Link>
            </div>
          )}

          <div>
            <label className="label">Notes</label>
            <textarea className="input" rows={2} value={form.notes}
              onChange={e => setForm(f => ({ ...f, notes: e.target.value }))}
              placeholder="Any observations, deviations from plan, issues, etc." />
          </div>

          <div className="flex gap-2 mt-4">
            <button className="btn-primary" onClick={submit} disabled={saving}>
              {saving ? 'Saving…' : 'Save Experiment'}
            </button>
            <button className="btn-secondary"
              onClick={() => setShowForm(false)}>Cancel</button>
          </div>
        </div>
      )}

      {/* Experiment list */}
      {experiments.length === 0 && !showForm ? (
        <div className="card p-10 text-center">
          <Beaker className="w-10 h-10 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500 font-medium">No experiments logged yet</p>
          <p className="text-xs text-gray-400 mt-1 mb-4">
            Log your real lab results here. They become the highest-trust data
            for Bayesian optimization.
          </p>
          <button className="btn-primary" onClick={() => setShowForm(true)}>
            <Plus className="w-4 h-4" /> Log First Experiment
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {experiments.map(exp => (
            <ExperimentCard
              key={exp.id}
              exp={exp}
              project={project}
              variables={variables}
              expanded={expandedId === exp.id}
              onToggle={() => setExpandedId(expandedId === exp.id ? null : exp.id)}
              onDelete={() => deleteExp(exp.id)}
            />
          ))}
        </div>
      )}

      <div className="card p-4 bg-indigo-50 border-indigo-200">
        <p className="text-sm text-indigo-800">
          <strong>Why this matters:</strong> User experiments are the highest-trust data
          in the model (2× weight vs literature). Each experiment you log directly
          improves the accuracy of the next recommendation. Even failed runs help
          — the model learns what conditions to avoid.
        </p>
      </div>
    </div>
  );
}

function ExperimentCard({ exp, project, variables, expanded, onToggle, onDelete }: {
  exp: UserExperiment;
  project: OptimizationProject | null;
  variables: ProjectVariable[];
  expanded: boolean;
  onToggle: () => void;
  onDelete: () => void;
}) {
  const inputVars  = variables.filter(v => v.role === 'input');
  const outputVars = variables.filter(v => v.role === 'output');

  return (
    <div className="card overflow-hidden">
      <button
        className="w-full px-5 py-3 flex items-center justify-between hover:bg-gray-50 transition-colors"
        onClick={onToggle}
      >
        <div className="flex items-center gap-3">
          <span className={`badge ${
            exp.status === 'completed' ? 'bg-green-100 text-green-700' :
            exp.status === 'failed'    ? 'bg-red-100 text-red-700' :
            'bg-gray-100 text-gray-600'
          }`}>{exp.status}</span>
          <span className="font-medium text-gray-800 text-sm">
            {exp.name || `Experiment ${exp.id.slice(0, 8)}`}
          </span>
          {exp.run_date && (
            <span className="text-xs text-gray-400">
              {exp.run_date.split('T')[0]}
            </span>
          )}
          {exp.objective_value != null && project?.objective_variable && (
            <span className="badge bg-indigo-100 text-indigo-700 font-mono">
              {project.objective_variable} = {exp.objective_value}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {expanded ? <ChevronUp className="w-4 h-4 text-gray-400" /> :
                      <ChevronDown className="w-4 h-4 text-gray-400" />}
        </div>
      </button>

      {expanded && (
        <div className="px-5 py-4 border-t border-gray-100 space-y-4">
          {/* Inputs */}
          {inputVars.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-blue-700 uppercase tracking-wide mb-2">
                Input Conditions
              </h4>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                {inputVars.map(v => {
                  const val = exp.input_values?.[v.name];
                  const display = val ? (typeof val === 'object' ? val.value : val) : null;
                  return (
                    <div key={v.name} className="text-xs">
                      <span className="text-gray-500">{v.label || v.name}</span>
                      <div className="font-mono text-gray-800">
                        {display != null ? `${display} ${v.unit || ''}` : '—'}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Outputs */}
          {outputVars.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-green-700 uppercase tracking-wide mb-2">
                Measured Results
              </h4>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                {outputVars.map(v => {
                  const val = exp.output_values?.[v.name];
                  const display = val ? (typeof val === 'object' ? val.value : val) : null;
                  return (
                    <div key={v.name} className={`text-xs ${v.is_objective ? 'font-semibold text-indigo-700' : ''}`}>
                      <span className={v.is_objective ? 'text-indigo-600' : 'text-gray-500'}>
                        {v.is_objective && '★ '}{v.label || v.name}
                      </span>
                      <div className="font-mono">
                        {display != null ? `${display} ${v.unit || ''}` : '—'}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {exp.notes && (
            <div>
              <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Notes</h4>
              <p className="text-xs text-gray-700">{exp.notes}</p>
            </div>
          )}

          {exp.from_recommendation_id && (
            <p className="text-xs text-indigo-600">
              📊 From recommendation run {exp.from_recommendation_id.slice(0, 8)}
            </p>
          )}

          <div className="flex justify-end">
            <button onClick={onDelete}
              className="text-xs text-red-400 hover:text-red-600 flex items-center gap-1">
              <Trash2 className="w-3.5 h-3.5" /> Delete
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
