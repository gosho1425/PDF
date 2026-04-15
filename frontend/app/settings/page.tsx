'use client';

import { useEffect, useState } from 'react';
import { settingsApi } from '@/lib/api';
import type { AppSettings, LlmInfo } from '@/types';
import toast from 'react-hot-toast';
import { Save, FolderSearch, Info, Plus, Trash2 } from 'lucide-react';

interface CustomParam {
  name: string;
  label: string;
  unit: string;
  role: 'input' | 'output' | 'material';
  description: string;
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [llm, setLlm] = useState<LlmInfo | null>(null);
  const [folder, setFolder] = useState('');
  const [folderValidation, setFolderValidation] = useState<{
    valid?: boolean; reason?: string; pdf_count?: number;
  } | null>(null);
  const [saving, setSaving] = useState(false);
  const [validating, setValidating] = useState(false);
  const [customParams, setCustomParams] = useState<CustomParam[]>([]);

  useEffect(() => {
    Promise.all([settingsApi.get(), settingsApi.getLlm()]).then(([s, l]) => {
      setSettings(s);
      setLlm(l);
      setFolder(s.paper_folder || '');
      try {
        const parsed = JSON.parse(s.custom_parameters || '[]');
        setCustomParams(Array.isArray(parsed) ? parsed : []);
      } catch { setCustomParams([]); }
    }).catch(() => toast.error('Could not load settings'));
  }, []);

  const validateFolder = async () => {
    if (!folder.trim()) return;
    setValidating(true);
    setFolderValidation(null);
    try {
      const r = await settingsApi.validateFolder(folder.trim());
      setFolderValidation(r);
    } catch (e: any) {
      setFolderValidation({ valid: false, reason: e.message });
    } finally {
      setValidating(false);
    }
  };

  const save = async () => {
    setSaving(true);
    try {
      await settingsApi.update({ paper_folder: folder.trim(), custom_parameters: customParams });
      toast.success('Settings saved!');
      const updated = await settingsApi.get();
      setSettings(updated);
    } catch (e: any) {
      toast.error(`Save failed: ${e.message}`);
    } finally {
      setSaving(false);
    }
  };

  const addParam = () => {
    setCustomParams(prev => [...prev, {
      name: '', label: '', unit: '', role: 'output', description: ''
    }]);
  };

  const removeParam = (i: number) =>
    setCustomParams(prev => prev.filter((_, idx) => idx !== i));

  const updateParam = (i: number, field: keyof CustomParam, value: string) =>
    setCustomParams(prev => prev.map((p, idx) =>
      idx === i ? { ...p, [field]: value } : p
    ));

