import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchDocuments } from '../api/documents'
import { fetchProfile, upsertProfile } from '../api/sessions'
import { fetchEligibility, runEligibility, fetchChecklist, runChecklist } from '../api/documents'
import type { ChecklistItem, CompanyProfile, DocumentChecklist, EligibilityCheck, EligibilityDocRequired } from '../types'

interface Props {
  sessionId: string
}

export default function EligibilityPanel({ sessionId }: Props) {
  const [editingProfile, setEditingProfile] = useState(false)
  const qc = useQueryClient()

  const { data: docs = [] } = useQuery({
    queryKey: ['documents', sessionId],
    queryFn: () => fetchDocuments(sessionId),
  })

  const { data: profile, isLoading: profileLoading } = useQuery<CompanyProfile>({
    queryKey: ['profile', sessionId],
    queryFn: () => fetchProfile(sessionId),
    retry: false,
  })

  const readyDocs = docs.filter((d) => d.status === 'ready')

  if (profileLoading) {
    return (
      <div className="px-8 py-6 space-y-3 animate-pulse">
        <div className="h-20 bg-white border border-gray-100 rounded-xl" />
        <div className="h-32 bg-white border border-gray-100 rounded-xl" />
      </div>
    )
  }

  return (
    <div className="px-8 py-6 max-w-4xl space-y-6">
      {/* Profile section */}
      {!profile || editingProfile ? (
        <ProfileForm
          sessionId={sessionId}
          profile={profile}
          onSaved={() => {
            qc.invalidateQueries({ queryKey: ['profile', sessionId] })
            setEditingProfile(false)
          }}
          onCancel={profile ? () => setEditingProfile(false) : undefined}
        />
      ) : (
        <ProfileCard profile={profile} onEdit={() => setEditingProfile(true)} />
      )}

      {/* Document checks */}
      {profile && !editingProfile && (
        <div className="space-y-3">
          <div>
            <h2 className="text-sm font-semibold text-gray-700">Document Eligibility Checks</h2>
            <p className="text-xs text-gray-400 mt-0.5">
              Run a check on any ready document to assess bid eligibility
            </p>
          </div>
          {readyDocs.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-center select-none">
              <div className="text-4xl mb-3">&#128196;</div>
              <p className="text-sm text-gray-500">No ready documents in this session yet</p>
            </div>
          ) : (
            readyDocs.map((doc) => (
              <DocumentEligibilityCard key={doc.id} docId={doc.id} filename={doc.filename} />
            ))
          )}
        </div>
      )}
    </div>
  )
}

// ── Profile Card ─────────────────────────────────────────────────────────────

function ProfileCard({ profile, onEdit }: { profile: CompanyProfile; onEdit: () => void }) {
  const certs = profile.certifications || []
  return (
    <div className="bg-white border border-gray-200 rounded-xl px-5 py-4">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-semibold text-blue-600 uppercase tracking-wider">Company Profile</span>
          </div>
          <p className="text-base font-semibold text-gray-800">{profile.company_name || 'Unnamed Company'}</p>
          <div className="flex flex-wrap gap-x-4 gap-y-1 mt-2 text-xs text-gray-500">
            {profile.annual_turnover && <span>Turnover: <span className="text-gray-700 font-medium">{profile.annual_turnover}</span></span>}
            {profile.years_in_business != null && <span>Est. <span className="text-gray-700 font-medium">{profile.years_in_business} yrs</span></span>}
            {profile.similar_projects != null && <span>Projects: <span className="text-gray-700 font-medium">{profile.similar_projects}</span></span>}
            {profile.employee_count && <span>Employees: <span className="text-gray-700 font-medium">{profile.employee_count}</span></span>}
          </div>
          {certs.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2">
              {certs.map((c) => (
                <span key={c} className="text-[11px] bg-blue-50 text-blue-700 border border-blue-100 px-2 py-0.5 rounded-full">{c}</span>
              ))}
            </div>
          )}
          {profile.extra_details && (
            <p className="text-xs text-gray-400 mt-2 leading-relaxed line-clamp-2">{profile.extra_details}</p>
          )}
        </div>
        <button
          onClick={onEdit}
          className="shrink-0 text-xs text-gray-400 hover:text-gray-600 border border-gray-200 rounded-lg px-3 py-1.5 hover:bg-gray-50 transition"
        >
          Edit Profile
        </button>
      </div>
    </div>
  )
}

// ── Profile Form ──────────────────────────────────────────────────────────────

