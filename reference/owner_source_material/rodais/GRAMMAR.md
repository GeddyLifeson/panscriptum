# Ròdais — grammar

The naming layer (`NAMING_LAYER.md`) covered lenition, broad/slender agreement, and the place-name
system. This file covers the rest of the language: sounds, spelling, nouns, articles, adjectives,
pronouns, prepositions, verbs, the copula, numbers and word order. Everything here is implemented
in `rodais_engine.py` and exercised by its self-test (`python rodais_engine.py`).

## 0. What Ròdais is

Ròdais is the Gaelic of the island of Rodos. Its grammar and its core vocabulary are Scottish
Gaelic's. It differs from standard Scottish Gaelic in three visible ways, all of them the "Irish
consonants, Scottish vowels" fusion the naming layer set out:

| Feature | Scottish Gaelic | Irish | **Ròdais** |
|---|---|---|---|
| Long vowels | grave: *mòr, sìth* | acute: *mór, síth* | **grave**: *mòr, sìth* |
| The cluster /sk/ | *sg*: *sgoil, uisge, sgeul* | *sc*: *scoil, uisce, scéal* | **sc**: *scoil, uisce, sceul* |
| "Thank you" | *tapadh leat* | *go raibh maith agat* | **gu robh math agad** |
| "City" | *baile mòr* | *cathair* | **cathair** |

Two of these are spelling rules and are applied mechanically by `normalize()`: any acute accent
becomes a grave, and *sg* becomes *sc* inside a word. So Ròdais can be written by anyone who
writes Scottish Gaelic, then normalized. The other two are word choices.

A few words exist only on Rodos: *Ròdos* (the island), *Ròdais* (the language), *Ròdach* (a
Ròdais person, pl. *Ròdaich*), *Tuathach* (a northerner, pl. *Tuathaich*), *Seann-Dhaoine* (the
Old Ones), *Rìoghachd Ròdais* (the kingdom), *Cathair dhearg* (the capital). *Gual* (coal) carries
extra weight: *fuil-ghuail* "coal-blood" is what the Ròdaich call the gift that sets them apart
from the Tuathaich.

## 1. Sounds and spelling

**Vowels.** Short *a e i o u*, long *à è ì ò ù*. Broad: *a o u à ò ù*. Slender: *e i è ì*.

**Caol le caol, leathan le leathan.** A consonant or consonant cluster inside one word has vowels
of the same class on both sides: *bris-ead-h*, *òl-adh*, *cuir-idh*, *seas-aidh*. That is why
most endings come in a broad and a slender form. `check_agreement()` enforces it; a handful of
real words break it and are listed in `AGREEMENT_EXCEPTIONS` (*esan, seo, an-seo, ceudna…*).

**Consonants.** Each consonant is broad (velarised) or slender (palatalised) according to the
vowel beside it. *h* after a consonant marks lenition:

| written | sound | example |
|---|---|---|
| bh, mh | v (often w/ nasal for mh) | *bhàta, mo mhàthair* |
| ch | x as in *loch* | *chaidh* |
| dh, gh (broad) | ɣ, a voiced *ch* | *dhubh* |
| dh, gh (slender) | j (as *y* in *yes*) | *dhèan* |
| fh | silent | *fhuair* ("hoo-ar") |
| ph | f | *phàigh* |
| sh, th | h | *shuidh, thuirt* |
| sc | sk (unaspirated) | *scoil* |

**Stress** falls on the first syllable of a word, except in a few adverbs that begin with a
particle: *a-màireach*, *an-diugh*, *an-dè*.

**Hyphens and apostrophes.** Written as in Scottish Gaelic: *t-* and *h-* and *n-* prefixes are
hyphenated (*an t-uisce, na h-eileanan, ar n-athair*); elision uses a plain apostrophe (*a'
bhean, dh'òl, m' athair*).

## 2. Mutations

Ròdais has two initial mutations.

**Lenition** (the main one). Rules, as `target > replacement / #_`:

    b > bh   c > ch   d > dh   f > fh   g > gh   m > mh   p > ph   s > sh   t > th

Not lenited: vowels; *l, n, r* (lenited in speech, never in writing); *sc, sp, st, sm* (and the
*sk-* of substrate roots: *Seann Skell*); and, after a word ending in *n* (the article, *seann*,
*aon*), words beginning *d, t, s* — the "dental block": *an taigh, seann duine, aon sagart*.
After *cha* only *d* and *t* are blocked.

