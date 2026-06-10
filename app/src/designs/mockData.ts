// Shared mock data for the BriefWorks design exploration gallery.
// Mirrors the real domain model: production (pipeline) runs contain skill runs,
// skill runs produce artifacts + extracted concepts, and sources feed the pipeline.

export type RunStatus = 'queued' | 'running' | 'completed' | 'failed' | 'cancelled'
export type Module = 'intellex' | 'mathesys' | 'qngen'
export type SourceStatus = 'stored' | 'processing' | 'ready' | 'failed'
export type ArtifactKind = 'eleven_reader_script' | 'lesson' | 'assessment' | 'concept_map'

export interface Concept {
  term: string
  definition: string
  importance: 'core' | 'supporting' | 'reference'
  citations: number
}

export interface Artifact {
  id: string
  title: string
  kind: ArtifactKind
  module: Module
  format: string
  sizeLabel: string
  createdAt: string
  status: RunStatus
  summary: string
  sourceTitle: string
}

export interface SkillRun {
  id: string
  skillName: string
  skillId: string
  version: string
  module: Module
  status: RunStatus
  model: string
  durationSec: number
  tokensIn: number
  tokensOut: number
  startedAt: string
  outputSummary: string
  artifactIds: string[]
  conceptCount: number
}

export interface PipelineRun {
  id: string
  label: string
  status: RunStatus
  targetArtifacts: ArtifactKind[]
  sourceTitles: string[]
  createdAt: string
  completedAt: string | null
  durationSec: number
  progress: number
  skillRuns: SkillRun[]
  error: string | null
}

export interface Source {
  id: string
  filename: string
  title: string
  documentType: string
  issuingAuthority: string
  mimeLabel: string
  sizeLabel: string
  pages: number
  status: SourceStatus
  confidence: number
  uploadedAt: string
  segments: number
  tags: string[]
}

export const WORKSPACE_NAME = 'USMC Doctrine Lab'

export const concepts: Concept[] = [
  {
    term: 'Commander’s Intent',
    definition:
      'A concise expression of the purpose of an operation and the desired end state that guides subordinate initiative.',
    importance: 'core',
    citations: 14,
  },
  {
    term: 'Center of Gravity',
    definition:
      'The source of power that provides moral or physical strength, freedom of action, or will to act.',
    importance: 'core',
    citations: 11,
  },
  {
    term: 'Maneuver Warfare',
    definition:
      'A warfighting philosophy that seeks to shatter the enemy’s cohesion through unexpected and rapid actions.',
    importance: 'core',
    citations: 9,
  },
  {
    term: 'Decisive Point',
    definition:
      'A geographic place, key event, or system that allows a commander to gain a marked advantage.',
    importance: 'supporting',
    citations: 6,
  },
  {
    term: 'Tempo',
    definition: 'The relative speed and rhythm of military operations over time, relative to the enemy.',
    importance: 'supporting',
    citations: 5,
  },
  {
    term: 'Mission Tactics',
    definition: 'Assigning a subordinate a mission without specifying how the mission must be accomplished.',
    importance: 'supporting',
    citations: 4,
  },
  {
    term: 'Friction',
    definition: 'The accumulation of chance, uncertainty, and disorder that impedes military action.',
    importance: 'reference',
    citations: 3,
  },
  {
    term: 'Boyd Cycle (OODA)',
    definition: 'The decision cycle of observe, orient, decide, and act used to outpace an adversary.',
    importance: 'reference',
    citations: 7,
  },
]

