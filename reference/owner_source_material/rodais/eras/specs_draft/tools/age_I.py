"""Age I, the Ancient Age (Vein Era): the island on the eve of the crowning."""
from common import *  # noqa: F401,F403

AGE = 'I'


def build():
    reset_names()
    s = Spec(AGE, collections.OrderedDict([
        ('age', 'I'),
        ('age_name', {'name': dt('An Aois Àrsaidh', 'age name'), 'name_en': 'the Ancient Age'}),
        ('era', {'abbr': 'VE', 'name': dt('Linn na Fèithe', 'era name'), 'name_en': 'the Vein Era'}),
        ('snapshot', collections.OrderedDict([
            ('date', '8 an Lùnastal, VE 5,324'),
            ('plan_label', 'VE 5,323 (ERA_PLAN): the last full year of the Vein Era; the snapshot is the eve of the crowning in that same year'),
            ('y', -7600), ('m', 8), ('d', 8),
            ('last_event_shown', 'I-0080a'),
            ('next_event', 'I-0080b'),
            ('description',
             "The island has no king and no name. On the coasts the Old Ones keep their landings, middens and moles from "
             "the river harbour at Skell round every shore, though they have long since left the high places and every new "
             "work of theirs looks on salt water; their walled outpost, their three-ringed fortress and their temple that faces "
             "the mountains already lie in ruin. In the high valleys about the burnt vein the hill-folk, who call themselves "
             "Clann nan Dè and say they were always there, live in small hearth-kindreds, bury their dead in the ground, keep "
             "the covered hearths of the Doire uaine hills, leave two forests uncut and walk to the column at Cnoc ghorm to hear "
             "that they did not come. At Tobar dhìreach the Mason's line, now called Clann na Ceiste, has lit six of the seven "
             "coals each by its own spirit over five thousand years; and in the oak grove at Doire ghlas Ailean son of Suibhne "
             "sits by the seven burning coals, the rainbow among them lit by the Keeper, fasting on the last night of his vigil. "
             "The oak stands over the northern lowlands, the north-western horn is bare, and Eilean dhubh has been an island since "
             "the sea drowned its neck."),
            ('cites', ['I-0080a', 'I-0065', 'I-0064', 'I-0056', 'I-0059', 'I-0061', 'I-0063', 'I-0046', 'I-0073', 'I-0074',
                       'I-0068a', 'I-0006', 'I-0006a', 'I-0007']),
        ])),
        ('land_changes', [
            collections.OrderedDict([('what', 'The northern lowlands are oak and hazel woodland, not moor: the oak came after the cold years and has not yet fallen back. Biome change only; coast, rivers and heights as on the master map.'),
                                     ('provinces', [23, 88, 91, 86, 7, 51, 45, 9, 113, 68, 27, 83, 92, 26, 54, 56, 62, 115, 20, 104, 8, 98]),
                                     ('cites', ['I-0006', 'I-0220a']), ('inferred', True)]),
            collections.OrderedDict([('what', 'The north-western horn and the windy coast stay bare heather and bog, as now.'),
                                     ('cites', ['I-0006a'])]),
            collections.OrderedDict([('what', 'Eilean dhubh is already an island at the snapshot (its neck drowned in VE 506), so the coast is as on the master map; the neck is shown only as an earlier-moment zone.'),
                                     ('cites', ['I-0007'])]),
            collections.OrderedDict([('what', 'The lake dwellings of Loch chrom stand on their oak piles in the shallows (burned in GE 1,525).'),
                                     ('cites', ['I-0020', 'I-0122'])]),
        ]),
    ]))
    d = s.d

    # ---------------------------------------------------------------- cultures
    d['cultures'] = [
        collections.OrderedDict([('key', 'seann-dhaoine'), ('name', dt('Na Seann-Dhaoine', 'culture')), ('name_en', 'the Old Ones'),
                                 ('master_culture', 0),
                                 ('provinces', []),
                                 ('note', 'The coastal people of the landings, middens and moles; their own name is not known. They cut the unread script and count their dead on stones only in the next age.'),
                                 ('cites', ['I-0010', 'I-0056', 'I-0064', 'I-0017'])]),
        collections.OrderedDict([('key', 'clann-nan-de'), ('name', dt('Clann nan Dè', 'culture')), ('name_en', 'the godkin, the hill-folk'),
                                 ('master_culture', 2),
                                 ('provinces', []),
                                 ('note', 'The hill-folk of the high valleys, forebears of the Dia-thìrich (that name is not taken until GE 2,201). They bury in the ground and cut no script. The Mason\'s line, the hearths of the east, the north-shore hunters and the lake-shore folk of the Red Hill are all counted here.'),
                                 ('cites', ['I-0065', 'I-0140'])]),
    ]

    # ---------------------------------------------------------------- faiths
    d['faiths'] = [
        collections.OrderedDict([('key', 'old-reverence'), ('name', dt('An Seann Urram', 'faith')), ('name_en', 'the old reverence of the hearths'),
                                 ('inferred_name', True),
                                 ('master_religion', 2), ('type', 'Folk'), ('form', 'ancestor and hearth reverence'),
                                 ('deity', None),
                                 ('provinces', []),
                                 ('practice', 'The slab over the burnt vein; the dead laid in the ground; the covered hearths of Doire uaine; two forests left uncut; the saying on the column, Cha do thàinig sinn; bha sinn ann. No priests, no temples, no god named.'),
                                 ('cites', ['I-0003', 'I-0046', 'I-0048', 'I-0051', 'I-0073', 'I-0074', 'I-0075', 'App.B §II'])]),
        collections.OrderedDict([('key', 'telling-of-the-making'), ('name', dt('Aithris a\' Chruthachaidh', 'faith')), ('name_en', 'the Telling of the Making'),
                                 ('master_religion', 1), ('type', 'Kindred lore'), ('form', 'a telling kept within one kindred'),
                                 ('deity', 'Caoran the Young God, with an Dagda, Danu and the Tuath Dè; Coimhdeach na Fine, the Keeper of the Kin'),
                                 ('provinces', [114]),
                                 ('practice', 'Told by the Keeper to Diarmad in the grove (VE 890) and kept by Clann na Ceiste with the riddle of the spirits; the lightings of the coals are its rites. It is the root from which the Old Faith later names its gods; at this date it has no order and no house.'),
                                 ('cites', ['I-0011a', 'I-0017a', 'I-0080a', 'App.B §III'])]),
        collections.OrderedDict([('key', 'old-ones-rite'), ('name', None), ('name_en', 'the rites of the Old Ones (unknown)'),
                                 ('master_religion', None), ('type', 'unknown'), ('form', 'unknown'),
                                 ('deity', None),
                                 ('provinces', []),
                                 ('practice', 'Their dead are rowed to Eilean dhearg and laid in stone boxes facing the mainland; their temple, with its altar turned to the central mountains, was stripped and forsaken by VE 4,275. What they held holy is not known.'),
                                 ('cites', ['I-0014', 'I-0035', 'I-0062', 'I-0063'])]),
    ]

    # ---------------------------------------------------------------- polities
    s.polity('seann-dhaoine', dt('Na Seann-Dhaoine', 'polity'), "the Old Ones' shores",
             form='coastal landings of one people; no ruler, council or bound is known',
             capital={'burg': 489}, ruler=None, culture='seann-dhaoine', color='#7f8fa6 (slate blue-grey, the sea-stone of their moles)',
             cites=['I-0056', 'I-0064', 'I-0012'],
             admin_units=[
                 {'name': None, 'name_en': 'the ten Seann places and the islands off them (VE 3,872)',
                  'kind': 'extent', 'provinces': [], 'cites': ['I-0056']},
             ])
    s.polity('clann-na-ceiste', dt('Clann na Ceiste', 'polity'), 'the Children of the Question (the Mason\'s line)',
             form='a kindred of the high valleys, keepers of the recited Line of the Mason',
             capital={'burg': 276},
             ruler={'name': 'Suibhne', 'note': 'father of Ailean; the line names him and no deed (App.A). Ailean mac Shuibhne keeps the vigil in the grove at the snapshot.', 'inferred': True},
             culture='clann-nan-de', color='#c8a24a (the gold of the first lit coal)',
             cites=['I-0068a', 'I-0073a', 'I-0080a', 'App.A Line of the Mason'])
    s.polity('hill-folk', dt('Clann nan Dè', 'polity'), 'the hill-folk of the high valleys',
             form='hearth-kindreds of the central mountains; no ruler; they meet at the column and at Tobar dhìreach',
             capital=None, ruler=None, culture='clann-nan-de', color='#8c6d46 (peat brown)',
             cites=['I-0065', 'I-0005', 'I-0046', 'I-0066'],
             admin_units=[{'name': None, 'name_en': 'the hearths of the Doire uaine hills (covered hearths)', 'kind': 'hearth-country',
                           'provinces': [112], 'cites': ['I-0046']},
                          {'name': None, 'name_en': 'the high valleys about the crack', 'kind': 'hearth-country',
                           'provinces': [65, 111, 35, 96, 48], 'cites': ['I-0005', 'I-0065', 'I-0066']}])
    s.polity('eastern-hearths', dt('Teaghlaichean an Ear', 'polity'), 'the hill households of the east',
             inferred_name=True,
             form='farm and hunting households of the eastern oak country',
             capital={'burg': 61}, ruler=None, culture='clann-nan-de', color='#5f8a4e (oak green)',
             cites=['I-0053', 'I-0054', 'gazetteer B61'], inferred=True)
    s.polity('north-shore', dt('Sealgairean a\' Chladaich', 'polity'), 'the hunters of the north-west shore',
             inferred_name=True,
             form='seal- and fish-hunting households of the north-west coast, out of the Sea-Watcher\'s sight',
             capital={'burg': 238}, ruler=None, culture='clann-nan-de', color='#4f7d8c (sea-grey)',
             cites=['I-0039', 'I-0042', 'I-0043', 'I-0008a', 'gazetteer B238'], inferred=True)
    s.polity('red-hill', dt('Muinntir a\' Chnuic Dheirg', 'polity'), 'the folk of the Red Hill (the lake shore)',
             inferred_name=True,
             form='an old line of the western lake shore; its spoken list begins only in the next age',
             capital={'burg': 19}, ruler=None, culture='clann-nan-de', color='#a8443a (red stone)',
             cites=['I-0083', 'I-0020', 'App.A holders of the Red Hill'], inferred=True)

    coast_old = [3, 105, 100, 110, 103, 31, 68, 64, 95, 121, 50, 13, 120, 39, 51, 11, 74, 60, 76, 83, 58, 102, 99, 4,
                 77, 38, 15, 2, 17, 72, 10, 25, 78, 108, 49, 19, 55, 53, 24, 116, 63, 80, 59, 43, 109, 101, 70, 123,
                 82, 30, 118, 115, 104, 8, 62, 56, 54, 119, 27, 113, 92, 9, 45, 91, 122]
    assign = {
        'seann-dhaoine': coast_old,
        'clann-na-ceiste': [114],
        'hill-folk': [112, 65, 111, 35, 96, 48, 87, 21, 90, 34],
        'eastern-hearths': [69, 66, 41, 61, 89, 16],
        'north-shore': [14, 7, 36, 86, 23, 88],
        'red-hill': [1, 5, 22, 32, 52],
    }
    assigned = {p for v in assign.values() for p in v}
    assign['unclaimed'] = [p for p in range(1, 124) if p not in assigned]
    s.assign(assign)
    d['province_polity_notes'] = collections.OrderedDict([
        ('seann-dhaoine', 'Every coast held at their widest reach (VE 3,872); by the snapshot they keep to the shore, so only coastal provinces are theirs. Interior provinces of the west and south are left unclaimed.'),
        ('unclaimed', 'Forest, moor and hill with no known hearth at the snapshot: the interior lowlands, the western hills, the north-western horn (no hearth found, I-0006a), the sacred forests and the unsettled lake country. The windy coast (no province) is unclaimed too.'),
        ('eastern-hearths', 'Inferred extent about Cnoc fhionn and the deer-drive country of Doire fhionn.'),
        ('north-shore', 'Inferred extent: the north-west coast from Ros ruadh to Caol mhòr, where the hunters moved out of the Sea-Watcher\'s sight.'),
        ('red-hill', 'Inferred extent: the south and west shore of Loch chrom about the hill where Cathair dhearg now stands.'),
    ])
    d['cultures'][0]['provinces'] = sorted(coast_old)
    d['cultures'][1]['provinces'] = sorted(set(range(1, 124)) - set(coast_old) - set(assign['unclaimed']))
    d['faiths'][0]['provinces'] = sorted(set(d['cultures'][1]['provinces']) - {114})
    d['faiths'][2]['provinces'] = sorted(coast_old)
    d['polities'][0]['admin_units'][0]['provinces'] = sorted(coast_old)

    d['diplomacy'] = [
        {'a': 'seann-dhaoine', 'b': 'hill-folk', 'relation': 'unknown; separate peoples in contact',
         'note': 'Whether the two shared the island or one came after the other, no telling knows. A chip of the vein reached a Seann-Dhaoine midden by gift, trade or theft.',
         'cites': ['I-0065', 'I-0068']},
        {'a': 'clann-na-ceiste', 'b': 'hill-folk', 'relation': 'kin (a kindred of the hill-folk)',
         'note': 'The households of the high valleys name the Mason\'s line the Inquisitors of the Mystic Coal.', 'cites': ['I-0068a']},
        {'a': 'hill-folk', 'b': 'eastern-hearths', 'relation': 'kin (inferred)', 'cites': ['I-0065'], 'inferred': True},
        {'a': 'hill-folk', 'b': 'red-hill', 'relation': 'none recorded', 'cites': ['I-0083'], 'inferred': True},
        {'a': 'north-shore', 'b': 'seann-dhaoine', 'relation': 'shared waters (seal grounds)', 'cites': ['I-0043', 'I-0190'], 'inferred': True},
    ]

    # ---------------------------------------------------------------- burgs
    OLD = 'seann-dhaoine'
    old_ones = {
        # id: (root, pop, role, cites, note)
        489: ('Skell', 300, 'their greatest landing, up the Abhainn naomh behind the unmortared mole', ['I-0012', 'I-0056'], None),
        16: ('Skell', 25, 'a single hollow-walled round tower over the water where the Sea-Watcher is seen', ['I-0023'], 'the least of the Skell places'),
        132: ('Skell', 80, 'a landing behind the second, curved breakwater on the north coast', ['I-0030'], None),
        18: ('Dunn', 150, 'the great midden of limpet, seal bone and burnt weed, taller than a man', ['I-0010', 'I-0064a'], 'the ancient sea-way runs from the river mouth below it'),
        295: ('Dunn', 30, 'three round houses framed with the ribs of a stranded whale', ['I-0021'], None),
        347: ('Dunn', 60, 'harbour stones of the east coast', ['gazetteer B347'], None),
        36: ('Cwen', 120, 'net-weights notched with the same three strokes: the eldest mark made again and again of purpose', ['I-0011'], None),
        14: ('Cwen', 60, 'a southern landing whose middens now grow as fast as those of Dunn once did', ['I-0064'], None),
        139: ('Cwen', 80, 'a south-coast landing', ['gazetteer B139'], None),
        47: ('Bral', 90, 'two hundred and twelve steps up the cliff; a chip of the vein on its midden', ['I-0013', 'I-0068'], None),
        110: ('Bral', 80, 'a landing and a line of fish-kilns on the south-east coast', ['I-0025'], None),
        186: ('Morn', 70, 'seven stone-lined fish-kilns, the first buildings made for a trade', ['I-0018'], None),
        465: ('Morn', 50, 'oyster, whelk and cockle shell heaped over a headland', ['I-0026'], None),
        328: ('Brenn', 60, 'slipways wide enough for hulls greater than any hide boat', ['I-0019'], None),
        440: ('Brenn', 40, 'twin landing of the north-east with the same long ramps', ['I-0027'], None),
        37: ('Toll', 40, 'stone huts in the lee of a dune', ['I-0024'], None),
        313: ('Toll', 50, 'a fish-channel cut through a rock shelf beside the Abhainn uaine', ['I-0015'], None),
        404: ('Toll', 30, 'a harbour in a cleft of the rock', ['gazetteer B404'], None),
        94: ('Vell', 90, 'fourteen round houses of dry stone with sunk hearths', ['I-0022', 'I-0014'], 'its dead are rowed to the stone boxes of Eilean dhearg'),
        97: ('Vell', 25, 'four houses and a boat-shed on the Abhainn bheag, their furthest north-east', ['I-0029'], None),
        127: ('Vell', 50, 'storage pits in the dune, lined with clay and lidded with slabs', ['I-0031'], None),
        162: ('Vell', 40, 'a river landing on the Abhainn fhionn', ['gazetteer B162'], None),
        64: ('Warr', 70, 'a road of crushed shell across the reed marsh on the western shore of Loch chrom', ['I-0016'], None),
        128: ('Warr', 40, 'a landing on the south shore of the gulf', ['gazetteer B128'], None),
        249: ('Tarr', 60, 'rows of the unread script cut in the cliff', ['I-0017'], None),
        34: ('Tarr', 30, 'a single long house built into a cleft of the cliff', ['I-0028'], None),
        402: ('Tarr', 40, 'landing stones in the north-east', ['gazetteer B402'], None),
    }
    for i, (root, pop, role, cites, note) in old_ones.items():
        s.burg(i, era_name=root, name_kind='seann',
               era_name_en='%s (the Old Ones\' own root; the hill-folk do not yet say Seann before it)' % root,
               name_note='NAMING_LAYER: the root is not Dia-thìris; Seann is prefixed from GE 591 (I-0097)',
               population=pop, kind=kind_for(pop, AGE), role=role, culture=OLD, faith='old-ones-rite',
               polity='seann-dhaoine', cites=cites + ['I-0097'], inferred=(pop is not None), note=note)
    hill = {
        276: (None, 90, 'the crack, the slab over the burnt vein and the hearths of the Mason\'s line; where the black coal and the fire coal were lit',
              'clann-na-ceiste', 'telling-of-the-making', ['I-0001', 'I-0002', 'I-0003', 'I-0038a', 'I-0068a', 'I-0073a'], False),
        277: (None, 40, 'a peat-hearth hamlet of the high valleys; the first small burning by a household not of the Mason\'s line',
              'hill-folk', 'old-reverence', ['I-0065', 'I-0066'], True),
        454: (None, 35, 'the eldest hearths of the high valleys; wool of the dead stained with broken coal',
              'hill-folk', 'old-reverence', ['I-0005', 'I-0067'], True),
        148: (None, 50, 'hill hearths dug into pits and roofed with slabs, hiding their light from the Hollow Man',
              'hill-folk', 'old-reverence', ['I-0044', 'I-0046'], True),
        392: (None, 20, 'the gathering-ground at the column, with post-holes of shelters for some hundreds, used and rebuilt; few live there between gatherings',
              'hill-folk', 'old-reverence', ['I-0073', 'I-0074'], True),
        315: (None, 80, 'households of the valleys about the hill that Ailean will take (the hill has no bank yet)',
              'hill-folk', 'old-reverence', ['I-0081', 'I-0082'], True),
        61: (None, 60, 'sheltered farms of the east; dogs buried beside people with a shell at the head',
             'eastern-hearths', 'old-reverence', ['I-0054', 'gazetteer B61'], False),
        238: (None, 40, 'fishing households of the north-west coast; seven boats lost in one calm season',
              'north-shore', 'old-reverence', ['I-0042', 'gazetteer B238'], False),
        95: (None, 30, 'a seal-hunting camp on the strait, where the hunters moved out of the Sea-Watcher\'s sight',
             'north-shore', 'old-reverence', ['I-0043'], True),
        19: (None, 60, 'hearths of the lake-shore line on the hill where Cathair dhearg now stands; the Red Hill list opens in GE 18',
             'red-hill', 'old-reverence', ['I-0083', 'App.A holders of the Red Hill'], True),
    }
    for i, (en, pop, role, pol, faith, cites, inf) in hill.items():
        s.burg(i, era_name=None, era_name_en=None,
               name_note='the name is the later Dia-thìris name; no older name is recorded',
               population=pop, kind=('gathering-ground' if i == 392 else ('camp' if i == 95 else kind_for(pop, AGE))),
               role=role, culture='clann-nan-de', faith=faith, polity=pol, cites=cites, inferred=inf)
    present = {b['id'] for b in d['burgs']}

    # the absent: everything else is not yet founded; a few are sites that the annals name in this age
    special_absent = {
        209: ('the oak grove only: the Keeper spoke here, and here the mahogany and rainbow coals were lit; no settlement until GE 2,470', ['I-0011a', 'I-0052a', 'I-0080a', 'I-0194'], 'holy grove, unsettled'),
        355: ('the camp where nine died in a hut beside a fresh hearth (VE 3,351); the hut was never opened again and the camp left', ['I-0047'], 'abandoned camp'),
        117: ('a gully of the deer-drives, not a settlement (see new burg I-N05)', ['I-0053'], 'hunting ground'),
        143: ('mooring stakes and a scrap of stitched hide in the tidal mud; who rowed them is not known', ['I-0039'], 'trace only'),
        84: ('the shore below where the town now stands, where Aodh threw the seven coals into the sea', ['I-0017a'], 'site only'),
        46: ('the kerbed way of the Old Ones passes through the ground here', ['I-0034'], 'site only'),
        433: ('the eleven from the southern shore went up into the hills near here and were lost', ['I-0080'], 'site only'),
    }
    for i in sorted(BURGS):
        if i in present:
            continue
        if i in special_absent:
            r, c, st = special_absent[i]
            s.absent(i, r, c, state=st)
        else:
            g = GAZ[i]
            s.absent(i, 'founded in Age %s%s' % (g['founded_age'], (' (%s)' % g['founded_event']) if g.get('founded_event') else ''),
                     ['gazetteer B%d' % i] + ([g['founded_event']] if g.get('founded_event') else []))

    # ---------------------------------------------------------------- new burgs: lost camps and hearths
    s.new_burg('I-N01', None, 'the seal-hunters\' camp on Eilean mhin', ('cell', 4226), cell=4226,
               population=15, kind='seasonal camp', role='kept a season at a time and left; the first sure crossing of open water of set purpose',
               culture='clann-nan-de', faith='old-reverence', polity='unclaimed',
               reason='the annals set camps here in VE 551; kept by the season, and no end is recorded before the Great Wave drives the shepherds off in SE 5',
               cites=['I-0008', 'V-0022'], inferred=True)
    s.new_burg('I-N02', None, 'the autumn seal camp on Eilean fhada', ('cell', 420), cell=420,
               population=15, kind='seasonal camp', role='north-shore hunters take the grey seals on the skerries in the autumn gales',
               culture='clann-nan-de', faith='old-reverence', polity='north-shore',
               reason='the seal-hunt on the skerries off Eilean fhada (VE 611); placed on the island itself (feature 4)',
               cites=['I-0008a'], inferred=True)
    s.new_burg('I-N03', dt('Crannagan Loch chrom', 'new burg I-N03'), 'the lake dwellings of Loch chrom', ('burg', 27),
               population=60, kind='lake dwelling', role='platforms on oak piles in the shallows, joined to the shore by plank walks; who built them is not known',
               culture='clann-nan-de', faith='old-reverence', polity='red-hill',
               reason='raised VE 1,588 and burned to the waterline GE 1,525, so standing at the snapshot; placed on the south-west shore near Ros dhomhain',
               cites=['I-0020', 'I-0122'], inferred=True)
    s.new_burg('I-N04', None, 'the summer camps in the passes', ('marker', 40),
               population=0, kind='seasonal camp', role='herders\' camps on the high passes, left empty at the same point every year while the panthers cross',
               culture='clann-nan-de', faith='old-reverence', polity='unclaimed',
               reason='the crossing season kept (VE 5,219); the camps stand empty in the season',
               cites=['I-0079'], inferred=True)
    s.new_burg('I-N05', None, 'the deer-drive camp of the eastern forest', ('burg', 117),
               population=25, kind='hunting camp', role='lines of stakes and brush drive the red deer into a gully; the antlers of the greatest stags are stacked apart',
               culture='clann-nan-de', faith='old-reverence', polity='eastern-hearths',
               reason='the deer-drives near Doire fhionn (VE 3,720); a camp, not the later village',
               cites=['I-0053'], inferred=True)
    s.new_burg('I-N06', None, 'the hearths of the southern shore', ('burg', 433),
               population=40, kind='hamlet', role='the households from which the party of eleven went up into the panther hills',
               culture='clann-nan-de', faith='old-reverence', polity='unclaimed',
               reason='a party of eleven "from the southern shore" is lost near Cnoc àrsaidh (VE 5,272); the shore they came from is not named',
               cites=['I-0080'], inferred=True)

    # ---------------------------------------------------------------- routes
    named = {
        410: dict(first='I', name='Slighe-mhara àrsaidh', group='searoutes', cites=['I-0064a'],
                  note='the Old Ones\' lane along the south-east coast, flat landing-stones a day\'s rowing apart'),
    }

    def rule(i, touched, present):
        return (False, None)
    classify_routes(d, AGE, present, named, rule,
                    'Age I has no made roads but the Old Ones\' few works: every master trail, road and sea-lane is absent '
                    'except the ancient sea-way, which the annals set in this age. Era tracks are added below.')
    d['routes']['new'] = [
        collections.OrderedDict([('key', 'I-R01'), ('name', None), ('name_en', 'the kerbed way between the forts'), ('group', 'roads'),
                                 ('points', [{'marker': 31}, {'burg': 46}, {'marker': 32}]),
                                 ('note', 'a cart\'s width, paved with flat slabs; the only road the Old Ones made away from the shore. Both forts are ruins at the snapshot, so the way is disused.'),
                                 ('cites', ['I-0034', 'I-0059', 'I-0061'])]),
        collections.OrderedDict([('key', 'I-R02'), ('name', None), ('name_en', 'the shell causeway of Warr'), ('group', 'roads'),
                                 ('points', [{'burg': 64}, {'cell': near_cell(('burg', 64), 95)}]),
                                 ('note', 'crushed shell across the reed marsh, a little over a mile long, raised a forearm above the reeds; unbroken until GE 147'),
                                 ('cites', ['I-0016', 'I-0087'])]),
        collections.OrderedDict([('key', 'I-R03'), ('name', None), ('name_en', 'the paths that stop at a line of stones'), ('group', 'trails'),
                                 ('points', [{'burg': 19}, {'marker': 24}]),
                                 ('note', 'tracks worn toward Coille Naomh Cnoc bheag from three quarters end at a low line of set stones short of the trees; one of the three is drawn, from the Red Hill (inferred)'),
                                 ('cites', ['I-0052']), ('inferred', True)]),
        collections.OrderedDict([('key', 'I-R04'), ('name', None), ('name_en', 'the seal-hunters\' crossing to Eilean mhin'), ('group', 'searoutes'),
                                 ('points', [{'burg': 94}, {'new_burg': 'I-N01'}]),
                                 ('note', 'the first sure crossing of open water of set purpose'), ('cites', ['I-0008']), ('inferred', True)]),
        collections.OrderedDict([('key', 'I-R05'), ('name', None), ('name_en', 'the skin boats to the skerries of Eilean fhada'), ('group', 'searoutes'),
                                 ('points', [{'burg': 440}, {'new_burg': 'I-N02'}]),
                                 ('note', 'the hunters of the north shore go out in the autumn gales'), ('cites', ['I-0008a']), ('inferred', True)]),
        collections.OrderedDict([('key', 'I-R06'), ('name', None), ('name_en', 'the way of the lightings (Tobar dhìreach to the grove)'), ('group', 'trails'),
                                 ('points', [{'burg': 276}, {'burg': 315}, {'cell': near_cell(('burg', 209), 23)}]),
                                 ('note', 'the Mason\'s line carried the coals from the crack to the grove where the Keeper spoke; Ailean carried the six lit coals along it'),
                                 ('cites', ['I-0052a', 'I-0080a']), ('inferred', True)]),
    ]

    # ---------------------------------------------------------------- markers
    M = {
        0: dict(era_name=None, era_name_en='the warm springs', note='Stone basins set into the springs; the sick are first brought here for healing, and the people buried near them have old breaks that knitted clean.', cites=['I-0057']),
        12: dict(era_name=None, era_name_en='the warning fire on the north-western headland', icon='🔥',
                 note='A fire kept on the headland to warn boats off the water where the Sea-Watcher was seen, never to bring them in; no tower.', cites=['I-0041']),
        19: dict(era_name=dt('Toll-dubh', 'marker'), note='The western shaft: cut straight down, stones thrown in are not heard to land.', cites=['I-0037']),
        20: dict(era_name=dt('Toll-dubh', 'marker'), note='The eastern shaft of the Old Ones, walls tooled smooth, no spoil beside it.', cites=['I-0036']),
        21: dict(note='Old sailors first tell of a vast creature off the north-western coast; seven boats of Ros ruadh are lost to it by name.', cites=['I-0040', 'I-0042']),
        22: dict(note='The inscriptions of the Doire uaine hills tell of something that walked without breathing and fell on any who lit a fire in its sight.', cites=['I-0044', 'I-0045']),
        23: dict(era_name=None, era_name_en='the uncut forest of the white stag',
                 note='A forest held sacred before any order: no axe is put in it, and three hunters see a white stag there and none draws. In this age the stag has no god.', cites=['I-0048', 'I-0049', 'I-0050']),
        24: dict(era_name=None, era_name_en='the unclaimed forest behind the line of stones',
                 note='Older than the first, never settled, felled or walked end to end; the paths toward it stop at a low line of set stones.', cites=['I-0051', 'I-0052']),
        28: dict(note='A standing stone with a line of the unread script on its upper face; the four Dia-thìris words, Bha teine sa chloich, were cut lower by another hand whose date is not known.', cites=['I-0069', 'I-0070']),
        29: dict(note='A second stone, Cuimhnich an teine; the ground about it trodden hard in a ring and paved with fire-cracked stones.', cites=['I-0071', 'I-0072']),
        30: dict(note='The column of the saying, Cha do thàinig sinn; bha sinn ann; crowds gather about it.', cites=['I-0073', 'I-0074']),
        31: dict(note='The walled outpost of the Old Ones, its one gate blocked with rubble from within (VE 3,973) and deserted (VE 4,023): a ruin at the snapshot.', cites=['I-0032', 'I-0058', 'I-0059']),
        32: dict(note='The three-ringed fortress, its cistern choked with the bones of whole cattle (VE 4,074) and deserted (VE 4,124): a ruin.', cites=['I-0033', 'I-0060', 'I-0061']),
        33: dict(note='The stepped platform with its altar square to the central mountains; its top stone prised off (VE 4,175) and the temple deserted (VE 4,275).', cites=['I-0035', 'I-0062', 'I-0063']),
        40: dict(note='The panther roads over the high passes, kept by the cats at fixed seasons; the hill-folk keep off the passes while they cross.', cites=['I-0078', 'I-0079', 'I-0080']),
        41: dict(note='A burial-ground about a place none remembers hallowing; a child buried with a sliver of the coloured coal in one hand; the graves begin to be laid in rows, heads toward the central mountains.', cites=['I-0075', 'I-0076', 'I-0077']),
        48: dict(note='Fearghas of the Mason\'s line let the six unlit coals fall from the highest ground, and the coal flecked with white stars took fire in the air (VE 2,170): the second of the lightings. The summit is named for the kindred.', cites=['I-0027a']),
    }
    for i in sorted(MARKERS):
        if i in M:
            kw = dict(M[i])
            s.marker(i, **kw)
        else:
            d['markers']['absent'].append(i)

    c_grove = near_cell(('burg', 209), 23)
    new_markers = [
        ('I-K01', None, 'the mason\'s fire and the slab over the vein', ('burg', 276), '🔥', 'I-0001',
         'Neachdan the mason broke into the vein; lightning fired it and he carried the first fire home. When it burned out his people laid a flat stone over the break and cut their well a stone\'s throw off. Three wells claim the crack; Tobar dhìreach can show a capped, scorched shaft.', ['I-0001', 'I-0002', 'I-0003']),
        ('I-K02', None, 'the Keeper in the grove', ('cell', c_grove), '🌫️', 'I-0011a',
         'In the oak grove at Doire ghlas a figure of grey smoke, Coimhdeach na Fine, told Diarmad of the Mason\'s line the making of the world and gave the riddle of the spirits.', ['I-0011a', 'I-0006']),
        ('I-K03', None, 'the first lighting: the gold coal on the sea', ('cell', near_cell(('burg', 84), 104)), '🟡', 'I-0017a',
         'Aodh threw the seven coals into the sea below where Ceann thais stands; the gold-sheen coal burned gold on the water until the waves put it under.', ['I-0017a']),
        ('I-K04', None, 'the third lighting: the black coal warm in the ground', ('burg', 276), '⚫', 'I-0038a',
         'Brian buried the five unlit coals beside the slab; the next day the black coal was warm and smouldered as the air came to it.', ['I-0038a']),
        ('I-K05', None, 'the fourth lighting: the blood of the misstrike', ('cell', c_grove), '🟤', 'I-0052a',
         'Cormac missed his stroke in the grove and opened his hand; where the blood fell the red-brown coal of life took fire.', ['I-0052a']),
        ('I-K06', None, 'the fifth lighting: the silver coal in the river', ('cell', near_cell(('burg', 276), 114, {BURGS[276]['cell']})), '⚪', 'I-0062a',
         'Eòghann tasted the Abhainn ghorm below Tobar dhìreach, said the water tasted different from the sea, and the silver coal took fire under the water.', ['I-0062a']),
        ('I-K07', None, 'the sixth lighting: the fire in the fingers', ('burg', 276), '🔥', 'I-0073a',
         'Seathan snapped his fingers and the coal-dust on his hand took fire; he beat it out and was not burned.', ['I-0073a']),
        ('I-K08', None, 'the seventh lighting: the rainbow coal and the vigil', ('cell', c_grove), '🌈', 'I-0080a',
         'Ailean of Clann na Ceiste carried the six lit coals to the grove; the Keeper lit the rainbow coal, all seven burned together, and he was bidden to stay until they were cold. He is on the last night of the vigil at the snapshot.', ['I-0080a']),
        ('I-K09', None, 'hearth-stones on the terraces of the Abhainn uaine', ('burg', 313), '🪨', 'I-0004',
         'On the gravel terraces of the lower river lie hearth-stones at three heights, each left as the meltwater rose to it.', ['I-0004']),
        ('I-K10', None, 'the fish-weirs of the Abhainn ìseal', ('cell', near_cell(('burg', 371), 9)), '🐟', 'I-0009',
         'Weirs of hazel stakes across the side channels of the longest river, renewed in the same holes for generations.', ['I-0009']),
        ('I-K11', None, 'the stone boxes of Eilean dhearg', ('cell', 3856), '⚱️', 'I-0014',
         'Forty stone boxes facing the mainland, where the Old Ones of Vell lay their dead.', ['I-0014']),
        ('I-K12', None, 'the steps of Bral', ('burg', 47), '🪜', 'I-0013',
         'Two hundred and twelve steps cut up the cliff, their treads worn hollow in the middle.', ['I-0013']),
        ('I-K13', None, 'the script in the cliff at Tarr', ('burg', 249), '🔣', 'I-0017',
         'Rows of the unread script cut above the harbour, the same signs later found on the standing stones.', ['I-0017']),
        ('I-K14', None, 'the hut of the nine', ('cell', near_cell(('burg', 355), 112)), '💀', 'I-0047',
         'Nine died in a hut at the hill camp beside a hearth of fresh ash, with no wound on any bone; the hut was never opened again.', ['I-0047']),
        ('I-K15', None, 'the geese of Eilean ghorm', ('cell', 1751), '🪿', 'I-0055',
         'The grey geese that come in with the first storm and leave with the last; none hunts them there.', ['I-0055']),
        ('I-K16', None, 'the drowned hearths of the neck', ('cell', 67), '🌊', 'I-0007',
         'The hearths of the low neck that joined Eilean dhubh to the island lie under the sand of the sound (VE 506).', ['I-0007']),
        ('I-K17', None, 'where the eleven were lost', ('cell', near_cell(('marker', 40), 78)), '🐆', 'I-0080',
         'A party of eleven from the southern shore went into the hills in the crossing season; their bones were found along the cats\' line.', ['I-0080']),
    ]
    for key, name, en, at, icon, eid, note, cites in new_markers:
        s.new_marker(key, name, en, at, icon=icon, event=eid, note=note, cites=cites)

    # ---------------------------------------------------------------- zones and labels
    d['zones'] = [
        collections.OrderedDict([('key', 'I-Z01'), ('name', None), ('name_en', 'the widest reach of the Old Ones (VE 3,872)'), ('type', 'earlier moment'),
                                 ('provinces', sorted(coast_old)), ('note', 'Every coast and the islands off them; the ten Seann places.'), ('cites', ['I-0056'])]),
        collections.OrderedDict([('key', 'I-Z02'), ('name', None), ('name_en', 'the covered hearths of the Doire uaine hills'), ('type', 'custom'),
                                 ('provinces', [112]), ('note', 'No open hearth shows in these hills for many lifetimes; no fire is lit in the Hollow Man\'s sight.'), ('cites', ['I-0046', 'I-0045'])]),
        collections.OrderedDict([('key', 'I-Z03'), ('name', None), ('name_en', 'the drowned neck of Eilean dhubh (VE 506)'), ('type', 'earlier moment'),
                                 ('cells', [67]), ('provinces', [119]), ('note', 'The low neck that joined the island to the mainland, flooded by the rising sea.'), ('cites', ['I-0007'])]),
        collections.OrderedDict([('key', 'I-Z04'), ('name', None), ('name_en', 'the oak of the northern lowlands'), ('type', 'land'),
                                 ('provinces', d['land_changes'][0]['provinces']), ('note', 'Oak and hazel over ground that was open heath when the vein was first broken; it falls back only in the next age.'), ('cites', ['I-0006', 'I-0220a'])]),
        collections.OrderedDict([('key', 'I-Z05'), ('name', None), ('name_en', 'the snowfields of the central mountains (to VE 227)'), ('type', 'earlier moment'),
                                 ('provinces', [35, 112, 96, 114, 65]), ('note', 'The high snowfields shrink and their meltwater cuts the bed of the Abhainn uaine.'), ('cites', ['I-0004'])]),
        collections.OrderedDict([('key', 'I-Z06'), ('name', None), ('name_en', 'the high places left by the Old Ones (VE 4,325)'), ('type', 'earlier moment'),
                                 ('provinces', [24, 31, 109, 110]), ('note', 'After the forts and the temple are forsaken every new work of the Old Ones is made within sight of salt water.'), ('cites', ['I-0064'])]),
        collections.OrderedDict([('key', 'I-Z07'), ('name', dt('Imrich nam Pantar', 'zone')), ('name_en', 'the panther roads'), ('type', 'custom'),
                                 ('provinces', [25, 78, 10, 100]), ('note', 'The cats cross the mountains by fixed ways at fixed seasons, and the hill-folk keep off the passes.'), ('cites', ['I-0078', 'I-0079'])]),
    ]
    d['labels'] = [
        {'text': 'Clann nan Dè', 'text_en': 'the hill-folk', 'at': {'burg': 277}, 'cites': ['I-0065']},
        {'text': 'Na Seann-Dhaoine', 'text_en': 'the Old Ones', 'at': {'burg': 489}, 'cites': ['I-0056']},
        {'text': None, 'text_en': 'the vigil of the seven fires', 'at': {'cell': c_grove}, 'cites': ['I-0080a']},
        {'text': 'Cha do thàinig sinn; bha sinn ann', 'text_en': 'we did not come; we were here', 'at': {'marker': 30}, 'cites': ['I-0073']},
    ]
    for l in d['labels']:
        if l['text']:
            dt(l['text'], 'label', 'phrase')

    # ---------------------------------------------------------------- military
    d['military']['hosts'] = []
    d['military']['campaigns'] = [
        collections.OrderedDict([('name', None), ('name_en', 'the walling of the outpost gate'), ('kind', 'deed of force (no war is recorded)'),
                                 ('date', ann_date('I-0058')), ('at', {'marker': 31}),
                                 ('note', 'The single gate blocked with rubble from inside by people who left another way, or did not leave.'), ('cites', ['I-0058'])]),
        collections.OrderedDict([('name', None), ('name_en', 'the fouling of the fortress cistern'), ('kind', 'deed of force (no war is recorded)'),
                                 ('date', ann_date('I-0060')), ('at', {'marker': 32}),
                                 ('note', 'The cistern that served four hundred choked with the bones of whole cattle.'), ('cites', ['I-0060', 'App.C Before the wars'])]),
    ]
    d['military']['note'] = 'No host, war or king in this age. What fighting there was among the Old Ones is not known.'

    # ---------------------------------------------------------------- arms
    d['arms'] = [
        collections.OrderedDict([('polity', 'seann-dhaoine'), ('blazon', None), ('signs', 'three notched strokes (the net-weights of Cwen), the unread script'),
                                 ('note', 'No arms: Dia-thìr had carved signs long before it had arms, and none was borne on a shield.'), ('cites', ['I-0011', 'App.J §I'])]),
        collections.OrderedDict([('polity', 'clann-na-ceiste'), ('blazon', None), ('signs', 'the seven coals by their colours (black, fire, snowflake, gold sheen, silver sheen, mahogany, rainbow); inferred as the kindred\'s sign'),
                                 ('note', 'No arms; the kindred keeps a recited line, not a seal.'), ('cites', ['App.B §III', 'App.J §I']), ('inferred', True)]),
        collections.OrderedDict([('polity', 'hill-folk'), ('blazon', None), ('signs', None), ('note', 'No arms.'), ('cites', ['App.J §I'])]),
    ]

    # ---------------------------------------------------------------- notes
    d['notes']['polities'] = collections.OrderedDict([
        ('seann-dhaoine', 'The Old Ones hold the landings of every coast from Skell on the Abhainn naomh round to Vell and Tarr. They build moles, steps, kilns and slipways, cut a script no one reads, and row their dead to Eilean dhearg. Since the high places were left their works keep in sight of salt water; their forts and temple stand empty above them.'),
        ('clann-na-ceiste', 'The Mason\'s line keeps the crack at Tobar dhìreach and the recited line from Neachdan the mason, each son of each father. Over five thousand years its men have lit the coals one by one, by sea, air, earth, blood, river and hand; the households call them the Inquisitors of the Mystic Coal. Tonight its last son of the line sits by the seven fires in the grove.'),
        ('hill-folk', 'The godkin of the high valleys live in hearth-kindreds with no ruler, burn a sliver of coal and no more, bury in the ground and cut no script. They keep their hearths covered in the Doire uaine hills and gather in hundreds at the column. They say they were always on the island.'),
        ('eastern-hearths', 'The farms and hunting households of the eastern oak country drive red deer into the gullies and bury their dogs beside them. Nothing in the record ties them to the high valleys but the one people.'),
        ('north-shore', 'The seal-hunters and fishers of the north-west coast work the south side of the headlands, out of the Sea-Watcher\'s sight. Their boats are hide and stitched plank, and a hard year is counted by the boats the gales kept ashore.'),
        ('red-hill', 'An old line of the western lake shore holds the hill where the red city later stands, with the lake dwellings in the shallows below. No holder is named until Beathag Ruadh in the first years of the next age.'),
    ])
    d['notes']['burgs'] = collections.OrderedDict([
        ('489', 'Skell, the greatest landing of the Old Ones, lies up the Abhainn naomh behind a mole of unmortared boulders that shelters a dozen boats; every later quay wall stands on it.'),
        ('276', 'The mason\'s crack: a capped, scorched shaft, the slab over the burnt vein and the hearths of Clann na Ceiste. The black coal and the fire coal were lit here, and from here the line carried the coals to the grove.'),
        ('18', 'Dunn\'s midden of shell, seal bone and burnt weed is the first sure trace of the Old Ones; the ancient sea-way starts at the river mouth below it.'),
        ('392', 'The gathering-ground at the column: post-holes of shelters for hundreds, rebuilt many times, where the saying of the hill-folk is spoken to a crowd.'),
        ('36', 'Cwen\'s net-weights are notched with the same three strokes, the eldest mark on the island made again and again of purpose.'),
    ])
    return s.finish()
