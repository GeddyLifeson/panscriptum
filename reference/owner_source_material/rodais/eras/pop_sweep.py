"""
pop_sweep.py -- carry the owner's decision of 2026-09-25 on the island's numbers into the map and the text, and log it.

The owner: Dia-thìr, about the size of Northern Ireland (some 5,340 square miles since the rescale), should have
about as many people as Northern Ireland, some 1.8 million in the present day (DE 27), not the 35 million the
generator gave it; and every figure everywhere must match.

  1. The map. Azgaar keeps populations in units; units.population.scale says how many people one unit is. It goes
     from 1,000 to 50 (legendarium/reconcile/place.json, the last layer of map_reconcile.py), so every population
     the map shows is a twentieth of what it was and the relative sizes stay as they are: 1,771,220 people on the
     land, 1,770,774 within the shires, 247,732 of them in towns (one in seven, as before). The urbanization rate
     stays 1. The regiments are cut to three tenths (a standing army of some 3,300 men and 23 guns for 1.8 million
     people, where a twentieth would leave 550); the four fleets keep their six hulls.
  2. The text. Every figure that follows from the map's population is scaled with it: the kingdom's heads and the
     peoples' counts, the faiths' people, the town sizes of the gazetteer and the appendix tables, the windy coast's
     tally, the musters. The Treasury's roll stays at 9,568 purses (the map's treasury does not change): the head-due
     is now eighteen purses on every five thousand heads, so 1,770,800 heads still yield 6,375 purses.
     Deaths counted in a single town are scaled where the town, at the size it had in its age, could not have held
     them; counts that were small beside their town, and the figures of the oldest ages (the tellings count houses,
     spears and knots, and none of them came from the map), are kept.
  3. The era specs. The older ages were drawn as shares of the present (eras/specs_draft/tools/common.py). With the
     present twenty times smaller, the shares are redrawn so that every age stays between the Age of Ailean, whose
     figures come from the tellings, and the present: III 0.2, IV 0.35, V 0.6, VI 0.85 of the present-day towns
     (they were 0.035, 0.12, 0.45, 0.85 of the old). The towns the annals give a size to are scaled by the same
     change (never above their present size), the clamps with them, and each age's kinds (hamlet, village, town...)
     are read as before. The engine writes populations in the master's units (50 people to the unit).

    python eras/pop_sweep.py            # apply, then write eras/POP_LOG.md
    python eras/pop_sweep.py --check    # list what would change, change nothing

Idempotent: text that already reads as the new form is left alone; the map edits and the era tools' figures are
written once. Files other hands are editing at the same time (the books) are read and written back one at a time,
immediately, with only these replacements. Built files are not edited here; they are rebuilt (LEGENDARIUM.md,
annals_dated.json, world.json, the Atlas, the era master annals are seeded copies and are swept like the annals).
"""
import glob
import json
import os
import re
import sys
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(ROOT, 'eras', 'POP_LOG.md')
MAP = os.path.join(ROOT, 'Diathir_Atlas', 'Diathir.map')
PLACE = os.path.join(ROOT, 'legendarium', 'reconcile', 'place.json')
PREVIEWS = os.path.join(ROOT, 'legendarium', 'town_previews.json')
TOOLS = os.path.join(ROOT, 'eras', 'specs_draft', 'tools')

OLD_RATE, RATE = 1000, 50           # people to the map's population unit
MIL = 0.3                           # the regiments' share of their old strength

TARGETS = [
    'legendarium/book/*.md', 'legendarium/appendices/*.md', 'legendarium/appendices/houses.json',
    'legendarium/annals/age_*.json', 'legendarium/gazetteer/*.json', 'legendarium/reconcile/*.json',
    'legendarium/reconcile/INTEGRATION.md', 'legendarium/burg_features.json', 'legendarium/canon_by_age.json',
    'legendarium/chronicle_canon.json', 'legendarium/PLACE_FACTS.txt', 'legendarium/README.md', 'legendarium/BRIEF.md',
    'eras/specs_draft/tools/*.py', 'eras/specs_draft/README.md', 'eras/THREADS.json', 'eras/PEOPLE.json',
    'eras/NAMES.json', 'eras/WRITERS_GUIDE.md', 'eras/age_*/annals/*_master.json', 'eras/engine/SPEC.md',
    'eras/maps/README.md', 'TEXTS.json', 'atlas_template.html', 'language_template.html', 'README.md',
]

# ---------------------------------------------------------------------------------------------- the map's numbers
_L = open(MAP, encoding='utf-8', newline='').read().split('\r\n')
_BURGS = {b['i']: b for b in json.loads(_L[15]) if isinstance(b, dict) and b.get('i') and not b.get('removed')}


def people(i):
    """A burg's people at the new scale."""
    return int(round(_BURGS[i]['population'] * RATE))


# the regiments as they stood (record 14, state 1): the generator's strengths, archers renamed riflemen
REGIMENTS_OLD = [
    {'infantry': 826, 'cavalry': 581, 'riflemen': 398, 'artillery': 13},
    {'infantry': 862, 'riflemen': 487, 'cavalry': 234, 'artillery': 11},
    {'riflemen': 314, 'artillery': 7, 'infantry': 732, 'cavalry': 302},
    {'infantry': 684, 'cavalry': 266, 'artillery': 7, 'riflemen': 364},
    {'infantry': 614, 'cavalry': 360, 'artillery': 14, 'riflemen': 319},
    {'infantry': 497, 'cavalry': 194, 'artillery': 8, 'riflemen': 308},
    {'infantry': 437, 'cavalry': 224, 'riflemen': 230, 'artillery': 5},
    {'infantry': 474, 'riflemen': 281, 'cavalry': 93, 'artillery': 4},
    {'riflemen': 321, 'infantry': 451, 'artillery': 10, 'cavalry': 68},
]


def scale_units(u):
    return {k: max(1, int(round(v * MIL + 1e-9))) for k, v in u.items()}


