'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ChevronDown, ChevronRight, BookOpen, FlaskConical,
  Thermometer, BarChart3, Microscope, AlertCircle,
  CheckCircle, Edit3, Save, X, Info,
} from 'lucide-react';
import { cn, confidenceColor, EXTRACTION_STATUS_COLORS } from '@/lib/utils';
import { extractionsApi } from '@/lib/api';
import type { ExtractionRecord, ProcessCondition, ResultProperty } from '@/types';
import { ConfidenceBadge } from '@/components/ui/ConfidenceBadge';
import toast from 'react-hot-toast';

interface ExtractionPanelProps {
  paperId: string;
}

function Section({
  title,
  icon: Icon,
  defaultOpen = true,
  children,
}: {
  title: string;
  icon: React.ElementType;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-2 px-4 py-3 bg-gray-50 hover:bg-gray-100 transition-colors text-left"
      >
        <Icon className="w-4 h-4 text-gray-500" />
        <span className="font-medium text-sm text-gray-700">{title}</span>
        <span className="ml-auto">
          {open ? <ChevronDown className="w-4 h-4 text-gray-400" /> : <ChevronRight className="w-4 h-4 text-gray-400" />}
        </span>
      </button>
      {open && <div className="p-4">{children}</div>}
    </div>
  );
}