export const artifacts: Artifact[] = [
  {
    id: 'art-001',
    title: 'Warfighting',
    kind: 'eleven_reader_script',
    module: 'mathesys',
    format: 'EPUB',
    sizeLabel: '482 KB',
    createdAt: '2026-06-05T14:22:00Z',
    status: 'completed',
    summary: 'Narrated EPUB script covering maneuver warfare philosophy with canonical terminology.',
    sourceTitle: 'MCDP 1',
  },
  {
    id: 'art-002',
    title: 'Maneuver Warfare',
    kind: 'concept_map',
    module: 'intellex',
    format: 'SVG',
    sizeLabel: '96 KB',
    createdAt: '2026-06-05T13:48:00Z',
    status: 'completed',
    summary: 'Relationship graph linking 22 essential terms across the doctrine publication.',
    sourceTitle: 'MCDP 1',
  },
  {
    id: 'art-003',
    title: 'Command & Control',
    kind: 'lesson',
    module: 'mathesys',
    format: 'PDF',
    sizeLabel: '1.2 MB',
    createdAt: '2026-06-04T19:10:00Z',
    status: 'completed',
    summary: 'Structured lesson with objectives, narrative, and high-contrast diagrams.',
    sourceTitle: 'MCDP 6',
  },
  {
    id: 'art-004',
    title: 'Warfighting',
    kind: 'assessment',
    module: 'qngen',
    format: 'JSON',
    sizeLabel: '54 KB',
    createdAt: '2026-06-04T18:02:00Z',
    status: 'completed',
    summary: '40 checks-for-understanding mapped to extracted concepts and source segments.',
    sourceTitle: 'MCDP 1',
  },
  {
    id: 'art-005',
    title: 'Tactics',
    kind: 'eleven_reader_script',
    module: 'mathesys',
    format: 'EPUB',
    sizeLabel: '610 KB',
    createdAt: '2026-06-06T09:31:00Z',
    status: 'running',
    summary: 'Generation in progress — assembling chapters from approved wiki entries.',
    sourceTitle: 'MCDP 1-3',
  },
  {
    id: 'art-006',
    title: 'Leadership',
    kind: 'concept_map',
    module: 'intellex',
    format: 'SVG',
    sizeLabel: '88 KB',
    createdAt: '2026-06-03T11:15:00Z',
    status: 'completed',
    summary: 'Graph of leadership principles and supporting traits with citation counts.',
    sourceTitle: 'MCWP 6-10',
  },
]

function skillRun(partial: SkillRun): SkillRun {
  return partial
}