REGIMENTS_NEW = [scale_units(u) for u in REGIMENTS_OLD]
TOT_OLD = {k: sum(u[k] for u in REGIMENTS_OLD) for k in ('infantry', 'cavalry', 'riflemen', 'artillery')}
TOT_NEW = {k: sum(u[k] for u in REGIMENTS_NEW) for k in ('infantry', 'cavalry', 'riflemen', 'artillery')}

ONES = ['', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten', 'eleven', 'twelve',
        'thirteen', 'fourteen', 'fifteen', 'sixteen', 'seventeen', 'eighteen', 'nineteen']
TENS = ['', '', 'twenty', 'thirty', 'forty', 'fifty', 'sixty', 'seventy', 'eighty', 'ninety']


def words(n):
    if n < 20:
        return ONES[n]
    if n < 100:
        return TENS[n // 10] + ('-' + ONES[n % 10] if n % 10 else '')
    raise ValueError(n)


def fmt(n):
    return format(n, ',')


def unit_phrase(u):
    guns = u['artillery']
    return 'musters %d foot, %d horse, %d riflemen and %d gun%s' % (u['infantry'], u['cavalry'], u['riflemen'], guns,
                                                                    '' if guns == 1 else 's')


# ---------------------------------------------------------------------------------------------- the text rules
HEADS, KINGDOM, TOWNS = 'heads', 'kingdom', 'towns'
DEAD, MUSTER, ERAS = 'dead', 'muster', 'eras'

RULES = [
    # ------------------------------------------------------------------ the kingdom's heads and the Treasury
    (HEADS, 'eighteen purses on every hundred thousand heads', 'eighteen purses on every five thousand heads'),
    (HEADS, 'eighteen purses per hundred thousand heads', 'eighteen purses per five thousand heads'),
    (HEADS, 'The kingdom counted 35,415,000 heads for the head-due', 'The kingdom counted 1,770,800 heads for the head-due'),
    (HEADS, 'Together the two peoples number some 35,415,000 within the shires, one in seven of them in a town.',
            'Together the two peoples number some 1,770,800 within the shires, one in seven of them in a town.'),
    (HEADS, '| 4,411,000 | 27,224,000 |', '| 220,600 | 1,361,200 |'),
    (HEADS, '| 543,000 | 3,237,000 within the shires;', '| 27,200 | 161,800 within the shires;'),
    (HEADS, 'some 543,000 people in them.', 'some 27,200 people in them.'),
    (HEADS, 'The Moot\'s tallies put them near nine thousand, a figure the royal clerks do not accept.',
            'The Moot\'s tallies put them near four hundred and fifty, a figure the royal clerks do not accept.'),
    (HEADS, 'The windy coast keeps, by the Moot\'s tally, about nine thousand people,',
            'The windy coast keeps, by the Moot\'s tally, about four hundred and fifty people,'),
    (HEADS, 'Sealers, fowlers and herders, near nine thousand by the Moot\'s tally;',
            'Sealers, fowlers and herders, near four hundred and fifty by the Moot\'s tally;'),
    # ------------------------------------------------------------------ the faiths, counted by the people in their towns
    (KINGDOM, 'Counted by the people in their towns, the Old Faith comes first by far, at nearly three million two '
              'hundred thousand. The Old Spirits come next, at a little over one million two hundred thousand, and the '
              'Church holds some five hundred and forty thousand. Among the orders Macha\'s is the largest in people, '
              'at nearly one million two hundred thousand, close behind the Old Spirits,',
              'Counted by the people in their towns, the Old Faith comes first by far, at nearly a hundred and sixty '
              'thousand. The Old Spirits come next, at a little over sixty thousand, and the Church holds some '
              'twenty-seven thousand. Among the orders Macha\'s is the largest in people, at nearly sixty thousand, '
              'close behind the Old Spirits,'),
    (KINGDOM, 'Cathair dhearg is counted at 10,274;', 'Cathair dhearg is counted at 514;'),
    (KINGDOM, 'The capital and every city of more than twenty thousand people, largest first.',
              'The capital and every city of more than a thousand people, largest first.'),
    # ------------------------------------------------------------------ the regiments
    (MUSTER, 'The regimental rolls of the present year count 5,577 foot, 3,022 riflemen and 2,322 horse in the nine '
             'regiments, with seventy-nine guns. The first regiment is the largest, at 1,818 men, and the eighth and '
             'ninth are the smallest, at about 850 each.',
             'The regimental rolls of the present year count %s foot, %s riflemen and %d horse in the nine regiments, '
             'with %s guns. The first regiment is the largest, at %d men, and the eighth and ninth are the smallest, '
             'at about %d each.' % (fmt(TOT_NEW['infantry']), fmt(TOT_NEW['riflemen']), TOT_NEW['cavalry'],
                                   words(TOT_NEW['artillery']), sum(REGIMENTS_NEW[0].values()),
                                   round((sum(REGIMENTS_NEW[7].values()) + sum(REGIMENTS_NEW[8].values())) / 10.0) * 5)),
]
# each regiment's note (reconcile/prose.json, the map's record 14)
for _o, _n in zip(REGIMENTS_OLD, REGIMENTS_NEW):
    RULES.append((MUSTER, 'In DE 27 it %s.' % unit_phrase(_o), 'In DE 27 it %s.' % unit_phrase(_n)))

RULES += [
    # ------------------------------------------------------------------ the town tables (appendix F; J rounds to tens)
    (TOWNS, '| An Creideamh Sean (Òrd Mhanannain) | 74,120 |', '| An Creideamh Sean (Òrd Mhanannain) | %s |' % fmt(people(489))),
    (TOWNS, '| An Creideamh Sean (Òrd Bhrìde) | 57,907 |', '| An Creideamh Sean (Òrd Bhrìde) | %s |' % fmt(people(431))),
    (TOWNS, '| Ros dhomhain | An Creideamh Sean (Òrd Mhacha) | 51,589 |', '| Ros dhomhain | An Creideamh Sean (Òrd Mhacha) | %s |' % fmt(people(27))),
    (TOWNS, '| Na Seann Spioradan | 49,681 |', '| Na Seann Spioradan | %s |' % fmt(people(110))),
    (TOWNS, '| An Creideamh Sean (Òrd an t-Seabhaig) | 49,661 |', '| An Creideamh Sean (Òrd an t-Seabhaig) | %s |' % fmt(people(20))),
    (TOWNS, '| Cathair mhòr | An Creideamh Sean (Òrd Mhacha) | 49,298 |', '| Cathair mhòr | An Creideamh Sean (Òrd Mhacha) | %s |' % fmt(people(23))),
    (TOWNS, '| An Creideamh Sean (Scoiltean nan Draoidhean) | 42,649 |', '| An Creideamh Sean (Scoiltean nan Draoidhean) | %s |' % fmt(people(475))),
    (TOWNS, '| Na Seann Spioradan | 42,136 |', '| Na Seann Spioradan | %s |' % fmt(people(395))),
    (TOWNS, '| An Eaglais | 42,002 |', '| An Eaglais | %s |' % fmt(people(95))),
    (TOWNS, '| An Eaglais (Eaglais nan Tuathach) | 40,740 |', '| An Eaglais (Eaglais nan Tuathach) | %s |' % fmt(people(209))),
    (TOWNS, '| An Eaglais | 32,420 |', '| An Eaglais | %s |' % fmt(people(143))),
    (TOWNS, '| An Eaglais (the vigil of the Grey Night) | 27,319 |', '| An Eaglais (the vigil of the Grey Night) | %s |' % fmt(people(305))),
    (TOWNS, '| An Eaglais | 25,112 |', '| An Eaglais | %s |' % fmt(people(142))),
]
# appendix J: the capital and the cities of more than a thousand, to the nearest ten
for _i, _old in [(19, '10,300'), (489, '74,100'), (27, '51,600'), (23, '49,300'), (365, '35,900'), (166, '34,900'),
                 (77, '34,200'), (30, '32,300'), (26, '29,400'), (422, '25,700'), (17, '24,000'), (63, '23,800'),
                 (315, '22,600'), (132, '22,100'), (255, '21,100'), (297, '20,900')]:
    _new = int(round(_BURGS[_i]['population'] * RATE / 10.0)) * 10
    RULES.append((TOWNS, '{{place:burg:%d}} | %%s | %s |' % (_i, _old), '{{place:burg:%d}} | %%s | %s |' % (_i, fmt(_new))))

RULES += [
    # ------------------------------------------------------------------ the gazetteer's towns, at their new sizes
    (TOWNS, 'which has never numbered more than a thousand or so,', 'which has never numbered more than fifty or so,'),
    (TOWNS, 'though it holds only a few thousand people,', 'though it holds only a hundred or so people,'),
    (TOWNS, 'a walled port town of nearly twenty thousand', 'a walled port town of nearly a thousand'),
    (TOWNS, 'a town of nearly forty thousand on the Abhainn ìseal', 'a town of nearly two thousand on the Abhainn ìseal'),
    (TOWNS, 'a port of nearly forty thousand', 'a port of nearly two thousand'),
    (TOWNS, 'It has never grown past seven hundred people.', 'It has never grown past thirty-five people.'),
    (TOWNS, 'a village of twenty-five thousand', 'a village of some twelve hundred'),
    (TOWNS, 'Fewer than seven hundred people live there now, among the spoil heaps.',
            'Fewer than forty people live there now, among the spoil heaps.'),
    (TOWNS, 'a hundred people among the spoil heaps', 'some thirty people among the spoil heaps'),
    (TOWNS, 'It is a large village now, of nearly ten thousand.', 'It is a large village now, of nearly five hundred.'),
    (TOWNS, 'It is a large town of twenty thousand.', 'It is a large town of a thousand.'),
    (TOWNS, 'a city of more than twenty-five thousand.', 'a city of more than twelve hundred.'),
    (TOWNS, 'It is a town of more than twenty thousand, with grain-halls',
            'It is a town of more than a thousand, with grain-halls'),
    (TOWNS, 'a town of nearly sixty thousand whose harbour', 'a town of nearly three thousand whose harbour'),
    (TOWNS, 'the seat of its province, a town of twelve thousand.', 'the seat of its province, a town of six hundred.'),
    (TOWNS, 'It is a port town of nearly nine thousand and the older of the two',
            'It is a port town of some four hundred and thirty and the older of the two'),
    (TOWNS, 'with fourteen thousand people.', 'with seven hundred people.'),
    (TOWNS, 'a town of twenty-seven thousand in fact', 'a town of some thirteen hundred in fact'),
    (TOWNS, 'It is small, fewer than a thousand people, and its inn', 'It is small, fewer than fifty people, and its inn'),
    (TOWNS, 'A farming village of six thousand just south', 'A farming village of three hundred just south'),
    (TOWNS, 'It is small, fewer than eight hundred people.', 'It is small, fewer than forty people.'),
    (TOWNS, 'It is a small place of fewer than two thousand.', 'It is a small place of fewer than a hundred.'),
    (TOWNS, 'It is a large town of nearly seventeen thousand,', 'It is a large town of more than eight hundred,'),
    (TOWNS, 'It is a town of five thousand.', 'It is a town of some two hundred and sixty.'),
    (TOWNS, 'a temple village of Macha of twenty-four thousand', 'a temple village of Macha of some twelve hundred'),
    (TOWNS, 'a church village of twenty-four thousand', 'a church village of some twelve hundred'),
    (TOWNS, 'the eastern mining district, a town of nearly nineteen thousand.',
            'the eastern mining district, a town of nearly a thousand.'),
    (TOWNS, 'It is a town of eleven thousand.', 'It is a town of some five hundred and seventy.'),
    (TOWNS, 'It is a fishing village of three thousand.', 'It is a fishing village of a hundred and fifty.'),
    (TOWNS, 'is a town of twenty thousand built around', 'is a town of a thousand built around'),
    (TOWNS, 'Fewer than a thousand people live there now.', 'Fewer than fifty people live there now.'),
    (TOWNS, 'though it holds under three thousand people.', 'though it holds under a hundred and fifty people.'),
    (TOWNS, 'It is a town of nearly nine thousand and the market', 'It is a town of some four hundred and fifty and the market'),
    (TOWNS, 'a river port of more than forty thousand', 'a river port of more than two thousand'),
    (TOWNS, 'harbour town of forty thousand crowned', 'harbour town of two thousand crowned'),
    (TOWNS, 'a mill town of fourteen thousand', 'a mill town of some seven hundred'),
    (TOWNS, 'It has fewer than a thousand people.', 'It has fewer than fifty people.'),
    (TOWNS, 'It is a town of nearly ten thousand.', 'It is a town of nearly five hundred.'),
    (TOWNS, 'It is a small village of fewer than two thousand.', 'It is a small village of fewer than a hundred.'),
    (TOWNS, 'a city of seventy-four thousand and the largest place', 'a city of some three thousand seven hundred and the largest place'),
    (TOWNS, 'a town of twenty thousand at a ford', 'a town of a thousand at a ford'),
    (TOWNS, 'It is small, fewer than seven hundred people.', 'It is small, fewer than forty people.'),
    (TOWNS, 'a white town of nine thousand', 'a white town of some four hundred and seventy'),
    (TOWNS, 'It is a town of three thousand in the eastern mining district.',
            'It is a town of a hundred and fifty in the eastern mining district.'),
    (TOWNS, 'It is a port town of four thousand.', 'It is a port town of two hundred.'),
    (TOWNS, 'a town of ten thousand that grew', 'a town of five hundred that grew'),
    (TOWNS, 'a town of nearly five thousand, of quarrymen', 'a town of some two hundred and thirty, of quarrymen'),
    (TOWNS, 'a town of thirty-four thousand with a citadel', 'a town of some seventeen hundred with a citadel'),
    (TOWNS, 'It has fewer than seven hundred people and lives on the garrison.',
            'It has fewer than forty people and lives on the garrison.'),
    (TOWNS, 'its twelve thousand people guard', 'its six hundred people guard'),
    (TOWNS, 'population 74,120 is the largest of all 505 burgs', 'population 3,706 is the largest of all 505 burgs'),
    # ------------------------------------------------------------------ deaths counted in one town, at the town's size in its age
    # (the age's share of the present: IV 0.35, V 0.6, VI 0.85; the counts keep their share of the town)
    (DEAD, 'kills some two hundred before it burns out', 'kills some thirty before it burns out'),
    (DEAD, 'A coughing sickness killed some two hundred at', 'A coughing sickness killed some thirty at'),
    (DEAD, 'A spotted fever kills some three hundred at Inis chrom', 'A spotted fever kills some forty at Inis chrom'),
    (DEAD, 'a spotted fever some three hundred at {{place:burg:92}}', 'a spotted fever some forty at {{place:burg:92}}'),
    (DEAD, 'a spotted fever killed some three hundred at Inis chrom', 'a spotted fever killed some forty at Inis chrom'),
    (DEAD, 'The Mission counts four hundred and six dead.', 'The Mission counts twenty-seven dead.'),
    (DEAD, 'The Mission counted four hundred and six dead.', 'The Mission counted twenty-seven dead.'),
    (DEAD, 'the Mission counts four hundred and six\ndead', 'the Mission counts twenty-seven\ndead'),
    (DEAD, 'killed four hundred and six by the Mission\'s count', 'killed twenty-seven by the Mission\'s count'),
    (DEAD, '| 406 by the Mission;', '| 27 by the Mission;'),
    (DEAD, 'the pox killed 406.', 'the pox killed 27.'),
    (DEAD, 'kept the dead below two hundred', 'kept the dead below fifteen'),
    (DEAD, 'keeping the dead under two hundred', 'keeping the dead under fifteen'),
    (DEAD, 'Two hundred and sixty die.', 'Seventeen die.'),
    (DEAD, 'and two hundred and sixty died there.', 'and seventeen died there.'),
    (DEAD, 'killed two hundred and sixty at Baile Mòr ruadh', 'killed seventeen at Baile Mòr ruadh'),
    (DEAD, '| 260 of drought-fever at Baile Mòr ruadh |', '| 17 of drought-fever at Baile Mòr ruadh |'),
    (DEAD, 'puts the dead at Doire ghlas above two hundred', 'puts the dead at Doire ghlas above ten'),
    (DEAD, 'more than two hundred were buried that winter', 'more than ten were buried that winter'),
    (DEAD, '| above 200 (Tuathaich memory) |', '| above 10 (Tuathaich memory) |'),
    (DEAD, 'a little over nine hundred', 'a little over forty'),
    (DEAD, 'Twenty-three townsfolk die.', 'Three townsfolk die.'),
    (DEAD, 'and burned the town behind it, killing twenty-three', 'and burned the town behind it, killing three'),
    (DEAD, '| Twenty-three townsfolk dead |', '| Three townsfolk dead |'),
    (DEAD, 'and twenty-three townsfolk died.', 'and three townsfolk died.'),
    (DEAD, 'the fishing town behind it set burning; twenty-three dead', 'the fishing town behind it set burning; three dead'),
    (DEAD, '| a little over 900 |', '| a little over 40 |'),
    # ------------------------------------------------------------------ the eras' notes on their own populations
    (ERAS, '- **Ages III–VI** default to the master population × 0.035, 0.12, 0.45 or 0.85, clamped per age, with overrides\n'
           '  for towns the annals give a size to.',
           '- **Ages III–VI** default to the master population × 0.2, 0.35, 0.6 or 0.85, clamped per age, with overrides\n'
           '  for towns the annals give a size to (never above the town\'s present size). The master counts 50 people to\n'
           '  its population unit, some 1.8 million on the island (see `../POP_LOG.md`); the shares keep every age between\n'
           '  the Age of Ailean, whose figures come from the tellings, and the present. Each age\'s kinds are read from its\n'
           '  populations as they were when the shares were first set (`KIND_SCALE` in `tools/common.py`).'),
    (ERAS, '- Populations are in Azgaar\'s units: a burg\'s `population` is in thousands (8.6 = 8,600).',
           '- Populations are in Azgaar\'s units: a burg\'s `population` times the master\'s `units.population.scale`\n'
           '  (50 people to the unit since the owner\'s decision of 2026-09-25) is its people (8.6 = 430). The drafts give\n'
           '  people; `convert_draft.py` divides by the master\'s scale.'),
    (ERAS, 'distance\nscale 0.14 mi/px;', 'distance\nscale 0.14 mi/px; population scale 50 people to the unit (some 1.8 million);'),
]

# ----------------------------------------------------------------------------------- reviewed and kept (for the log)
KEPT = [
    ('the tellings\' counts of the Ancient Age and the Age of Ailean (four hundred with their beasts in the cistern '
     'fort, three thousand spears, some four hundred of Ailean\'s blood in the river, nine hundred knots on the cord, '
     'three thousand strokes on the counting wall)', 'the figures of the tellings; none came from the map, and the era '
     'drafts keep Age II as the tellings give it (some 110,000 on the island)'),
    ('the census of hands, eleven thousand four hundred households holding the right and some two thousand refused '
     '(II-0143, book III)', 'fits the Holy Age redrawn at a fifth of the present, some 300,000 people'),
    ('some three hundred dead at the ford of Àth shean (III-0106, B, C, book IV)', 'a battle of the whole realm, some '
     '570,000 people in the Age of Sundering; not a town\'s count'),
    ('some four thousand people on the salt flats of Ros fhionn in a single day (Age IV)', 'the great fair drew from '
     'the whole island (some 570,000)'),
    ('the strangers\' fever: ninety-one Dia-thìrich and eleven humans (IV-0034)', 'spread down the whole west coast; '
     'small beside it'),
    ('eleven, fourteen, seven and thirty-one dead in the galleries, eighteen and twenty-three drowned by Am Fuath Mòr '
     'and the storm at Baile ghorm, five killed in the first bloodshed', 'counts of a gallery, a boat or a street, '
     'small beside their towns'),
    ('the human families left on the island, a few thousand in all, behind the walls of Ros bheag and marched north '
     '(IV-0363, V truce; era Age V refugee camp of 3,000)', 'the humans were counted apart from the map\'s peoples; '
     'their descendants are the Tuathaich, now some 189,000 with the northern towns that took them in'),
    ('a barracks for two hundred at Dùn chrom (IV id), the guild\'s sick-roll of four hundred men (V id), a column of '
     'holdouts some hundreds strong and their dead in the hundreds (VI ids)', 'beside regiments of some 3,300 men and '
     'an island of 1.5 to 1.8 million, as they stand'),
    ('the Administration\'s census rounded to the hundred, and to the thousand in the hill districts (IV-0246)',
     'district counts of an island of about a million'),
    ('a village of forty houses become a town of four hundred at Ceann chaol (IV-0212)', 'the town has 476 people '
     'today; the Age V draft now gives it 400, as the annal does'),
    ('the four fleets, six hulls, about a hundred men to a hull', 'the fleets are not cut'),
    ('INTEGRATION.md and reconcile/state.json, land.json: the recount of 2026-09 (36,225,000 -> 35,412,000 heads, the '
     'frozen coast\'s 397,430 people, the Moot\'s tally of seven or nine thousand)', 'the record of how the map was '
     'reconciled, in the map\'s units of that day (1,000 people to the unit); the numbers as they stand now are here'),
    ('reconcile/military.json: the notes "— infantry: 826 ..." of its regiment edits', 'set aside by the prose layer '
     '(its "skip"); never on the map'),
    ('the Treasury\'s roll, 9,568 purses: 6,375 from the head-due and 3,193 from the market-due; the market-courts\' '
     '8,058 dealings and the sales in purses (appendix G)', 'the map\'s treasury and trade are unchanged; the head-due\'s '
     'rate is written per five thousand heads so that the roll still adds up'),
]


# ---------------------------------------------------------------------------------------------- the map edits
def place_layer(check):
    raw = open(PLACE, encoding='utf-8').read()
    d = json.loads(raw)
    edits = d['map_edits']
    have = {(e['record'], e['path']) for e in edits}
    add = []
    if (1, '.units.population.scale') not in have:
        add.append({'record': 1, 'path': '.units.population.scale', 'old': OLD_RATE, 'value': RATE,
                    'why': 'The owner: about as many people as Northern Ireland, some 1.8 million in DE 27, where the '
                           'generator gave the island 35.4 million (some 6,750 to the square mile). At 50 people to '
                           'the unit the land holds 1,771,220 people and the shires 1,770,774 (about 337 to the square '
                           'mile), 247,732 of them in towns, one in seven as before; every town, shire, people and '
                           'faith keeps its share. The urbanization rate stays 1. Every figure in the history that '
                           'follows from these is scaled with them (eras/POP_LOG.md).'})
    for i, (o, n) in enumerate(zip(REGIMENTS_OLD, REGIMENTS_NEW)):
        if (14, '[1].military[%d].u' % i) not in have:
            add.append({'record': 14, 'path': '[1].military[%d].u' % i, 'old': o, 'value': n,
                        'why': 'The regiments cut with the people: three tenths of the generator\'s strength, a '
                               'standing army of some %s men and %d guns for 1.8 million people (a twentieth, as the '
                               'population, would leave %d men).' % (
                                   fmt(sum(TOT_NEW.values())), TOT_NEW['artillery'],
                                   round(sum(TOT_OLD.values()) / 20.0))})
        if (14, '[1].military[%d].a' % i) not in have:
            add.append({'record': 14, 'path': '[1].military[%d].a' % i, 'old': sum(o.values()), 'value': sum(n.values()),
                        'why': 'The regiment\'s total, as Azgaar sums its units.'})
    note = (' The owner\'s decision on the numbers (2026-09-25): 50 people to the population unit, some 1.8 million '
            'on the island (Northern Ireland\'s), and the regiments at three tenths of their strength, set after the '
            'military layer\'s (eras/POP_LOG.md).')
    if note.strip() not in d['summary']:
        d['summary'] += note
    edits += add
    new = json.dumps(d, ensure_ascii=False, indent=1) + ('\n' if raw.endswith('\n') else '')
    if new != raw:
        print('place.json: %d map edits added' % len(add))
        if not check:
            open(PLACE, 'w', encoding='utf-8').write(new)
    return add


# ---------------------------------------------------------------------------------------------- town previews
def previews(check):
    """Every burg's town-plan link at the new scale (Azgaar's createWatabouCityLinks / VillageLinks)."""
    raw = open(PREVIEWS, encoding='utf-8').read()
    rows = json.loads(raw)
    changed = 0
    for r in rows:
        b = _BURGS[r['id']]
        url = urllib.parse.urlsplit(r['link'])
        q = urllib.parse.parse_qsl(url.query, keep_blank_values=True)
        d = dict(q)
        if 'city-generator' in url.path:
            pop = int(round(b['population'] * RATE))
            size = min(100, max(6, int(-(-(2.13 * (b['population'] * RATE / 10.0) ** 0.385) // 1))))
            d['population'], d['size'] = str(pop), str(size)
        else:
            c = int(round(b['population'] * RATE))
            w = 1600 if c > 1500 else 1400 if c > 1000 else 1000 if c > 500 else 800 if c > 200 else 600 if c > 100 else 400
            tags = [t for t in d['tags'].split(',') if t not in ('sparse', 'dense')]
            if c < 100:
                tags.append('sparse')
            elif c > 300:
                tags.append('dense')
            d['pop'], d['width'], d['height'], d['tags'] = str(c), str(w), str(int(round(w / 2.05))), ','.join(tags)
        q = [(k, d[k]) for k, _ in q]
        link = urllib.parse.urlunsplit((url.scheme, url.netloc, url.path, urllib.parse.urlencode(q), url.fragment))
        if link != r['link']:
            r['link'] = link
            changed += 1
    new = '[\n' + ',\n'.join(json.dumps(r, ensure_ascii=False) for r in rows) + '\n]' + ('\n' if raw.endswith('\n') else '')
    if new != raw:
        print('town_previews.json: %d links' % changed)
        if not check:
            open(PREVIEWS, 'w', encoding='utf-8').write(new)
    return changed


# ---------------------------------------------------------------------------------------------- the era tools
KIND_G = {'III': 0.2 / 0.035 / 20, 'IV': 0.35 / 0.12 / 20, 'V': 0.6 / 0.45 / 20}
MARK = '# populations at the master\'s 50 people to the unit (eras/pop_sweep.py)'
TOOL_FIXED = {('V', 397): 400}                  # IV-0212: "a village of forty houses become a town of four hundred"
TOOL_KEEP = ('refugee camp',)                   # the human families received under the truce: a few thousand


def rnd(n):
    if n < 100:
        return int(round(n / 5.0) * 5)
    if n < 1000:
        return int(round(n, -1))
    if n < 10000:
        return int(round(n, -2))
    return int(round(n, -3))


def era_tools(check):
    """The towns the drafts give a size to, in ages III-V, and the regimental post of Age VII."""
    out = []
    # a town the drafts give a size to does not shrink from one age to the next (the Age of Ailean's sizes come
    # from the tellings and stand as they are), unless it would outgrow its present size
    prev = {int(m.group(1)): int(m.group(2)) for m in re.finditer(r'(\d+): dict\(population=(\d+)',
                                                                   open(os.path.join(TOOLS, 'age_II.py'), encoding='utf-8').read())}
    for age, g in list(KIND_G.items()) + [('VII', MIL)]:
        path = os.path.join(TOOLS, 'age_%s.py' % age)
        text = open(path, encoding='utf-8').read()
        if MARK in text:
            continue
        lines = text.split('\n')
        for n, line in enumerate(lines):
            for m in list(re.finditer(r'population=(\d+)', line))[::-1]:
                v = int(m.group(1))
                if v < 100 or any(k in line for k in TOOL_KEEP):
                    continue
                bid = re.match(r'\s*(\d+): dict\(', line)
                bid = int(bid.group(1)) if bid else None
                if (age, bid) in TOOL_FIXED:
                    nv = TOOL_FIXED[(age, bid)]
                else:
                    nv = rnd(v * g)
                    if bid is not None:
                        nv = max(nv, prev.get(bid, 0))
                        if nv > people(bid):
                            nv = people(bid)        # never above the town's present size
                if bid is not None:
                    prev[bid] = max(prev.get(bid, 0), nv)
                if nv != v:
                    line = line[:m.start(1)] + str(nv) + line[m.end(1):]
                    out.append((age, bid, v, nv, n + 1))
            lines[n] = line
        # the mark goes after the module docstring
        text = '\n'.join(lines)
        i = text.find('"""', text.find('"""') + 3) + 3
        text = text[:i] + '\n' + MARK + text[i:]
        if not check:
            open(path, 'w', encoding='utf-8').write(text)
    for age, bid, v, nv, ln in out:
        print('era tool age_%s.py:%d  burg %s  %d -> %d' % (age, ln, bid, v, nv))
    return out


# ---------------------------------------------------------------------------------------------- applying the rules
def targets():
    out = []
    for pat in TARGETS:
        out += sorted(glob.glob(os.path.join(ROOT, pat)))
    return [p for p in out if os.path.isfile(p)]


def forms(old, new, path):
    yield old, new
    if path.endswith('.py') and "'" in old:
        yield old.replace("'", "\\'"), new.replace("'", "\\'")
    if path.endswith('.json') and ('\n' in old or '"' in old):
        yield json.dumps(old, ensure_ascii=False)[1:-1], json.dumps(new, ensure_ascii=False)[1:-1]


def apply(text, old, new):
    """old -> new everywhere, leaving alone text that already reads as new (even when old is part of new)."""
    if old == new or old not in text:
        return text, 0
    mark = '\x00SWEEP\x00'
    guarded = text.replace(new, mark) if old in new else text
    n = guarded.count(old)
    if not n:
        return text, 0
    return guarded.replace(old, new).replace(mark, new), n


def apply_table(text, old, new):
    """The appendix J rows: '{{place:burg:N}} | %s | OLD |' with the shire cell in the middle."""
    pre, post = old.split('%s')
    npre, npost = new.split('%s')
    pat = re.compile(re.escape(pre) + r'([^|\n]*)' + re.escape(post))
    n = len(pat.findall(text))
    return pat.sub(lambda m: npre + m.group(1) + npost, text), n


def run_rules(check):
    files = targets()
    applied = []
    for path in files:
        text = open(path, encoding='utf-8').read()          # read, replace and write back at once: other hands
        new_text = text                                       # may be editing the books at the same time
        for kind, old, new in RULES:
            if '%s' in old:
                new_text, k = apply_table(new_text, old, new)
                if k:
                    applied.append((kind, os.path.relpath(path, ROOT), k, old[:80]))
                continue
            for o, n in forms(old, new, path):
                new_text, k = apply(new_text, o, n)
                if k:
                    applied.append((kind, os.path.relpath(path, ROOT), k, o[:80]))
        if new_text != text and not check:
            if open(path, encoding='utf-8').read() != text:
                raise SystemExit('%s changed while it was being swept; run again' % path)
            open(path, 'w', encoding='utf-8').write(new_text)
    for kind, rel, k, o in applied:
        print('%-8s %-50s x%d  %s' % (kind, rel, k, o.replace('\n', ' ')))
    return files


def line_of(text, needle):
    i = text.find(needle)
    return text.count('\n', 0, i) + 1 if i >= 0 else None


def where(files, texts, old, new):
    out = []
    for p in files:
        if '%s' in new:
            pre, post = new.split('%s')
            m = re.search(re.escape(pre) + r'[^|\n]*' + re.escape(post), texts[p])
            if m:
                out.append('%s:%d' % (os.path.relpath(p, ROOT), texts[p].count('\n', 0, m.start()) + 1))
            continue
        for o, n in forms(old, new, p):
            ln = line_of(texts[p], n)
            if ln:
                out.append('%s:%d' % (os.path.relpath(p, ROOT), ln))
                break
    return out


def write_log(files, tools):
    texts = {p: open(p, encoding='utf-8').read() for p in files}
    tot_old, tot_new = sum(TOT_OLD.values()), sum(TOT_NEW.values())
    out = ['# The island\'s numbers cut to Northern Ireland\'s (2026-09-25)', '',
           'The owner\'s decision: Dia-thìr, some 5,340 square miles since the rescale (eras/RESCALE_LOG.md), should hold '
           'about as many people as Northern Ireland, some 1.8 million in the present day (DE 27), and every figure '
           'everywhere must match. The script is `eras/pop_sweep.py`; its docstring gives the rules.', '',
           '## Headline figures', '',
           '| | before (1,000 people to the unit) | after (50 to the unit) |', '|---|---|---|',
           '| people on the land | 35,424,408 | 1,771,220 |',
           '| people within the shires (the head-due\'s count) | 35,415,000 | 1,770,800 |',
           '| in towns (one in seven) | 4,954,633 | 247,732 |',
           '| Dia-thìrich: in towns / in the country | 4,411,000 / 27,224,000 | 220,600 / 1,361,200 |',
           '| Tuathaich: in towns / in the country within the shires | 543,000 / 3,237,000 | 27,200 / 161,800 |',
           '| the windy coast (the Moot\'s tally) | near nine thousand | near four hundred and fifty (447) |',
           '| to the square mile, within the shires | ~6,750 | ~337 (~130 to the km²) |',
           '| the largest town, Seann Skell of the west | 74,120 | 3,706 |',
           '| the capital, Cathair dhearg | 10,274 | 514 |',
           '| the Old Faith / Old Spirits / Church, in their towns | 3,177,500 / 1,233,920 / 543,200 | 158,875 / 61,696 / 27,160 |',
           '| the regiments (foot, horse, riflemen, guns) | %s, %s, %s, %d: %s | %s, %d, %d, %d: %s |' % (
               fmt(TOT_OLD['infantry']), fmt(TOT_OLD['cavalry']), fmt(TOT_OLD['riflemen']), TOT_OLD['artillery'],
               fmt(tot_old), fmt(TOT_NEW['infantry']), TOT_NEW['cavalry'], TOT_NEW['riflemen'], TOT_NEW['artillery'],
               fmt(tot_new)),
           '| the head-due | 18 purses on every 100,000 heads: 6,375 purses | 18 purses on every 5,000 heads: 6,375 purses |',
           '| the Treasury\'s roll | 9,568 purses | 9,568 purses (unchanged, as the map\'s treasury) |', '',
           '### The regiments', '',
           '| regiment | before | after |', '|---|---|---|']
    for i, (o, n) in enumerate(zip(REGIMENTS_OLD, REGIMENTS_NEW)):
        out.append('| %d | %s (%d) | %s (%d) |' % (i + 1, unit_phrase(o)[8:], sum(o.values()), unit_phrase(n)[8:],
                                                   sum(n.values())))
    out += ['', '### The ages', '',
            'The era drafts drew each age as a share of the present. The shares are redrawn so every age lies between '
            'the Age of Ailean (drawn from the tellings, unchanged) and the present. The people on the island at the '
            'close of each age, as the era maps hold them (their towns, with the country scaled as the towns are):', '',
            '| age | shares of the present, before -> after | people, before -> after |', '|---|---|---|']
    out += ERA_ROWS
    out += ['', 'Towns the era drafts give a size to (eras/specs_draft/tools), scaled with their age\'s share and never '
                'above the town\'s present size:', '']
    for age, bid, v, nv, ln in tools:
        out.append('- age_%s.py:%d, %s: %s -> %s' % (age, ln, 'burg %d (%s)' % (bid, _BURGS[bid]['name']) if bid else 'new burg',
                                                     fmt(v), fmt(nv)))
    out += ['', 'Also by hand: `eras/specs_draft/tools/common.py` (the master\'s scale read from the map, `POP_FACTOR`, '
                '`POP_CLAMP`, `KIND_SCALE`, the drafts\' `population_scale`), `eras/engine/convert_draft.py` (divides by '
                'the master\'s scale; groups and town works read at the kinds\' scale), '
                '`legendarium/map_reconcile.py` (world.json\'s populations at the map\'s scale), and the population '
                'rule in `eras/WRITERS_GUIDE.md`.', '',
            'The map: `legendarium/reconcile/place.json` sets `units.population.scale` (1,000 -> 50) and the nine '
            'regiments\' units and totals (record 14), after the military layer\'s. '
            '`legendarium/town_previews.json` is rebuilt from the map at the new scale (Watabou\'s population, size, '
            'width and density tags).', '',
            '## The changes', '',
            'Each rule, and where its new text now stands (file:line of the first occurrence in each file).', '']
    names = {HEADS: 'The kingdom\'s heads and the Treasury', KINGDOM: 'The faiths, the capital, the cities',
             MUSTER: 'The regiments', TOWNS: 'The towns, at their new sizes', DEAD: 'Deaths counted in one town',
             ERAS: 'The notes on the eras\' populations'}
    for kind in (HEADS, KINGDOM, MUSTER, TOWNS, DEAD, ERAS):
        out += ['### %s' % names[kind], '']
        for k, old, new in RULES:
            if k != kind or old == new or new is None:
                continue
            w = where(files, texts, old, new)
            out += ['- **before:** %s' % old.replace('\n', ' ').replace('%s', '…'),
                    '  **after:** %s' % new.replace('\n', ' ').replace('%s', '…'),
                    '  **in:** %s' % (', '.join(w) or '(nowhere: text not present)'), '']
    out += ['## Reviewed and kept', '']
    for what, why in KEPT:
        out.append('- %s: %s.' % (what, why))
    out += ['', '## Oddities for the owner', '',
            '- The generator\'s towns are many and small: 505 of them hold one person in seven, and at 1.8 million the '
            'largest (Seann Skell of the west) has 3,706 people and the capital, Cathair dhearg, 514. The relative sizes '
            'are kept as asked; a real capital would need the urbanization rate raised, and even then no town could be '
            'large without breaking the shares every table gives.',
            '- The Tuathaich number some 189,000 today; the humans left on the island at the Severance were "a few '
            'thousand", about a hundred years before. The northern towns that were Dia-thìreach before the Severance '
            'account for part of it.', '']
    open(LOG, 'w', encoding='utf-8').write('\n'.join(out))


ERA_ROWS = []


def era_rows():
    """Each age's people from the era drafts (towns, and the country at the towns' share of the master's)."""
    rows = []
    master_town = sum(b['population'] for b in _BURGS.values()) * RATE
    total = 1771220
    before = {'I': 18000, 'II': 111000, 'III': 1050000, 'IV': 3900000, 'V': 15000000, 'VI': 30100000, 'VII': 35424000}
    shares = {'III': ('0.035', '0.2'), 'IV': ('0.12', '0.35'), 'V': ('0.45', '0.6'), 'VI': ('0.85', '0.85')}
    for age in ('I', 'II', 'III', 'IV', 'V', 'VI', 'VII'):
        p = os.path.join(ROOT, 'eras', 'specs_draft', 'age_%s.json' % age)
        d = json.load(open(p, encoding='utf-8'))
        town = sum(b['population'] for b in d['burgs']) + sum(b['population'] for b in d['new_burgs'])
        ppl = total if age == 'VII' else town + (total - master_town) * min(1.0, town / master_town)
        sh = shares.get(age, ('tellings', 'tellings') if age in ('I', 'II') else ('1', '1'))
        rows.append('| %s | %s -> %s | ~%s -> ~%s |' % (age, sh[0], sh[1], fmt(before[age]), fmt(int(round(ppl, -3)))))
    return rows


def main():
    check = '--check' in sys.argv
    place_layer(check)
    previews(check)
    tools = era_tools(check)
    files = run_rules(check)
    if check:
        return
    if not check:
        try:
            ERA_ROWS[:] = era_rows()
        except (OSError, KeyError, ValueError):
            ERA_ROWS[:] = ['| (the era drafts are rebuilt after this script; run it again for this table) | | |']
        prev = [l for l in open(LOG, encoding='utf-8').read().split('\n') if l.startswith('- age_')] if os.path.exists(LOG) else []
        tl = tools or [(m.group(1), int(m.group(3)) if m.group(3) else None, int(m.group(4).replace(',', '')),
                        int(m.group(5).replace(',', '')), int(m.group(2)))
                       for m in (re.match(r'- age_(\w+)\.py:(\d+), (?:burg (\d+) \([^)]*\)|new burg): ([\d,]+) -> ([\d,]+)', l)
                                 for l in prev) if m]
        write_log(files, tl)
        print('log: %s' % os.path.relpath(LOG, ROOT))


if __name__ == '__main__':
    main()
