export type Module = 'intellex' | 'mathesys' | 'qngen'

export const moduleLabels: Record<Module, string> = {
  intellex: 'Intellex',
  mathesys: 'Mathesys',
  qngen: 'QnGen',
}

export const documentTypeLabels: Record<string, string> = {
  military_doctrine: 'Doctrinal Publication',
  research_paper: 'Research Paper',
  white_paper: 'White Paper',
  report: 'Report',
  unknown: 'Unknown',
}

export function documentTypeLabel(type: string): string {
  return (
    documentTypeLabels[type] ??
    type
      .split('_')
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(' ')
  )
}

export const artifactKindLabels: Record<string, string> = {
  eleven_reader_script: 'ElevenReader EPUB',
  speechify_script: 'Speechify EPUB',
  speechify_audio: 'Speechify SSML',
  elevenlabs_audio: 'ElevenLabs Audio',
  lesson: 'Lesson Module',
  assessment: 'Assessment Bank',
  concept_map: 'Concept Map',
  flashcards: 'Flashcards',
  quizzes: 'Quizzes',
  scenarios: 'Scenarios',
}

export function artifactKindLabel(kind: string): string {
  return artifactKindLabels[kind] ?? kind.replace(/_/g, ' ')
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

export function statusLabel(status: string): string {
  return status.charAt(0).toUpperCase() + status.slice(1)
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function mimeLabel(mimeType: string): string {
  const parts = mimeType.split('/')
  const subtype = parts[parts.length - 1] ?? mimeType
  return subtype.toUpperCase()
}
