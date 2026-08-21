import { SlidersHorizontal } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { useWorkspace } from '../../features/workspace/workspaceContext'
import {
  deleteStageSetting,
  getModelCatalog,
  getStageSettings,
  getTtsCatalog,
  putStageSetting,
  type CatalogModel,
  type StageSetting,
  type TtsCatalogModel,
} from '../../lib/workspaceApi'
import { ErrorBanner } from './ErrorBanner'

const AUDIO_NARRATION_ACTION = 'audio_narration'

function formatPrice(input: number | null, output: number | null): string {
  if (input == null || output == null) {
    return 'Price n/a'
  }
  return `$${input.toFixed(2)} in · $${output.toFixed(2)} out / Mtok`
}

function formatTtsPrice(pricePerMillion: number | null | undefined): string {
  if (pricePerMillion == null) {
    return 'Price n/a'
  }
  return `$${pricePerMillion.toFixed(2)} / Mchar`
}

const EFFORT_OPTIONS = ['low', 'medium', 'high'] as const
const BUDGET_OPTIONS = [2048, 4096, 8192] as const
const DEFAULT_EFFORT = 'medium'
const DEFAULT_BUDGET = 2048

// Which reasoning control fits a model: budget-mode models (Anthropic Haiku/4.5)
// take a token cap; everything else reasoning-capable takes an effort dial.
function reasoningKind(entry: CatalogModel | undefined): 'effort' | 'budget' | 'none' {
  if (!entry || !entry.supports_reasoning) {
    return 'none'
  }
  if (entry.reasoning_modes.includes('budget')) {
    return 'budget'
  }
  return 'effort'
}

function CapabilityMeter({ tier }: { tier: number }) {
  return (
    <span className="as-console__cap" aria-label={`Capability tier ${tier} of 5`}>
      {[1, 2, 3, 4, 5].map((step) => (
        <span
          key={step}
          className={`as-console__cap-seg${step <= tier ? ' is-on' : ''}`}
          aria-hidden="true"
        />
      ))}
    </span>
  )
}