export const pipelineRuns: PipelineRun[] = [
  {
    id: 'run-2041',
    label: 'Warfighting → Listenable Brief',
    status: 'completed',
    targetArtifacts: ['eleven_reader_script'],
    sourceTitles: ['MCDP 1'],
    createdAt: '2026-06-05T13:40:00Z',
    completedAt: '2026-06-05T14:22:00Z',
    durationSec: 2520,
    progress: 100,
    error: null,
    skillRuns: [
      skillRun({
        id: 'sr-9001',
        skillName: 'Source Research',
        skillId: 'source-research',
        version: '1.0.0',
        module: 'intellex',
        status: 'completed',
        model: 'gpt-5.5',
        durationSec: 184,
        tokensIn: 18400,
        tokensOut: 2100,
        startedAt: '2026-06-05T13:40:00Z',
        outputSummary: 'Corroborated title, issuing authority, and publication date with web gap-fill.',
        artifactIds: [],
        conceptCount: 0,
      }),
      skillRun({
        id: 'sr-9002',
        skillName: 'Document Deconstructor',
        skillId: 'document-deconstructor',
        version: '1.0.0',
        module: 'intellex',
        status: 'completed',
        model: 'gpt-5.5',
        durationSec: 642,
        tokensIn: 96200,
        tokensOut: 8800,
        startedAt: '2026-06-05T13:44:00Z',
        outputSummary: 'Extracted 22 essential concepts and supporting terminology.',
        artifactIds: ['art-002'],
        conceptCount: 22,
      }),
      skillRun({
        id: 'sr-9003',
        skillName: 'ElevenReader Script',
        skillId: 'eleven-reader-script',
        version: '1.0.0',
        module: 'mathesys',
        status: 'completed',
        model: 'gpt-5.5',
        durationSec: 1694,
        tokensIn: 142000,
        tokensOut: 51200,
        startedAt: '2026-06-05T13:56:00Z',
        outputSummary: 'Produced a Wiki-aware EPUB manifest with 9 narrated chapters.',
        artifactIds: ['art-001'],
        conceptCount: 0,
      }),
    ],
  },
  {
    id: 'run-2048',
    label: 'Tactics → Listenable Brief',
    status: 'running',
    targetArtifacts: ['eleven_reader_script'],
    sourceTitles: ['MCDP 1-3'],
    createdAt: '2026-06-06T09:05:00Z',
    completedAt: null,
    durationSec: 1560,
    progress: 64,
    error: null,
    skillRuns: [
      skillRun({
        id: 'sr-9101',
        skillName: 'Source Research',
        skillId: 'source-research',
        version: '1.0.0',
        module: 'intellex',
        status: 'completed',
        model: 'gpt-5.5',
        durationSec: 171,
        tokensIn: 16800,
        tokensOut: 1900,
        startedAt: '2026-06-06T09:05:00Z',
        outputSummary: 'Metadata extracted and verified against public catalog.',
        artifactIds: [],
        conceptCount: 0,
      }),
      skillRun({
        id: 'sr-9102',
        skillName: 'Document Deconstructor',
        skillId: 'document-deconstructor',
        version: '1.0.0',
        module: 'intellex',
        status: 'completed',
        model: 'gpt-5.5',
        durationSec: 588,
        tokensIn: 88400,
        tokensOut: 7600,
        startedAt: '2026-06-06T09:09:00Z',
        outputSummary: 'Extracted 18 essential concepts.',
        artifactIds: [],
        conceptCount: 18,
      }),
      skillRun({
        id: 'sr-9103',
        skillName: 'ElevenReader Script',
        skillId: 'eleven-reader-script',
        version: '1.0.0',
        module: 'mathesys',
        status: 'running',
        model: 'gpt-5.5',
        durationSec: 801,
        tokensIn: 61200,
        tokensOut: 22400,
        startedAt: '2026-06-06T09:20:00Z',
        outputSummary: 'Assembling narrated chapters — 6 of 11 complete.',
        artifactIds: ['art-005'],
        conceptCount: 0,
      }),
    ],
  },
  {
    id: 'run-2039',
    label: 'Command & Control → Lesson',
    status: 'completed',
    targetArtifacts: ['lesson'],
    sourceTitles: ['MCDP 6'],
    createdAt: '2026-06-04T18:30:00Z',
    completedAt: '2026-06-04T19:10:00Z',
    durationSec: 2400,
    progress: 100,
    error: null,
    skillRuns: [
      skillRun({
        id: 'sr-8801',
        skillName: 'Document Deconstructor',
        skillId: 'document-deconstructor',
        version: '1.0.0',
        module: 'intellex',
        status: 'completed',
        model: 'gpt-5.5',
        durationSec: 540,
        tokensIn: 79200,
        tokensOut: 6900,
        startedAt: '2026-06-04T18:30:00Z',
        outputSummary: 'Extracted 16 concepts for command and control.',
        artifactIds: [],
        conceptCount: 16,
      }),
      skillRun({
        id: 'sr-8802',
        skillName: 'Lesson Builder',
        skillId: 'lesson-builder',
        version: '1.0.0',
        module: 'mathesys',
        status: 'completed',
        model: 'gpt-5.5',
        durationSec: 1860,
        tokensIn: 121000,
        tokensOut: 44800,
        startedAt: '2026-06-04T18:40:00Z',
        outputSummary: 'Generated lesson module with objectives and diagrams.',
        artifactIds: ['art-003'],
        conceptCount: 0,
      }),
    ],
  },
  {
    id: 'run-2031',
    label: 'Warfighting → Assessment Bank',
    status: 'completed',
    targetArtifacts: ['assessment'],
    sourceTitles: ['MCDP 1'],
    createdAt: '2026-06-04T17:20:00Z',
    completedAt: '2026-06-04T18:02:00Z',
    durationSec: 2520,
    progress: 100,
    error: null,
    skillRuns: [
      skillRun({
        id: 'sr-8701',
        skillName: 'Question Generator',
        skillId: 'question-generator',
        version: '1.0.0',
        module: 'qngen',
        status: 'completed',
        model: 'gpt-5.5',
        durationSec: 2280,
        tokensIn: 102400,
        tokensOut: 38600,
        startedAt: '2026-06-04T17:20:00Z',
        outputSummary: 'Produced 40 checks-for-understanding mapped to concepts.',
        artifactIds: ['art-004'],
        conceptCount: 0,
      }),
    ],
  },
  {
    id: 'run-2025',
    label: 'Leadership → Concept Map',
    status: 'failed',
    targetArtifacts: ['concept_map'],
    sourceTitles: ['MCWP 6-10'],
    createdAt: '2026-06-03T10:50:00Z',
    completedAt: '2026-06-03T11:15:00Z',
    durationSec: 1500,
    progress: 48,
    error: 'Deconstructor exceeded context window on chapter 4; retry with chunked segments.',
    skillRuns: [
      skillRun({
        id: 'sr-8601',
        skillName: 'Source Research',
        skillId: 'source-research',
        version: '1.0.0',
        module: 'intellex',
        status: 'completed',
        model: 'gpt-5.5',
        durationSec: 162,
        tokensIn: 15200,
        tokensOut: 1700,
        startedAt: '2026-06-03T10:50:00Z',
        outputSummary: 'Metadata extracted successfully.',
        artifactIds: [],
        conceptCount: 0,
      }),
      skillRun({
        id: 'sr-8602',
        skillName: 'Document Deconstructor',
        skillId: 'document-deconstructor',
        version: '1.0.0',
        module: 'intellex',
        status: 'failed',
        model: 'gpt-5.5',
        durationSec: 318,
        tokensIn: 132000,
        tokensOut: 0,
        startedAt: '2026-06-03T10:54:00Z',
        outputSummary: 'Context window exceeded on chapter 4.',
        artifactIds: [],
        conceptCount: 0,
      }),
    ],
  },
]

