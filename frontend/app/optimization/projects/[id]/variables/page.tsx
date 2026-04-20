'use client';

import { useEffect, useState, useCallback } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { optimizationApi } from '@/lib/api';
import type { OptimizationProject, ProjectVariable } from '@/types';
import { ArrowLeft, Plus, Trash2, Star, AlertTriangle, Sparkles, Settings } from 'lucide-react';

const ROLE_OPTIONS = ['input', 'output', 'material'] as const;
const TYPE_OPTIONS = ['continuous', 'categorical', 'integer'] as const;

const DEFAULT_NEW_VAR = {
  name: '', label: '', role: 'input', var_type: 'continuous', unit: '',
  description: '', min_value: '', max_value: '', is_objective: false, is_constraint: false,
};

export default function VariablesPage() {
  const { id } = useParams<{ id: string }>();
  const [project, setProject]     = useState<OptimizationProject | null>(null);
  const [variables, setVariables] = useState<ProjectVariable[]>([]);
  const [showForm, setShowForm]   = useState(false);
  const [newVar, setNewVar]       = useState({ ...DEFAULT_NEW_VAR });
  const [saving, setSaving]       = useState(false);
  const [seeding, setSeeding]     = useState(false);
  const [error, setError]         = useState<string | null>(null);
  const [success, setSuccess]     = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [proj, vars] = await Promise.all([
        optimizationApi.getProject(id),
        optimizationApi.listVariables(id),
      ]);
      setProject(proj);
      setVariables(vars);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load');
    }
  }, [id]);

  useEffect(() => { load(); }, [load]);

  const setNewField = (k: string, v: unknown) => setNewVar(f => ({ ...f, [k]: v }));

  const addVar = async () => {
    if (!newVar.name.trim()) { setError('Variable name is required'); return; }
    setSaving(true); setError(null);
    try {
      await optimizationApi.createVariable(id, {
        ...newVar,
        min_value: newVar.min_value !== '' ? Number(newVar.min_value) : undefined,
        max_value: newVar.max_value !== '' ? Number(newVar.max_value) : undefined,
        label: newVar.label || newVar.name,
      });
      setShowForm(false);
      setNewVar({ ...DEFAULT_NEW_VAR });
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to create variable');
    } finally {
      setSaving(false);
    }
  };

  const deleteVar = async (varId: string) => {
    if (!confirm('Delete this variable?')) return;
    try {
      await optimizationApi.deleteVariable(varId);
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to delete');
    }
  };

  const setObjective = async (v: ProjectVariable) => {
    try {
      await optimizationApi.updateVariable(v.id, { is_objective: true });
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to update');
    }
  };

  const seedFromDefaults = async () => {
    setSeeding(true); setError(null);
    try {
      const res = await optimizationApi.seedVariables(id);
      setSuccess(`Added ${res.count} variables from default parameter list.`);
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to seed');
    } finally {
      setSeeding(false);
    }
  };

  const inputVars    = variables.filter(v => v.role === 'input');
  const outputVars   = variables.filter(v => v.role === 'output');
  const materialVars = variables.filter(v => v.role === 'material');

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link href={`/optimization/projects/${id}`} className="btn-secondary px-2 py-1">
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
              <Settings className="w-5 h-5 text-gray-600" /> Variables
            </h1>
            {project && <p className="text-sm text-gray-500">{project.name}</p>}
          </div>
        </div>
        <div className="flex gap-2">
          <button className="btn-secondary" onClick={seedFromDefaults} disabled={seeding}>
            <Sparkles className="w-4 h-4" />
            {seeding ? 'Seeding…' : 'Seed from Defaults'}
          </button>
          <button className="btn-primary" onClick={() => { setShowForm(true); setError(null); }}>
            <Plus className="w-4 h-4" /> Add Variable
          </button>
        </div>
      </div>

      {error && (
        <div className="card p-3 bg-red-50 border-red-300 flex gap-2">
          <AlertTriangle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}
      {success && (
        <div className="card p-3 bg-green-50 border-green-300 text-sm text-green-700">
          {success}
        </div>
      )}

      {/* Add variable form */}
      {showForm && (
        <div className="card p-5 border-indigo-300 bg-indigo-50/30">
          <h3 className="font-semibold text-gray-800 mb-4">New Variable</h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-3">
            <div>
              <label className="label">Name (key) *</label>
              <input className="input" value={newVar.name}
                onChange={e => setNewField('name', e.target.value)}
                placeholder="e.g. sputtering_power" />
            </div>
            <div>
              <label className="label">Label</label>
              <input className="input" value={newVar.label}
                onChange={e => setNewField('label', e.target.value)}
                placeholder="Human-readable name" />
            </div>
            <div>
              <label className="label">Role</label>
              <select className="input" value={newVar.role}
                onChange={e => setNewField('role', e.target.value)}>
                {ROLE_OPTIONS.map(r => <option key={r} value={r}>{r}</option>)}
              </select>
            </div>
            <div>
              <label className="label">Type</label>
              <select className="input" value={newVar.var_type}
                onChange={e => setNewField('var_type', e.target.value)}>
                {TYPE_OPTIONS.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            <div>
              <label className="label">Unit</label>
              <input className="input" value={newVar.unit}
                onChange={e => setNewField('unit', e.target.value)}
                placeholder="K, W, nm, Pa…" />
            </div>
            <div className="grid grid-cols-2 gap-1.5">
              <div>
                <label className="label">Min</label>
                <input type="number" className="input" value={newVar.min_value}
                  onChange={e => setNewField('min_value', e.target.value)} />
              </div>
              <div>
                <label className="label">Max</label>
                <input type="number" className="input" value={newVar.max_value}
                  onChange={e => setNewField('max_value', e.target.value)} />
              </div>
            </div>
          </div>
          <div className="flex items-center gap-4 mb-4">
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={newVar.is_objective}
                onChange={e => setNewField('is_objective', e.target.checked)} />
              <Star className="w-3.5 h-3.5 text-indigo-500" />
              Set as objective
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={newVar.is_constraint}
                onChange={e => setNewField('is_constraint', e.target.checked)} />
              Constraint
            </label>
          </div>
          <div className="flex gap-2">
            <button className="btn-primary" onClick={addVar} disabled={saving}>
              {saving ? 'Adding…' : 'Add'}
            </button>
            <button className="btn-secondary"
              onClick={() => { setShowForm(false); setNewVar({ ...DEFAULT_NEW_VAR }); }}>
              Cancel
            </button>
          </div>
        </div>
      )}

      {variables.length === 0 ? (
        <div className="card p-10 text-center">
          <Settings className="w-10 h-10 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500 font-medium">No variables defined</p>
          <p className="text-xs text-gray-400 mt-1 mb-4">
            Click <strong>Seed from Defaults</strong> to import all standard superconductor parameters,
            or add custom variables manually.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {[
            { label: 'Input Variables (controllable conditions)', vars: inputVars, color: 'blue' },
            { label: 'Output Variables (measured results)',        vars: outputVars, color: 'green' },
            { label: 'Material Descriptors',                       vars: materialVars, color: 'gray' },
          ].map(({ label, vars, color }) =>
            vars.length > 0 ? (
              <div key={label} className="card overflow-hidden">
                <div className={`px-4 py-2 text-xs font-semibold uppercase tracking-wide
                  ${color === 'blue' ? 'bg-blue-50 text-blue-700' :
                    color === 'green' ? 'bg-green-50 text-green-700' :
                    'bg-gray-50 text-gray-600'}`}>
                  {label} ({vars.length})
                </div>
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-100">
                      <th className="text-left px-4 py-2 text-xs text-gray-500 font-medium">Name</th>
                      <th className="text-left px-4 py-2 text-xs text-gray-500 font-medium">Label</th>
                      <th className="text-left px-4 py-2 text-xs text-gray-500 font-medium">Unit</th>
                      <th className="text-left px-4 py-2 text-xs text-gray-500 font-medium">Range</th>
                      <th className="text-left px-4 py-2 text-xs text-gray-500 font-medium">Flags</th>
                      <th className="px-4 py-2" />
                    </tr>
                  </thead>
                  <tbody>
                    {vars.map(v => (
                      <tr key={v.id} className="border-b border-gray-50 hover:bg-gray-50">
                        <td className="px-4 py-2 font-mono text-xs text-gray-700">{v.name}</td>
                        <td className="px-4 py-2 text-gray-700">{v.label || '—'}</td>
                        <td className="px-4 py-2 text-gray-500 text-xs">{v.unit || '—'}</td>
                        <td className="px-4 py-2 text-gray-500 text-xs">
                          {v.min_value != null || v.max_value != null
                            ? `${v.min_value ?? '—'} … ${v.max_value ?? '—'}`
                            : 'auto'}
                        </td>
                        <td className="px-4 py-2">
                          <div className="flex gap-1">
                            {v.is_objective && (
                              <span className="badge bg-indigo-100 text-indigo-700 gap-0.5">
                                <Star className="w-2.5 h-2.5" /> objective
                              </span>
                            )}
                            {v.is_constraint && (
                              <span className="badge bg-amber-100 text-amber-700">constraint</span>
                            )}
                          </div>
                        </td>
                        <td className="px-4 py-2">
                          <div className="flex gap-1 justify-end">
                            {v.role === 'output' && !v.is_objective && (
                              <button
                                className="text-xs text-indigo-600 hover:underline flex items-center gap-0.5"
                                onClick={() => setObjective(v)}
                                title="Set as optimization objective"
                              >
                                <Star className="w-3 h-3" /> Set objective
                              </button>
                            )}
                            <button
                              className="text-red-400 hover:text-red-600 ml-2"
                              onClick={() => deleteVar(v.id)}
                              title="Delete"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : null
          )}
        </div>
      )}

      <div className="card p-4 bg-amber-50 border-amber-200">
        <p className="text-sm text-amber-800">
          <strong>Tip:</strong> Variable names must match exactly what is stored in your PDF extractions
          (e.g. <code className="bg-amber-100 px-1 rounded">Tc</code>,{' '}
          <code className="bg-amber-100 px-1 rounded">sputtering_power</code>).
          Click <strong>Seed from Defaults</strong> to auto-import all standard names.
          Set <strong>Min/Max</strong> ranges to improve recommendation quality.
          Mark one output variable as the <strong>objective</strong>.
        </p>
      </div>
    </div>
  );
}
