# Ròdais
### The Gaelic dialect of Rodos — reference sheet

## The fusion, in one rule
Ròdais spells consonants the Irish way (digraphs: *bh, mh, dh, gh, ch, sh*,
and the diphthong *ao*) but marks long vowels the Scottish way, with a
**grave** accent (*à è ì ò ù*) instead of Irish's acute. That single swap
is the whole visible signature — anyone who knows either language will
half-recognize Ròdais and know immediately it isn't quite either one.

## Lenition (the mutation rule)
The second word in a place name is *lenited* — its initial consonant
softens — the way a genitive or a word after most Goidelic generic nouns
does in real Irish and Scottish Gaelic. As of this pass, lenition is no
longer a lookup table — it's declared as actual sound-change rules, in
the same `target > replacement / environment` notation real historical
linguists (and tools like Vulgarlang) use to write phonological rules:

```
m > mh / #_        b > bh / #_        c > ch / #_
p > ph / #_         t > th / #_        d > dh / #_
g > gh / #_          s > sh / #_        f > fh / #_
```

`#_` means "at the start of a word." So *mòr* ("big") becomes *mhòr*
after a generic noun: **Cathair mhòr**, "big city." Two real refinements
sit on top of the plain rule, both implemented in `rodais_engine.py`:

- **Lenited *f* is spelled *fh*, and stays written even though it goes
  silent.** An earlier pass of this system was dropping the *f*
  entirely, which isn't how modern Gaelic orthography actually works —
  *fiadhaich* (wild) lenites to *fhiadhaich*, not *hiadhaich*.
- ***S* does not lenite before *c, p, t,* or *m*.** The clusters *sc-,
  sp-, st-, sm-* resist mutation in real Gaelic, so a word starting
  *Sk-* stays *Sk-* rather than becoming *Sh-* in that position.
- **A lenited proper noun keeps its capital letter**, with the *h*
  inserted right after it — *Dunn* lenites to *Dhunn*, not *dhunn*.

## Caol le caol, leathan le leathan
*Slender with slender, broad with broad* — the actual defining law of
Gaelic spelling, and the one rule this system didn't enforce until this
pass. Vowels are split into two classes:

- **Broad**: *a, o, u, à, ò, ù*
- **Slender**: *e, i, è, ì*

Inside a single word, any consonant (or consonant cluster) with a vowel
on both sides needs those two vowels to agree in class. This is why
real Gaelic suffixes so often come in matched pairs — a broad form and
a slender form — depending on what they're attaching to. Ròdais's minor
river suffix works the same way: *eas* (a real Gaelic word for a
waterfall or rapids) is the slender allomorph, *as* is the broad one,
and `rodais_engine.attach_suffix()` picks between them automatically by
checking the last vowel of the root. *Ciar* + suffix gives **Ciaras**,
not *Ciareas* — even though the word starts with a slender-looking *i*,
the vowel actually touching the suffix boundary is the *a* in *-iar*,
and *a* is broad.

**Two-word compounds are exempt.** *Cathair mhòr* doesn't need to
satisfy this rule, because the law only binds within one orthographic
word — it has nothing to say about the boundary between two separate
words in a phrase.

The rule is enforced by an actual checker now, `check_agreement()`,
not just applied by hand — every one of the 157 river names in the
current build was run back through it and came back clean. Worth being
honest about how it got there: the first version of the checker had a
real bug (it treated *any* two adjacent vowels with nothing between
them — a diphthong like the *ai* in *Àrsaidh* — as a violation, when
diphthongs are exactly what Gaelic orthography allows freely; the rule
only governs pairs of vowels with a consonant *between* them). Fixed
now, and the fix is what the checker actually enforces going forward.

## The substrate layer — "old," not a fossil suffix
Before Ròdais existed, an older culture lived on the island — canonised
here as the **Seann-Dhaoine**, "the Old Ones," folded in directly from
the map's own otherwise-unused "Wildlands" culture entry. An earlier
version of this system marked their surviving place names with an
invented, non-Gaelic *-oc* suffix. That's been replaced with the real
word: **Seann**, the old, irregular pre-nominal form of *sean* ("old"),
used exactly the way real Gaelic uses it before a noun it lenites — as
in *seann bhaile*, "old town." So a substrate settlement now reads
**Seann Dhunn**, **Seann Chwen**, **Seann Shkell** — "old Dunn," "old
Chwen," "old Shkell" — the root words themselves (*Bral-, Cwen-, Tarr-,
Vell-, Morn-, Skell-, Brenn-, Toll-, Warr-, Dunn-*) still aren't Gaelic,
still standing in for a language that came before and didn't survive
except as a name — but the word marking them as old now is Gaelic, the
same way real Gaelic speakers would actually have talked about them.
About one port in four still carries this older layer instead of a
full Ròdais generic-plus-qualifier name, the same real-world pattern as
Old Norse *-vík* surviving inside Scottish Gaelic coastal names like
Ullapool: borrowed and fossilized, not translated.

## Generic elements (place-name heads)
Real Irish and Scottish toponyms are built from a small closed set of
generic nouns plus a descriptive qualifier — *Dún Laoghaire, Cill Airne,
Gleann Domhain*. Ròdais does the same, and the generator picks the
generic by what kind of settlement it's naming:

| Role | Generics used |
|---|---|
| Capital | Cathair, Dùn |
| City | Cathair, Baile Mòr, Dùn |
| Town | Baile, Àth, Cnoc, Muileann |
| Village | Cill, Tobar, Achadh, Doire |
| Hamlet | Tobar, Cill, Carraig |
| Port (any size) | + Ros, Ceann, Cuan, Caol, Inis |