function ProfileForm({
  sessionId,
  profile,
  onSaved,
  onCancel,
}: {
  sessionId: string
  profile?: CompanyProfile
  onSaved: () => void
  onCancel?: () => void
}) {
  const [form, setForm] = useState({
    company_name: profile?.company_name ?? '',
    annual_turnover: profile?.annual_turnover ?? '',
    years_in_business: profile?.years_in_business != null ? String(profile.years_in_business) : '',
    certifications: (profile?.certifications ?? []).join(', '),
    similar_projects: profile?.similar_projects != null ? String(profile.similar_projects) : '',
    employee_count: profile?.employee_count ?? '',
    extra_details: profile?.extra_details ?? '',
  })

  const saveMut = useMutation({
    mutationFn: () => upsertProfile(sessionId, {
      company_name: form.company_name.trim(),
      annual_turnover: form.annual_turnover.trim(),
      years_in_business: form.years_in_business ? parseInt(form.years_in_business) : null,
      certifications: form.certifications.split(',').map((s) => s.trim()).filter(Boolean),
      similar_projects: form.similar_projects ? parseInt(form.similar_projects) : null,
      employee_count: form.employee_count.trim(),
      extra_details: form.extra_details.trim(),
    }),
    onSuccess: onSaved,
  })

  function field(label: string, key: keyof typeof form, opts?: { type?: string; placeholder?: string; hint?: string }) {
    return (
      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
        <input
          type={opts?.type ?? 'text'}
          value={form[key]}
          onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
          placeholder={opts?.placeholder}
          className="w-full text-sm bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100 transition"
        />
        {opts?.hint && <p className="text-[11px] text-gray-400 mt-0.5">{opts.hint}</p>}
      </div>
    )
  }

  return (
    <div className="bg-white border border-gray-200 rounded-xl px-6 py-5">
      <div className="mb-4">
        <h2 className="text-sm font-semibold text-gray-800">
          {profile ? 'Edit Company Profile' : 'Set Up Company Profile'}
        </h2>
        <p className="text-xs text-gray-400 mt-0.5">
          This profile is compared against each tender to assess bid eligibility
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="col-span-2">
          {field('Company Name *', 'company_name', { placeholder: 'Acme Infrastructure Ltd.' })}
        </div>
        {field('Annual Turnover', 'annual_turnover', { placeholder: '₹50 Crore / USD 5M' })}
        {field('Years in Business', 'years_in_business', { type: 'number', placeholder: '12' })}
        {field('Similar Projects Completed', 'similar_projects', { type: 'number', placeholder: '5' })}
        {field('Employee Count', 'employee_count', { placeholder: '200-500' })}
        <div className="col-span-2">
          {field('Certifications', 'certifications', {
            placeholder: 'ISO 9001, ISO 27001, CMMI Level 3',
            hint: 'Comma-separated list',
          })}
        </div>
        <div className="col-span-2">
          <label className="block text-xs font-medium text-gray-600 mb-1">Additional Details</label>
          <textarea
            value={form.extra_details}
            onChange={(e) => setForm((f) => ({ ...f, extra_details: e.target.value }))}
            placeholder="Any other relevant qualifications, domains, past clients, geographic presence..."
            rows={3}
            className="w-full text-sm bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100 transition resize-none"
          />
        </div>
      </div>

      <div className="flex items-center gap-2 mt-4">
        <button
          onClick={() => saveMut.mutate()}
          disabled={saveMut.isPending || !form.company_name.trim()}
          className="px-4 py-2 text-xs font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:opacity-50"
        >
          {saveMut.isPending ? 'Saving...' : 'Save Profile'}
        </button>
        {onCancel && (
          <button
            onClick={onCancel}
            className="px-4 py-2 text-xs font-medium text-gray-500 hover:text-gray-700 border border-gray-200 rounded-lg hover:bg-gray-50 transition"
          >
            Cancel
          </button>
        )}
        {saveMut.isError && (
          <span className="text-xs text-red-500">Failed to save</span>
        )}
      </div>
    </div>
  )
}

// ── Score badge ───────────────────────────────────────────────────────────────

function ScoreBadge({ score }: { score: number }) {
  const color = score >= 80
    ? { text: 'text-emerald-700', bg: 'bg-emerald-50', bar: 'bg-emerald-500', border: 'border-emerald-200', label: 'Eligible' }
    : score >= 50
    ? { text: 'text-yellow-700', bg: 'bg-yellow-50', bar: 'bg-yellow-500', border: 'border-yellow-200', label: 'Partial' }
    : { text: 'text-red-700', bg: 'bg-red-50', bar: 'bg-red-500', border: 'border-red-200', label: 'Ineligible' }

  return (
    <div className={'flex items-center gap-3 px-4 py-3 rounded-xl border ' + color.bg + ' ' + color.border}>
      <div className="text-center shrink-0">
        <span className={'text-3xl font-bold ' + color.text}>{score}</span>
        <span className={'text-sm ' + color.text}>%</span>
        <p className={'text-[10px] font-semibold uppercase tracking-wider mt-0.5 ' + color.text}>{color.label}</p>
      </div>
      <div className="flex-1 min-w-0">
        <div className="w-full bg-white rounded-full h-2 border border-gray-100">
          <div className={'h-2 rounded-full transition-all ' + color.bar} style={{ width: score + '%' }} />
        </div>
      </div>
    </div>
  )
}