Lenition is caused by: the possessives *mo, do, a* "his"; *glè* "very"; *ro* "too"; the past tense
and conditional of verbs; *cha* (except before *d, t*); a feminine noun after the article; an
adjective after a feminine noun; the vocative particle *a*; most simple prepositions (*de, do,
fo, mu, ro, tro, bho, gun, mar*); and the second element of a name (*Cathair mhòr*).

**Prefixed letters.** *h-* before a vowel after *a* "her", *na* (plural and feminine genitive
article), *le*, *gu*, *ri*, *ro*, *do* before a vowel-initial verbal noun: *a h-athair* "her
father", *na h-eileanan* "the islands". *t-* after the article (§3). *n-* after *ar* "our" and
*ur* "your (pl.)": *ar n-athair*.

## 3. Nouns and the article

Nouns are masculine or feminine. There is one article, "the"; there is no word for "a".
*Cù* "a dog", *an cù* "the dog".

**Nominative singular article:**

| noun begins with | masculine | feminine |
|---|---|---|
| vowel | **an t-**: *an t-uisce* | **an**: *an oidhche* |
| b, m, p | **am**: *am bàta* | **a'** + lenition: *a' bhean, a' mhàthair* |
| c, g | **an**: *an cù* | **a'** + lenition: *a' chaileag* |
| f | **am**: *am fear* | **an** + lenition: *an fhìrinn* |
| s + vowel, sl, sn, sr | **an**: *an sagart* | **an t-**: *an t-sràid, an t-sùil* |
| d, t, l, n, r, sc, sp, st, sm | **an** | **an**: *an deoch, an leabaidh* |

**Plural article:** *na* (*na h-* before a vowel): *na coin, na h-eileanan*.

**Genitive.** Used after a noun ("the X of the Y") and after compound prepositions. Singular
masculine: *an* + lenition (like the feminine nominative): *taigh a' bhàird* "the poet's house".
Singular feminine: *na* (*na h-* before vowel): *doras na h-eaglaise*. Plural: *nan* (*nam* before
b, f, m, p). A noun without an article in the genitive is lenited if masculine: *pìos arain*
"a piece of bread". The genitive form of the noun itself is lexical (usually slenderised for
masculines: *bàta → bàta*, *balach → balaich*; *-e* added for feminines: *sràid → sràide*); the
lexicon records it where it differs.

**Plurals** are lexical. Common patterns: *-an/-ean* (*bàta → bàtaichean*, *leabhar →
leabhraichean*, *craobh → craobhan*), slenderising (*balach → balaich*, *cat → cait*), *-(e)achan*
and irregulars (*bean → mnathan*, *duine → daoine*, *cù → coin*). After numerals the singular is
used (§10).

**Dative.** After a simple preposition with the article, masculine nouns take the forms of the
nominative; feminine nouns are slenderised where a form exists: *air a' bhòrd* "on the table",
*anns a' chidsin* "in the kitchen". After the article + preposition, nouns beginning with *b, c,
f, g, m, p* are lenited (both genders): *air a' bhòrd, bhon a' bhaile*.

## 4. Adjectives

Adjectives follow the noun: *taigh mòr* "a big house". After a feminine noun they are lenited:
*bean mhòr*. After a plural noun ending in a slender consonant they are lenited: *balaich bheaga*.
Plural adjectives add *-a/-e*: *taighean mòra*. A few adjectives go before the noun and lenite it:
*seann* "old" (*seann bhean*, but *seann taigh*, *seann duine* by the dental block), *deagh* "good", *droch* "bad", *fìor* "true, very".

**Place names are the exception.** On the map the qualifier is lenited after every generic,
masculine or feminine: *Baile ghorm, Cnoc bheag, Dùn thais*. In speech an adjective after a
masculine noun stays plain (*baile gorm*). Ròdais keeps the always-lenited form as a fixed naming
pattern, the way English keeps *Newcastle* as one word; `place_name()` builds it.

**Predicate adjectives** use *tha*: *Tha an taigh mòr* "the house is big". With *gu* before them
they become adverbs: *gu math* "well", *gu luath* "quickly". *Glè* "very" lenites: *glè mhath*.

**Comparison.** *nas* + comparative form (present): *nas motha* "bigger"; *na bu* (past):
*na bu mhotha*. "Than" is *na*. Superlative: *as* + comparative: *an taigh as motha* "the biggest
house". The comparative adds *-e/-a* and slenderises: *luath → luaithe*, *òg → òige*, *geal →
gile*. Irregulars: *math → fheàrr*, *dona → miosa*, *mòr → motha*, *beag → lugha*, *fada → fhaide*,
*furasta → fhasa*, *duilich → dorra*, *teth → teotha*.