export function FoundryStageSettings() {
  const { activeWorkspace } = useWorkspace()
  const workspaceId = activeWorkspace?.id ?? null

  const [catalog, setCatalog] = useState<CatalogModel[]>([])
  const [ttsCatalog, setTtsCatalog] = useState<TtsCatalogModel[]>([])
  const [settings, setSettings] = useState<StageSetting[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [savingAction, setSavingAction] = useState<string | null>(null)

  const catalogByModel = useMemo(() => {
    const map = new Map<string, CatalogModel>()
    for (const entry of catalog) {
      map.set(entry.model, entry)
    }
    return map
  }, [catalog])

  const groupedCatalog = useMemo(() => {
    const groups = new Map<string, CatalogModel[]>()
    for (const entry of catalog) {
      const bucket = groups.get(entry.provider) ?? []
      bucket.push(entry)
      groups.set(entry.provider, bucket)
    }
    return [...groups.entries()]
  }, [catalog])

  const groupedTtsCatalog = useMemo(() => {
    const groups = new Map<string, TtsCatalogModel[]>()
    for (const entry of ttsCatalog) {
      const bucket = groups.get(entry.provider) ?? []
      bucket.push(entry)
      groups.set(entry.provider, bucket)
    }
    return [...groups.entries()]
  }, [ttsCatalog])

  const ttsByModel = useMemo(() => {
    const map = new Map<string, TtsCatalogModel>()
    for (const entry of ttsCatalog) {
      map.set(entry.model, entry)
    }
    return map
  }, [ttsCatalog])

  const load = useCallback(async () => {
    if (!workspaceId) {
      setCatalog([])
      setTtsCatalog([])
      setSettings([])
      setError(null)
      return
    }
    setIsLoading(true)
    setError(null)
    try {
      const [nextCatalog, nextTtsCatalog, nextSettings] = await Promise.all([
        getModelCatalog(),
        getTtsCatalog(),
        getStageSettings(workspaceId),
      ])
      setCatalog(nextCatalog)
      setTtsCatalog(nextTtsCatalog)
      setSettings(nextSettings)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Failed to load stage settings.')
    } finally {
      setIsLoading(false)
    }
  }, [workspaceId])

  useEffect(() => {
    void load()
  }, [load])

  const handleSelect = useCallback(
    async (setting: StageSetting, model: string) => {
      if (!workspaceId || model === setting.model) {
        return
      }
      const isNarration = setting.stage_action === AUDIO_NARRATION_ACTION
      const ttsEntry = isNarration ? ttsByModel.get(model) : undefined
      const llmEntry = isNarration ? undefined : catalogByModel.get(model)
      const entry = ttsEntry ?? llmEntry
      if (!entry) {
        return
      }
      setSavingAction(setting.stage_action)
      setError(null)
      try {
        const voiceId = ttsEntry ? ttsEntry.default_voice_id : undefined
        const updated = await putStageSetting(workspaceId, setting.stage_action, {
          provider: entry.provider,
          model: entry.model,
          voice_id: voiceId,
        })
        setSettings((current) =>
          current.map((item) =>
            item.stage_action === updated.stage_action ? updated : item,
          ),
        )
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : 'Failed to update stage.')
      } finally {
        setSavingAction(null)
      }
    },
    [workspaceId, catalogByModel, ttsByModel],
  )

  const handleReset = useCallback(
    async (setting: StageSetting) => {
      if (!workspaceId) {
        return
      }
      setSavingAction(setting.stage_action)
      setError(null)
      try {
        await deleteStageSetting(workspaceId, setting.stage_action)
        await load()
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : 'Failed to reset stage.')
      } finally {
        setSavingAction(null)
      }
    },
    [workspaceId, load],
  )

  const handleVoice = useCallback(
    async (setting: StageSetting, voiceId: string) => {
      if (!workspaceId || voiceId === setting.voice_id) {
        return
      }
      const entry = ttsByModel.get(setting.model)
      setSavingAction(setting.stage_action)
      setError(null)
      try {
        const updated = await putStageSetting(workspaceId, setting.stage_action, {
          provider: entry?.provider ?? setting.provider,
          model: setting.model,
          voice_id: voiceId,
        })
        setSettings((current) =>
          current.map((item) =>
            item.stage_action === updated.stage_action ? updated : item,
          ),
        )
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : 'Failed to update voice.')
      } finally {
        setSavingAction(null)
      }
    },
    [workspaceId, ttsByModel],
  )

  const applyReasoning = useCallback(
    async (
      setting: StageSetting,
      reasoning: { effort?: string | null; tokens?: number | null },
    ) => {
      if (!workspaceId) {
        return
      }
      // Pin the current resolved model (the catalog provider when known) so
      // setting reasoning on a default stage creates a faithful override.
      const entry = catalogByModel.get(setting.model)
      setSavingAction(setting.stage_action)
      setError(null)
      try {
        const updated = await putStageSetting(workspaceId, setting.stage_action, {
          provider: entry?.provider ?? setting.provider,
          model: setting.model,
          reasoning_effort: reasoning.effort ?? null,
          reasoning_tokens: reasoning.tokens ?? null,
        })
        setSettings((current) =>
          current.map((item) =>
            item.stage_action === updated.stage_action ? updated : item,
          ),
        )
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : 'Failed to update reasoning.')
      } finally {
        setSavingAction(null)
      }
    },
    [workspaceId, catalogByModel],
  )

  return (
    <>
      <header className="as-console__header">
        <div>
          <div className="as-console__eyebrow">Configuration</div>
          <h2>Stage Models</h2>
        </div>
        <span className="as-console__live">
          <span className="as-live-dot" /> {settings.length} stages
        </span>
      </header>

      <div className="as-console__scroll">
        {error ? <ErrorBanner message={error} /> : null}

        {!workspaceId ? (
          <div className="as-console__empty">Select a workspace to configure stage models.</div>
        ) : isLoading && settings.length === 0 ? (
          <div className="as-console__empty">Loading stage settings…</div>
        ) : (
          <div className="as-console__stage-settings">
            {settings.map((setting) => {
              const isNarration = setting.stage_action === AUDIO_NARRATION_ACTION
              const llmCurrent = isNarration ? undefined : catalogByModel.get(setting.model)
              const isSaving = savingAction === setting.stage_action
              const optionHasCurrent = isNarration
                ? ttsByModel.has(setting.model)
                : catalogByModel.has(setting.model)
              const kind = reasoningKind(llmCurrent)
              const ttsEntry = isNarration ? ttsByModel.get(setting.model) : undefined
              const voiceOptions = ttsEntry?.voices ?? []
              const voiceHasCurrent = Boolean(
                setting.voice_id && voiceOptions.some((voice) => voice.id === setting.voice_id),
              )
              const effortValue = setting.reasoning_effort ?? DEFAULT_EFFORT
              const budgetValue = setting.reasoning_tokens ?? DEFAULT_BUDGET
              const effortHasCurrent = (EFFORT_OPTIONS as readonly string[]).includes(effortValue)
              const budgetHasCurrent = BUDGET_OPTIONS.includes(budgetValue as (typeof BUDGET_OPTIONS)[number])
              return (
                <div className="as-console__panel as-console__setting" key={setting.stage_action}>
                  <div className="as-console__setting-main">
                    <div className="as-console__setting-icon" aria-hidden="true">
                      <SlidersHorizontal size={16} strokeWidth={1.75} />
                    </div>
                    <div className="as-console__setting-body">
                      <div className="as-console__setting-title">
                        {setting.label}
                        <span
                          className={`as-console__setting-badge${
                            setting.is_overridden ? ' is-override' : ''
                          }`}
                        >
                          {setting.is_overridden ? 'Override' : 'Default'}
                        </span>
                      </div>
                      <div className="as-console__setting-meta">
                        {isNarration && ttsEntry ? (
                          <>
                            <CapabilityMeter tier={ttsEntry.capability_tier} />
                            <span className="seg">{formatTtsPrice(ttsEntry.price_per_million)}</span>
                          </>
                        ) : isNarration ? (
                          <span className="seg">{setting.provider} · uncatalogued model</span>
                        ) : llmCurrent ? (
                          <>
                            <CapabilityMeter tier={llmCurrent.capability_tier} />
                            <span className="seg">{formatPrice(
                              llmCurrent.input_per_million,
                              llmCurrent.output_per_million,
                            )}</span>
                          </>
                        ) : (
                          <span className="seg">{setting.provider} · uncatalogued model</span>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="as-console__setting-control">
                    <select
                      className="as-console__select"
                      value={setting.model}
                      disabled={isSaving}
                      onChange={(event) => void handleSelect(setting, event.target.value)}
                      aria-label={`Model for ${setting.label}`}
                    >
                      {!optionHasCurrent ? (
                        <option value={setting.model}>{setting.model} (current)</option>
                      ) : null}
                      {(isNarration ? groupedTtsCatalog : groupedCatalog).map(
                        ([provider, models]) => (
                          <optgroup key={provider} label={provider}>
                            {models.map((entry) => (
                              <option key={entry.model} value={entry.model}>
                                {'input_per_million' in entry
                                  ? `${entry.display_name} · T${entry.capability_tier} · ${formatPrice(entry.input_per_million, entry.output_per_million)}`
                                  : `${entry.display_name} · T${entry.capability_tier} · ${formatTtsPrice(entry.price_per_million)}`}
                              </option>
                            ))}
                          </optgroup>
                        ),
                      )}
                    </select>

                    {isNarration ? (
                      <label className="as-console__reasoning">
                        <span className="as-console__reasoning-label">Voice ID</span>
                        <select
                          className="as-console__select as-console__select--sm"
                          value={setting.voice_id ?? ''}
                          disabled={isSaving}
                          onChange={(event) => void handleVoice(setting, event.target.value)}
                          aria-label={`Voice for ${setting.label}`}
                        >
                          {!voiceHasCurrent && setting.voice_id ? (
                            <option value={setting.voice_id}>{setting.voice_id}</option>
                          ) : null}
                          {voiceOptions.map((voice) => (
                            <option key={voice.id} value={voice.id}>
                              {voice.display_name}
                            </option>
                          ))}
                        </select>
                      </label>
                    ) : kind === 'effort' ? (
                      <label className="as-console__reasoning">
                        <span className="as-console__reasoning-label">Reasoning effort</span>
                        <select
                          className="as-console__select as-console__select--sm"
                          value={effortValue}
                          disabled={isSaving}
                          onChange={(event) =>
                            void applyReasoning(setting, {
                              effort: event.target.value,
                            })
                          }
                        >
                          {!effortHasCurrent ? (
                            <option value={effortValue}>
                              {effortValue.charAt(0).toUpperCase() + effortValue.slice(1)}
                            </option>
                          ) : null}
                          {EFFORT_OPTIONS.map((effort) => (
                            <option key={effort} value={effort}>
                              {effort.charAt(0).toUpperCase() + effort.slice(1)}
                            </option>
                          ))}
                        </select>
                      </label>
                    ) : kind === 'budget' ? (
                      <label className="as-console__reasoning">
                        <span className="as-console__reasoning-label">Thinking budget</span>
                        <select
                          className="as-console__select as-console__select--sm"
                          value={String(budgetValue)}
                          disabled={isSaving}
                          onChange={(event) =>
                            void applyReasoning(setting, {
                              tokens: Number(event.target.value),
                            })
                          }
                        >
                          {!budgetHasCurrent ? (
                            <option value={budgetValue}>
                              {budgetValue.toLocaleString()} tokens
                            </option>
                          ) : null}
                          {BUDGET_OPTIONS.map((tokens) => (
                            <option key={tokens} value={tokens}>
                              {tokens.toLocaleString()} tokens
                            </option>
                          ))}
                        </select>
                      </label>
                    ) : null}

                    {setting.is_overridden ? (
                      <button
                        type="button"
                        className="as-console__reset-link"
                        disabled={isSaving}
                        onClick={() => void handleReset(setting)}
                      >
                        Reset to default ({setting.default_model})
                      </button>
                    ) : null}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </>
  )
}
