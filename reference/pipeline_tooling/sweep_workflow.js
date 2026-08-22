export const meta = {
  name: 'panscriptum-sweep-batch',
  description: 'Catalogue a batch of Acquisitions Roll sources into citation-ready records: full category research for web/hybrid sources, folder cross-reference for mechanical sources, and a power-ceiling synthesis per source.',
  phases: [
    { title: 'Research' },
    { title: 'Synthesize' },
  ],
}

const CATEGORIES = [
  'Persons (named individual characters, real or fictional)',
  'Factions & Organizations (groups, nations, guilds, companies, orders)',
  'Places & Locations (worlds, regions, cities, planes, ships-as-places)',
  'Vessels & Things (items, vehicles, weapons, artifacts, notable objects)',
  'Events (major storyline events, wars, historical turning points within the fiction)',
  'Media (in-fiction media: books, songs, broadcasts, works that exist within the story itself)',
  'Powers, Abilities & Systems (magic systems, power systems, tech systems, disciplines)'
]

const RESEARCH_SCHEMA = {
  type: 'object',
  properties: {
    entries: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          name: { type: 'string' },
          type: { type: 'string', description: 'specific subtype, e.g. Character, Faction, Planet, Weapon, Event, Comic Issue, Magic System' },
          description: { type: 'string', description: '1-3 sentence factual description, grounded in what sources actually say' },
          scale_note: { type: 'string', description: 'any known power/scale statement or feat, if applicable; empty string if none' },
        },
        required: ['name', 'type', 'description']
      }
    },
    coverage_note: { type: 'string', description: 'what was actually covered (which wiki/source), how exhaustive the sweep of this category was, and any known gaps or stub areas' }
  },
  required: ['entries', 'coverage_note']
}

const SYNTH_SCHEMA = {
  type: 'object',
  properties: {
    source: { type: 'string' },
    total_entries: { type: 'number' },
    ceiling_entity: { type: 'string', description: 'the single strongest / most far-reaching entity or object identified for this source' },
    ceiling_rationale: { type: 'string', description: 'the specific feat(s) or statement(s) supporting this as the ceiling' },
    provisional_magnitude: { type: 'string', description: 'M0-M10 band estimate with brief justification. M0-2 mundane/city, M3-4 country/continent, M5 planetary, M6 stellar/solar-system, M7 galactic, M8 universal, M9 multiversal, M10 omniversal/conceptual' },
    canon_branches: { type: 'array', items: { type: 'string' }, description: 'distinct official continuities/canons for this source if more than one exist; empty array if single continuity' },
    integration_notes: { type: 'string', description: 'brief note on how this source could plausibly entangle with others later, given its ceiling and nature' }
  },
  required: ['source', 'total_entries', 'ceiling_entity', 'ceiling_rationale', 'provisional_magnitude', 'canon_branches', 'integration_notes']
}

const batch = args.sources // [{name, category, mode, seq, folder_hint}]