## 5. Pronouns

| | plain | emphatic |
|---|---|---|
| I | mi | mise |
| you (sg., familiar) | thu (tu after *is* and in some verb forms) | thusa |
| he, it (m.) | e | esan |
| she, it (f.) | i | ise |
| we | sinn | sinne |
| you (pl. and polite) | sibh | sibhse |
| they | iad | iadsan |

*Sibh* is the polite singular as well as the plural, as in Scottish Gaelic.

**Possessives** come before the noun:

| | before a consonant | before a vowel |
|---|---|---|
| my | mo + lenition | m' (*m' athair*) |
| your (sg.) | do + lenition | d' (*d' athair*), t' before fh + vowel |
| his | a + lenition | a (*a athair*) |
| her | a | a h- (*a h-athair*) |
| our | ar | ar n- |
| your (pl.) | ur | ur n- |
| their | an (am before b, f, m, p) | an |

For many relationships (friends, possessions not part of oneself) Ròdais, like Scottish Gaelic,
prefers *aig* + article: *an taigh agam* "my house" (lit. the house at-me). Body parts, close
family and the like take the possessive: *mo cheann*, *mo mhàthair*.

## 6. Prepositions and prepositional pronouns

Simple prepositions fuse with a following personal pronoun:

| | aig "at" | air "on" | do "to" | le "with" | ann "in" | bho "from" | ri "against, to" | de "of, off" | à "out of" | fo "under" | mu "about" |
|---|---|---|---|---|---|---|---|---|---|---|---|
| mi | agam | orm | dhomh | leam | annam | bhuam | rium | dhìom | asam | fodham | umam |
| thu | agad | ort | dhut | leat | annad | bhuat | riut | dhìot | asad | fodhad | umad |
| e | aige | air | dha | leis | ann | bhuaithe | ris | dheth | às | fodha | uime |
| i | aice | oirre | dhi | leatha | innte | bhuaipe | rithe | dhith | aisde | foidhpe | uimpe |
| sinn | againn | oirnn | dhuinn | leinn | annainn | bhuainn | rinn | dhinn | asainn | fodhainn | umainn |
| sibh | agaibh | oirbh | dhuibh | leibh | annaibh | bhuaibh | ribh | dhibh | asaibh | fodhaibh | umaibh |
| iad | aca | orra | dhaibh | leotha | annta | bhuapa | riutha | dhiubh | asta | fodhpa | umpa |

**Possession** is "X is at Y": *Tha cù agam* "I have a dog". **Feelings and states** are "X is on
Y": *Tha an t-acras orm* "I am hungry", *Tha an cnatan oirre* "she has a cold". **Liking** uses
*le* with the copula: *Is toil leam cofaidh* "I like coffee". **Ability**: *Is urrainn dhomh* "I
can". **Must**: *Feumaidh mi* or *Tha agam ri* + verbal noun.

*Ann* "in" before a noun is *ann an* (*ann am* before b, f, m, p): *ann an taigh*, *ann am
bàta*. With the article: *anns an taigh, anns a' bhàta*.

**Compound prepositions** take the genitive: *air beulaibh an taighe* "in front of the house",
*air cùlaibh, ri taobh, an aghaidh, airson, mu dheidhinn, tro mheadhan*. With a pronoun they
take the possessive: *mu mo dheidhinn* "about me".

## 7. Verbs

Ròdais verbs are cited in two forms: the **root** (the imperative singular: *seas* "stand!")
and the **verbal noun** (*seasamh*). The verbal noun is lexical and is what the lexicon gives
for "to X".

### 7.1 Tenses of a regular verb

Every tense has an **independent** form (used alone, at the start of a sentence) and a
**dependent** form (used after the particles *cha, an, nach, gun, mura, ma*).

