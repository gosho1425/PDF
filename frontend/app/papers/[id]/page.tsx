'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { papersApi } from '@/lib/api';
import type { Paper, Extraction, FieldValue } from '@/types';
import { StatusBadge } from '@/components/ui/StatusBadge';
import toast from 'react-hot-toast';
import {
  ArrowLeft, FileText, RotateCcw, ChevronDown, ChevronUp,
  FlaskConical, TrendingUp, BookOpen
} from 'lucide-react';

export default function PaperDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [paper, setPaper] = useState<Paper | null>(null);
  const [summary, setSummary] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<'overview' | 'inputs' | 'outputs' | 'summary'>('overview');

  useEffect(() => {
    setLoading(true);
    papersApi.get(id)
      .then(p => {
        setPaper(p);
        if (p.has_extraction) {
          papersApi.summary(id).then(setSummary).catch(() => {});
        }
      })
      .catch(e => toast.error(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  const reprocess = async () => {
    if (!confirm('Re-extract this paper? This will call the LLM again.')) return;
    try {
      await papersApi.reprocess(id);
      toast.success('Re-processing started — refresh in a moment');
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  if (loading) return <div className="p-8 text-gray-400">Loading…</div>;
  if (!paper) return <div className="p-8 text-gray-500">Paper not found.</div>;

  const ext = paper.extraction as Extraction | null | undefined;

  return (
    <div className="max-w-4xl space-y-6">
      {/* Back + actions */}
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <button onClick={() => router.back()} className="btn-secondary text-sm">
          <ArrowLeft className="w-4 h-4" /> Back
        </button>
        <button onClick={reprocess} className="btn-secondary text-sm">
          <RotateCcw className="w-4 h-4" /> Re-extract
        </button>
      </div>

      {/* Header */}
      <div className="card p-6">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <h1 className="text-xl font-bold text-gray-900">
              {paper.title || paper.file_name}
            </h1>
            {paper.authors?.length > 0 && (
              <p className="text-sm text-gray-500 mt-1">
                {paper.authors.join(', ')}
              </p>
            )}
            <div className="flex items-center gap-3 mt-2 flex-wrap">
              {paper.journal && <span className="text-sm text-gray-600">{paper.journal}</span>}
              {paper.year && <span className="text-sm text-gray-500">({paper.year})</span>}
              {paper.doi && (
                <a href={`https://doi.org/${paper.doi}`} target="_blank"
                  className="text-xs text-blue-500 hover:underline font-mono">
                  DOI: {paper.doi}
                </a>
              )}
              {paper.impact_factor && (
                <span className="badge bg-purple-100 text-purple-700">
                  IF: {paper.impact_factor}
                </span>
              )}
            </div>
          </div>
          <StatusBadge status={paper.status} />
        </div>

        <div className="mt-3 pt-3 border-t border-gray-100 text-xs text-gray-400 flex gap-4 flex-wrap font-mono">
          <span>File: {paper.file_name}</span>
          {paper.file_size_bytes && (
            <span>Size: {(paper.file_size_bytes / 1024).toFixed(0)} KB</span>
          )}
        </div>

        {paper.status === 'failed' && paper.error_message && (
          <div className="mt-3 bg-red-50 border border-red-200 rounded-lg p-3">
            <p className="text-sm font-medium text-red-700">Extraction failed</p>
            <p className="text-xs font-mono text-red-600 mt-1">{paper.error_message}</p>
          </div>
        )}
      </div>

      {/* Tabs */}
      {ext && (
        <>
          <div className="flex gap-1 border-b border-gray-200">
            {(['overview', 'inputs', 'outputs', 'summary'] as const).map(t => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors capitalize ${
                  tab === t
                    ? 'border-blue-600 text-blue-700'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                {t === 'inputs' && <FlaskConical className="w-3.5 h-3.5 inline mr-1" />}
                {t === 'outputs' && <TrendingUp className="w-3.5 h-3.5 inline mr-1" />}
                {t === 'summary' && <FileText className="w-3.5 h-3.5 inline mr-1" />}
                {t === 'overview' && <BookOpen className="w-3.5 h-3.5 inline mr-1" />}
                {t}
              </button>
            ))}
          </div>

          {/* Overview */}
          {tab === 'overview' && (
            <div className="space-y-4">
              {ext.abstract && (
                <div className="card p-5">
                  <h3 className="font-semibold text-gray-800 mb-2">Abstract</h3>
                  <p className="text-sm text-gray-700 leading-relaxed">{ext.abstract}</p>
                </div>
              )}
              {Object.keys(ext.material_info).length > 0 && (
                <div className="card p-5">
                  <h3 className="font-semibold text-gray-800 mb-3">Material Information</h3>
                  <FieldTable fields={ext.material_info} />
                </div>
              )}
            </div>
          )}

          {/* Inputs */}
          {tab === 'inputs' && (
            <div className="card p-5">
              <h3 className="font-semibold text-gray-800 mb-1">Input Variables</h3>
              <p className="text-xs text-gray-400 mb-3">
                Controllable experimental parameters — these become X inputs for Bayesian optimization.
              </p>
              <FieldTable fields={ext.input_variables} showEvidence />
            </div>
          )}

          {/* Outputs */}
          {tab === 'outputs' && (
            <div className="card p-5">
              <h3 className="font-semibold text-gray-800 mb-1">Output Variables</h3>
              <p className="text-xs text-gray-400 mb-3">
                Measured results — these become y targets for Bayesian optimization.
              </p>
              <FieldTable fields={ext.output_variables} showEvidence />
            </div>
          )}

          {/* Summary */}
          {tab === 'summary' && (
            <div className="card p-5">
              <h3 className="font-semibold text-gray-800 mb-3">AI Summary</h3>
              {summary ? (
                <pre className="text-sm text-gray-700 font-mono whitespace-pre-wrap leading-relaxed bg-gray-50 rounded-lg p-4 overflow-x-auto">
                  {summary}
                </pre>
              ) : (
                <p className="text-sm text-gray-400">
                  {ext.raw_summary || '(no summary)'}
                </p>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}

function FieldTable({ fields, showEvidence = false }: {
  fields: Record<string, FieldValue>;
  showEvidence?: boolean;
}) {
  const [openEvidence, setOpenEvidence] = useState<string | null>(null);
  const entries = Object.entries(fields).filter(([, fv]) => fv.value != null);

  if (!entries.length) {
    return <p className="text-sm text-gray-400 italic">No values extracted.</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-100">
            <th className="text-left py-2 pr-4 font-medium text-gray-500 w-48">Parameter</th>
            <th className="text-left py-2 pr-4 font-medium text-gray-500">Value</th>
            <th className="text-left py-2 font-medium text-gray-500">Confidence</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-50">
          {entries.map(([key, fv]) => (
            <>
              <tr key={key} className="hover:bg-gray-50">
                <td className="py-2 pr-4 font-mono text-xs text-gray-600">{key}</td>
                <td className="py-2 pr-4">
                  <span className="font-medium text-gray-900">{String(fv.value)}</span>
                  {fv.unit && <span className="text-gray-400 ml-1">{fv.unit}</span>}
                </td>
                <td className="py-2">
                  <div className="flex items-center gap-2">
                    <div className="w-16 bg-gray-200 rounded-full h-1.5">
                      <div
                        className="h-1.5 rounded-full bg-blue-500"
                        style={{ width: `${fv.confidence * 100}%` }}
                      />
                    </div>
                    <span className="text-xs text-gray-400">
                      {Math.round(fv.confidence * 100)}%
                    </span>
                    {showEvidence && fv.evidence && (
                      <button
                        onClick={() => setOpenEvidence(openEvidence === key ? null : key)}
                        className="text-xs text-blue-500 hover:underline ml-1 flex items-center gap-0.5"
                      >
                        evidence
                        {openEvidence === key
                          ? <ChevronUp className="w-3 h-3" />
                          : <ChevronDown className="w-3 h-3" />}
                      </button>
                    )}
                  </div>
                </td>
              </tr>
              {showEvidence && openEvidence === key && fv.evidence && (
                <tr key={`${key}-ev`}>
                  <td colSpan={3} className="pb-2 pl-2">
                    <div className="bg-amber-50 border border-amber-200 rounded p-2 text-xs text-amber-900 italic">
                      {fv.page && <span className="font-medium not-italic mr-1">[p.{fv.page}]</span>}
                      "{fv.evidence}"
                    </div>
                  </td>
                </tr>
              )}
            </>
          ))}
        </tbody>
      </table>
    </div>
  );
}