const results = await pipeline(
  batch,
  async (src) => {
    if (src.mode === 'owner-original') {
      return { src, merged: [], skippedResearch: true }
    }
    if (src.mode === 'folder-mechanical') {
      // one light synthesis-oriented pass instead of full 7-category fan-out
      const r = await agent(
        `"${src.name}" is a Dungeons & Dragons rules/mechanics sourcebook already fully extracted from the owner's real XML homebrew archive (${src.folder_hint || 'mechanical content already logged'}). Do a light web pass to confirm/name the most notable specific named entities it introduces (e.g. named monsters, named magic items, iconic NPCs if any) beyond generic rules text. Do not attempt to re-derive the full mechanical content; that's already logged. List what you find.`,
        { label: `${src.name}:mech-check`, phase: 'Research', schema: RESEARCH_SCHEMA }
      )
      return { src, merged: (r?.entries || []).map(e => ({ ...e, category: 'Mechanical/Named Content' })), skippedResearch: false }
    }
    // web or hybrid: full category fan-out
    const folderCtx = src.mode === 'hybrid' && src.folder_hint
      ? ` Note: ${src.folder_hint} mechanical entries from this source are already logged separately in the archive — focus your research on NARRATIVE content (named NPCs, factions, locations, plot events, artifacts) not restated rules text.`
      : ''
    const specialCtx = src.special_note ? ` IMPORTANT: ${src.special_note}` : ''
    const catResults = await parallel(CATEGORIES.map(cat => () =>
      agent(
        `You are cataloguing the source "${src.name}" for an in-universe omniverse encyclopedia. Research this source as exhaustively as realistically possible using web search, prioritizing dedicated wikis (Fandom, official databases, or for real-world traditions: reference/academic overviews) and walking their category indexes rather than sampling only famous entries. Enumerate EVERY named ${cat} you can find documented for this source.${folderCtx}${specialCtx} For each entry give its name, specific type/subtype, and a factual 1-3 sentence description. If you find a scale/power statement or notable feat, include it in scale_note. Do not stop at the first handful of famous examples — aim for genuine completeness. Note coverage gaps honestly in coverage_note rather than silently omitting them.`,
        { label: `${src.name}:${cat.split(' ')[0]}`, phase: 'Research', schema: RESEARCH_SCHEMA }
      )
    ))
    const merged = catResults.filter(Boolean).flatMap((r, i) => (r.entries || []).map(e => ({ ...e, category: CATEGORIES[i] })))
    return { src, merged, skippedResearch: false }
  },
  async (prev, src) => {
    if (prev.skippedResearch && src.mode === 'owner-original') {
      return {
        source: src.name,
        category: src.category,
        mode: src.mode,
        entries: [
          { name: 'Rowan', type: 'Person', description: 'Named figure from the owner\'s unpublished screenplay; details not yet supplied beyond the name.', category: 'Persons' },
          { name: 'Wendy', type: 'Person', description: 'Named figure from the owner\'s unpublished screenplay; details not yet supplied beyond the name.', category: 'Persons' },
          { name: 'Mihai Niculescu', type: 'Person', description: 'Named figure from the owner\'s unpublished screenplay; details not yet supplied beyond the name.', category: 'Persons' },
          { name: 'the Omanears', type: 'Faction/Species (unconfirmed)', description: 'Named group/people from the owner\'s unpublished screenplay; nature not yet supplied beyond the name.', category: 'Factions & Organizations' },
          { name: 'the culoare adevarata', type: 'Concept/Power (unconfirmed)', description: '"The true color" (Romanian) — named concept from the owner\'s unpublished screenplay, likely central to its magic/thematic system; nature not yet supplied.', category: 'Powers, Abilities & Systems' },
        ],
        synthesis: {
          source: src.name, total_entries: 5, ceiling_entity: 'UNDETERMINED — insufficient source material',
          ceiling_rationale: 'This is the owner\'s own unpublished screenplay. Only five names have been mentioned in conversation; the actual text/treatment has not been provided. No further cataloguing is possible without the source material itself.',
          provisional_magnitude: 'DECLINED — insufficient evidence', canon_branches: [],
          integration_notes: 'Flagged INCOMPLETE pending the owner supplying the screenplay or a synopsis. Logged now only so the source exists on the roster with correct status.'
        },
        status: 'incomplete-needs-source'
      }
    }
    const synth = await agent(
      `Given this catalogue of ${prev.merged.length} entries for the source "${src.name}" (mode: ${src.mode}): ${JSON.stringify(prev.merged).slice(0, 14000)}\n\nIdentify the single strongest/most far-reaching entity or object (the "ceiling"), its provisional Magnitude band, whether this source has multiple distinct official continuities, and a brief integration note for how it might later entangle with other verses given its ceiling.`,
      { label: `synth:${src.name}`, phase: 'Synthesize', schema: SYNTH_SCHEMA }
    )
    log(`${src.name}: ${prev.merged.length} entries, ceiling=${synth?.ceiling_entity} (${synth?.provisional_magnitude})`)
    return { source: src.name, category: src.category, mode: src.mode, entries: prev.merged, synthesis: synth, status: 'catalogued' }
  }
)

return results