// ── Document Eligibility Card ─────────────────────────────────────────────────

function DocumentEligibilityCard({ docId, filename }: { docId: string; filename: string }) {
  const [expanded, setExpanded] = useState(false)
  const qc = useQueryClient()

  const { data: check, isLoading, isError } = useQuery<EligibilityCheck>({
    queryKey: ['eligibility', docId],
    queryFn: () => fetchEligibility(docId),
    retry: false,
    staleTime: 10 * 60 * 1000,
  })

  const runMut = useMutation({
    mutationFn: () => runEligibility(docId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['eligibility', docId] })
      setExpanded(true)
    },
  })

  const noCheck = !isLoading && (isError || !check)

  return (
    <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-3 px-5 py-3.5">
        <p className="flex-1 text-sm font-medium text-gray-800 truncate min-w-0">{filename}</p>

        {isLoading && (
          <span className="text-xs text-gray-400 shrink-0">Loading...</span>
        )}

        {check && (
          <>
            <div className="shrink-0 text-center">
              <span className={
                'text-sm font-bold ' +
                (check.score >= 80 ? 'text-emerald-600' : check.score >= 50 ? 'text-yellow-600' : 'text-red-600')
              }>
                {check.score}%
              </span>
              <span className="text-[10px] text-gray-400 ml-1">eligible</span>
            </div>
            <button
              onClick={() => setExpanded((v) => !v)}
              className="shrink-0 text-xs text-gray-400 hover:text-gray-600 px-2 py-1 rounded hover:bg-gray-50 transition"
            >
              {expanded ? 'Collapse' : 'Details'}
            </button>
            <button
              onClick={() => runMut.mutate()}
              disabled={runMut.isPending}
              title="Re-run check"
              className="shrink-0 text-[10px] text-gray-300 hover:text-gray-500 transition px-1 disabled:opacity-50"
            >
              {runMut.isPending ? '...' : 'Re-check'}
            </button>
          </>
        )}

        {noCheck && (
          <button
            onClick={() => runMut.mutate()}
            disabled={runMut.isPending}
            className="shrink-0 text-xs px-3 py-1.5 bg-blue-50 text-blue-600 border border-blue-200 rounded-lg hover:bg-blue-100 transition disabled:opacity-50"
          >
            {runMut.isPending ? 'Checking...' : 'Run Check'}
          </button>
        )}

        {runMut.isError && (
          <span className="text-xs text-red-500 shrink-0">Failed</span>
        )}
      </div>

      {/* Expanded detail */}
      {expanded && check && (
        <div className="border-t border-gray-100 px-5 py-4 space-y-4">
          <ScoreBadge score={check.score} />

          <div className="grid grid-cols-2 gap-4">
            {/* Met criteria */}
            <div>
              <h4 className="text-[10px] font-semibold text-emerald-600 uppercase tracking-wider mb-2">
                &#10003; Criteria Met ({check.met.length})
              </h4>
              {check.met.length === 0 ? (
                <p className="text-xs text-gray-400">None identified</p>
              ) : (
                <ul className="space-y-1.5">
                  {check.met.map((m, i) => (
                    <li key={i} className="flex items-start gap-1.5 text-xs text-gray-700">
                      <span className="text-emerald-500 shrink-0 mt-0.5">&#10003;</span>
                      <span className="leading-relaxed">{m}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {/* Missing criteria */}
            <div>
              <h4 className="text-[10px] font-semibold text-red-500 uppercase tracking-wider mb-2">
                &#10007; Gaps / Missing ({check.missing.length})
              </h4>
              {check.missing.length === 0 ? (
                <p className="text-xs text-gray-400">No gaps identified</p>
              ) : (
                <ul className="space-y-1.5">
                  {check.missing.map((m, i) => (
                    <li key={i} className="flex items-start gap-1.5 text-xs text-gray-700">
                      <span className="text-red-400 shrink-0 mt-0.5">&#10007;</span>
                      <span className="leading-relaxed">{m}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          {/* Required documents */}
          {check.documents_required.length > 0 && (
            <div>
              <h4 className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-2">
                Required Documents
              </h4>
              <div className="flex flex-wrap gap-2">
                {check.documents_required.map((doc: EligibilityDocRequired, i: number) => (
                  <span
                    key={i}
                    className={
                      'flex items-center gap-1.5 text-[11px] px-2.5 py-1 rounded-full border ' +
                      (doc.status === 'available'
                        ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                        : 'bg-orange-50 text-orange-700 border-orange-200')
                    }
                  >
                    <span>{doc.status === 'available' ? '&#9745;' : '&#9744;'}</span>
                    {doc.name}
                  </span>
                ))}
              </div>
              <p className="text-[10px] text-gray-400 mt-1.5">
                &#9745; Available &nbsp;&#9744; Needs to be arranged
              </p>
            </div>
          )}

          {/* Recommendation */}
          {check.recommendation && (
            <div className="bg-blue-50 border border-blue-100 rounded-lg px-4 py-3">
              <h4 className="text-[10px] font-semibold text-blue-600 uppercase tracking-wider mb-1">Recommendation</h4>
              <p className="text-xs text-gray-700 leading-relaxed">{check.recommendation}</p>
            </div>
          )}

          {/* Bid Submission Checklist */}
          <ChecklistSection docId={docId} />
        </div>
      )}
    </div>
  )
}

// ── Bid Submission Checklist ──────────────────────────────────────────────────

const CAT_COLORS: Record<string, string> = {
  Technical: 'bg-purple-50 text-purple-700 border-purple-200',
  Financial: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  Legal: 'bg-red-50 text-red-700 border-red-200',
  Administrative: 'bg-blue-50 text-blue-700 border-blue-200',
}

const CATEGORIES = ['Technical', 'Financial', 'Legal', 'Administrative'] as const

function ChecklistSection({ docId }: { docId: string }) {
  const qc = useQueryClient()

  const { data: cl, isLoading, isError } = useQuery<DocumentChecklist>({
    queryKey: ['checklist', docId],
    queryFn: () => fetchChecklist(docId),
    retry: false,
    staleTime: 10 * 60 * 1000,
  })

  const genMut = useMutation({
    mutationFn: () => runChecklist(docId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['checklist', docId] }),
  })

  const noChecklist = !isLoading && (isError || !cl)

  const grouped = cl
    ? CATEGORIES.reduce<Record<string, ChecklistItem[]>>((acc, cat) => {
        acc[cat] = (cl.items || []).filter((i) => i.category === cat)
        return acc
      }, {} as Record<string, ChecklistItem[]>)
    : {}

  return (
    <div className="border-t border-gray-100 pt-4">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider">
          Bid Submission Checklist
        </h4>
        {cl && (
          <button
            onClick={() => genMut.mutate()}
            disabled={genMut.isPending}
            className="text-[10px] text-gray-400 hover:text-gray-600 transition disabled:opacity-50"
          >
            {genMut.isPending ? 'Regenerating...' : 'Regenerate'}
          </button>
        )}
      </div>

      {isLoading && <p className="text-xs text-gray-400">Loading...</p>}

      {noChecklist && (
        <div className="flex items-center gap-3">
          <p className="text-xs text-gray-400 flex-1">
            Generate a document checklist from this tender
          </p>
          <button
            onClick={() => genMut.mutate()}
            disabled={genMut.isPending}
            className="text-xs px-3 py-1.5 bg-purple-50 text-purple-700 border border-purple-200 rounded-lg hover:bg-purple-100 transition disabled:opacity-50"
          >
            {genMut.isPending ? 'Generating...' : 'Generate Checklist'}
          </button>
          {genMut.isError && <span className="text-xs text-red-500">Failed</span>}
        </div>
      )}

      {cl && cl.items.length === 0 && (
        <p className="text-xs text-gray-400">No checklist items extracted from this document.</p>
      )}

      {cl && cl.items.length > 0 && (
        <div className="space-y-3">
          {CATEGORIES.filter((cat) => grouped[cat]?.length > 0).map((cat) => (
            <div key={cat}>
              <p className={'inline-flex text-[10px] font-semibold uppercase tracking-wider border rounded-full px-2 py-0.5 mb-1.5 ' + CAT_COLORS[cat]}>
                {cat}
              </p>
              <ul className="space-y-1.5">
                {grouped[cat].map((item, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <span className={
                      'shrink-0 mt-0.5 text-[10px] font-medium border rounded px-1 ' +
                      (item.status === 'required' ? 'bg-orange-50 text-orange-700 border-orange-200' : 'bg-gray-50 text-gray-500 border-gray-200')
                    }>
                      {item.status === 'required' ? 'REQ' : 'OPT'}
                    </span>
                    <div className="min-w-0">
                      <p className="text-xs font-medium text-gray-800 leading-snug">{item.name}</p>
                      {item.notes && <p className="text-[11px] text-gray-400 leading-relaxed mt-0.5">{item.notes}</p>}
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