| | independent | dependent |
|---|---|---|
| **past** | lenited root; *dh'* before a vowel or *fh*: *sheas, dh'òl, dh'fhàg* | *do* + past: *an do sheas thu? cha do dh'òl mi* |
| **future** | root + *-idh* (slender) / *-aidh* (broad): *seasaidh, cuiridh, òlaidh* | bare root: *cha seas, an òl thu?* |
| **conditional** | lenited root + *-eadh/-adh*: *sheasadh, dh'òladh* | root + *-eadh/-adh*: *cha seasadh* |
| conditional, 1st sg. | lenited root + *-inn/-ainn*: *sheasainn* | *cha seasainn* |
| **imperative** | root: *seas!*; pl./polite root + *-ibh/-aibh*: *seasaibh!* | negative *na* + root: *na seas!* |
| **relative future** | root + *-eas/-as*: *an duine a sheasas* "the man who will stand" | |

The ending chooses broad or slender by the last vowel of the root, the same rule as the river
suffix (`attach_suffix`). Verbs whose root ends in *-ich* (*ceannaich* "buy") are slender:
*cheannaich, ceannaichidh, cheannaicheadh*.

The **present** has no simple form. It is built with *bi* + *ag* + verbal noun (*a'* before a
consonant): *Tha mi a' seasamh* "I am standing", *Tha i ag òl* "she is drinking". The
**perfect** uses *air*: *Tha mi air seasamh* "I have stood". A **habitual present** uses the future:
*Òlaidh mi cofaidh gach latha* "I drink coffee every day".

The **object** of a progressive goes in the genitive after the verbal noun: *Tha mi ag òl
cofaidh*. A pronoun object becomes a possessive before the verbal noun: *Tha mi ga fhaicinn* "I
see him" (*ga* = *aig a*), *Tha e gam fhaicinn* "he sees me", *Tha i gad fhaicinn* "she sees
you". The full table is `OBJECT_PARTICLES` in the engine.

### 7.2 Particles

| particle | use | effect |
|---|---|---|
| **cha** / **chan** | not | *cha* lenites, except *d* and *t*: *cha bhris, cha sheas* (the proverb *cha sheas poca falamh*), but *cha dèan, cha tèid*; *chan* before a vowel and before lenited *f*: *chan òl, chan fhaic* |
| **an** / **am** | question | *am* before b, f, m, p: *am faic thu?* |
| **nach** | negative question; "that ... not" | |
| **gun** / **gum** | that | *gum* before b, f, m, p |
| **ma** | if (real) | takes the independent form: *ma thig e* |
| **nan** / **nam** | if (unreal) | with the conditional |
| **mura** | if not | dependent form |
| **a** | who, which (relative) | lenites; takes the relative future |
| **na** | don't | *na seas!* |

**Yes and no.** Ròdais has no words for yes and no. An answer repeats the verb: *An robh thu
ann? — Bha.* "Were you there? — (I) was." / *Cha robh.* In the word list, *Seadh* ("it is so") stands
for "yes" and *Chan eil* for "no", the forms a Ròdach would give to a bare yes/no question with no
verb to echo.

### 7.3 The verb *bi* "be"

| | independent | dependent | negative |
|---|---|---|---|
| present | **tha** | **bheil** (*a bheil thu?*) | **chan eil** |
| past | **bha** | **robh** (*an robh?*) | **cha robh** |
| future | **bidh** | **bi** (*am bi?*) | **cha bhi** |
| conditional | **bhiodh** (*bhithinn* 1sg.) | **biodh** | **cha bhiodh** |
| relative future | **bhios** | | |
| imperative | **bi!**, **bithibh!** | | **na bi** |
| verbal noun | **bhith** (*a bhith*) | | |

*Bi* is for existence, location and states: *Tha mi scìth* "I am tired" (Scottish *sgìth*),
*Tha e anns a' chidsin* "he is in the kitchen".

### 7.4 The copula *is*

The copula links two nouns, or a noun and a pronoun, and fronts things for emphasis.

| | positive | question | negative | neg. question |
|---|---|---|---|---|
| present | **is** / **'s** | **an e** / **am** | **chan e**, **cha** | **nach e** |
| past/conditional | **bu** (+ lenition) | **am bu** | **cha bu** | **nach bu** |

Identity: *Is e tidsear a th' innte* "she is a teacher" (lit. it is a teacher that is in her);
or, with a definite noun, *Is i Aisling an ceannard* "Aisling is the leader". Emphasis: *Is e
Cian a rinn e* "it was Cian who did it". Fixed phrases: *is toil leam* (I like), *is fheàrr
leam* (I prefer), *is urrainn dhomh* (I can), *is dòcha* (perhaps), *is e do bheatha* (you're
welcome).

### 7.5 Irregular verbs

Ten verbs are irregular, exactly Scottish Gaelic's. `IRREGULAR` in the engine holds every form.

