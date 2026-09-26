"""
rescale_sweep.py -- carry the owner's decisions of 2026-09-25 into the delivered text, and log them.

  1. Size. Dia-thìr is about the size of Northern Ireland: the map's distance scale goes from 0.2 to 0.14 miles
     to the unit (legendarium/reconcile/place.json). Every length is scaled by 0.7, every area by 0.49, every travel
     time by about 0.7 (rounded the way a teller would round it), every density by 1/0.49. Town counts and
     populations stay as they are.
  2. Place. The island lies alone in the Atlantic, west of the Outer Hebrides and north-west of Donegal. The humans'
     homeland lies EAST, over the eastern sea; Manannan's mist lies on that sea, and the one passage through it runs
     north-about, out past the north cape and down on the north-west, which is why every harbour of the Crossing is
     on the west coast. The Otherworld of the tellings (Tìr nan Òg, Magh Meall) stays in the west.

Each rule is (kind, old, new). A rule is applied to every target file that holds its old text; the old text of a
rule inside a .py source is also tried with its apostrophes escaped (\\'). The sweep is idempotent: text that already
reads as the new form is left alone, even where the old form is part of the new one.

    python eras/rescale_sweep.py            # apply, then write eras/RESCALE_LOG.md
    python eras/rescale_sweep.py --check    # list what would change, change nothing

Built files are not edited here; they are rebuilt from these sources (LEGENDARIUM.md, annals_dated.json, world.json,
the Atlas, TEXTS.md, NAMES.md, the era master annals).
"""
import glob
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(ROOT, 'eras', 'RESCALE_LOG.md')

TARGETS = [
    'legendarium/book/*.md', 'legendarium/appendices/*.md', 'legendarium/appendices/houses.json',
    'legendarium/annals/age_*.json', 'legendarium/gazetteer/*.json', 'legendarium/reconcile/*.json',
    'legendarium/burg_features.json', 'legendarium/town_previews.json', 'legendarium/route_extensions.json',
    'legendarium/canon_by_age.json', 'legendarium/chronicle_canon.json', 'legendarium/PLACE_FACTS.txt',
    'legendarium/canon_words_and_faiths.txt', 'legendarium/README.md', 'legendarium/BRIEF.md',
    'eras/specs_draft/*.json', 'eras/specs_draft/tools/*.py', 'eras/THREADS.json', 'eras/PEOPLE.json',
    'eras/WRITERS_GUIDE.md', 'TEXTS.json', 'atlas_template.html', 'language_template.html', 'README.md',
]

SCALE, PLACE, COMPASS = 'scale', 'place', 'compass'

