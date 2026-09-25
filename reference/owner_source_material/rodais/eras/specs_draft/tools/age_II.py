"""Age II, the Age of Ailean (Grove Era): the island on the eve of Blàr Àth na Fala."""
import math
from common import *  # noqa: F401,F403

AGE = 'II'

SEANN_RUINS = [14, 16, 34, 36, 37, 47, 64, 94, 97, 110, 127, 128, 132, 139, 162, 186, 249, 295, 313, 328, 347, 402,
               404, 440, 465, 29, 497]


def build():
    reset_names()
    s = Spec(AGE, collections.OrderedDict([
        ('age', 'II'),
        ('age_name', {'name': dt('An Aois Ailein', 'age name'), 'name_en': 'the Age of Ailean'}),
        ('era', {'abbr': 'GE', 'name': dt('Linn na Doire', 'era name'), 'name_en': 'the Grove Era'}),
        ('snapshot', collections.OrderedDict([
            ('date', '30 an Lùnastal, GE 4,603'),
            ('plan_label', 'GE 4,603, the eve of Blàr Àth na Fala (ERA_PLAN); the same year is FE 1 in the count that opens at the king\'s fall'),
            ('y', -2998), ('m', 8), ('d', 30),
            ('last_event_shown', 'I-0256'),
            ('next_event', 'I-0098a'),
            ('description',
             "Ailean Mòr has been king of the godkin for four thousand six hundred and two years. He holds the hill of Dùn "
             "ìseal in his own hand again, as in the first days, for the list of those who held it under him ended with "
             "Catrìona Mhòr; the Red Hill on the lake keeps its own holders and is sworn to him and not to the hill; the salt "
             "shore, the north and the west have set their hands in his at the great gathering at the ford. At Tobar dhìreach "
             "nine keepers drawn by lot watch the slab, and the king does not overrule them. Every hearth of the hills burns its "
             "handful by the one stone measure, the sharing before the storms is kept on every coast, and the saying is spoken "
             "at every gathering, but none of it is declared and no oath is yet sworn over the vein. The Old Ones have been silent "
             "for four thousand years and their harbours are empty but for Seann Skell and a few that the hill-folk have taken "
             "up. East of the vein the households who never bowed have gathered their spears at Dùn dhearg and are coming down "
             "to the ford below it, while the king's kin wait in tents in the valley under Dùn ìseal for their shares."),
            ('cites', ['I-0256', 'I-0255a', 'I-0255b', 'I-0208a', 'I-0089a', 'I-0104b', 'I-0247', 'I-0158', 'I-0248',
                       'I-0168', 'I-0096', 'I-0098', 'I-0098a', 'book III']),
        ])),
        ('land_changes', [
            collections.OrderedDict([('what', 'The oak has fallen back from the northern lowlands (GE 3,588): heather, birch and bog-moss as on the master map, groves only in the sheltered valleys.'),
                                     ('cites', ['I-0220a'])]),
            collections.OrderedDict([('what', 'Loch chrom stands a hand higher on the Ros dhomhain tide-rock than at the first cut; no change to the drawn shore.'),
                                     ('cites', ['I-0128'])]),
            collections.OrderedDict([('what', 'The lake dwellings of Loch chrom are burned (GE 1,525); the charred piles stand in the shallows.'),
                                     ('cites', ['I-0122'])]),
            collections.OrderedDict([('what', 'The crack across the valley at Cill ghlas, banked with stones and marked by a line of white stones.'),
                                     ('cites', ['I-0106', 'I-0107', 'I-0226'])]),
        ]),
    ]))
    d = s.d

    d['cultures'] = [
        collections.OrderedDict([('key', 'dia-thirich'), ('name', dt('Na Dia-thìrich', 'culture')), ('name_en', 'the Dia-thìrich (the godkin)'),
                                 ('master_culture', 2), ('provinces', []),
                                 ('note', 'The hill-folk take the names Dia-thìrich and Dia-thìr in this age (by GE 2,201), and with them the belief that they did not come. They order themselves by blood and recite seven names back before a marriage.'),
                                 ('cites', ['I-0140', 'I-0141', 'I-0142'])]),
        collections.OrderedDict([('key', 'seann-dhaoine'), ('name', dt('Na Seann-Dhaoine', 'culture')), ('name_en', 'the Old Ones (vanished)'),
                                 ('master_culture', 0), ('provinces', []),
                                 ('note', 'No work of theirs is dated after the half-cut stone of GE 510; by GE 551 they are silent. They hold no land at the snapshot; their names stay on the harbours with Seann before them.'),
                                 ('cites', ['I-0095', 'I-0096', 'I-0097'])]),
    ]
    d['faiths'] = [
        collections.OrderedDict([('key', 'old-reverence'), ('name', dt('An Seann Urram', 'faith')), ('name_en', 'the old reverence of the hearths'),
                                 ('inferred_name', True), ('master_religion', 2), ('type', 'Folk'),
                                 ('form', 'hearth reverence with a custody of the vein by lot'), ('deity', None), ('provinces', []),
                                 ('practice', 'The measured handful in the stone cup, burned on one dark night of the year; the nine keepers of the slab by lot; the sharing of surplus before the storms; the saying spoken at every gathering; the unlit hearth; the dead rowed to Eilean ìseal on the south-east coast. It is one reverence: nothing is declared and no god is named at the hearth.'),
                                 ('cites', ['I-0110', 'I-0146', 'I-0151', 'I-0153', 'I-0168', 'I-0247', 'I-0248', 'I-0253', 'I-0256', 'App.B §II'])]),
        collections.OrderedDict([('key', 'telling-of-the-making'), ('name', dt('Aithris a\' Chruthachaidh', 'faith')), ('name_en', 'the Telling of the Making'),
                                 ('master_religion', 1), ('type', 'Kindred lore'), ('form', 'kept within Clann na Ceiste'),
                                 ('deity', 'Caoran and the Tuath Dè, who crowned Ailean in the grove'), ('provinces', [114]),
                                 ('practice', 'Kept by the Children of the Question with the Line of the Mason and, apart from it, the Line of Somhairle. Ailean tells no one what the gods put into him.'),
                                 ('cites', ['I-0080b', 'I-0104a', 'App.A Line of Aisling', 'App.B §III'])]),
    ]

    # ---------------------------------------------------------------- polities
    s.polity('rioghachd', dt('Rìoghachd Chlann nan Dè', 'polity'), 'the kingdom of the godkin (Ailean\'s kingdom)',
             inferred_name=True,
             form='kingship of one man crowned by the gods; holdings sworn to him in person; no written law',
             capital={'burg': 315},
             ruler={'name': dt('Ailean Mòr', 'ruler', 'person'), 'title': dt('Rìgh Chlann nan Dè', 'title', 'phrase'),
                    'note': 'crowned in the grove GE 1 aged 24; about 4,626 years old; has held Dùn ìseal in his own hand since Catrìona Mhòr died (GE 4,391)',
                    'cites': ['I-0080b', 'I-0081', 'I-0255a', 'I-0098a']},
             culture='dia-thirich', color='#b8923a (the gold of the grove)',
             cites=['I-0081', 'I-0208a', 'I-0255a', 'App.A Stone Kings'],
             admin_units=[
                 {'name': dt('Dùn ìseal', 'admin'), 'name_en': 'the hill and the valleys about it, held by the king in his own hand',
                  'kind': 'royal hill', 'provinces': [35, 87, 34, 12, 65, 111, 112, 96, 90, 76, 46, 42],
                  'cites': ['I-0081', 'I-0085', 'I-0255a']},
                 {'name': None, 'name_en': 'the salt shore', 'kind': 'holding sworn to the king (knelt GE 728)',
                  'provinces': [25, 78, 10, 72, 17, 108, 100, 19, 49, 11], 'cites': ['I-0104b', 'I-0208a']},
                 {'name': None, 'name_en': 'the north', 'kind': 'holding sworn to the king (at the gathering, GE 3,000)',
                  'provinces': [27, 23, 88, 91, 86, 7, 36, 28, 105, 14, 75, 107, 51, 45, 9, 6, 68, 83, 113, 92, 119, 26,
                                54, 56, 62, 115, 20, 104, 8, 98, 118, 97, 47, 30, 102, 103, 50, 79, 99, 16, 120],
                  'cites': ['I-0208a', 'I-0190', 'I-0200'], 'inferred': True},
                 {'name': None, 'name_en': 'the west', 'kind': 'holding sworn to the king (at the gathering, GE 3,000)',
                  'provinces': [5, 95, 2, 15, 38, 64, 3, 77, 73, 117, 52, 29, 74, 40, 33, 81],
                  'cites': ['I-0208a', 'I-0171'], 'inferred': True},
                 {'name': None, 'name_en': 'the south coast (holders the gathering does not name)', 'kind': 'settlements under the king (inferred)',
                  'provinces': [44, 93, 21, 24, 31, 53, 55, 94, 18, 4, 116, 63, 80, 121],
                  'cites': ['I-0205', 'I-0207', 'I-0210'], 'inferred': True},
             ])
    s.polity('red-hill', dt('Muinntir a\' Chnuic Dheirg', 'polity'), 'the Red Hill (a vassal line)',
             inferred_name=True,
             form='an old line of the western lake shore, not of Ailean\'s blood; keeps its own holders and its own list, sworn to the king and not to Dùn ìseal',
             capital={'burg': 19},
             ruler={'name': None, 'note': 'not named: the spoken list of the Red Hill ends with Seumas Òg (in office GE 4,347)', 'cites': ['I-0244']},
             culture='dia-thirich', color='#a8443a (red stone)',
             suzerain='rioghachd',
             cites=['I-0083', 'I-0089a', 'I-0113', 'I-0244', 'App.A holders of the Red Hill'],
             admin_units=[{'name': None, 'name_en': 'the Red Hill\'s households (Cathair dhomhain, Baile ghlas, Cnoc bheag of the forest, Ceann àrsaidh)',
                           'kind': 'households counted in the Red Hill list', 'provinces': [1, 22, 32, 106, 71, 67],
                           'cites': ['I-0117', 'I-0186', 'I-0230', 'I-0238'], 'inferred': True}])
    s.polity('dun-dhearg', dt('Dùn dhearg', 'polity'), 'Dùn dhearg and the households east of the vein',
             form='a league of eastern households sworn to owe nothing to Dùn ìseal or its king; its spears gathered at the double-banked fort',
             capital={'burg': 422},
             ruler={'name': None, 'note': 'the Stone Kings\' list does not name the holders of Dùn dhearg', 'cites': ['I-0235']},
             culture='dia-thirich', color='#5b4a7a (the dark of the eastern hills)',
             cites=['I-0235', 'I-0236', 'I-0255b', 'I-0208a'])
    s.polity('keepers', dt('Luchd-faire na Lice', 'polity'), 'the keepers of the slab',
             inferred_name=True,
             form='nine keepers drawn by lot, one for each district of the hills; they hold no land but the slab and the keepers\' house, and the king does not overrule them',
             capital={'burg': 276},
             ruler={'name': None, 'note': 'nine keepers by lot; they meet at the slab only when a keeper dies. The first keeper by lot was Oighrig nic Dhòmhnaill (GE 2,403).', 'cites': ['I-0151', 'I-0247']},
             culture='dia-thirich', color='#6f6f6f (grey stone of the cup)',
             cites=['I-0151', 'I-0152', 'I-0157', 'I-0158', 'I-0246', 'I-0247', 'I-0255'],
             admin_units=[{'name': None, 'name_en': 'the nine districts of the hills (one keeper each)', 'kind': 'lot districts, not bounded on any record',
                           'provinces': [114, 35, 65, 111, 112, 96, 87, 34, 12], 'cites': ['I-0247'], 'inferred': True}])

    king = s.d['polities'][0]
    for u in king['admin_units']:
        u['provinces'] = [p for p in u['provinces'] if isinstance(p, int)]
    east = [85, 37, 84, 57, 109, 43, 59, 13, 101, 110, 58, 60, 66, 61, 82, 70, 89, 41, 69, 123, 48, 39]
    assign = {'red-hill': [1, 22, 32, 106, 71, 67], 'dun-dhearg': east, 'keepers': [114]}
    used = {p for v in assign.values() for p in v}
    king_provs = []
    for u in king['admin_units']:
        u['provinces'] = [p for p in u['provinces'] if p not in used]
        king_provs += u['provinces']
    assert len(king_provs) == len(set(king_provs)), [p for p in king_provs if king_provs.count(p) > 1]
    assign['rioghachd'] = king_provs
    used |= set(king_provs)
    assign['unclaimed'] = [p for p in range(1, 124) if p not in used]
    s.assign(assign)
    d['province_polity_notes'] = collections.OrderedDict([
        ('rioghachd', 'The bounds of the five holdings are not recorded; they are drawn from the places each holding\'s settlers came from and went to. Dùn thais (16) is set in the north: at the parting after the king\'s fall it lay on the line between the north and the east.'),
        ('dun-dhearg', 'East of the vein: every province whose households sent no one to the gathering. The Holy Age reads Dùn thais and Achadh mhòr as border ground.'),
        ('unclaimed', 'Only the island shires without people and the windy coast (no province) are left; the king\'s holdings are taken to reach every settled coast west of the vein.'),
    ])
    d['cultures'][0]['provinces'] = [p for p in range(1, 124) if assign.get('unclaimed') is None or p not in assign['unclaimed']]
    d['faiths'][0]['provinces'] = list(d['cultures'][0]['provinces'])

    d['diplomacy'] = [
        {'a': 'rioghachd', 'b': 'red-hill', 'relation': 'suzerain and vassal', 'since': ann_date('I-0089a'),
         'note': 'Uisdean Mòr knelt to the king on the lake shore; the Red Hill swears to the king and not to Dùn ìseal, so neither list names the other until the peace of the ford.', 'cites': ['I-0089a', 'I-0113']},
        {'a': 'rioghachd', 'b': 'dun-dhearg', 'relation': 'war', 'since': ann_date('I-0255b'),
         'note': 'The king bade the east come in; they sent his messenger back with nothing and gathered their spears at Dùn dhearg. The host comes to the ford at the snapshot.', 'cites': ['I-0255b', 'I-0256', 'I-0098a']},
        {'a': 'rioghachd', 'b': 'keepers', 'relation': 'separate charges: the king rules the grazing and the gatherings, the slab rules the vein',
         'note': 'Calum Ciar was refused the lot; Catrìona Mhòr neither refused nor granted the keepers\' asking to be named. The matter is left to the next age.', 'cites': ['I-0157', 'I-0158', 'I-0255']},
        {'a': 'red-hill', 'b': 'dun-dhearg', 'relation': 'trade at the ford', 'cites': ['I-0236'], 'inferred': True},
        {'a': 'keepers', 'b': 'dun-dhearg', 'relation': 'none recorded; the handful is burned in the hills alike', 'cites': ['I-0248'], 'inferred': True},
    ]

    # ---------------------------------------------------------------- burgs
    polity_of = {int(k): v for k, v in d['province_polity'].items()}
    special = {
        315: dict(population=600, kind='fort', walls=True, role='the king\'s hill: two banks and ditches, the gathering-ground and the shared store within the bank; held by the king in his own hand',
                  cites=['I-0081', 'I-0082', 'I-0139', 'I-0147', 'I-0250', 'I-0255a'], inferred=True),
        19: dict(era_name=dt('Cnoc dhearg', 'burg 19', 'place'), era_name_en='the Red Hill',
                 name_note='inferred Dia-thìris form of "the Red Hill" by the naming layer (place_name("Cnoc", "dearg")); the ground is called Cathair dhearg only from the Holy Age (II-0076)',
                 population=300, kind='fort', role='the hill of the Red Hill line: ditch and palisade across the neck, a stone landing at the river-mouth below',
                 cites=['I-0083', 'I-0089', 'I-0172', 'II-0076'], inferred=True),
        422: dict(population=500, kind='fort', walls=True, role='the double-banked hill-fort of the east; the spears of the east are gathered here',
                  cites=['I-0235', 'I-0255b'], inferred=True),
        276: dict(population=150, kind='hamlet', role='the slab over the crack and the keepers\' house facing it; a place of pilgrimage; home of Clann na Ceiste',
                  cites=['I-0112', 'I-0151', 'I-0152', 'I-0246', 'I-0104a'], inferred=True),
        27: dict(population=450, kind='village', role='the greatest settlement on the shores of Loch chrom, some sixty houses round the tide-rock; its people fish from boats',
                 cites=['I-0127', 'I-0171', 'I-0169'], inferred=True),
        365: dict(population=480, kind='village', role='round a spring that never freezes; some eighty houses at its height',
                  cites=['I-0200'], inferred=True),
        170: dict(population=250, kind='village', role='the salt-pans behind the shingle bar; the salt shore that knelt to the king without a blow',
                  cites=['I-0099', 'I-0100', 'I-0104', 'I-0104b', 'I-0175'], inferred=True),
        489: dict(era_name=dt('Seann Skell', 'burg 489'), era_name_en='Seann Skell (the old landings taken up)',
                  population=350, kind='village', role='hill-folk families settled in the empty river harbour, using the Old Ones\' mole and mending none of it',
                  cites=['I-0098', 'I-0097'], inferred=True),
        431: dict(population=150, kind='hamlet', role='the old harbour of the south taken up by Dia-thìreach households; busiest landing of the south coast within a few generations',
                  cites=['I-0210'], inferred=True),
        18: dict(population=60, kind='hamlet', role='households at the eastern Seann Dunn who cut into the old midden for a house-floor, found the tally stones and built elsewhere',
                 cites=['I-0252'], inferred=True),
        16: dict(population=10, kind='watch-tower', role='the Old Ones\' hollow-walled tower, used as a lookout: four watchers here saw the Sea-Watcher',
                 cites=['I-0165', 'I-0023'], inferred=True),
        398: dict(population=250, kind='village', role='the keepers of the southern beacon, on the cape round a well of reddish water; the greatest place on the south coast', cites=['I-0207', 'I-0164'], inferred=True),
        23: dict(population=220, kind='village', role='households below the ruined outpost; they take no stone from it', cites=['I-0205'], inferred=True),
        209: dict(population=250, kind='village', role='settled in rings under the oaks of the grove where the king was crowned', cites=['I-0194', 'I-0080b'], inferred=True),
        119: dict(population=180, kind='village', role='rebuilt in stone to the eaves after the Black Wind, the first walls on the coast built against wind', cites=['I-0159', 'I-0197'], inferred=True),
        95: dict(population=200, kind='village', role='households on the strait, built on the Old Ones\' middens', cites=['I-0190', 'I-0043'], inferred=True),
        476: dict(population=120, kind='hamlet', role='the long-house forty paces long, byre and hall under one roof, the greatest building of the north-west', cites=['I-0119'], inferred=True),
        26: dict(era_name=None, era_name_en='the harbour houses of the Red Hill', name_note='no name is recorded for the round houses by the harbour; Cathair dhomhain is named only in FE 634',
                 population=80, kind='hamlet', role='round houses by the harbour near enough the Red Hill to pay it salt', cites=['I-0117', 'II-0075'], inferred=True),
        28: dict(population=25, kind='flint pit', role='the only good flint on the island, worked in a pit on the hill; its flakes go to hearths from end to end of the island', cites=['I-0129'], inferred=True),
        123: dict(population=50, kind='hamlet', role='houses kept a stone\'s throw from the crack across the valley, marked by a line of white stones', cites=['I-0106', 'I-0107', 'I-0226'], inferred=True),
        198: dict(population=20, kind='hearth', role='the household of the first trench for another vein, which refuses its handful', cites=['I-0143', 'I-0249'], inferred=True),
        364: dict(era_name=None, era_name_en='the village above the wave-sand', name_note='the master town Cnoc chaol is founded later on this ground; no older name kept',
                  population=60, kind='hamlet', role='houses higher on the slope after two waves; none lost to the second', cites=['I-0105', 'I-0225'], inferred=True),
        304: dict(population=40, kind='hamlet', role='the green-stone quarry households; the quarry forsaken before the age ends', cites=['I-0219', 'I-0220'], inferred=True),
    }
    special = {k: v for k, v in special.items() if v}
    present = set()
    for i in sorted(BURGS):
        g = GAZ[i]
        founded = g['founded_age']
        if i in special:
            kw = dict(special[i])
            pol = polity_of.get(BURGS[i]['prov'], 'unclaimed')
            s.burg(i, polity=pol, culture='dia-thirich',
                   faith=('telling-of-the-making' if i == 276 else 'old-reverence'), **kw)
            present.add(i)
            continue
        if i in SEANN_RUINS:
            s.absent(i, 'an empty harbour of the Old Ones: silent since GE 551 and not yet resettled (resettled in the Holy Age by the gazetteer%s)' %
                     ({186: '; II-0039', 64: '; II-0040', 328: '; II-0053'}.get(i, '')),
                     ['I-0096', 'gazetteer B%d' % i] + ({186: ['II-0039'], 64: ['II-0040', 'I-0087'], 328: ['II-0053'], 128: ['I-0092'],
                                                        139: ['I-0095'], 402: ['I-0093'], 36: ['I-0180']}.get(i, [])),
                     state='ruin of the Old Ones')
            continue
        if founded in ('I', 'II'):
            if i in (192,):
                s.absent(i, 'a ring of stones of unknown builders; the Dia-thìrich make a place of it only in the Holy Age (ancestor-cairn FE 417)',
                         ['gazetteer B192', 'II-0054'], inferred=True, state='ring of stones, unsettled')
                continue
            fb = g.get('founded_between')
            # the tellings' villages, sized against the master's towns as they were counted at 1,000 people to the
            # unit (the Age of Ailean does not shrink with the present; eras/POP_LOG.md)
            pop = int(max(30, min(220, math.sqrt(BURGS[i]['pop'] * 1000.0 / RATE) * 1.0)))
            pop = rnd(pop, AGE)
            fbtxt = g['founded_by'].split(';')[0]
            role = fbtxt[0].upper() + fbtxt[1:]
            cites = ['gazetteer B%d' % i] + ([g['founded_event']] if g.get('founded_event') else [])
            s.burg(i, population=pop, kind=kind_for(pop, AGE), role=role, culture='dia-thirich', faith='old-reverence',
                   polity=polity_of.get(BURGS[i]['prov'], 'unclaimed'), cites=cites, inferred=True,
                   note=('founded GE %s–%s by the gazetteer' % (fb[0] + 7601, fb[1] + 7601)) if fb and fb[0] != fb[1] else None)
            present.add(i)
            continue
        s.absent(i, 'founded in Age %s%s' % (founded, (' (%s)' % g['founded_event']) if g.get('founded_event') else ''),
                 ['gazetteer B%d' % i] + ([g['founded_event']] if g.get('founded_event') else []))

    # ---------------------------------------------------------------- new burgs
    s.new_burg('II-N01', None, 'the heirs\' camp in the valley under Dùn ìseal', ('burg', 315),
               population=2000, kind='camp of tents', role='the king\'s kin come in from every coast to wait for their shares: a fire and a steward for each line, more than any reciter can name in a night',
               culture='dia-thirich', faith='old-reverence', polity='rioghachd',
               reason='the kin wait about the king for their shares at the snapshot; they stay on after the Binding to part the kingdom',
               cites=['I-0256', 'I-0208a', 'II-0001a', 'book III'], inferred=True)
    s.new_burg('II-N02', None, 'the war-camp of the eastern host', ('burg', 422),
               population=1500, kind='war camp', role='the spears of the east, gathered since GE 4,520, moving down to the ford below Dùn dhearg',
               culture='dia-thirich', faith='old-reverence', polity='dun-dhearg',
               reason='the host that comes against the king at the ford (FE 1); its numbers are not told, only that its dead dammed the river',
               cites=['I-0255b', 'I-0256', 'I-0098a'], inferred=True)
    s.new_burg('II-N03', None, 'the salt-folk\'s shelters at the ford gathering', ('marker', 38),
               population=0, kind='seasonal fair-ground', role='the ford where salt was first traded for wool: salt people downstream, hill people upstream, flint people on the far bank, Dùn dhearg on ground of its own',
               culture='dia-thirich', faith='old-reverence', polity='rioghachd',
               reason='the yearly gathering at the ford from GE 1,208; no one is said to live there between gatherings (Muileann òg is founded in the Holy Age)',
               cites=['I-0113', 'I-0114', 'I-0218', 'I-0236', 'I-0208a'], inferred=True)
    s.new_burg('II-N04', None, 'the ring of shelters at the warm springs', ('marker', 0),
               population=20, kind='pilgrim shelters', role='pilgrims in numbers; the eldest healing-tale is set here', culture='dia-thirich',
               faith='old-reverence', polity='rioghachd', reason='a ring of shelters built GE 2,455; the bath-house comes only in FE 529',
               cites=['I-0187', 'II-0063'], inferred=True)

    # ---------------------------------------------------------------- routes
    named = {
        410: dict(first='I', name='Slighe-mhara àrsaidh', group='searoutes', cites=['I-0064a'], note='the fishers of the south-east coast keep to the Old Ones\' lane'),
        264: dict(first='III', name='Slighe Cnoc leathan', group='trails', cites=['II-0207'], track_before=True),
        16: dict(first='III', group='trails', cites=['II-0035'], track_before=True), 39: dict(first='III', cites=['II-0035'], track_before=True),
        52: dict(first='III', cites=['II-0035'], track_before=True), 70: dict(first='III', cites=['II-0035'], track_before=True),
        111: dict(first='III', cites=['II-0035'], track_before=True), 115: dict(first='III', cites=['II-0035'], track_before=True),
        130: dict(first='III', cites=['II-0035'], track_before=True), 131: dict(first='III', cites=['II-0035'], track_before=True),
        446: dict(first='III', cites=['II-0035'], track_before=True),
        3: dict(first='III', cites=['II-0057'], track_before=True),
        17: dict(first='IV', cites=['III-0145'], track_before=True), 98: dict(first='IV', cites=['III-0145'], track_before=True),
        173: dict(first='IV', cites=['III-0114'], track_before=True), 175: dict(first='IV', cites=['III-0114'], track_before=True),
        210: dict(first='IV', cites=['III-0114'], track_before=True), 229: dict(first='IV', cites=['III-0114'], track_before=True),
        233: dict(first='IV', cites=['III-0114'], track_before=True), 248: dict(first='IV', cites=['III-0114'], track_before=True),
        447: dict(first='IV', cites=['III-0114'], track_before=True),
        50: dict(first='VI', cites=['V-0090']), 71: dict(first='VI', cites=['V-0090']),
        403: dict(first='IV', cites=['III-0168b']), 354: dict(first='IV', cites=['III-0189a']), 349: dict(first='V', cites=['IV-0076a']),
        383: dict(first='IV', last='IV', cites=['III-0215']), 385: dict(first='VI', cites=['gazetteer B205'], inferred=True),
    }
    classify_routes(d, AGE, present, named, touched_rule(min_touch=1, allow_empty=False),
                    'A master trail or sea-lane is present when every town it touches stands in this age (or both its end towns '
                    'stand and at most a quarter of the sites between are not yet towns); trails and lanes that touch no town, and '
                    'the roads and lanes the annals date later, are absent. The two great carrying ways of the age are added.')
    d['routes']['new'] = [
        collections.OrderedDict([('key', 'II-R01'), ('name', None), ('name_en', 'the flint road'), ('group', 'trails'),
                                 ('points', [{'burg': 28}, {'cell': near_cell(('burg', 441), 7)}, {'marker': 38}]),
                                 ('note', 'worn by the flint-carriers from Cnoc àrsaidh south and east toward the ford gathering; near Àth leathan their feet sink it a yard deep'),
                                 ('cites', ['I-0129', 'I-0130'])]),
        collections.OrderedDict([('key', 'II-R02'), ('name', None), ('name_en', 'the salt road'), ('group', 'trails'),
                                 ('points', [{'burg': 170}, {'marker': 38}, {'burg': 244}]),
                                 ('note', 'from the pans of Baile ghorm by the ford gathering to the north-west; at Muileann àrsaidh salt costs three times its price at the pans'),
                                 ('cites', ['I-0193', 'I-0115'])]),
        collections.OrderedDict([('key', 'II-R03'), ('name', None), ('name_en', 'the stepping-stones of the Abhainn fhionn'), ('group', 'trails'),
                                 ('points', [{'burg': 88}, {'cell': near_cell(('burg', 88), 71, {BURGS[88]['cell']})}]),
                                 ('note', 'the first made crossing of any river on the island'), ('cites', ['I-0221']), ('inferred', True)]),
        collections.OrderedDict([('key', 'II-R04'), ('name', None), ('name_en', 'the road of the salt and wool (the Red Hill to the ford)'), ('group', 'trails'),
                                 ('points', [{'burg': 19}, {'burg': 255}, {'marker': 38}]),
                                 ('note', 'Murchadh Gearr walked the salt road every year to be seen on it; Dùn chrom\'s bank faces both ways between the Red Hill and the hills of the vein'),
                                 ('cites', ['I-0115', 'I-0204']), ('inferred', True)]),
    ]

    # ---------------------------------------------------------------- markers
    M = {
        0: dict(note='Pilgrims in numbers and a ring of shelters; a herder came lame and walked home. The herds of Dùn ìseal wintered here under Gormshuil and drank here in the dry year.', cites=['I-0187', 'I-0084', 'I-0224']),
        12: dict(era_name_en='the beacon on the north-western headland', icon='🔥', note='The headland fire of Baile chrom, one of the five points the coasts are lit at.', cites=['I-0041', 'I-0164']),
        13: dict(era_name_en='the storm beacon on the eastern cape', icon='🔥', note='Kept by the coast households in turn to bring boats home in a storm, not to warn them off.', cites=['I-0161']),
        14: dict(era_name_en='the shore-fire on the northern point', icon='🔥', note='Its ash goes down through three yards of fire-reddened soil.', cites=['I-0162']),
        15: dict(era_name_en='the fire on the north-eastern cape', icon='🔥', note='Steps cut up to it from the shore, narrower than those at Seann Bhral.', cites=['I-0163']),
        16: dict(era_name_en='the fire on the southern cape', icon='🔥', note='Kept for the boats of the south coast; with the other four the coasts are lit at five points.', cites=['I-0164']),
        19: dict(note='The western shaft of the Old Ones; stones thrown in are not heard to land.', cites=['I-0037']),
        20: dict(note='A youth was let down on a rope of plaited hide to the rope\'s end and drawn up alive; he never told what lay below, and no one goes down again in this age.', cites=['I-0120']),
        21: dict(note='Four watchers on the Seann Skell tower see a back as long as three boats; wreckage of stitched boats washes up in the western water.', cites=['I-0165', 'I-0166']),
        22: dict(note='A herding family that lit an open fire vanished; two herders without a fire saw a figure walk the ridge breathless, and lived. The covered hearth spreads to Muileann chiar.', cites=['I-0121', 'I-0188', 'I-0189']),
        23: dict(era_name_en='the uncut forest of the white stag', note='Pilgrims sit a night at the line of the trees without entering; their small fires lie all along the edge.', cites=['I-0184']),
        24: dict(era_name_en='the unclaimed forest', note='A child of Cnoc bheag went past the line of stones and was not found; the settlers take timber only from the far side of the river.', cites=['I-0185', 'I-0186']),
        28: dict(note='The obelisk with the unread line and the four Dia-thìris words.', cites=['I-0069', 'I-0070']),
        29: dict(note='Cuimhnich an teine, in its ring of fire-cracked stones.', cites=['I-0071', 'I-0072']),
        30: dict(note='After Anndra Breac was put out of the ford for saying "we came", the saying on the column is spoken as a rule at the opening of the gathering; its worn words are recut by a hand from the hill (GE 4,364).', cites=['I-0167', 'I-0168', 'I-0251']),
        31: dict(note='Ruin of the Old Ones\' outpost; the households of Cathair mhòr below take no stone from it.', cites=['I-0059', 'I-0205']),
        32: dict(note='Ruin of the fortress; the fishers of Ceann mhin will not go up to it.', cites=['I-0061', 'I-0209']),
        33: dict(note='The temple ruin: the Dia-thìrich pass it without stopping, and a path is worn round it at a distance.', cites=['I-0063', 'I-0216']),
        34: dict(era_name=None, era_name_en='the cairns of the heads of households on the hill', icon='🪨', note='A cairn for each head of a household at death, on the slope above the cattle-fold; some forty by the end of the age.', cites=['I-0213', 'I-0214']),
        37: dict(era_name=None, era_name_en='the games by the wind-stones', icon='🤼', note='The gathering at the eight wind-stones of Ceann leathan ends with wrestling and the lifting of stones; the black boulder lies there still.', cites=['I-0137', 'I-0217']),
        38: dict(era_name=None, era_name_en='the ford gathering', icon='🤝', note='Raghnall Ceannfhionn and the holder of the Red Hill agreed salt for wool here; it became the yearly gathering. At the great gathering (GE 3,000) the holders set their hands in the king\'s with four hundred of his blood about him. Both king-lists were recited here whole.', cites=['I-0113', 'I-0114', 'I-0142', 'I-0208a', 'I-0218', 'I-0245']),
        39: dict(era_name=None, era_name_en='the landing of the dug-out', note='A boat hollowed from one oak trunk, long enough for six, sunk and left at the landing.', cites=['I-0103']),
        40: dict(note='The panthers turn back at the foothills (a hard winter follows); cattle driven into the passes out of season are taken.', cites=['I-0177', 'I-0178', 'I-0179']),
        41: dict(note='A family by the burial ground takes on the clearing of thorn; diggers break into a grave lined in the Old Ones\' manner, close it and move the row.', cites=['I-0182', 'I-0183']),
        46: dict(note='The keeper\'s cup and its three copies set side by side on a flat stone and filled from the spring in turn.', cites=['I-0154a']),
        48: dict(note='The Mason\'s Point.', cites=['I-0027a']),
    }
    for i in sorted(MARKERS):
        if i in M:
            s.marker(i, **M[i])
        else:
            d['markers']['absent'].append(i)
    c_grove = near_cell(('burg', 209), 23)
    ford = near_cell(('burg', 422), 85)
    NM = [
        ('II-K01', None, 'the crowning in the grove', ('cell', c_grove), '👑', 'I-0080b',
         'Ailean kept the seven fires seven nights, fasting; on the eighth Caoran came with the Tuath Dè and named him Rìgh Chlann nan Dè, and put into him the power that was in the coals.', ['I-0080b']),
        ('II-K02', dt('Àth na Fala', 'marker II-K02'), 'the ford below Dùn dhearg (named for the blood after the battle)', ('cell', ford), '⚔️', 'I-0098a',
         'The ford where the host of the east comes against the king. The battle opens the next day: he holds it alone three days and three nights, the dead of the host dam the river, and he falls on the third night. The ford is called Àth na Fala after.', ['I-0098a', 'I-0255b', 'I-0256']),
        ('II-K03', None, 'the boundary stones of Dòmhnall Clachach', ('cell', near_cell(('burg', 315), 35, {BURGS[315]['cell']})), '🪨', 'I-0085',
         'Marker stones along the valley below the hill, parting the grazing of Dùn ìseal from its neighbours\'; some still stand and are argued over.', ['I-0085']),
        ('II-K04', None, 'where the Red Hill knelt', ('cell', near_cell(('burg', 19), 1)), '🙇', 'I-0089a',
         'Uisdean Mòr came down to the lake shore and knelt to the king.', ['I-0089a']),
        ('II-K05', None, 'the shingle of Baile ghorm', ('burg', 170), '🧂', 'I-0104b',
         'Iain Dubh, the king\'s son, was slain here raiding the salt; the king came down alone, and none struck. The salt shore became his without blood.', ['I-0099', 'I-0104', 'I-0104b']),
        ('II-K06', None, 'the keepers\' house and the stone cup', ('burg', 276), '🥣', 'I-0152',
         'A house for the holder of the lot, its door facing the slab; Oighrig nic Dhòmhnaill\'s cup of grey stone, the measure of every handful; the coal of Gilleasbuig Beag laid back under the slab.', ['I-0152', 'I-0153', 'I-0156']),
        ('II-K07', None, 'the hawk lintel of Àth mhòr', ('burg', 436), '🦅', 'I-0131',
         'A hawk carved over a house door, wings closed, head turned: the oldest carving of any bird on the island.', ['I-0131']),
        ('II-K08', None, 'the wolf graves of Tobar fhiadhaich', ('burg', 435), '🐺', 'I-0132',
         'Wolves buried whole and with care, laid on their sides as people are.', ['I-0132']),
        ('II-K09', None, 'Gilleasbuig Beag\'s island', ('cell', 510), '🏝️', 'I-0155',
         'The keeper who took coal was rowed out to Eilean chrom and left without a boat; his fire was seen three nights. The island stays empty and unfished.', ['I-0155', 'I-0254']),
        ('II-K10', None, 'the tide-rock of Ros dhomhain', ('burg', 27), '📏', 'I-0127',
         'High-water marks cut at an even interval on a boulder in the harbour mouth; Seònaid Mhòr cut hers in pairs. A third rock is kept at Inis thais.', ['I-0127', 'I-0128', 'I-0169', 'I-0170']),
        ('II-K11', None, 'the stone of the Black Wind', ('burg', 457), '🌪️', 'I-0223',
         'A stone set in the midst of Ceann chiar with a mark for every house the Black Wind took: twenty-two.', ['I-0159', 'I-0223']),
        ('II-K12', None, 'the white stones of the fault', ('burg', 123), '⚪', 'I-0107',
         'A line of white stones along the crack; no house within a stone\'s throw. Broken in two places when the ground shook again, and laid again.', ['I-0107', 'I-0226']),
        ('II-K13', None, 'the first trench for another vein', ('burg', 198), '⛏️', 'I-0143',
         'Diggers from Dùn ìseal opened it seeking coal like the vein\'s and left it when two were crushed. A second opening elsewhere found common rock, and the prospecting ended.', ['I-0143', 'I-0144', 'I-0145']),
        ('II-K14', None, 'the tally wall of Seann Warr', ('burg', 128), '🧱', 'I-0092',
         'The Old Ones\' counting stones built into a wall, some three thousand strokes; they thicken together in the bad years.', ['I-0092', 'I-0094']),
        ('II-K15', None, 'the half-cut stone', ('burg', 139), '🪨', 'I-0095',
         'The last tally stone of the Old Ones, two strokes finished and a third begun and forsaken.', ['I-0095', 'I-0096']),
        ('II-K16', None, 'the wind-stones and the eight notches', ('cell', 420), '🧭', 'I-0138',
         'The eight wind-names cut on the high point of Eilean fhada as on the main island; eight tall stones on the point at Ceann leathan.', ['I-0136', 'I-0137', 'I-0138']),
        ('II-K17', None, 'Eilean ìseal, the island of the dead', ('cell', 3295), '⚱️', 'I-0253',
         'The households of the south-east coast begin to row their dead here after the old manner of the Old Ones.', ['I-0253']),
        ('II-K18', None, 'the long-house of Cathair gheal', ('burg', 476), '🏠', 'I-0119',
         'Forty paces long, byre and hall under one roof; twice burned and twice rebuilt on the same footing.', ['I-0119']),
        ('II-K19', None, 'the wind-stone of Seann Chwen', ('burg', 36), '🧭', 'I-0180',
         'A wind-name cut in the Dia-thìreach manner over an older mark of the Old Ones.', ['I-0180']),
    ]
    for key, name, en, at, icon, eid, note, cites in NM:
        s.new_marker(key, name, en, at, icon=icon, event=eid, note=note, cites=cites)

    # ---------------------------------------------------------------- zones
    Z = []

    def zone(key, name_en, typ, provs, note, cites, name=None, master_zone=None, date=None):
        z = collections.OrderedDict([('key', key), ('name', name), ('name_en', name_en), ('type', typ)])
        if date:
            z['date'] = date
        if master_zone is not None:
            z['master_zone'] = master_zone
        z['provinces'] = provs
        z['note'] = note
        z['cites'] = cites
        if name:
            dt(name, 'zone ' + key)
        Z.append(z)
    zone('II-Z01', 'the first kingdom: the hill and its valleys (GE 1)', 'conquest', [35, 87, 34, 12, 111, 112, 65],
         'Ailean takes the hill and brings the households of the valleys under his hand.', ['I-0081'], date=ann_date('I-0081'))
    zone('II-Z02', 'the Red Hill bends the knee (GE 290)', 'conquest', [1, 22, 32, 106, 71, 67],
         'The Red Hill keeps its holders and swears to the king.', ['I-0089a'], date=ann_date('I-0089a'))
    zone('II-Z03', 'the salt shore bends the knee (GE 728)', 'conquest', [25, 78, 10, 72, 17, 108, 100, 19, 49, 11],
         'No blood is shed and none is paid.', ['I-0104b'], date=ann_date('I-0104b'))
    zone('II-Z04', 'the great gathering at the ford (GE 3,000): the north and the west set their hands in the king\'s', 'conquest',
         king['admin_units'][2]['provinces'] + king['admin_units'][3]['provinces'],
         'Only the households east of the vein send no one.', ['I-0208a'], date=ann_date('I-0208a'))
    zone('II-Z05', 'the hunger at Baile chrom (GE 1,966)', 'famine', [28, 14],
         'Pots left full of boiled bark and seaweed; the grave-rows doubled. The oldest hunger tied to a place.', ['I-0134'], master_zone=1, date=ann_date('I-0134'))
    zone('II-Z06', 'the drought at Achadh shean (GE 2,006)', 'drought', [61],
         'The springs run dry so long that the field banks are forsaken; the fields are cut anew on another line.', ['I-0135', 'I-0211'], master_zone=2, date=ann_date('I-0135'))
    zone('II-Z07', 'the ground opens at Cill ghlas (GE 827; again GE 3,863)', 'fault', [96],
         'A crack a man could fall into; a spring moves a hundred paces downhill and back.', ['I-0106', 'I-0226'], master_zone=3, date=ann_date('I-0106'))
    zone('II-Z08', 'the waves at Cnoc chaol (GE 777; GE 3,817)', 'wave', [120],
         'Sand a hand thick with deep-water shells over the hearths; the second wave takes no house.', ['I-0105', 'I-0225'], master_zone=4, date=ann_date('I-0105'))
    zone('II-Z09', 'A\' Ghaoth Dhubh, the Black Wind (GE 2,417)', 'storm', [82, 60, 70, 61, 69],
         'Strips the thatch from every house of the east coast from Cuan ruadh to Ceann chiar; the coast feeds Cuan ruadh through the winter from its shared surplus.', ['I-0159', 'I-0160'],
         name='A\' Ghaoth Dhubh', date=ann_date('I-0159'))
    zone('II-Z10', 'the host of the east (GE 4,520 to the snapshot)', 'war', east,
         'The households east of the vein, sworn to owe nothing to Dùn ìseal, gather their spears at Dùn dhearg.', ['I-0255b', 'I-0256'])
    zone('II-Z11', 'the last counts of the Old Ones (GE 308–551)', 'earlier moment', [100, 31, 11, 39, 102, 110],
         'Strokes on midden stones, the tally wall of Seann Warr, the count at Seann Tarr; the bad years on three coasts at once; the half-cut stone; silence.', ['I-0090', 'I-0092', 'I-0093', 'I-0094', 'I-0095', 'I-0096'])
    zone('II-Z12', 'the moor takes the north (GE 3,588)', 'land', [23, 88, 91, 86, 7, 51, 45, 9, 113, 68, 27, 83, 92, 26],
         'The oak falls back; heather, birch and bog-moss spread over the northern lowlands and the winters lengthen.', ['I-0220a'])
    d['zones'] = Z
    d['labels'] = [
        {'text': 'Rìoghachd Chlann nan Dè', 'text_en': 'the kingdom of the godkin', 'at': {'burg': 315}, 'cites': ['I-0081']},
        {'text': None, 'text_en': 'the kin wait for their shares', 'at': {'new_burg': 'II-N01'}, 'cites': ['I-0256']},
        {'text': None, 'text_en': 'the spears of the east', 'at': {'burg': 422}, 'cites': ['I-0255b']},
        {'text': 'Cha do thàinig sinn; bha sinn ann', 'text_en': 'we did not come; we were here', 'at': {'marker': 30}, 'cites': ['I-0168']},
    ]
    for l in d['labels']:
        if l['text']:
            dt(l['text'], 'label', 'phrase')

    # ---------------------------------------------------------------- military
    d['military']['hosts'] = [
        collections.OrderedDict([('name', None), ('name_en', 'the host of Dùn dhearg and the eastern households'), ('polity', 'dun-dhearg'),
                                 ('station', {'burg': 422}), ('strength', 'not told; its dead dammed the river'),
                                 ('note', 'Gathered at Dùn dhearg since GE 4,520; at the snapshot it comes down to the ford.'), ('cites', ['I-0255b', 'I-0098a'])]),
        collections.OrderedDict([('name', dt('Ailean Mòr', 'host', 'person')), ('name_en', 'the king, alone'), ('polity', 'rioghachd'),
                                 ('station', {'cell': ford}), ('strength', 'one man'),
                                 ('note', 'He holds the ford alone three days and three nights; the kin who should have come are quarrelling over the shares.'), ('cites', ['I-0098a', 'App.C Blàr Àth na Fala'])]),
        collections.OrderedDict([('name', dt('Ìomhar Dearg', 'host', 'person')), ('name_en', 'the household of Ìomhar Dearg'), ('polity', 'rioghachd'),
                                 ('station', {'new_burg': 'II-N01'}), ('strength', 'a household'),
                                 ('note', 'A son of the king, some fourteen hundred years old; still in the valley arguing for river-grazing. He rides east late, falls on the spent host the morning after the king falls and takes Dùn dhearg.'), ('cites', ['App.C Blàr Àth na Fala', 'II-0001b', 'book III'])]),
    ]
    d['military']['campaigns'] = [
        collections.OrderedDict([('name', None), ('name_en', 'the salt-flats raid'), ('date', ann_date('I-0099')), ('at', {'burg': 170}),
                                 ('sides', ['Mòrag Chruaidh and the hill-folk', 'the salt-pans that did not own the king']),
                                 ('note', 'The first war in either list; seven fell on the hill side.'), ('cites', ['I-0099'])]),
        collections.OrderedDict([('name', None), ('name_en', 'the death of Iain Dubh and the king at Baile ghorm'), ('date', ann_date('I-0104b')), ('at', {'burg': 170}),
                                 ('note', 'Iain Dubh slain on the shingle; the king came alone and the salt shore knelt.'), ('cites', ['I-0104', 'I-0104b'])]),
        collections.OrderedDict([('name', None), ('name_en', 'the king\'s wars over the island'), ('date', 'GE 1–4,603'),
                                 ('note', 'The lists keep no count of the wars the king rode to, only that he came home from all of them but the last. How he won, none who stood against him could say.'), ('cites', ['I-0081', 'App.C Before the wars'])]),
        collections.OrderedDict([('name', dt('Blàr Àth na Fala', 'campaign')), ('name_en', 'the Battle of the Ford of Blood (opens the next day)'), ('date', ann_date('I-0098a')),
                                 ('at', {'cell': ford}), ('sides', ['Ailean Mòr, alone', 'the host of Dùn dhearg and the east']),
                                 ('note', 'Shown as imminent: it is the opening event of the Holy Age.'), ('cites', ['I-0098a', 'App.C Blàr Àth na Fala'])]),
    ]
    d['arms'] = [
        collections.OrderedDict([('polity', 'rioghachd'), ('blazon', None), ('signs', None),
                                 ('note', 'No arms: the first arms on the island are the seal of the vein-house in the Age of Sundering.'), ('cites', ['App.J §I'])]),
        collections.OrderedDict([('polity', 'red-hill'), ('blazon', None), ('signs', 'the red stone of the hill (inferred)'), ('note', 'No arms.'), ('cites', ['App.J §I']), ('inferred', True)]),
        collections.OrderedDict([('polity', 'dun-dhearg'), ('blazon', None), ('signs', None), ('note', 'No arms.'), ('cites', ['App.J §I'])]),
        collections.OrderedDict([('polity', 'keepers'), ('blazon', None), ('signs', 'the stone cup of grey stone', ), ('note', 'No arms; the cup is the keepers\' measure and token.'), ('cites', ['I-0153', 'App.J §I'])]),
    ]
    d['notes']['polities'] = collections.OrderedDict([
        ('rioghachd', 'The first kingdom is one man: Ailean Mòr, crowned by the gods in the grove, who took the hill of Dùn ìseal and brought the island under his hand in four and a half thousand years of riding. His children and kin held the hill for him one after another and are counted as the Stone Kings; since the last of them he has held it himself. He has told no one what is in him.'),
        ('red-hill', 'The Red Hill on the lake is an old line not of the king\'s blood, which knelt to him and kept its own holders and its own list. It traded salt for wool with the hill at the ford and fostered a son of Eilidh Ghlas. Its list ends with Seumas Òg, and its name is not yet Cathair dhearg.'),
        ('dun-dhearg', 'East of the vein the households raised a double-banked fort at Dùn dhearg and never came to the gatherings until Catrìona Mhòr\'s time, and then only to trade. When the king bade them come in they swore to owe nothing to him. Their host is at the ford.'),
        ('keepers', 'The keepers of the slab are drawn by lot, one for each of the nine districts of the hills, and watch the burnt vein at Tobar dhìreach. They refused Calum Ciar the lot, and the king would not overrule them. They have asked to have their charge declared before the whole gathering, and it has not been.'),
    ])
    d['notes']['burgs'] = collections.OrderedDict([
        ('315', 'Dùn ìseal: two banks and ditches on the hill the first king took, the shared store within them, the valley below full of the tents of his kin.'),
        ('19', 'The Red Hill: ditch and palisade across the neck of the hill above the lake, a laid-stone landing at the river-mouth, and the Red Hill list kept by its reciters.'),
        ('422', 'Dùn dhearg: a double bank on the grass plateau east of the vein, where the spears of the east have gathered.'),
        ('276', 'Tobar dhìreach: the slab, the keepers\' house facing it, the lot of the nine and the pilgrims; Clann na Ceiste keep the lines here.'),
        ('27', 'Ros dhomhain: some sixty houses round the tide-rock, the greatest place on the shores of Loch chrom.'),
        ('489', 'Seann Skell: hill-folk families in the Old Ones\' river harbour, using the old mole and mending none of it.'),
    ])
    return s.finish()