| root | meaning | past | dep. past | future | dep. future | conditional | verbal noun |
|---|---|---|---|---|---|---|---|
| abair | say | thuirt | tuirt | their | abair | theireadh | ràdh |
| beir | catch, bear | rug | do rug | beiridh | beir | bheireadh | breith |
| cluinn | hear | chuala | cuala | cluinnidh | cluinn | chluinneadh | cluinntinn |
| dèan | do, make | rinn | do rinn | nì | dèan | dhèanadh | dèanamh |
| faic | see | chunnaic | faca | chì | faic | chitheadh | faicinn |
| faigh | get | fhuair | d' fhuair | gheibh | faigh | gheibheadh | faighinn |
| rach | go | chaidh | deach | thèid | tèid | rachadh | dol |
| ruig | reach | ràinig | do ràinig | ruigidh | ruig | ruigeadh | ruigsinn |
| thig | come | thàinig | tàinig | thig | tig | thigeadh | tighinn |
| thoir | give, take | thug | tug | bheir | toir | bheireadh | toirt |

## 8. Word order

Verb – subject – object – everything else:

    Chunnaic   Cian   an   long    ann an Cathair dhearg   an-dè.
    saw        Cian   the  ship    in Cathair dhearg        yesterday
    "Cian saw the ship in Cathair dhearg yesterday."

    Tha   Aisling   a'  coiseachd   dhan   bhaile.
    is    Aisling   at  walking     to-the town
    "Aisling is walking to the town."

Questions and negatives put a particle in front of the verb and nothing else moves:
*Am faca Cian an long?* / *Chan fhaca Cian an long.* Relative clauses and emphasis use the
copula to front the stressed part (§7.4). Adverbs of time usually close the sentence.

`clause()` in the engine builds VSO clauses from a verb, a tense, a subject and an object, with
negation and questions, so these forms can be generated and checked rather than hand-spelled.

## 9. Politeness and address

*Sibh* for anyone older, anyone of rank and any stranger; *thu* for friends, children and
animals. The vocative particle *a* lenites and slenderises a masculine name: *a Chiain!* "Cian!",
*a Dhubhain!*; a feminine name is only lenited: *a Mhàiri!*, and a vowel-initial name is
unchanged: *a Aisling!*

## 10. Numbers

| | counting | with a noun |
|---|---|---|
| 1 | a h-aon | aon + lenition (*aon chù*) |
| 2 | a dhà | dà + lenition + singular (*dà chù*) |
| 3 | a trì | trì (*trì coin*) |
| 4 | a ceithir | ceithir |
| 5 | a còig | còig |
| 6 | a sia | sia |
| 7 | a seachd | seachd |
| 8 | a h-ochd | ochd |
| 9 | a naoi | naoi |
| 10 | a deich | deich |
| 11 | a h-aon deug | aon ... deug (*aon chù deug*) |
| 12 | a dhà dheug | dà ... dheug |
| 20 | fichead | fichead (*fichead cù*) |
| 30 | trithead | |
| 40 | ceathrad | |
| 50 | caogad | |
| 100 | ceud | |
| 1000 | mìle | |

Ròdais counts in tens (the modern decimal system); the older vigesimal forms (*dà fhichead* "40")
are understood and used for ages and in old texts. Ordinals: *a' chiad* "first" (lenites),
*an dàrna*, *an treas*, *an ceathramh*, *an còigeamh*.

## 11. Time and weekdays

*an-diugh* today, *a-màireach* tomorrow, *an-dè* yesterday, *a-nochd* tonight, *a-nis* now,
*an-uiridh* last year. Days: *Diluain, Dimàirt, Diciadain, Diardaoin, Dihaoine, Disathairne,
Didòmhnaich*. Months: *am Faoilleach, an Gearran, am Màrt, an Giblean, an Cèitean, an t-Ògmhios,
an t-Iuchar, an Lùnastal, an t-Sultain, an Dàmhair, an t-Samhain, an Dùbhlachd*.

## 12. Writing Ròdais from Scottish Gaelic

1. Write standard Scottish Gaelic (Gaelic Orthographic Conventions spelling).
2. Use *cathair* for "city" and *gu robh math agad / agaibh* for "thank you".
3. Run the text through `normalize()`: acute to grave, *sg* to *sc*, curly apostrophes to straight.
4. Run `check_agreement()` over each word; anything it flags is either a typo or belongs in
   `AGREEMENT_EXCEPTIONS`.
