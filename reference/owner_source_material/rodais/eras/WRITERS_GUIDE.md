# Writing an era legendarium: the writers' guide

Each of the seven ages gets its own legendarium: a book of 500–600 pages in the house design of the master
`The_Diathir_Legendarium.pdf`, covering that age alone. This guide is the working contract for everyone writing one.
Read `../legendarium/BRIEF.md`, the TOLKIEN and BOOK_STYLE briefs and the master record of your age before you start.
Avoid the tells listed in `quality/TELLS_FOR_WRITERS.md`; `python quality/tells_scan.py <K>` finds them in your files.
**Era detail adds to the master canon and never contradicts it.**

## 1. The files

```
eras/
  WRITERS_GUIDE.md          this guide
  build_era.py              builds an age: dated annals, LEGENDARIUM.md, the PDF, the Atlas data
  check_era.py              validates an age
  NAMES.json                English name -> Dia-thìris proper noun, with gloss (kept by the lead)
  THREADS.json              the storylines events belong to (kept by the lead)
  PEOPLE.json               the people events name (kept by the lead)
  age_<K>/                  K = I, II, III, IV, V, VI, VII
    annals/age_<K>_master.json   the master events of the age. NEVER EDIT. (Rebuilt by: python build_era.py K --seed)
    annals/age_<K>_<NN>.json     writer NN's annals file
    book/<NN>_<slug>.md          the Books of the age, in file-name order
    gazetteer/<NN>_<slug>.json   the towns of the age
    appendices/<L>_<slug>.md     the appendices, in file-name order (A_rulers.md, B_faiths.md, ...)
    places.json                  (optional, lead) places the age knew that the master map does not
    front.json                   (optional, lead) the epigraph of the title pages
  -- written by the build, never by hand:
    annals_dated.json, LEGENDARIUM.md, atlas.json, The_Diathir_Legendarium_<Age>.pdf, ../master_links.json
```

## 2. Who owns what: working in parallel without clashing