RULES = [
    # ------------------------------------------------------------------ 1. size (x0.7 lengths, x0.49 areas)
    (SCALE, 'Dia-thìr is a little over two hundred miles from the capes of the far north-west to the eastern cape, and '
            'nowhere much more than a hundred miles from the north coast to the south. The main island covers about '
            'eleven thousand square miles. Twelve small islands lie off its coasts, and the largest of them is some '
            'seventeen square miles.',
            'Dia-thìr is a little over a hundred and fifty miles from the capes of the far north-west to the eastern '
            'cape, and nowhere much more than seventy miles from the north coast to the south. The main island covers '
            'about five thousand three hundred square miles, near fourteen thousand of the square measure the humans '
            'call the kilometre. Twelve small islands lie off its coasts, and the largest of them is some eight square '
            'miles.'),
    (SCALE, 'about a hundred and ninety square miles that no shire holds', 'about ninety-three square miles that no shire holds'),
    (SCALE, 'a single massif about seventy miles from west to east and thirty-five from north to south',
            'a single massif about fifty miles from west to east and twenty-five from north to south'),
    (SCALE, 'the longest river on Dia-thìr, about fifty-three miles.', 'the longest river on Dia-thìr, about thirty-seven miles.'),
    (SCALE, '**Abhainn fhionn**, about forty-five miles.', '**Abhainn fhionn**, about thirty-two miles.'),
    (SCALE, '**Abhainn uaine**, about forty miles.', '**Abhainn uaine**, about twenty-eight miles.'),
    (SCALE, '**Abhainn chaol**, about thirty-four miles.', '**Abhainn chaol**, about twenty-four miles.'),
    (SCALE, '**Abhainn gheal**, the northern, about thirty-one miles.', '**Abhainn gheal**, the northern, about twenty-two miles.'),
    (SCALE, "**Abhainn dhomhain**, the capital's river, about thirty miles.", "**Abhainn dhomhain**, the capital's river, about twenty-one miles."),
    (SCALE, '**Abhainn naomh**, the western, about thirty miles.', '**Abhainn naomh**, the western, about twenty-one miles.'),
    (SCALE, '**Abhainn gheal**, the lake river, about twenty-four miles.', '**Abhainn gheal**, the lake river, about seventeen miles.'),
    (SCALE, '**Abhainn ghorm**, the north-eastern, about twenty-seven miles.', '**Abhainn ghorm**, the north-eastern, about nineteen miles.'),
    (SCALE, 'fall south to the south coast in twenty miles or less', 'fall south to the south coast in fourteen miles or less'),
    (SCALE, 'about seventy-four square miles of fresh water', 'about thirty-six square miles of fresh water'),
    (SCALE, '| {{place:feature:8}} | off the west coast | 17 |', '| {{place:feature:8}} | off the west coast | 8 |'),
    (SCALE, '| {{place:feature:13}} | off the south coast | 16 |', '| {{place:feature:13}} | off the south coast | 8 |'),
    (SCALE, '| {{place:feature:15}} | off the south-east coast | 10 |', '| {{place:feature:15}} | off the south-east coast | 5 |'),
    (SCALE, '| {{place:feature:4}} | off the north coast | 7 |', '| {{place:feature:4}} | off the north coast | 4 |'),
    (SCALE, '| {{place:feature:12}} | off the south-east coast | 7 |', '| {{place:feature:12}} | off the south-east coast | 3 |'),
    (SCALE, '| {{place:feature:14}} | off the south coast | 5 |', '| {{place:feature:14}} | off the south coast | 3 |'),
    (SCALE, '| {{place:feature:6}} | off the north coast | 5 |', '| {{place:feature:6}} | off the north coast | 3 |'),
    (SCALE, '| {{place:feature:5}} | off the north-east coast | 4 |', '| {{place:feature:5}} | off the north-east coast | 2 |'),
    (SCALE, '| {{place:feature:3}} | off the north coast | 3 |', '| {{place:feature:3}} | off the north coast | 1 |'),
    (SCALE, '| {{place:feature:10}} | off the east coast | 2 |', '| {{place:feature:10}} | off the east coast | 1 |'),
    (SCALE, '| {{place:feature:7}} | off the Tuathaich coast | 2 |', '| {{place:feature:7}} | off the Tuathaich coast | 1 |'),
    (SCALE, '| {{place:feature:11}} | off the west coast | 2 |', '| {{place:feature:11}} | off the west coast | 1 |'),
    (SCALE, "some 190 square miles, in two pieces", "some 93 square miles, in two pieces"),
    (SCALE, 'some 10,900 square miles, of which the shires hold some 10,720',
            'some 5,340 square miles, of which the shires hold some 5,250'),
    (SCALE, '(about 9,220 square miles)', '(about 4,520 square miles)'),
    (SCALE, '(about 1,680 square miles)', '(about 825 square miles)'),
    # Fenn's line (IV-0027a): 221 miles, 45 of them sea, at 0.2; 155 and 30 at 0.14
    (SCALE, 'two hundred and twenty-one miles, some forty-five of them sea at the western end',
            'a hundred and fifty-five miles, some thirty of them sea at the western end'),
    # the Leaden Hawk (IV-0342a..e): on foot 79 -> 55 mi, by carriage 33 and 43 -> 23 and 30 mi; the eves 3,1,2,2 -> 2,1,1,2
    (SCALE, 'some eighty miles in a little over three days', 'some fifty-five miles in a little over two days'),
    (SCALE, 'Two days by carriage across country', 'A day and a half by carriage across country'),
    (SCALE, 'Two days more by carriage', 'A day and a half more by carriage'),
    (SCALE, 'Two more days by carriage', 'A day and a half more by carriage'),
    (SCALE, 'A day and a half by carriage across country, off every road, bring the',
            'A day and a half by carriage across country, off every road, brings the'),
    (SCALE, 'A day and a half more by carriage, still off the roads, bring the',
            'A day and a half more by carriage, still off the roads, brings the'),
    (SCALE, 'eight days after it left Cuan dhearg', 'six days after it left Cuan dhearg'),
    (SCALE, 'Inis thais eight days after they had set out', 'Inis thais six days after they had set out'),
    (SCALE, 'Inis thais nine days after they had set out', 'Inis thais six days after they had set out'),
    (SCALE, 'eight days out of Cuan dhearg', 'six days out of Cuan dhearg'),
    # the north's wool to Muileann òg by cart (V-0147): 66 -> 46 miles
    (SCALE, 'by cart, a week on the road', 'by cart, five days on the road'),
    # word of the ships from Cuan shean to Baile fhiadhaich (IV-0004): 20 -> 14 miles
    (SCALE, 'Word of the ships reaches Baile fhiadhaich, up the western coast, in three days.',
            'Word of the ships reaches Baile fhiadhaich, up the western coast, in two days.'),

    # ------------------------------------------------------------------ 2. place: the north-about passage
    (PLACE, "That winter Manannan's mist lifted, which had lain on the western sea since the fleet of the Sundering "
            "sailed into it and had hidden the island from every ship beyond.",
            "That winter Manannan's mist lifted from the northern water, which had lain on the eastern sea since the "
            "fleet of the Sundering sailed into it and had hidden the island from every ship beyond. The humans' land "
            "lies east of Dia-thìr, over that sea, and nearer than any Dia-thìreach had guessed; but on the straight "
            "way between, the mist has never cleared. The one road through it that the humans ever found ran "
            "north-about, out past the north cape and down again on the north-west of the island, and so it was off "
            "the north-west that the strangers first raised the land, and every harbour of the Crossing was a harbour "
            "of the west coast."),
    (PLACE, 'One sea surrounds all of it, and the Dia-thìrich call it by one name on every coast, north and south: '
            "*Muir Mhanannain*, Manannan's sea, for the lord of the sea whose mist lay on it and hid the island from "
            'every ship beyond until the humans came out of the west ({{date:IV-0001a}}, {{date:IV-0002}}).',
            'One sea surrounds all of it, and the Dia-thìrich call it by one name on every coast, north and south: '
            "*Muir Mhanannain*, Manannan's sea, for the lord of the sea whose mist lay on it and hid the island from "
            'every ship beyond until the humans came down out of it from the north ({{date:IV-0001a}}, '
            "{{date:IV-0002}}). Dia-thìr lies alone in it. The humans' charts put the nearest shore of their own land "
            'some sixty miles east of the eastern cape, among a chain of low islands, and a greater coast a hundred '
            'miles to the south-east; no one on the island has seen either, even from the summits on the clearest '
            'day, for the mist lies on that sea.'),
    (PLACE, "Beyond the headlands to the west lay Manannan's own mist. The Dia-thìrich tell that the fleet of the "
            "Sundering sailed into it ({{date:III-0023}}), and the order of Manannan teaches that he shut the western "
            "sea behind the fleet with it",
            "Beyond the northern and eastern headlands lies Manannan's own mist. To the west the open ocean runs on "
            "past sight of land, and the tellings put the Otherworld there; the mist lies to the north and east, on "
            "the sea between the island and the humans' land, and the straight way east has never been found "
            "through it. The one passage the humans knew ran north-about, out past the north cape and down on the "
            "north-west, and that is why every harbour of the Crossing was on the west coast. The Dia-thìrich tell "
            "that the fleet of the Sundering sailed into the mist by the same road ({{date:III-0023}}), and the order "
            "of Manannan teaches that he shut the eastern sea behind the fleet with it"),
    (PLACE, 'Since the Severance no ship has come from the west, and the priests say the lord of the sea has shut it again',
            'Since the Severance no ship has come out of it, and the priests say the lord of the sea has shut it again'),
    (PLACE, 'For so northerly a place Dia-thìr is a mild island, wet and windy, with cool summers and winters that are seldom hard.',
            'For so northerly a place Dia-thìr is a mild island, wet and windy, with cool summers and winters that are '
            'seldom hard. It stands alone in the open ocean, and no land breaks the gales before they reach it.'),

    # ------------------------------------------------------------------ 3. compass: the humans' homeland is east
    (COMPASS, 'men from over the western sea ruled the island', 'men from over the eastern sea ruled the island'),
    (COMPASS, 'coming on slowly out of the west with the mist tearing off their bows',
              'coming on slowly down from the north with the mist tearing off their bows'),
    (COMPASS, 'three hulls out of the west riding at anchor off the town', 'three hulls down from the north riding at anchor off the town'),
    (COMPASS, 'Harrow sailed west with hides and cloth', 'Harrow sailed for home with hides and cloth'),
    (COMPASS, 'Harrow sails west with hides and dyed cloth', 'Harrow sails for home with hides and dyed cloth'),
    (COMPASS, "Edmund Harrow's ship did not come home from the western crossing", "Edmund Harrow's ship did not come home from the crossing"),
    (COMPASS, "Edmund Harrow's ship does not come back from the western crossing", "Edmund Harrow's ship does not come back from the crossing"),
    (COMPASS, 'sent their son Calum west on a Company ship', 'sent their son Calum over the sea on a Company ship'),
    (COMPASS, 'The boy, Calum, sailed west on a Company ship', 'The boy, Calum, sailed over the sea on a Company ship'),
    (COMPASS, 'Sailed west on a Company ship', 'Sailed over the sea on a Company ship'),
    (COMPASS, 'the human dockers were shipped west', 'the human dockers were shipped over the sea'),
    (COMPASS, 'the human dockers are shipped west', 'the human dockers are shipped over the sea'),
    (COMPASS, 'When it ends they are not shipped west', 'When it ends they are not shipped over the sea'),
    (COMPASS, 'Their crew-leaders are among those shipped west', 'Their crew-leaders are among those shipped over the sea'),
    (COMPASS, 'Eight were shipped west to an Tìr Thall', 'Eight were shipped over the sea to an Tìr Thall'),
    (COMPASS, 'eight are shipped west to an Tìr Thall', 'eight are shipped over the sea to an Tìr Thall'),
    (COMPASS, 'the eight who were shipped west', 'the eight who were shipped over the sea'),
    (COMPASS, 'when the ships went west, and did not go', 'when the ships went out, and did not go'),
    (COMPASS, 'With the roads cut and no ships from the west', 'With the roads cut and no ships from over the sea'),
    (COMPASS, 'The roads cut and no ships coming from the west', 'The roads cut and no ships coming from over the sea'),
    (COMPASS, 'The keeper watched her stand out to the west, smaller and greyer', 'The keeper watched her stand out to the north, smaller and greyer'),
    (COMPASS, 'whatever road had brought the humans over the western water', 'whatever road had brought the humans over the eastern water'),
    (COMPASS, 'a ship was sent out past the western capes to seek the crossing the humans had used. She came home after a month of open water.',
              'a ship was sent out past the north-western capes and north-about to seek the crossing the humans had used. She came home after a month of grey water.'),
    (COMPASS, '"title": "The ship sent west"', '"title": "The ship sent north"'),
    (COMPASS, 'The council sends a ship out past the western capes to seek the crossing the humans used. She returns after a month of open water',
              'The council sends a ship out past the north-western capes and north-about to seek the crossing the humans used. She returns after a month of grey water'),
    (COMPASS, 'has shut the western sea again', 'has shut the eastern sea again'),
    (COMPASS, 'under the seal of a magistrate who had sailed west', 'under the seal of a magistrate who had sailed home'),
    (COMPASS, 'went out past the western capes', 'went out past the north-western capes'),
    (COMPASS, 'goes out past the western capes', 'goes out past the north-western capes'),
    (COMPASS, 'gone out past the western capes', 'gone out past the north-western capes'),
    (COMPASS, 'beyond the western capes', 'beyond the north-western capes'),
    (COMPASS, 'They say the fleet stood out west into Manannan\'s sea, toward the Otherworld of the tellings',
              'They say the fleet stood out past the north cape into Manannan\'s sea, toward the Otherworld of the tellings'),
    (COMPASS, 'had shut the western sea behind the fleet with his mist', 'had shut the eastern sea behind the fleet with his mist'),
    (COMPASS, 'shut the western sea behind the fleet with his mist', 'shut the eastern sea behind the fleet with his mist'),
    (COMPASS, 'Manannan shut the western sea behind the fleet of the Sundering', 'Manannan shut the eastern sea behind the fleet of the Sundering'),
    (COMPASS, 'the mist on the western sea', 'the mist on the eastern sea'),
    (COMPASS, 'the mist that had lain on the western sea since the fleet of the Sundering sailed into it lifts. Two fishing boats',
              'the mist that had lain on the eastern sea since the fleet of the Sundering sailed into it lifts from the northern water. Two fishing boats'),
    (COMPASS, 'meet three ships coming out of the thin grey from the west, and hail them',
              'meet three ships coming down out of the thin grey from the north, and hail them'),
    (COMPASS, 'meet three ships out of the west and hail them', 'meet three ships coming down from the north and hail them'),
    (COMPASS, 'met the three ships from the west in the first days of the Crossing',
              'met the three ships coming down from the north in the first days of the Crossing'),
    (COMPASS, 'Three ships out of the west anchor off Cuan shean', 'Three ships down from the north anchor off Cuan shean'),
    (COMPASS, 'Three ships out of the west anchored off', 'Three ships down from the north anchored off'),
    (COMPASS, 'A fisher of the west coast, putting out before dawn', 'A fisher of the north-west coast, putting out before dawn'),
    (COMPASS, 'on still mornings the fishers of the west coast begin to see', 'on still mornings the fishers of the north-west coast begin to see'),
    (COMPASS, 'west the mist lies thinner each winter', 'north-west the mist lies thinner each winter'),
    (COMPASS, 'where ships from the west first raise the land', 'where ships coming down from the north first raise the land'),
    (COMPASS, 'and there the ships bound for an Tìr Thall leave it and the ships from the west come in',
              'and there the ships bound for an Tìr Thall leave it for the passage north-about, and the ships coming down from the north come in'),
    (COMPASS, 'The willing sail west. ', 'The willing sail out past the north cape. '),
    (COMPASS, 'the fleet of the willing sailed west into Manannan\'s mist', 'the fleet of the willing sailed north-about into Manannan\'s mist'),
    (COMPASS, '**The Otherworld.** The Old Faith holds that the Otherworld lies west over the sea, behind Manannan\'s mist.',
              '**The Otherworld.** The Old Faith holds that the Otherworld lies west over the open sea, past the sight of any headland.'),
    (COMPASS, 'The fleet of the Sundering sailed west into that mist ({{date:III-0023}}), and the saying',
              'The fleet of the Sundering went out north-about into Manannan\'s mist on the eastern sea '
              '({{date:III-0023}}), not west, but the tellers say it went to find the Otherworld all the same, and the saying'),
    (COMPASS, 'When no ship came from the west after the Severance', 'When no ship came from an Tìr Thall after the Severance'),
    (COMPASS, 'No ship has come from the west since the last one sailed from Ros bheag', 'No ship has come from an Tìr Thall since the last one sailed from Ros bheag'),
    (COMPASS, 'sent it west to the scholars of an Tìr Thall', 'sent it over the sea to the scholars of an Tìr Thall'),
    (COMPASS, 'sends it west to the scholars of an Tìr Thall', 'sends it over the sea to the scholars of an Tìr Thall'),
    (COMPASS, 'Copied by Samuel Wren and sent west; no answer came', 'Copied by Samuel Wren and sent over the sea; no answer came'),
    (COMPASS, '"title": "Fewer ships from the west"', '"title": "Fewer ships from over the sea"'),
    (COMPASS, '"title": "No relief from the west"', '"title": "No relief from over the sea"'),
    (COMPASS, '"title": "Timber from the west"', '"title": "Timber out of the mist"'),
    (COMPASS, '"title": "The last ship from the west"', '"title": "The last ship from the east"'),
    (COMPASS, '"title": "The ship that sailed west"', '"title": "The ship that sailed east"'),
    (COMPASS, 'Lionel Strake, the last Commissioner, sails west from Cuan shean with his officers',
              'Lionel Strake, the last Commissioner, sails from Cuan shean for an Tìr Thall with his officers'),
    (COMPASS, 'Strake sailed west in the last ship able to make the crossing', 'Strake sailed for an Tìr Thall in the last ship able to make the crossing'),
    (COMPASS, 'The last Commissioner sailed west, and where he came to land is not known',
              'The last Commissioner sailed for an Tìr Thall, and where he came to land is not known'),
    (COMPASS, 'the last Commissioner; sailed west, and of his landing nothing is known',
              'the last Commissioner; sailed for an Tìr Thall, and of his landing nothing is known'),
    (COMPASS, 'its last Commissioner sailed west from Cuan shean with his officers', 'its last Commissioner sailed from Cuan shean for an Tìr Thall with his officers'),
    (COMPASS, 'Strake left the Residency (AE 150) and sailed west from Cuan shean', 'Strake left the Residency (AE 150) and sailed from Cuan shean for an Tìr Thall'),
    (COMPASS, 'sailed west; nothing on Dia-thìr tells of his coming anywhere', 'sailed for an Tìr Thall; nothing on Dia-thìr tells of his coming anywhere'),
    (COMPASS, 'He sailed west from Cuan shean and was not heard of again.', 'He sailed from Cuan shean for an Tìr Thall and was not heard of again.'),
    (COMPASS, 'the last ship from the west anchored here', 'the last ship from the east anchored here'),
    (COMPASS, 'The mist that lay on the western sea since the Sundering lifted in the winter of the Crossing.',
              'The mist that lay on the eastern sea since the Sundering lifted from the northern water in the winter of the Crossing.'),
    (COMPASS, "sea='the western sea'", "sea='the eastern sea'"),
    (COMPASS, '"sea": "the western sea"', '"sea": "the eastern sea"'),
    (COMPASS, 'the western sea is open water at the snapshot, but no ship will come again',
              'the northern water is open at the snapshot, but no ship will come again'),
    (COMPASS, "Manannan's mist lies on the western sea beyond the headlands", "Manannan's mist lies on the eastern sea beyond the northern and eastern headlands"),
    (COMPASS, "Manannan's mist on the western sea", "Manannan's mist on the eastern sea"),
    (COMPASS, 'the departed: west, beyond the mist', 'the departed: north-about, beyond the mist'),
]