*(Cathair* = stone fort/city · *Dùn* = fortified hill · *Baile* =
settlement · *Àth* = ford · *Cnoc* = hill · *Muileann* = mill · *Cill* =
church site · *Tobar* = well · *Achadh* = field · *Doire* = oak grove ·
*Carraig* = rock · *Ros* = headland · *Ceann* = headland/point · *Cuan*
= harbor · *Caol* = strait · *Inis* = island.)*

## Qualifiers
Color, size, and character words, always lenited when they follow a
generic: *mòr* (big), *beag* (small), *dubh* (black), *geal/bàn*
(white), *dearg/ruadh* (red), *uaine/glas* (green-grey), *fada* (long),
*domhain* (deep), *ìseal* (low), *fiadhaich* (wild), *naomh* (holy),
*fionn* (fair), *ciar* (dusky), *gorm* (blue), *sean* (old), *òg*
(young), *garbh* (rough), *min* (smooth), *caol* (narrow), *leathan*
(wide), *crom* (bent), *dìreach* (straight), *àrsaidh* (ancient).

## Rivers
Major rivers (length at or above the island's median) take **Abhainn**
("river") plus a lenited qualifier: *Abhainn mhòr, Abhainn dhubh*. Minor
streams take a root plus the broad/slender-matched *-as/-eas* suffix
described above: *Fionnas, Ciaras, Àrsaidheas*.

## Provinces
Azgaar itself names a province after its own capital settlement by
default — Ròdais keeps that convention rather than inventing a separate
naming layer, so a province's name always matches its seat: *Siorrachd
Cathair mhòr* is simply "the shire of [the city] Cathair mhòr."
*Siorrachd* is the Scottish Gaelic word for shire/county.

## The state and its peoples
- **Ròdaich** — the majority population (formerly "Marltash" in the raw
  generation). **These are the coal-empowered people** — Aisling,
  Cian, Lorccan, and Fionnan's side of the story. Demonym built the
  real Gaelic way: root + *-aich* ("people of X"). They hold the
  capital, confirmed directly in the data — *Cathair dhearg* belongs
  to culture 2, Ròdaich.
- **Tuathaich** — the northern minority (formerly "Kiverton"). **These
  are the normal humans** — Dubhan's people, mortal and peripheral,
  the same way the story's own politics place them: powerless,
  pushed to the edge of the island, holding none of the capital. From
  *tuath*, "north" — the same *-aich* formation as Ròdaich, so the two
  read as siblings on the page even though their circumstances aren't.
- **Seann-Dhaoine** — "the Old Ones," the near-vanished pre-Gaelic
  substrate culture, source of the *Seann*-marked coastal names above.
- The state's full title is **Rìoghachd Ròdais** — "the Kingdom of
  Rodos" — replacing the auto-generated "Kingdom of Wincland," and
  folding the island's own name back into its own language.
- The capital, formerly **Luteley**, is now **Cathair dhearg** — "the
  red city."

## The tool itself
`rodais_engine.py` is a small, standalone rule system now, separate
from the renaming script that uses it — modeled on the same idea
Vulgarlang's phonology tools use (explicit phoneme classes, sound
changes written as readable rules) but running entirely on real
Irish/Scottish Gaelic phonology rather than a randomized one. It
exposes three checkable pieces: `lenite()`, `attach_suffix()`, and
`check_agreement()` — so any future name added to Rodos's map can be
run through the same rules and the same QA pass that the current 505
burgs, 157 rivers, and 123 provinces already went through, rather than
being hand-checked one at a time.

## What this is not (yet)
This is a naming layer, not a grammar. There's no verb system, no case
beyond lenition and the broad/slender agreement rule, no sentence-level
syntax — enough to make every place name on the map feel like it
belongs to one coherent, invented tongue, checkable against real Gaelic
dictionaries and real Gaelic grammar rules, and enough of a rule-system
that you could extend it by hand for dialogue. Building it out further
— verbs, pronouns, a real sentence grammar — is a separate, much larger
project from renaming a map.

---

## Errata (2026-09-22, with the grammar pass)

The rest of the language now lives in `GRAMMAR.md`, and the "What this is not (yet)" section above
is out of date: Ròdais now has verbs, pronouns, articles, prepositional pronouns and VSO syntax,
all implemented in `rodais_engine.py`. Three corrections to this sheet:

1. **Seann Shkell was wrong by this sheet's own rule.** The sheet says *Sk-* does not lenite, but
   the engine's blocker set was *c, p, t, m* and left out *k*, so the map got *Seann Shkell*.
   `S_BLOCKERS` now includes *k* (and *g*, for unconverted Scottish *sg-*), and the name is
   **Seann Skell**.
2. **Seann does not lenite d, t or s.** Real Gaelic writes *seann duine*, *seann taigh*: after a
   word ending in *n*, the dentals stay plain. So the substrate names are **Seann Dunn, Seann
   Tarr, Seann Toll** (and *Seann Chwen, Seann Bhral* are unchanged). `substrate_name()`
   applies this, and `finish_map.py` carried it into the burgs and the provinces named after them.
3. **"Always lenited" is a naming convention.** In everyday Ròdais an adjective after a masculine
   noun is not lenited (*baile gorm*). The map's *Baile ghorm, Cnoc bheag, Dùn thais* keep the
   always-lenited form as a fixed place-name pattern. `GRAMMAR.md` §4 says so, and
   `place_name()` builds it.

The engine's old self-test comment expected *Ciareas*; the correct output, *Ciaras*, is what the
sheet already said and what the engine produces.