The lead gives every writer of an age a **writer number** N (1–9; 0 is the lead's own) and, for the annals, a
**span** of the master annals. Everything below follows from those two.

| You own | Rule |
|---|---|
| `annals/age_<K>_0N.json` | Your file alone. Nobody else edits it. |
| ids `E<K>-N000` … `E<K>-N999` | Writer 1 of Age III uses `EIII-1000`–`EIII-1999`, writer 2 `EIII-2000`–`EIII-2999`. Need more? Ask the lead for a second number. To slip an event in between two you already have, add a letter: `EIII-1203a`. |
| your span `[FROM, TO]` | Two master ids of your age (TO may be `"end"`). Your events fall after FROM and before TO. No two files may share a gap between master events: the build refuses overlapping spans. |
| `book/`, `gazetteer/`, `appendices/` files the lead assigns you | One file per writer per piece. The build reads them in file-name order, so the lead sets the order with the prefix (`03_the_war_of_the_claimants.md`). |

`NAMES.json`, `THREADS.json`, `PEOPLE.json`, `places.json` and `front.json` are the lead's. Send the lead new names,
threads, people and places; don't edit these files yourself.

## 3. An annals event

Your file:

```json
{"writer": 1, "span": ["III-0001", "III-0060"], "events": [
  {"id": "EIV-1001", "title": "The first telling at the western quays",
   "body": "Pilots on the quays repeat the word of a far shore to anyone who will stand them a cup.",
   "place": "burg:19", "kind": "discovery", "category": "land",
   "links": [{"to": "III-0002", "type": "location"}],
   "threads": ["the-mist"], "people": [], "told_in": "book/01_the_word_from_the_west.md#i-of-the-pilots-tale"},
  {"after": "III-0003"},
  {"id": "EIV-1002", "...": "..."}
]}
```

| Field | Required | What it is |
|---|---|---|
| `id` | yes | `E<K>-nnnn` in your block. Never reuse or renumber an id once a book or link uses it. |
| `title`, `body` | yes | As in the master annals: a short title; a body of one to four plain sentences, in the annals' voice. |
| `place` | when there is one | `burg:19`, `marker:3`, `province:1`, `zone:0`, `river:5`, `feature:2`: a master map id, or a place declared in `places.json`. |
| `kind` | yes | The master annals' free word (discovery, court, war, rite, trade, craft, loss…). |
| `category` | **yes** | One of the nine categories (§6). |
| `links` | **yes** | `[]` when there is truly nothing to link, which is rare (§5). |
| `threads` | **yes** | Ids from `THREADS.json`; `[]` when the event belongs to none. |
| `people` | **yes** | Ids from `PEOPLE.json` of those who take part; `[]` when none is named. |
| `told_in` | where apt | `"book/<file>.md#<anchor>"`: the Book section that tells this event (§7). |
| dating fields | optional | `era_between`, `between`, `on`, `within`, `same_day`, `eve`, `first_of_year`, `seed` (§4). |

An era event may not carry `canon`, `canon_date` or `keep`: those mark the owner's chronicle, which is in the master
events already.

## 4. Dates: you choose the order, the build chooses the day

Never type a date. Put your events in the order they happened; the build dates them.

**How interleaving works.** The master events of the age are fixed, each on exactly its master date, and they
cut the age into gaps. Your events go into the gaps of your span, in the order your file lists them:

- events at the top of the file, before any marker, come right after FROM;
- `{"after": "III-0042"}` is a marker: the events that follow it come after master event III-0042 (and before the
  master event that follows it). Markers must go forward in master order and stay inside your span;
- the build spreads the events of each gap evenly between its two master events, as the master reckoning spreads
  its own, with days and months from the same album pool.

**Masters cannot move.** Each gap is dated on its own, and every date it gets is held inside the gap, so no era event
can move, pass or reorder a master event. The build checks this on every run, and
`check_era.py K --fuzz 200` proves it by throwing hundreds of random events at every gap.

**Steering a date:**

| Field | Meaning |
|---|---|
| `"era_between": [120, 140]` | Fall in years 120–140 **of your age's era** (LE 120–140). Preferred. |
| `"between": [81, 101]` | The same in the continuous count the master annals use (`reckoning.py`). |
| `"on": [312, 4, 17]` | Exactly 17 an Giblean of era year 312. It must lie inside its gap, and after any earlier `on` in the gap. Otherwise the build stops. Use it only for a day the story needs. |
| `"within": ["III-0042", 5]` / `["III-0042", 20, 16]` | No more than 5 years after that event (and at least 16 years after it): one life, one reign, "the following year". |
| `"same_day": true` | The day of the event just before it (a master event or yours). |
| `"eve": true` / `"eve": 3` | The day before the next event, or N days before it. |
| `"first_of_year": true` | The first day of its year. |
| `"seed": "EIV-1001"` | Take another id's day-of-year hash: rarely needed. |

A window that cannot hold between its master neighbours is dropped with a note, and the event is spread evenly
instead. If you see such a note, you have put the event in the wrong gap.

Era years: year 1 of an era is the year its age opens; there is no year 0. The build shows every date as
`12 am Màrt, LE 67`.

## 5. Links: tie every event to what it answers, causes, continues or echoes

`"links": [{"to": "<event id>", "type": "<type>", "note": "a few words, optional"}]`. The target may be any event:
this age's master or era events, another age's era events, or the master record. **Write each link once.** The
build adds the reverse link to the target, with the incoming label below. In the PDF, a link to this age jumps to
the entry. A link to another age prints `→ An Aois Naomh, FE 312` and opens that age's own PDF. In the Atlas it is a
chip in the entry's "Related" panel.

| type | arrow | on your event | on the target | example |
|---|---|---|---|---|
| `cause` | → | Leads to | Caused by | The count of hulls finds too few: `{"to": "III-0007", "type": "cause"}`, and the ships are built. |
| `sequel` | ← | Follows from | Leads to | The woodmen's vigil comes after the oaks are marked: `{"to": "EIV-1004", "type": "sequel"}`. |
| `parallel` | ⇄ | At the same time | At the same time | The mist thins while the humans' ships cross: `{"to": "IV-0001", "type": "parallel"}`. |
| `legacy` | ⇝ | Legacy | Legacy of | A custom kept long after its cause: `{"to": "II-0249", "type": "legacy"}`. |
| `location` | ○ | Same place | Same place | Two things done at Cathair dhearg: `{"to": "III-0002", "type": "location"}`. |
| `person` | ◇ | Same person | Same person | Two deeds of one queen: `{"to": "III-0005", "type": "person"}`. |
| `fulfils` | ✦ | Fulfils | Fulfilled by | An oath kept generations later: `{"to": "EIII-2210", "type": "fulfils"}`. |
| `answers` | ↩ | Answers | Answered by | The last word on the far shore answers its finding: `{"to": "III-0001", "type": "answers"}`. |

**When to link:** always when an event directly answers, causes, continues or echoes another. Look for lineages
(births, crownings, deaths), feuds and their vengeance, promises and their keeping, a place founded and later
destroyed, a law made and later repealed, the first and the last of anything. Link across ages when the story
does: a Holy Age oath kept in the Age of Sundering. Don't link just because two events share a word. `location` and
`person` are for links a reader would want. Not every event at the same town needs one.

## 6. Categories

Every event has one `category`, the colour of its dot in the Atlas and its filter:

| category | shown as | example |
|---|---|---|
| `rulers` | rulers and houses | A king crowned; a house dies out; a regency. |
| `war` | war | A battle, a siege, a truce, a raid of the sea-thieves. |
| `faith` | faith and myth | A rite, a synod, a vision, a sacred place founded. |
| `coal` | coal and the vein | A new gallery in the vein; the measured handful; a coal failing. |
| `trade` | trade and work | A market charter, a guild, a new craft, a fair. |
| `land` | land and sea | A flood, a drought, a storm, a harbour silting, a voyage. |
| `law` | law and learning | A law made or repealed, a school, a book written, a census. |
| `humans` | the humans | Anything done by or to the humans from across the sea. |
| `coalblood` | the coal-blood | The coal-blooded: their marks, their fate, what was said of them. |

## 7. Threads, people and the telling

- **`threads`**: the storylines of `THREADS.json` (`line-of-aisling`, `the-seven-coals`, `the-mist`, `the-long-war`…).
  The Atlas's "Follow this thread" walks a thread across the ages, so tag every event that moves one. For a new
  thread, send the lead an id, its Dia-thìris name, a gloss and a sentence.
- **`people`**: the ids of `PEOPLE.json` (id, name, born, died, parents, children, houses, first and last event).
  Name everyone who acts in the event. For a new person, send the lead their entry: id, name, and the born and died
  events if the annals tell them.
- **`told_in`**: `"book/<file>.md#<anchor>"`, the section of a Book that tells the event. The anchor is the section
  heading with its accents dropped, in lower case, with every other run of characters turned into a hyphen:
  `## IV. Of the Sunwise Turn` → `iv-of-the-sunwise-turn`; `## II. Of Blàr Àth na Fala` → `ii-of-blar-ath-na-fala`.
  A master event's telling may point into the master books (`book/age_IV.md#…`).

## 8. Names: Dia-thìris only, the build adds the English

**Every proper noun is in Dia-thìris**: places, institutions, ages and eras, wars and battles, peoples, titles used as
names, gods, offices, laws, documents, orders, ships and feasts. The only exception is the humans' personal names,
which stay as the humans wrote them (Martha Greaves). Take every form from `NAMES.json`, and ask the lead for new
ones. Write the Dia-thìris name only, never "(the Holy Age)" after it. On the first mention in each Book section,
annals entry, gazetteer entry and appendix section, the build adds the English gloss: a numbered footnote in the
PDF, and a hover gloss in the Atlas. `check_era.py` notes every English form of a `NAMES.json` name it finds in your
text.

Spelling: long vowels take the grave accent, never the acute; write sc where Scottish Gaelic writes sg; and keep
caol le caol (slender with slender, broad with broad) inside one word. `check_era.py` runs every Dia-thìris form
through `rodais_engine.normalize()` and `check_agreement()`. Forms the master record already uses are accepted as
they stand. Never write "obsidian", "Rodos", "Ròdais" or "Ròdaich". Write no meta: no mention of writers, builds,
files or this guide in the text.

## 9. Tokens: references, never typed dates or names

In books, appendices, gazetteer text and annals bodies:

| Token | Gives |
|---|---|
| `{{date:III-0157}}` | the full date of any event, era or master, of any age: `10 an Giblean, LE 118` |
| `{{year:EIV-1203}}` | its year: `LE 1,203` |
| `{{reckon:A:B:KEY}}` | a day the reckoning makes between years A and B of the continuous count, the same for the same KEY every time (a birth, a founding) |
| `{{reckonyear:A:B:KEY}}` | just its year |
| `{{place:burg:19}}` | a place's name: the master map, or the age's own name for it from `places.json` |

`{{date:}}` and `{{year:}}` look in this age's annals first, then in the whole master record. Every token must
resolve, or the build stops.

## 10. Books, gazetteer, appendices

**A Book** (`book/NN_slug.md`) is one part of the age: a generation, a reign, a war. It opens like a master Book:

```markdown
# Of the Word from the West, the Choosing and the Keels

*LE 1 – 40*

> *Cha do thàinig sinn; bha sinn ann.*
> We did not come; we were here.

## I. Of the Pilots' Tale

It was told first on the quays of {{place:burg:19}}, on {{date:EIV-1001}}…

## II. Of the Marking of the Oaks
```

One `#` heading, the title. The build numbers the Books ("The First Book: …") in file order; a title with a comma
prints its second half as a subtitle. Then the date line, an optional epigraph in `>`, and `## I.`, `## II.`…
sections (each opens with a drop capital). `###` and `####` are sub-headings. Write in the book voice of the
BOOK_STYLE brief: recollection and point of view, organised by generation or reign.

**A gazetteer file** (`gazetteer/NN_slug.json`) is `{burg id: entry}` in the master gazetteer's shape, told as the
town stood in this age:

```json
{"19": {"founded_age": "II", "founded_by": "the holders of the Red Hill",
        "history": "In this age the queens kept their hall here…", "known_for": "the queen's hall"},
 "4001": {"founded_age": "IV", "founded_event": "EIV-1006", "founded_by": "pitch-burners",
          "history": "…", "known_for": "pitch for the keels", "name": "Baile na bìthe"}}
```

A master town keeps its master founding (don't give it another `founded_age`); the build prints its master founding
day. Optional `name` and `province` give what the town and its shire were called in this age ("X (now Y)"). A town
that existed in this age but not on the master map needs an id declared by the lead in `places.json`
(`{"burg:4001": {"name": …, "province": …}}`, ids from 1000 × age number + n, e.g. 4001). Every town must stand by the
end of the age. One town is one entry: two files can't both hold burg 19.

**An appendix** (`appendices/L_slug.md`) opens `# Title` (or `# Appendix C — Title`; otherwise the build letters
them in file order), with `##` sections. Rulers, faiths, wars, words, peoples, trade, shires or shares, land and
arms, all as they stood in this age.

## 11. Build and check

```
cd eras
python check_era.py IV              # validate (exit 0 when every check holds)
python build_era.py IV --no-pdf     # date the annals and write LEGENDARIUM.md and atlas.json: seconds
python build_era.py IV              # the same and the PDF: about a minute at full size
python check_era.py IV --final      # at hand-in: also fail when a section is outside its size target
python check_era.py IV --fuzz 200   # prove again that no era event can move a master event
python build_era.py all             # every age
```

Run `check_era.py` before every hand-in. It checks:

- the seed and the master dates;
- ids and writer blocks;
- categories and links: link types, and that every target exists;
- threads, people and `told_in`;
- tokens, places and the gazetteer's burgs;
- Dia-thìris spelling;
- forbidden words;
- size.

## 12. Size

| Section | Target |
|---|---|
| Annals | 1,200–1,800 dated entries, ~90–130k words |
| Books | ~100–130k words |
| Gazetteer | ~40–60k words |
| Appendices | ~30–50k words |
| **The book** | **500–600 pages** |

These ranges are ceilings for each section alone, not all at once. At the house design's densities (measured on the
master PDF: annals ~540 words a page, books ~405, appendices ~445, gazetteer ~620), all four at their midpoints come
to ~660 pages. **Aim for about 250–270k words in all.** For example: annals ~95k, books ~100–105k, gazetteer ~40k,
appendices ~30k, which comes to about 565–580 pages. `check_era.py` prints the running estimate.