KEPT = [
    ("the bearers are eleven days on the road with the body of Fionnlagh Dall (III-0036)",
     "a funeral procession of about 20 miles (was 28), stopping at every hearth; the pace was never set by the distance"),
    ("'a day's walk' (Muileann ghlas from Cathair dhearg, 15 mi; Baile àrsaidh up the coast), 'within a day' of a "
     "waypoint house, 'a day's rowing apart', 'a day's sail east', 'half a day's journey', 'a half-day's walk'",
     "still true at the smaller scale (a day's walk now covers every one of these with room to spare)"),
    ("'a few miles apart' (Cathair dhomhain and the capital, now 5 mi), 'a few miles from' (Inis thais and Baile "
     "dhìreach, 5 mi; the paper-mill and the library)", "still a few miles"),
    ("'a little over a mile long' (the shell road at Seann Warr), 'for a mile' (the fires on the east bank), 'passes "
     "Caol gharbh by a mile'", "works and sights smaller than a map cell, not measured from the map"),
    ("the west coast, the western harbours, the western Seann Skell, Cidhe an Iar, the western crossing of the Abhainn "
     "dhomhain, the western reefs, the gales off the north-western sea, the rain off the western ocean, 'the drowned, "
     "gone west over the sea', the Old Ones sailing 'westward, toward the setting sun', Naomh Breandan sailing west "
     "from an Tìr Thall to the Isle of the Blessed",
     "the island's own geography, the Atlantic weather, and the Otherworld in the west: all agree with the new map"),
    ("reconcile/*.json 'why' and 'summary' texts that give the 0.2 scale, the North Channel frame, the journey's "
     "80 + 33 + 43 miles and Fenn's 221 miles; INTEGRATION.md; CONTINUITY_LOG.md; gazetteer/CONSISTENCY_LOG.md",
     "the record of earlier decisions; reconcile/place.json sets the scale and frame aside and says why"),
]


