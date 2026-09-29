# AI-prose DETECT report (flag only; nothing edited)

Scope: 10 chapters under output/raw/ (100 entries, about 123 KB). Profile: blog defaults, adapted to the archival register.
Read prompts/system_style.txt and src/tells.py first. Template headings/labels are excluded from all counts.
Counts are line/phrase hits across the 10 files. Flags are writing-quality signals, not authorship proof.

Running tells.scan() over the 10 files gives about 100 hits, all on words and shapes it already lists
(testament 11, not-merely 10, serves-as 7, more-than-just 7, enigmatic 6, intricate 6, resonates 5,
underscores 5, interplay 4, fabric 4, echoes of 4, tapestry 4, pivotal 4). So the listed tells still leak.
The larger problem is what the lists do not see.

## 1. Cross-chapter patterns, ranked by voice flattening

1. **Marginalia are one template with the nouns swapped (worst).** Every entry has 3 to 4 notes, drawn from a small pool of near-identical lines.
   - Persons_171_180: "A youth in a world of power--what will he ..." (5 of 10 MOTH lines); "in a world of gods and dragons--how ..." (3 more);
     AVAR "...but his name is already part of the record/saga" (6 of 10).
   - Places_1_10: the seven "List of characters" entries repeat AVAR/MOTH/UNNAMED nearly verbatim ("this list is a good summary, but it misses the depth").
   - Places_321_330: Mika / Miki / Mika Kashiwagi get one note reworded three times.
   - Fails Ground Rule 5 (note must be specific) and the "vary Avar's shape" rule.
2. **QUILL as first-person eyewitness filler.** 87 of about 100 Quill lines open "I ..."; 43 use I saw/met/read/watched/played/fought.
   "in action" appears 14 times: "I've seen Cougarmon in action--it's a beast." "I've seen Targetmon in action--it's a powerhouse."
   Several break frame ("I played through Digimon Data Squad", "I watched the anime", "I fought Leo in a simulation"). They add no fact.
3. **UNNAMED HAND overused and formulaic.** 70 notes in 100 entries, against "appears rarely". 32 open Beware / Be wary / Be cautious / Be mindful / Watch.
   About 9 say "may not be what it seems": "Beware the crown. It may not be what it seems." Not tied to the entry's detail.
4. **Thematic abstraction closers in Marginalia and Record.** Moralising about "the world": "a reminder that" 14; "testament" 11;
   "reflect(s)/reflection of" 28; "(a) mirror/reflection of" 13; "study in" 6; "duality" 8; "embod-" 6; "deeper role/lore/meaning/connection" 18;
   "raises questions" and kin about 10; "carries weight/weight of" 11; "themes of" 12; "shapes/shaping the ..." 24.
   Quotes: "a reminder that even the most sacred places can harbor danger"; "a mirror of the world's own contradictions".
5. **Data-gap narration as filler.** The Record talks about the record instead of the subject: "remains unexplored / yet to be / not yet fully / remains to be uncovered" 30;
   "the entry points to a list of characters" 5+; "Further details are pending classification". Conflicts with Rule 2 (short true entry).
   Stacked hedged inference: "suggests a/that" 37, "may symbolize", "is said to".
6. **Clone Records.** 26 open "X is a character/Digimon/figure from ..."; runs of near-duplicate paragraphs:
   Persons_171_180 ("teenager under Demetria's sway ... story remains to be told" x5), Places_1_10 (7 list entries), Places_321_330 (Mika x3). Rule 6 violation; a phrase list cannot see it.
7. **Hollow hype nouns/idioms.** "force to be reckoned with", "force of nature", "marvel of engineering/architecture" (4), "powerhouse", "showstopper", "rollercoaster", "a beast"
   (about 33 loose hits). "the world's own X" possessive framing ("the world's own balance/complexity/resilience").
8. **Negation-reveal variants tells misses.** "not mere/not a mere" 8 ("not mere undead but disciplined warriors", "not a mere script but a living language", "not mere decoration").
   tells catches "not merely/simply", and "not just" only with a "but".
9. **Em-dash density.** 109 em-dashes across 100 entries (rule: rarely, at most one per entry), nearly all in Quill/Avar notes ("in action--it's a ...").
   No checker for it.
