import { moduleLabels, type Module } from '../../lib/foundryFormat'
import type { PipelineStep } from '../../lib/workspaceApi'

export function moduleLabel(module: string): string {
  return moduleLabels[module as Module] ?? module
}

export function pipelineStepModuleLabel(step: PipelineStep): string {
  return step.module ? moduleLabel(step.module) : ''
}