def targets():
    out = []
    for pat in TARGETS:
        out += sorted(glob.glob(os.path.join(ROOT, pat)))
    return [p for p in out if os.path.isfile(p)]


def forms(old, new, path):
    yield old, new
    if path.endswith('.py') and "'" in old:
        yield old.replace("'", "\\'"), new.replace("'", "\\'")


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


def line_of(text, needle):
    i = text.find(needle)
    return text.count('\n', 0, i) + 1 if i >= 0 else None


def main():
    check = '--check' in sys.argv
    files = targets()
    changed = {}
    applied = []
    for path in files:
        text = open(path, encoding='utf-8').read()
        new_text = text
        for kind, old, new in RULES:
            for o, n in forms(old, new, path):
                new_text, k = apply(new_text, o, n)
                if k:
                    applied.append((kind, os.path.relpath(path, ROOT), k, o[:80]))
        if new_text != text:
            changed[path] = new_text
    for kind, rel, k, o in applied:
        print('%-7s %-45s x%d  %s' % (kind, rel, k, o))
    if check:
        print('%d files would change' % len(changed))
        return
    for path, text in changed.items():
        open(path, 'w', encoding='utf-8').write(text)
    write_log(files)
    print('%d files changed; log: %s' % (len(changed), os.path.relpath(LOG, ROOT)))


