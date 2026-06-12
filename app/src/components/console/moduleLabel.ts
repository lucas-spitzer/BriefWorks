import { moduleLabels, type Module } from '../../lib/consoleFormat'

export function moduleLabel(module: string): string {
  return moduleLabels[module as Module] ?? module
}