export const sources: Source[] = [
  {
    id: 'src-101',
    filename: 'mcdp-1-warfighting.pdf',
    title: 'MCDP 1',
    documentType: 'Doctrinal Publication',
    issuingAuthority: 'U.S. Marine Corps',
    mimeLabel: 'PDF',
    sizeLabel: '3.4 MB',
    pages: 113,
    status: 'ready',
    confidence: 0.97,
    uploadedAt: '2026-06-02T08:14:00Z',
    segments: 642,
    tags: ['doctrine', 'philosophy', 'maneuver'],
  },
  {
    id: 'src-102',
    filename: 'mcdp-6-command-control.pdf',
    title: 'MCDP 6',
    documentType: 'Doctrinal Publication',
    issuingAuthority: 'U.S. Marine Corps',
    mimeLabel: 'PDF',
    sizeLabel: '4.1 MB',
    pages: 138,
    status: 'ready',
    confidence: 0.95,
    uploadedAt: '2026-06-02T08:21:00Z',
    segments: 781,
    tags: ['doctrine', 'c2', 'decision-making'],
  },
  {
    id: 'src-103',
    filename: 'mcdp-1-3-tactics.pdf',
    title: 'MCDP 1-3',
    documentType: 'Doctrinal Publication',
    issuingAuthority: 'U.S. Marine Corps',
    mimeLabel: 'PDF',
    sizeLabel: '5.2 MB',
    pages: 152,
    status: 'processing',
    confidence: 0.88,
    uploadedAt: '2026-06-06T08:58:00Z',
    segments: 410,
    tags: ['doctrine', 'tactics'],
  },
  {
    id: 'src-104',
    filename: 'mcwp-6-10-leading-marines.pdf',
    title: 'MCWP 6-10',
    documentType: 'Warfighting Publication',
    issuingAuthority: 'U.S. Marine Corps',
    mimeLabel: 'PDF',
    sizeLabel: '2.8 MB',
    pages: 96,
    status: 'failed',
    confidence: 0.72,
    uploadedAt: '2026-06-03T10:42:00Z',
    segments: 0,
    tags: ['leadership', 'ethos'],
  },
  {
    id: 'src-105',
    filename: 'fmfm-1-1-campaigning.pdf',
    title: 'FMFM 1-1',
    documentType: 'Fleet Manual',
    issuingAuthority: 'U.S. Marine Corps',
    mimeLabel: 'PDF',
    sizeLabel: '2.1 MB',
    pages: 84,
    status: 'ready',
    confidence: 0.91,
    uploadedAt: '2026-06-01T15:30:00Z',
    segments: 503,
    tags: ['campaign', 'operational-art'],
  },
  {
    id: 'src-106',
    filename: 'boyd-patterns-of-conflict.docx',
    title: 'Patterns of Conflict (Boyd)',
    documentType: 'Briefing Transcript',
    issuingAuthority: 'John Boyd',
    mimeLabel: 'DOCX',
    sizeLabel: '740 KB',
    pages: 58,
    status: 'ready',
    confidence: 0.83,
    uploadedAt: '2026-05-30T12:05:00Z',
    segments: 322,
    tags: ['ooda', 'theory', 'history'],
  },
]

export interface Metric {
  label: string
  value: string
  delta: string
  trend: 'up' | 'down' | 'flat'
}

export const metrics: Metric[] = [
  { label: 'Pipeline runs (7d)', value: '24', delta: '+18%', trend: 'up' },
  { label: 'Artifacts produced', value: '63', delta: '+9', trend: 'up' },
  { label: 'Success rate', value: '92%', delta: '+3%', trend: 'up' },
  { label: 'Avg run time', value: '41m', delta: '-6m', trend: 'down' },
  { label: 'Concepts extracted', value: '418', delta: '+72', trend: 'up' },
  { label: 'Tokens used (7d)', value: '4.6M', delta: '+0.4M', trend: 'up' },
]

export const moduleLabels: Record<Module, string> = {
  intellex: 'Intellex',
  mathesys: 'Mathesys',
  qngen: 'QnGen',
}

export const artifactKindLabels: Record<ArtifactKind, string> = {
  eleven_reader_script: 'Listenable Brief',
  lesson: 'Lesson Module',
  assessment: 'Assessment Bank',
  concept_map: 'Concept Map',
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

export function formatDuration(sec: number): string {
  if (sec < 60) return `${sec}s`
  const minutes = Math.floor(sec / 60)
  const seconds = sec % 60
  if (minutes < 60) return seconds ? `${minutes}m ${seconds}s` : `${minutes}m`
  const hours = Math.floor(minutes / 60)
  return `${hours}h ${minutes % 60}m`
}

export function statusLabel(status: RunStatus | SourceStatus): string {
  return status.charAt(0).toUpperCase() + status.slice(1)
}
