import { describe, expect, it } from 'vitest'
import {
  READER_DEFINE_MAX_WORDS,
  buildNarration,
  matchWikiTerms,
  resolveReaderSelection,
  type Block,
} from './readerContent'

const blocks: Block[] = [
  {
    seq: 0,
    id: 'h1',
    kind: 'heading',
    level: 1,
    text: 'Chapter',
    md: null,
    chapterTitle: 'Chapter',
    isChapterStart: true,
  },
  {
    seq: 1,
    id: 'p1',
    kind: 'paragraph',
    level: 0,
    text: 'Alpha beta gamma delta.',
    md: null,
    chapterTitle: 'Chapter',
    isChapterStart: false,
  },
  {
    seq: 2,
    id: 'p2',
    kind: 'paragraph',
    level: 0,
    text: 'They increased tempo in the fight.',
    md: null,
    chapterTitle: 'Chapter',
    isChapterStart: false,
  },
  {
    seq: 3,
    id: 'p3',
    kind: 'paragraph',
    level: 0,
    text: 'Later they slowed down.',
    md: null,
    chapterTitle: 'Chapter',
    isChapterStart: false,
  },
]

describe('resolveReaderSelection', () => {
  const { wordBlocks } = buildNarration(blocks)

  it('returns neighbors and sentence for a same-block selection', () => {
    const tempo = wordBlocks[2].words.find((w) => w.text === 'tempo')
    expect(tempo).toBeTruthy()
    const resolved = resolveReaderSelection(wordBlocks, [tempo!.global], new Map())
    expect(resolved).not.toBeNull()
    expect(resolved!.term).toBe('tempo')
    expect(resolved!.neighbors.prev).toBe('Alpha beta gamma delta.')
    expect(resolved!.neighbors.current).toBe('They increased tempo in the fight.')
    expect(resolved!.neighbors.next).toBe('Later they slowed down.')
    expect(resolved!.sentence).toBe('They increased tempo in the fight.')
    expect(resolved!.entryId).toBeNull()
  })

  it('rejects selections over the word cap', () => {
    const long: Block[] = [
      {
        seq: 0,
        id: 'long',
        kind: 'paragraph',
        level: 0,
        text: 'one two three four five six seven eight nine ten',
        md: null,
        chapterTitle: 'Chapter',
        isChapterStart: false,
      },
    ]
    const { wordBlocks: longBlocks } = buildNarration(long)
    const globals = longBlocks[0].words.map((w) => w.global)
    expect(globals.length).toBeGreaterThan(READER_DEFINE_MAX_WORDS)
    expect(
      resolveReaderSelection(longBlocks, globals.slice(0, READER_DEFINE_MAX_WORDS + 1), new Map()),
    ).toBeNull()
    expect(
      resolveReaderSelection(longBlocks, globals.slice(0, READER_DEFINE_MAX_WORDS), new Map())
        ?.term,
    ).toBe('one two three four five six seven eight')
  })

  it('rejects multi-block selections', () => {
    const a = wordBlocks[1].words[0].global
    const b = wordBlocks[2].words[0].global
    // Non-contiguous across blocks
    expect(resolveReaderSelection(wordBlocks, [a, b], new Map())).toBeNull()
  })

  it('returns wiki entryId when selection matches a linked term', () => {
    const entries = [
      { id: 'e1', preferred_label: 'tempo', aliases: [] as string[], status: 'canonical' },
    ]
    const termByWord = matchWikiTerms(wordBlocks, entries)
    const tempo = wordBlocks[2].words.find((w) => w.text === 'tempo')!
    expect(termByWord.get(tempo.global)).toBe('e1')
    const resolved = resolveReaderSelection(wordBlocks, [tempo.global], termByWord)
    expect(resolved!.entryId).toBe('e1')
  })
})