function PropertyRow({
  label,
  value,
  unit,
  confidence,
  isInferred,
  needsReview,
  sourceText,
}: {
  label: string;
  value: string | number | null | undefined;
  unit?: string | null;
  confidence?: number | null;
  isInferred?: boolean;
  needsReview?: boolean;
  sourceText?: string | null;
}) {
  const [showSource, setShowSource] = useState(false);

  if (value === null || value === undefined) return null;

  return (
    <div className={cn(
      'flex items-start py-2 border-b border-gray-100 last:border-0 gap-3',
      needsReview && 'bg-amber-50 rounded px-2'
    )}>
      <span className="text-xs text-gray-500 w-44 flex-shrink-0 pt-0.5">{label}</span>
      <div className="flex-1 min-w-0">
        <div className="flex items-baseline gap-1.5 flex-wrap">
          <span className="text-sm font-mono font-medium text-gray-800">
            {value}
          </span>
          {unit && <span className="text-xs text-gray-500">{unit}</span>}
          {needsReview && (
            <span className="badge bg-amber-100 text-amber-700 border-amber-200 text-[10px]">
              ⚠ Review
            </span>
          )}
          {isInferred && (
            <span className="text-[10px] text-gray-400 italic">inferred</span>
          )}
        </div>
        {confidence !== undefined && (
          <ConfidenceBadge confidence={confidence} isInferred={isInferred} className="mt-0.5" />
        )}
        {sourceText && (
          <div>
            <button
              onClick={() => setShowSource(!showSource)}
              className="text-[10px] text-brand-500 hover:text-brand-600 mt-0.5 flex items-center gap-0.5"
            >
              <Info className="w-3 h-3" />
              {showSource ? 'Hide source' : 'Show source'}
            </button>
            {showSource && (
              <blockquote className="mt-1 pl-2 border-l-2 border-gray-200 text-xs text-gray-500 italic">
                "{sourceText}"
              </blockquote>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export function ExtractionPanel({ paperId }: ExtractionPanelProps) {
  const queryClient = useQueryClient();
  const [editMode, setEditMode] = useState(false);
  const [editValues, setEditValues] = useState<Partial<ExtractionRecord>>({});

  const { data: extraction, isLoading, error } = useQuery({
    queryKey: ['extraction', paperId],
    queryFn: () => extractionsApi.get(paperId),
    retry: false,
  });

  const updateMutation = useMutation({
    mutationFn: (data: Partial<ExtractionRecord>) => extractionsApi.update(paperId, data),
    onSuccess: () => {
      toast.success('Extraction updated');
      setEditMode(false);
      queryClient.invalidateQueries({ queryKey: ['extraction', paperId] });
    },
    onError: () => toast.error('Failed to save changes'),
  });

  if (isLoading) return <div className="p-8 text-center text-gray-400 text-sm">Loading extraction…</div>;

  if (error || !extraction) {
    return (
      <div className="p-8 text-center">
        <AlertCircle className="w-8 h-8 text-gray-200 mx-auto mb-2" />
        <p className="text-sm text-gray-500">No extraction available yet.</p>
      </div>
    );
  }

  const handleSave = () => {
    updateMutation.mutate(editValues);
  };

  return (
    <div className="space-y-4">
      {/* Status bar */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className={cn('badge', EXTRACTION_STATUS_COLORS[extraction.status as keyof typeof EXTRACTION_STATUS_COLORS])}>
            {extraction.status}
          </span>
          {extraction.human_edited && (
            <span className="badge bg-blue-100 text-blue-700 border-blue-200">
              Human Edited
            </span>
          )}
          {extraction.relevant_for_optimization && (
            <span className="badge bg-emerald-100 text-emerald-700 border-emerald-200">
              BO Relevant ✓
            </span>
          )}
        </div>
        <div className="flex gap-2">
          {editMode ? (
            <>
              <button onClick={handleSave} className="btn-primary text-xs py-1.5 flex items-center gap-1">
                <Save className="w-3.5 h-3.5" /> Save
              </button>
              <button onClick={() => setEditMode(false)} className="btn-secondary text-xs py-1.5">
                Cancel
              </button>
            </>
          ) : (
            <button onClick={() => { setEditMode(true); setEditValues({}); }} className="btn-secondary text-xs py-1.5 flex items-center gap-1">
              <Edit3 className="w-3.5 h-3.5" /> Edit
            </button>
          )}
        </div>
      </div>

      {/* Summary */}
      {extraction.summary_text && (
        <div className="bg-blue-50 border border-blue-100 rounded-lg p-4">
          <p className="text-sm text-gray-700 leading-relaxed">{extraction.summary_text}</p>
        </div>
      )}

      {/* Materials */}
      {extraction.materials.length > 0 && (
        <Section title="Materials / Systems" icon={FlaskConical}>
          {extraction.materials.map((mat, i) => (
            <div key={mat.id} className="mb-4 last:mb-0">
              <h4 className="text-xs font-semibold text-gray-500 uppercase mb-2">
                Material {i + 1}: {mat.name || 'Unknown'}
              </h4>
              <PropertyRow label="Composition" value={mat.composition} />
              <PropertyRow label="Stoichiometry" value={mat.stoichiometry} />
              <PropertyRow label="Substrate" value={mat.substrate} />
              <PropertyRow label="Crystal structure" value={mat.crystal_structure} />
              <PropertyRow label="Device structure" value={mat.device_structure} />
              <PropertyRow label="Layer stack" value={mat.layer_stack} />
              <PropertyRow label="Dimensionality" value={mat.dimensionality} />
              <PropertyRow label="Morphology" value={mat.morphology} />
              {mat.dopants && mat.dopants.length > 0 && (
                <PropertyRow label="Dopants" value={mat.dopants.join(', ')} />
              )}
            </div>
          ))}
        </Section>
      )}

      {/* Process Conditions (Inputs) */}
      {extraction.process_conditions.length > 0 && (
        <Section title="Processing Conditions (Input Variables)" icon={Thermometer}>
          <div className="space-y-0">
            {extraction.process_conditions.map((cond) => (
              <PropertyRow
                key={cond.id}
                label={cond.parameter_name}
                value={cond.value_numeric ?? cond.value_text}
                unit={cond.unit}
                confidence={cond.confidence}
                isInferred={cond.is_inferred}
              />
            ))}
          </div>
        </Section>
      )}

      {/* Measurement Methods */}
      {extraction.measurement_methods.length > 0 && (
        <Section title="Characterization Methods" icon={Microscope}>
          <div className="flex flex-wrap gap-2">
            {extraction.measurement_methods.map((m) => (
              <span key={m.id} className="badge bg-gray-100 text-gray-700 border-gray-200">
                {m.technique_name}
                {m.category && <span className="text-gray-400 ml-1">· {m.category}</span>}
              </span>
            ))}
          </div>
        </Section>
      )}

      {/* Results (Outputs) */}
      {extraction.result_properties.length > 0 && (
        <Section title="Experimental Results (Output Variables)" icon={BarChart3}>
          {extraction.result_properties.map((rp) => (
            <PropertyRow
              key={rp.id}
              label={rp.property_name}
              value={
                rp.value_numeric !== null
                  ? rp.value_numeric
                  : rp.value_text
              }
              unit={rp.unit}
              confidence={rp.confidence}
              isInferred={rp.is_inferred}
              needsReview={rp.needs_review}
            />
          ))}
        </Section>
      )}

      {/* Outcomes */}
      <Section title="Key Findings & Outcomes" icon={BookOpen}>
        {editMode ? (
          <div className="space-y-3">
            {(['main_findings', 'claimed_mechanism', 'limitations', 'notable_novelty'] as const).map((field) => (
              <div key={field}>
                <label className="text-xs text-gray-500 font-medium mb-1 block capitalize">
                  {field.replace(/_/g, ' ')}
                </label>
                <textarea
                  className="input text-xs min-h-[60px]"
                  value={(editValues[field] as string) ?? (extraction[field] as string) ?? ''}
                  onChange={(e) => setEditValues((prev) => ({ ...prev, [field]: e.target.value }))}
                />
              </div>
            ))}
            <div>
              <label className="text-xs text-gray-500 font-medium mb-1 block">Review Notes</label>
              <textarea
                className="input text-xs min-h-[60px]"
                value={editValues.review_notes ?? extraction.review_notes ?? ''}
                onChange={(e) => setEditValues((prev) => ({ ...prev, review_notes: e.target.value }))}
              />
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            {extraction.main_findings && (
              <div>
                <h4 className="text-xs font-semibold text-gray-500 uppercase mb-1">Main Findings</h4>
                <p className="text-sm text-gray-700">{extraction.main_findings}</p>
              </div>
            )}
            {extraction.claimed_mechanism && (
              <div>
                <h4 className="text-xs font-semibold text-gray-500 uppercase mb-1">Claimed Mechanism</h4>
                <p className="text-sm text-gray-700">{extraction.claimed_mechanism}</p>
              </div>
            )}
            {extraction.limitations && (
              <div>
                <h4 className="text-xs font-semibold text-gray-500 uppercase mb-1">Limitations</h4>
                <p className="text-sm text-gray-700">{extraction.limitations}</p>
              </div>
            )}
            {extraction.notable_novelty && (
              <div>
                <h4 className="text-xs font-semibold text-gray-500 uppercase mb-1">Notable Novelty</h4>
                <p className="text-sm text-gray-700">{extraction.notable_novelty}</p>
              </div>
            )}
            {extraction.review_notes && (
              <div className="bg-amber-50 border border-amber-100 rounded p-3">
                <h4 className="text-xs font-semibold text-amber-700 mb-1">Review Notes</h4>
                <p className="text-xs text-amber-700">{extraction.review_notes}</p>
              </div>
            )}
          </div>
        )}
      </Section>
    </div>
  );
}
