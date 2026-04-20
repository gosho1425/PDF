'use client';

import { useEffect, useState, useCallback } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { optimizationApi } from '@/lib/api';
import type { OptimizationProject, ProjectVariable } from '@/types';
import {
  ArrowLeft, Plus, Trash2, Star, AlertTriangle,
  Sparkles, Settings, Pencil, Check, X, Tag,
} from 'lucide-react';

const ROLE_OPTIONS = ['input', 'output', 'material'] as const;
const TYPE_OPTIONS = ['continuous', 'categorical', 'integer'] as const;

const DEFAULT_NEW_VAR = {
  name: '', label: '', role: 'input' as string, var_type: 'continuous', unit: '',
  description: '', min_value: '', max_value: '',
  choices: '',          // comma-separated string for UI
  is_objective: false, is_constraint: false,
};

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

/** Parse a comma-separated choices string into an array. */
const parseChoices = (s: string): string[] =>
  s.split(',').map(c => c.trim()).filter(Boolean);

/** True when the role uses a numeric range (input / output). */
const isNumeric = (role: string) => role === 'input' || role === 'output';

// ─────────────────────────────────────────────────────────────────────────────
// Inline-edit types
// ─────────────────────────────────────────────────────────────────────────────

interface EditState {
  label:         string;
  unit:          string;
  min_value:     string;
  max_value:     string;
  choices:       string;   // comma-separated
  is_objective:  boolean;
  is_constraint: boolean;
  role:          string;
}

interface VariableSavePayload {
  label?:         string;
  unit?:          string | null;
  min_value?:     number | null;
  max_value?:     number | null;
  choices?:       string[] | null;
  is_objective?:  boolean;
  is_constraint?: boolean;
  role?:          string;
}