def write_log(files):
    texts = {p: open(p, encoding='utf-8').read() for p in files}
    out = ['# The rescale and the move into the Atlantic (2026-09-25)', '',
           "The owner's decisions: Dia-thìr about the size of Northern Ireland (the map's distance scale 0.2 -> 0.14 miles "
           'to the unit: lengths x0.7, areas x0.49, travel times x0.7 rounded as a teller would, densities x2.04; town '
           "counts and populations unchanged), and the island alone in the Atlantic west of the Outer Hebrides, with the "
           "humans' homeland east of it, Manannan's mist on the eastern sea, and the one passage through the mist running "
           'north-about (which is why the harbours of the Crossing are on the west coast). The Otherworld stays west.', '',
           'Headline figures (land 272,668 map units of area; frame 1536 x 702 units):', '',
           '| | at 0.2 mi/unit | at 0.14 mi/unit |', '|---|---|---|',
           '| the land with its islands | ~10,900 sq mi | ~5,340 sq mi (~13,840 km²) |',
           '| the shires | ~10,720 sq mi | ~5,250 sq mi |',
           '| Dia-thìrich / Tuathaich country | ~9,220 / ~1,680 sq mi | ~4,520 / ~825 sq mi |',
           '| the windy coast | ~190 sq mi | ~93 sq mi |',
           '| Loch chrom | ~74 sq mi | ~36 sq mi |',
           '| the island, west to east / north to south (land bounding box) | ~220 x ~103 mi | ~154 x ~72 mi |',
           "| Fenn's line (IV-0027a) | 221 mi, 45 of sea | 155 mi, 30 of sea |",
           '| the Leaden Hawk (IV-0342a..e) | 80 mi on foot in 3+ days; 2 + 2 days by carriage; 8 days in all | 55 mi in 2+ days; 1½ + 1½ days; 6 days |',
           '| the map frame | 307 x 140 mi, 54.2-56.2 N, 8.0-3.6 W | 215 x 98 mi, 56.12-57.54 N, 13.56-7.87 W |',
           '| people within the shires (35,415,000, unchanged) | ~3,300 a sq mi | ~6,750 a sq mi (~2,600 a km²) |',
           "| (since cut to 1,770,800 by the owner's later decision: ~337 a sq mi; see POP_LOG.md) | | |", '',
           "The map: legendarium/reconcile/place.json (the last layer of map_reconcile.py) sets the scale and the frame and "
           "sets aside the earlier layers' scale and frame edits; the climate layer's temperatures are computed for the "
           "frame they were set in (recompute_temperature 'frame'), so the weather does not change. The land's middle is "
           'near 56.9 N 11.1 W; the eastern cape is some 62 miles west of Barra, the south coast some 100 miles '
           'north-west of the Donegal coast, the north-east of the island some 50 miles south-west of St Kilda; the frame '
           'holds no real coast. The Leaden Hawk\'s eves in annals/age_V.json were set to 2, 1, 1, 2 days.', '',
           'Towns the lore ties to the Crossing, all on the west coast and all left where they are: the meeting off the '
           'north-west cape by Achadh àrsaidh (burg 242, marker 45), Ceann mhòr (143), Cuan shean (282), Ros bheag (63), '
           'Seann Skell of the west (16), Baile dhìreach (105).', '',
           '## The changes', '',
           'Each rule, and where its new text now stands (file:line of the first occurrence in each file).', '']
    for kind in (SCALE, PLACE, COMPASS):
        out += ['### %s' % {SCALE: 'Distances, areas and travel times', PLACE: 'Where the island is',
                            COMPASS: "The humans' homeland in the east"}[kind], '']
        for k, old, new in RULES:
            if k != kind or old == new:
                continue
            where = []
            for p in files:
                for o, n in forms(old, new, p):
                    ln = line_of(texts[p], n)
                    if ln:
                        where.append('%s:%d' % (os.path.relpath(p, ROOT), ln))
                        break
            out += ['- **before:** %s' % old, '  **after:** %s' % new,
                    '  **in:** %s' % (', '.join(where) or '(nowhere: text not present)'), '']
    out += ['### Also changed by hand', '',
            '- legendarium/annals/age_V.json: the eves of IV-0342a and IV-0342c (3 -> 2, 2 -> 1), so the Leaden Hawk '
            'reaches Inis thais six days after leaving Cuan dhearg.',
            '- eras/NAMES.json (via the names tool): the last ship from the east; the ship that sailed east, *An Long a '
            "Sheòl an Ear*; Manannan's mist over the eastern sea.",
            '- eras/WRITERS_GUIDE.md: the rule on geography, distance and compass (section 13), and the example book '
            'title.',
            '- legendarium/build_book.py: the gazetteer\'s opening lines give the size and place of the island.',
            '- check_rodais.py: the frame and the scale are checked; legendarium/README.md and map_reconcile.py '
            'describe the place layer.', '',
            '## Reviewed and kept', '']
    for what, why in KEPT:
        out.append('- %s: %s.' % (what, why))
    out.append('')
    open(LOG, 'w', encoding='utf-8').write('\n'.join(out))


if __name__ == '__main__':
    main()
