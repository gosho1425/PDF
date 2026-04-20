'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { optimizationApi } from '@/lib/api';
import { ArrowLeft, FlaskConical } from 'lucide-react';

export default function NewProjectPage() {
  const router = useRouter();
  const [form, setForm] = useState({
    name: '',
    description: '',
    material_system: '',
    objective_variable: 'Tc',
    objective_direction: 'maximize',
    constraints_note: '',
  });
  const [saving, setSaving] = useState(false);
  const [error, setError]   = useState<string | null>(null);

  const set = (k: string, v: string) => setForm(f => ({ ...f, [k]: v }));

  const submit = async () => {
    if (!form.name.trim()) { setError('Project name is required'); return; }
    setSaving(true);
    setError(null);
    try {
      const proj = await optimizationApi.createProject({
        name: form.name.trim(),
        description: form.description.trim() || undefined,
        material_system: form.material_system.trim() || undefined,
        objective_variable: form.objective_variable.trim() || undefined,
        objective_direction: form.objective_direction,
        constraints_note: form.constraints_note.trim() || undefined,
      });
      router.push(`/optimization/projects/${proj.id}`);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to create project');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="max-w-xl space-y-6">
      <div className="flex items-center gap-3">
        <Link href="/optimization" className="btn-secondary px-2 py-1">
          <ArrowLeft className="w-4 h-4" />
        </Link>
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <FlaskConical className="w-6 h-6 text-indigo-600" />
          New Optimization Project
        </h1>
      </div>

      {error && (
        <div className="card p-3 bg-red-50 border-red-300 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="card p-6 space-y-5">
        <div>
          <label className="label">Project Name *</label>
          <input className="input" value={form.name}
            onChange={e => set('name', e.target.value)}
            placeholder="e.g. Maximise Tc for YBCO PLD films" />
        </div>

        <div>
          <label className="label">Description</label>
          <textarea className="input" rows={2} value={form.description}
            onChange={e => set('description', e.target.value)}
            placeholder="What are you trying to achieve?" />
        </div>

        <div>
          <label className="label">Material System</label>
          <input className="input" value={form.material_system}
            onChange={e => set('material_system', e.target.value)}
            placeholder="e.g. YBCO, NbN, MgB2" />
          <p className="text-xs text-gray-400 mt-1">
            Used to filter relevant literature papers. Leave blank to use all papers.
          </p>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="label">Objective Variable</label>
            <input className="input" value={form.objective_variable}
              onChange={e => set('objective_variable', e.target.value)}
              placeholder="e.g. Tc, Jc, resistivity" />
            <p className="text-xs text-gray-400 mt-1">
              The output you want to optimise.
            </p>
          </div>
          <div>
            <label className="label">Direction</label>
            <select className="input" value={form.objective_direction}
              onChange={e => set('objective_direction', e.target.value)}>
              <option value="maximize">Maximize (↑)</option>
              <option value="minimize">Minimize (↓)</option>
            </select>
          </div>
        </div>

        <div>
          <label className="label">Constraints / Notes</label>
          <textarea className="input" rows={2} value={form.constraints_note}
            onChange={e => set('constraints_note', e.target.value)}
            placeholder="e.g. film_thickness must be < 200 nm, budget: 20 depositions" />
        </div>

        <div className="flex gap-3 pt-2">
          <button className="btn-primary" onClick={submit} disabled={saving}>
            {saving ? 'Creating…' : 'Create Project'}
          </button>
          <Link href="/optimization" className="btn-secondary">Cancel</Link>
        </div>
      </div>

      <div className="card p-4 bg-amber-50 border-amber-200">
        <p className="text-sm text-amber-800">
          <strong>After creating:</strong> Add variables (inputs + outputs), then
          seed from the default parameter list, review which literature papers
          match your material system, and click &quot;Recommend&quot; to get your first
          suggested experiments.
        </p>
      </div>
    </div>
  );
}