  return (
    <div className="max-w-2xl space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="text-gray-500 mt-1">Configure your paper folder and extraction parameters.</p>
      </div>

      {/* ── Paper folder ─────────────────────────────────────────────────── */}
      <div className="card p-6 space-y-4">
        <h2 className="font-semibold text-gray-800">Paper Folder</h2>
        <p className="text-sm text-gray-500">
          Enter the full Windows path to the folder containing your PDF files.
          The app will scan this folder recursively.
        </p>

        <div>
          <label className="label">Folder Path</label>
          <input
            className="input font-mono"
            value={folder}
            onChange={e => { setFolder(e.target.value); setFolderValidation(null); }}
            placeholder="C:\Users\YourName\Documents\Papers"
          />
          <p className="text-xs text-gray-400 mt-1">
            Windows paths with backslashes work directly — no conversion needed.
          </p>
        </div>

        {folderValidation && (
          <div className={`rounded-md p-3 text-sm ${
            folderValidation.valid
              ? 'bg-green-50 text-green-800 border border-green-200'
              : 'bg-red-50 text-red-800 border border-red-200'
          }`}>
            {folderValidation.valid
              ? `✓ Folder accessible — ${folderValidation.pdf_count} PDF(s) found`
              : `✗ ${folderValidation.reason}`}
          </div>
        )}

        <div className="flex gap-2">
          <button
            onClick={validateFolder}
            disabled={!folder.trim() || validating}
            className="btn-secondary text-sm"
          >
            <FolderSearch className="w-4 h-4" />
            {validating ? 'Checking…' : 'Validate Path'}
          </button>
          <button onClick={save} disabled={saving} className="btn-primary text-sm">
            <Save className="w-4 h-4" />
            {saving ? 'Saving…' : 'Save Settings'}
          </button>
        </div>

        {settings && (
          <div className="text-xs text-gray-500 space-y-0.5">
            <p>Current saved folder: <span className="font-mono">{settings.paper_folder || '(none)'}</span></p>
            <p>Status: <span className={
              settings.folder_status === 'ok' ? 'text-green-600' :
              settings.folder_status === 'not_found' ? 'text-red-600' : 'text-amber-600'
            }>{settings.folder_status}</span></p>
            {settings.folder_status === 'ok' && (
              <p>PDFs in folder: {settings.pdf_count}</p>
            )}
          </div>
        )}
      </div>

      {/* ── LLM info ─────────────────────────────────────────────────────── */}
      {llm && (
        <div className="card p-6 space-y-3">
          <div className="flex items-center gap-2">
            <h2 className="font-semibold text-gray-800">LLM Configuration</h2>
            <Info className="w-4 h-4 text-gray-400" />
          </div>
          <p className="text-sm text-gray-500">
            Change the provider/model in <code className="font-mono bg-gray-100 px-1 rounded">backend/.env</code>.
            The API key is never exposed to the browser.
          </p>
          <div className="bg-gray-50 rounded-lg p-3 text-sm font-mono space-y-1">
            <p><span className="text-gray-400">Provider:</span> {llm.provider}</p>
            <p><span className="text-gray-400">Model:</span>    {llm.model}</p>
            <p><span className="text-gray-400">Max tokens:</span> {llm.max_tokens}</p>
            <p><span className="text-gray-400">Temperature:</span> {llm.temperature}</p>
            <p><span className="text-gray-400">Timeout:</span>  {llm.timeout_seconds}s</p>
          </div>
        </div>
      )}

      {/* ── Custom parameters ─────────────────────────────────────────────── */}
      <div className="card p-6 space-y-4">
        <div>
          <h2 className="font-semibold text-gray-800">Custom Extraction Parameters</h2>
          <p className="text-sm text-gray-500 mt-1">
            Add research-specific parameters beyond the defaults. These are sent to the LLM
            for every paper. Role: <em>input</em> = controllable, <em>output</em> = measured.
          </p>
        </div>

        {customParams.length === 0 && (
          <p className="text-sm text-gray-400 italic">
            No custom parameters. The default 30+ superconductor parameters are always extracted.
          </p>
        )}

        <div className="space-y-3">
          {customParams.map((p, i) => (
            <div key={i} className="border border-gray-200 rounded-lg p-3 space-y-2">
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="label text-xs">Name (snake_case)</label>
                  <input className="input text-xs" value={p.name}
                    onChange={e => updateParam(i, 'name', e.target.value)}
                    placeholder="my_parameter" />
                </div>
                <div>
                  <label className="label text-xs">Label</label>
                  <input className="input text-xs" value={p.label}
                    onChange={e => updateParam(i, 'label', e.target.value)}
                    placeholder="My Parameter" />
                </div>
                <div>
                  <label className="label text-xs">Unit</label>
                  <input className="input text-xs" value={p.unit}
                    onChange={e => updateParam(i, 'unit', e.target.value)}
                    placeholder="K, nm, Pa…" />
                </div>
                <div>
                  <label className="label text-xs">Role</label>
                  <select className="input text-xs" value={p.role}
                    onChange={e => updateParam(i, 'role', e.target.value as any)}>
                    <option value="input">input (controllable)</option>
                    <option value="output">output (measured)</option>
                    <option value="material">material (descriptor)</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="label text-xs">Description (for LLM)</label>
                <input className="input text-xs" value={p.description}
                  onChange={e => updateParam(i, 'description', e.target.value)}
                  placeholder="Describe what to extract…" />
              </div>
              <button onClick={() => removeParam(i)}
                className="text-xs text-red-500 hover:text-red-700 flex items-center gap-1">
                <Trash2 className="w-3 h-3" /> Remove
              </button>
            </div>
          ))}
        </div>

        <div className="flex gap-2">
          <button onClick={addParam} className="btn-secondary text-sm">
            <Plus className="w-4 h-4" /> Add Parameter
          </button>
          {customParams.length > 0 && (
            <button onClick={save} disabled={saving} className="btn-primary text-sm">
              <Save className="w-4 h-4" /> {saving ? 'Saving…' : 'Save Parameters'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