10. **Chapter preambles.** Generic scene-setting ("vast and intricate", "vast and shifting landscapes", "not mere backdrops", "active participants", "web of events", "backbone").
    Words are partly listed; the construction is not. Also "unfolding" (10): "unfolding events/narrative/saga".
11. **Rhetorical-question MOTH lines** (about 9): "how do they even define truth in such a context?" "what will he choose?"

Out of scope but seen (not prose tells): template damage ("Attest, Transcribed", "Dig,", stray duplicate "Threads:" lines, Class values like Character/Media/Event on persons and creatures)
and game-rules leakage in L.7.4 ("900 XP", "Dexterity bonus", "potion of healing", "event to be run during the adventure").

## 2. tells.py: covered vs missed

Covered: testament, not merely, serves as a, more than just, enigmatic, intricate, resonates, underscores, interplay, fabric, echoes of, tapestry, pivotal, profound, formidable,
navigate the, journey of, plays a role, not only...but also, whispers of, looms over.
Missed: items 1, 2, 3, 5, 6, 7, 8 (partly), 9, 10 (partly), 11 entirely. Also near forms: "marvel", "embodies", "duality", "reminder". Every cross-entry duplication pattern needs a
similarity check, not a phrase list (the MinHash item CLAUDE.md deferred).

## 3. Candidate additions

### Clear problems
- `\b(?:a|is a|are a) reminder (?:that|of)\b`
- `\b(?:a|is a) mirror\b`, `\breflection of the world`, `\breflects the world`, `\bthe world['’]s own\b`
- `\ba study in\b`, `\ba marvel of\b`, `\bforce of nature\b`, `\bforce to be reckoned with\b`, `\bpowerhouse\b`, `\bshowstopper\b`
- `\bnot (?:a )?mere\b` (widens "not merely"); "not just a/an/the X" without "but"
- `\bmay not be (?:what|as) (?:it|he|she|they) seem`, `\bmore than (?:he|she|it|they) seem`, `\bnot what it seems`
- `already part of the (?:record|saga)`, `name is already`
- `\bin a world of (?:gods|power|magic|myth)`, `world of gods and dragons`
- `\bremains? (?:unexplored|underdeveloped|undefined|to be (?:uncovered|revealed|explored))`, `\byet to be (?:fully )?(?:realized|defined|written|revealed)`, `\bnot yet fully`
- `\bthe entry (?:points to|describes|suggests)`, `\bthe text does not (?:elaborate|clarify)` (record narrating the record)
- `\bvast and (?:intricate|shifting|complex)`, `\bactive participants`, `\bnot mere backdrops?`, `\bweb of events`, `\bwoven (?:into|through)`, `\bunfolding (?:events|narrative|saga|story)`
- `\braises questions`, `\bsuggests a deeper`, `\bdeeper (?:role|lore|meaning|connection|understanding|narrative)`, `\bembod(?:y|ies)\b`, `\bduality\b`, `\bcarr(?:y|ies) (?:more )?weight`
- UNNAMED opener cap: `^UNNAMED[ A-Z]*: (?:Beware|Be wary|Be cautious|Be mindful)` limited to about 2 per chapter
- Quill tic: `^QUILL: I(?:['’]ve| have)? (?:seen|read|watched) .{0,50} in action`, more than 1 per chapter

### Judgment calls
- Em-dash cap (more than 1 per entry, or per Marginalia line). The rule exists in prose only; a check would be cheap.
- Rhetorical-question MOTH lines (`^MOTH: .*\?$`): fine occasionally; 9 in 100 reads as a tic.
- `suggests (?:a|that)` / `may (?:symbolize|indicate)`: legitimate in a Custodial "attested but unplaced" voice; flag at 3+ per entry.
- `themes? of`, `shapes? the`, `reflect(?:s|ion)`: ordinary English; rate-report only, like the existing lexical set.
- Quill "I saw/met/read..." opener is by design ("Quill went there"); cap the share per chapter (e.g. under 40%) rather than ban.
- Within-chapter Marginalia n-gram overlap test (a shared 5-gram across 3+ entries) instead of more phrases.
