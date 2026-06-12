export type ConsolePage = 'ops' | 'sources' | 'skills' | 'artifacts' | 'assessments' | 'workspace'

export type ConsoleView = 'grid' | 'list'

export const railItems: { id: ConsolePage; label: string; icon: string }[] = [
  { id: 'ops', label: 'OPS', icon: '▥' },
  { id: 'sources', label: 'SRC', icon: '▤' },
  { id: 'skills', label: 'SKL', icon: '✦' },
  { id: 'artifacts', label: 'ART', icon: '◆' },
  { id: 'assessments', label: 'ASM', icon: '◎' },
  { id: 'workspace', label: 'WRK', icon: '◇' },
]