function varToEditState(v: ProjectVariable): EditState {
  return {
    label:         v.label ?? '',
    unit:          v.unit  ?? '',
    min_value:     v.min_value != null ? String(v.min_value) : '',
    max_value:     v.max_value != null ? String(v.max_value) : '',
    choices:       Array.isArray(v.choices) ? v.choices.join(', ') : '',
    is_objective:  v.is_objective,
    is_constraint: v.is_constraint,
    role:          v.role,
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// NumericRow  (input / output)
// ─────────────────────────────────────────────────────────────────────────────

function NumericRow({
  v, onSave, onDelete, onSetObjective,
}: {
  v: ProjectVariable;
  onSave: (id: string, p: VariableSavePayload) => Promise<void>;
  onDelete: (id: string) => void;
  onSetObjective: (v: ProjectVariable) => void;
}) {
  const [editing, setEditing]     = useState(false);
  const [draft, setDraft]         = useState<EditState>(varToEditState(v));
  const [rowSaving, setRowSaving] = useState(false);

  const startEdit  = () => { setDraft(varToEditState(v)); setEditing(true); };
  const cancelEdit = () => setEditing(false);
  const set        = (k: keyof EditState, val: unknown) =>
    setDraft(d => ({ ...d, [k]: val }));

  const toNum = (s: string): number | null => {
    if (s === '') return null;
    const n = Number(s);
    return isNaN(n) ? null : n;
  };

  const commitEdit = async () => {
    setRowSaving(true);
    try {
      await onSave(v.id, {
        label:         draft.label || v.name,
        unit:          draft.unit || null,
        min_value:     toNum(draft.min_value),
        max_value:     toNum(draft.max_value),
        is_objective:  v.role === 'output' ? draft.is_objective : false,
        is_constraint: draft.is_constraint,
        role:          draft.role,
      });
      setEditing(false);
    } finally {
      setRowSaving(false);
    }
  };

  if (editing) {
    return (
      <tr className="border-b border-indigo-100 bg-indigo-50/40">
        {/* Key */}
        <td className="px-3 py-2 font-mono text-xs text-gray-600 whitespace-nowrap">{v.name}</td>

        {/* Label */}
        <td className="px-3 py-2">
          <input className="input py-1 text-xs w-full min-w-[110px]"
            value={draft.label} placeholder={v.name}
            onChange={e => set('label', e.target.value)} />
        </td>

        {/* Unit */}
        <td className="px-3 py-2">
          <input className="input py-1 text-xs w-16"
            value={draft.unit} placeholder="K / W / nm…"
            onChange={e => set('unit', e.target.value)} />
        </td>

        {/* Min */}
        <td className="px-3 py-2">
          <input type="number" step="any" className="input py-1 text-xs w-20"
            value={draft.min_value} placeholder="min"
            onChange={e => set('min_value', e.target.value)} />
        </td>

        {/* Max */}
        <td className="px-3 py-2">
          <input type="number" step="any" className="input py-1 text-xs w-20"
            value={draft.max_value} placeholder="max"
            onChange={e => set('max_value', e.target.value)} />
        </td>

        {/* Flags — objective only for output */}
        <td className="px-3 py-2">
          <div className="flex flex-col gap-1">
            {v.role === 'output' && (
              <label className="flex items-center gap-1 text-xs cursor-pointer select-none">
                <input type="checkbox"
                  checked={draft.is_objective}
                  onChange={e => set('is_objective', e.target.checked)} />
                <Star className="w-3 h-3 text-indigo-500" /> obj
              </label>
            )}
            <label className="flex items-center gap-1 text-xs cursor-pointer select-none">
              <input type="checkbox"
                checked={draft.is_constraint}
                onChange={e => set('is_constraint', e.target.checked)} />
              constraint
            </label>
          </div>
        </td>

        {/* Actions */}
        <td className="px-3 py-2">
          <div className="flex items-center gap-1.5">
            <button
              className="flex items-center gap-1 text-xs bg-indigo-600 text-white
                         px-2 py-1 rounded hover:bg-indigo-700 disabled:opacity-50"
              onClick={commitEdit} disabled={rowSaving}>
              <Check className="w-3 h-3" />{rowSaving ? '…' : 'Save'}
            </button>
            <button className="text-gray-400 hover:text-gray-600" onClick={cancelEdit}>
              <X className="w-4 h-4" />
            </button>
          </div>
        </td>
      </tr>
    );
  }

  // ── Read-only ──
  return (
    <tr className="border-b border-gray-50 hover:bg-gray-50 group">
      <td className="px-3 py-2 font-mono text-xs text-gray-600 whitespace-nowrap">{v.name}</td>
      <td className="px-3 py-2 text-sm text-gray-700">
        {v.label || <span className="text-gray-300">—</span>}
      </td>
      <td className="px-3 py-2 text-xs text-gray-500">
        {v.unit || <span className="text-gray-300">—</span>}
      </td>
      <td className="px-3 py-2 text-xs text-gray-500 font-mono">
        {v.min_value != null ? v.min_value : <span className="text-gray-300">—</span>}
      </td>
      <td className="px-3 py-2 text-xs text-gray-500 font-mono">
        {v.max_value != null ? v.max_value : <span className="text-gray-300">—</span>}
      </td>
      <td className="px-3 py-2">
        <div className="flex gap-1 flex-wrap">
          {v.is_objective && (
            <span className="badge bg-indigo-100 text-indigo-700 flex items-center gap-0.5">
              <Star className="w-2.5 h-2.5" /> objective
            </span>
          )}
          {v.is_constraint && (
            <span className="badge bg-amber-100 text-amber-700">constraint</span>
          )}
        </div>
      </td>
      <td className="px-3 py-2">
        <div className="flex items-center gap-1.5 justify-end opacity-0 group-hover:opacity-100 transition-opacity">
          {v.role === 'output' && !v.is_objective && (
            <button
              className="text-xs text-indigo-500 hover:text-indigo-700 flex items-center gap-0.5"
              onClick={() => onSetObjective(v)} title="Set as optimization objective">
              <Star className="w-3 h-3" />
            </button>
          )}
          <button className="text-gray-400 hover:text-indigo-600"
            onClick={startEdit} title="Edit variable">
            <Pencil className="w-3.5 h-3.5" />
          </button>
          <button className="text-gray-300 hover:text-red-500"
            onClick={() => onDelete(v.id)} title="Delete variable">
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </td>
    </tr>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// MaterialRow  (material descriptors — no unit / min / max)
// ─────────────────────────────────────────────────────────────────────────────

function MaterialRow({
  v, onSave, onDelete,
}: {
  v: ProjectVariable;
  onSave: (id: string, p: VariableSavePayload) => Promise<void>;
  onDelete: (id: string) => void;
}) {
  const [editing, setEditing]     = useState(false);
  const [draft, setDraft]         = useState<EditState>(varToEditState(v));
  const [rowSaving, setRowSaving] = useState(false);

  const startEdit  = () => { setDraft(varToEditState(v)); setEditing(true); };
  const cancelEdit = () => setEditing(false);
  const set        = (k: keyof EditState, val: unknown) =>
    setDraft(d => ({ ...d, [k]: val }));

  const commitEdit = async () => {
    setRowSaving(true);
    try {
      const choicesArr = parseChoices(draft.choices);
      await onSave(v.id, {
        label:   draft.label || v.name,
        choices: choicesArr.length > 0 ? choicesArr : null,
      });
      setEditing(false);
    } finally {
      setRowSaving(false);
    }
  };

  if (editing) {
    return (
      <tr className="border-b border-gray-200 bg-gray-50/60">
        {/* Key */}
        <td className="px-3 py-2 font-mono text-xs text-gray-600 whitespace-nowrap">{v.name}</td>

        {/* Label */}
        <td className="px-3 py-2">
          <input className="input py-1 text-xs w-full min-w-[110px]"
            value={draft.label} placeholder={v.name}
            onChange={e => set('label', e.target.value)} />
        </td>

        {/* Choices */}
        <td className="px-3 py-2" colSpan={2}>
          <div>
            <input className="input py-1 text-xs w-full"
              value={draft.choices}
              placeholder="e.g. YBCO, BSCCO, NbN  (comma-separated)"
              onChange={e => set('choices', e.target.value)} />
            <p className="text-[10px] text-gray-400 mt-0.5">
              Optional — list common values separated by commas
            </p>
          </div>
        </td>

        {/* Description (type hint) */}
        <td className="px-3 py-2">
          <span className="badge bg-gray-100 text-gray-500 text-[10px]">categorical / text</span>
        </td>

        {/* Actions */}
        <td className="px-3 py-2">
          <div className="flex items-center gap-1.5">
            <button
              className="flex items-center gap-1 text-xs bg-gray-700 text-white
                         px-2 py-1 rounded hover:bg-gray-800 disabled:opacity-50"
              onClick={commitEdit} disabled={rowSaving}>
              <Check className="w-3 h-3" />{rowSaving ? '…' : 'Save'}
            </button>
            <button className="text-gray-400 hover:text-gray-600" onClick={cancelEdit}>
              <X className="w-4 h-4" />
            </button>
          </div>
        </td>
      </tr>
    );
  }

  // ── Read-only ──
  const choices: string[] = Array.isArray(v.choices) ? v.choices : [];
  return (
    <tr className="border-b border-gray-50 hover:bg-gray-50 group">
      <td className="px-3 py-2 font-mono text-xs text-gray-600 whitespace-nowrap">{v.name}</td>
      <td className="px-3 py-2 text-sm text-gray-700">
        {v.label || <span className="text-gray-300">—</span>}
      </td>
      {/* Choices — spans the Unit + Min + Max columns */}
      <td className="px-3 py-2" colSpan={2}>
        {choices.length > 0 ? (
          <div className="flex flex-wrap gap-1">
            {choices.map(c => (
              <span key={c} className="inline-flex items-center gap-0.5 badge
                bg-gray-100 text-gray-600 text-[10px]">
                <Tag className="w-2.5 h-2.5" />{c}
              </span>
            ))}
          </div>
        ) : (
          <span className="text-xs text-gray-300 italic">free text</span>
        )}
      </td>
      {/* Type hint */}
      <td className="px-3 py-2">
        <span className="badge bg-gray-100 text-gray-500 text-[10px]">categorical / text</span>
      </td>
      {/* Actions */}
      <td className="px-3 py-2">
        <div className="flex items-center gap-1.5 justify-end opacity-0 group-hover:opacity-100 transition-opacity">
          <button className="text-gray-400 hover:text-indigo-600"
            onClick={startEdit} title="Edit variable">
            <Pencil className="w-3.5 h-3.5" />
          </button>
          <button className="text-gray-300 hover:text-red-500"
            onClick={() => onDelete(v.id)} title="Delete variable">
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </td>
    </tr>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Page
// ─────────────────────────────────────────────────────────────────────────────

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

  // ── Save existing variable ──────────────────────────────────────────────────
  const saveVar = async (varId: string, data: VariableSavePayload) => {
    setError(null);
    try {
      await optimizationApi.updateVariable(varId, data as object);
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to save');
      throw e;
    }
  };

  // ── Create new variable ─────────────────────────────────────────────────────
  const addVar = async () => {
    if (!newVar.name.trim()) { setError('Variable name is required'); return; }
    setSaving(true); setError(null);
    const isMat = newVar.role === 'material';
    try {
      await optimizationApi.createVariable(id, {
        name:      newVar.name,
        label:     newVar.label || newVar.name,
        role:      newVar.role,
        var_type:  isMat ? 'categorical' : newVar.var_type,
        unit:      isMat ? undefined : (newVar.unit || undefined),
        min_value: isMat || newVar.min_value === '' ? undefined : Number(newVar.min_value),
        max_value: isMat || newVar.max_value === '' ? undefined : Number(newVar.max_value),
        choices:   isMat && newVar.choices ? parseChoices(newVar.choices) : undefined,
        is_objective:  newVar.role === 'output' ? newVar.is_objective : false,
        is_constraint: isMat ? false : newVar.is_constraint,
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
    setSeeding(true); setError(null); setSuccess(null);
    try {
      const res = await optimizationApi.seedVariables(id);
      setSuccess(`Added ${res.count} variable(s). Click ✏️ on any row to edit.`);
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

  // ── Numeric table (Input / Output) ──────────────────────────────────────────
  const numericTable = (
    label: string,
    vars: ProjectVariable[],
    color: 'blue' | 'green',
  ) => {
    if (vars.length === 0) return null;
    return (
      <div key={label} className="card overflow-hidden">
        <div className={`px-4 py-2 text-xs font-semibold uppercase tracking-wide
          ${color === 'blue' ? 'bg-blue-50 text-blue-700' : 'bg-green-50 text-green-700'}`}>
          {label} ({vars.length})
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50/50">
                <th className="text-left px-3 py-2 text-xs text-gray-500 font-medium whitespace-nowrap">Key</th>
                <th className="text-left px-3 py-2 text-xs text-gray-500 font-medium">Label</th>
                <th className="text-left px-3 py-2 text-xs text-gray-500 font-medium">Unit</th>
                <th className="text-left px-3 py-2 text-xs text-gray-500 font-medium">Min</th>
                <th className="text-left px-3 py-2 text-xs text-gray-500 font-medium">Max</th>
                <th className="text-left px-3 py-2 text-xs text-gray-500 font-medium">Flags</th>
                <th className="px-3 py-2 w-24" />
              </tr>
            </thead>
            <tbody>
              {vars.map(v => (
                <NumericRow key={v.id} v={v}
                  onSave={saveVar} onDelete={deleteVar} onSetObjective={setObjective} />
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  // ── Material table ───────────────────────────────────────────────────────────
  const materialTable = () => {
    if (materialVars.length === 0) return null;
    return (
      <div className="card overflow-hidden">
        <div className="px-4 py-2 text-xs font-semibold uppercase tracking-wide bg-gray-50 text-gray-600">
          Material Descriptors ({materialVars.length})
          <span className="ml-2 font-normal text-gray-400 normal-case">
            — categorical / text fields, no unit or range
          </span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50/50">
                <th className="text-left px-3 py-2 text-xs text-gray-500 font-medium whitespace-nowrap">Key</th>
                <th className="text-left px-3 py-2 text-xs text-gray-500 font-medium">Label</th>
                <th className="text-left px-3 py-2 text-xs text-gray-500 font-medium" colSpan={2}>
                  Common Values <span className="text-gray-400 font-normal">(optional hint)</span>
                </th>
                <th className="text-left px-3 py-2 text-xs text-gray-500 font-medium">Type</th>
                <th className="px-3 py-2 w-24" />
              </tr>
            </thead>
            <tbody>
              {materialVars.map(v => (
                <MaterialRow key={v.id} v={v}
                  onSave={saveVar} onDelete={deleteVar} />
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  // Derived: is the new-var form showing material role?
  const newIsMaterial = newVar.role === 'material';
  const newIsOutput   = newVar.role === 'output';

  return (
    <div className="space-y-6">
      {/* Header */}
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

      {/* Feedback banners */}
      {error && (
        <div className="card p-3 bg-red-50 border-red-300 flex gap-2">
          <AlertTriangle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}
      {success && (
        <div className="card p-3 bg-green-50 border-green-300 text-sm text-green-700">
          ✓ {success}
        </div>
      )}

      {/* Inline usage hint */}
      {variables.length > 0 && (
        <div className="flex items-center gap-2 text-xs text-gray-400 px-1">
          <Pencil className="w-3 h-3" />
          Hover any row → click <strong className="text-gray-600">✏</strong> to edit inline.
        </div>
      )}

      {/* ── Add variable form ─────────────────────────────────────────────── */}
      {showForm && (
        <div className="card p-5 border-indigo-300 bg-indigo-50/30">
          <h3 className="font-semibold text-gray-800 mb-4">New Variable</h3>

          {/* Row 1: key, label, role */}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-3">
            <div>
              <label className="label">Key name *</label>
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
          </div>

          {/* Row 2: role-dependent fields */}
          {newIsMaterial ? (
            /* Material: only choices */
            <div className="mb-3">
              <label className="label flex items-center gap-1">
                <Tag className="w-3.5 h-3.5" /> Common Values
                <span className="text-gray-400 font-normal">(optional)</span>
              </label>
              <input className="input" value={newVar.choices}
                onChange={e => setNewField('choices', e.target.value)}
                placeholder="YBCO, BSCCO, NbN, MgB₂  (comma-separated)" />
              <p className="text-xs text-gray-400 mt-1">
                Material descriptors are free-text — no unit or numeric range needed.
              </p>
            </div>
          ) : (
            /* Numeric: type, unit, min, max */
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-3">
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
              <div>
                <label className="label">Min</label>
                <input type="number" step="any" className="input" value={newVar.min_value}
                  onChange={e => setNewField('min_value', e.target.value)} />
              </div>
              <div>
                <label className="label">Max</label>
                <input type="number" step="any" className="input" value={newVar.max_value}
                  onChange={e => setNewField('max_value', e.target.value)} />
              </div>
            </div>
          )}

          {/* Flags — only for non-material */}
          {!newIsMaterial && (
            <div className="flex items-center gap-4 mb-4">
              {newIsOutput && (
                <label className="flex items-center gap-2 text-sm cursor-pointer">
                  <input type="checkbox" checked={newVar.is_objective}
                    onChange={e => setNewField('is_objective', e.target.checked)} />
                  <Star className="w-3.5 h-3.5 text-indigo-500" />
                  Set as objective
                </label>
              )}
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input type="checkbox" checked={newVar.is_constraint}
                  onChange={e => setNewField('is_constraint', e.target.checked)} />
                Constraint
              </label>
            </div>
          )}

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

      {/* ── Variable tables ──────────────────────────────────────────────── */}
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
          {numericTable('Input Variables — controllable conditions', inputVars,  'blue')}
          {numericTable('Output Variables — measured results',       outputVars, 'green')}
          {materialTable()}
        </div>
      )}

      {/* Tips */}
      <div className="card p-4 bg-amber-50 border-amber-200 space-y-1.5">
        <p className="text-sm font-semibold text-amber-800">Tips</p>
        <ul className="text-xs text-amber-700 space-y-1 list-disc list-inside">
          <li>
            <strong>Input variables</strong>: set Min / Max to define the BO search space
            (e.g. sputtering_power 50–300 W).
          </li>
          <li>
            <strong>Output variables</strong>: mark exactly one with <strong>★ objective</strong>
            — that is what the BO engine will try to maximise or minimise.
          </li>
          <li>
            <strong>Material descriptors</strong>: free-text / categorical — just add common
            values as hints (optional). No range needed.
          </li>
          <li>
            Key names must match the extraction schema exactly
            (e.g. <code className="bg-amber-100 px-1 rounded">Tc</code>,{' '}
            <code className="bg-amber-100 px-1 rounded">sputtering_power</code>).
          </li>
        </ul>
      </div>
    </div>
  );
}
