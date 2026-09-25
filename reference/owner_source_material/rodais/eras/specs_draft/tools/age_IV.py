"""Age IV, the Age of Sundering (Landfall Era): the island on the eve of the Crossing."""
# populations: the drafts' own figures, never above a town's present size (eras/pop_sweep.py, round 2)
from common import *  # noqa: F401,F403

AGE = 'IV'

ORDER_NAMES = collections.OrderedDict([
    ('custody', dict(name='Òrd Bhrìde', name_en='the custody of the vein (the vein-house: Crom\'s stone, heir to the Keepers\' Hall)',
                     gods='Brìde of the flame; Crom Cruaich of the stone', seat=491,
                     note='The vein-house above Muileann dhearg keeps Crom\'s stone and the custody-book and holds the Small-Burning Law; since LE 859 the ruler is its master. It has no written creed.',
                     cites=['III-0006', 'III-0034', 'III-0047', 'III-0138', 'III-0239'])),
    ('seabhag', dict(name='Òrd an t-Seabhaig', name_en='the order of the Hawk of Acaill (the Hungry Hawk)', gods='Mòd, the Hawk of Acaill; Fionntan mac Bòchra',
                     seat=20, note='Gathered at Cnoc bheag by Gormshuil nic Artair (LE 229); split in LE 889, the Fed Hawk turned out to the northern Seann Skell and not heard of as a house after its petition was refused.',
                     cites=['III-0062', 'III-0063', 'III-0065', 'III-0140', 'III-0142', 'III-0143'])),
    ('sgoiltean', dict(name='Scoiltean nan Draoidhean', name_en='the druid schools of Flidais', gods='Flidais, lady of the deer; the white stag',
                       seat=77, note='Houses of disputation at Dùn thais (LE 314, shut and opened more than once) and Inis mhòr (LE 769); they keep Coille Naomh Muileann chiar and walk its bounds; Eilidh Dhubh\'s tracts burned; the table of years forbidden.',
                       cites=['III-0074', 'III-0092', 'III-0094', 'III-0128', 'III-0171', 'III-0172', 'III-0230'])),
    ('macha', dict(name='Òrd Mhacha', name_en='the order of Macha, the order of the crown', gods='Macha; Liath Macha and Dubh Sainglenn, two horses, one yoke',
                   seat=19, note='The order of Cathair dhearg and the crown since King Aonghas (LE 441); keeper of Coille Naomh Cnoc bheag by royal grant; its great house at Cathair mhòr.',
                   cites=['III-0089', 'III-0091', 'III-0096', 'III-0198'])),
    ('cloch', dict(name='Òrd na Cloiche', name_en='the order of the Stone (Lia Fàil) and its Fianna', gods='Lia Fàil, called Clach',
                   seat=166, note='First preached at Inis thais (LE 409), its temple roofed with northern slate; split over prayer for the dead (LE 1,389): the temple at Inis thais and the house at Baile gheal, not reconciled.',
                   cites=['III-0086', 'III-0087', 'III-0118', 'III-0191', 'III-0193'])),
    ('manannan', dict(name='Òrd Mhanannain', name_en='the order of Manannan', gods='Manannan mac Lir; the yellow scorpion of his Cup of Truth',
                      seat=489, note='Proclaimed at Seann Skell (LE 654); no boat of the faithful out of sight of land; the prayer to keep the sea shut, said on the day of the empty-harbour rite; it records the mist thinning.',
                      cites=['III-0120', 'III-0122', 'III-0123', 'III-0212', 'III-0223', 'III-0239a'])),
])


def build():
    reset_names()
    s = Spec(AGE, collections.OrderedDict([
        ('age', 'IV'),
        ('age_name', {'name': dt('An Aois Scaraidh', 'age name'), 'name_en': 'the Age of Sundering'}),
        ('era', {'abbr': 'LE', 'name': dt('Linn na Tìre', 'era name'), 'name_en': 'the Landfall Era'}),
        ('snapshot', collections.OrderedDict([
            ('date', '4 am Faoilleach, LE 1,820 (the eve of the Crossing, AE 1)'),
            ('plan_label', 'LE 1,819 (ERA_PLAN): the close of the Landfall Era; the snapshot is the day before the humans come ashore'),
            ('y', 1780), ('m', 1), ('d', 4),
            ('last_event_shown', 'III-0239a'),
            ('next_event', 'IV-0001'),
            ('description',
             "Eighteen centuries after the fleet of the willing sailed north-about into Manannan's mist, the island is one realm with "
             "an empty crown. The Council of Custodians sits at Cathair dhearg in the crown's place, for the ruler of Dia-thìr "
             "has been master of the vein-house too since Dòmhnall Ruadh, and the heads of the seven houses of custody are "
             "the council; the kingdom seals with the vein-house's trellis and hollow stone. The shires keep the firlot of "
             "Cathair dhearg and their seats keep the crown's measures; the coal-roads from the mountain are the crown's, "
             "posted and ridden. The Small-Burning Law still holds, though three of the seven houses now hold more than half "
             "the right, and the silver petition lies unanswered. The orders of the Old Faith have their houses: the Hawk at "
             "Cnoc bheag, the Stone at Inis thais, Manannan at Seann Skell, Macha with the crown, the schools arguing at Dùn "
             "thais; the Old Spirits keep the spirit-house at Dùn ìseal. The north-west is thinly held since the dearth. On the "
             "north-west the mist lies thinner each winter, and on still mornings the fishers see the line of the open sea."),
            ('cites', ['IV-0005', 'III-0138', 'III-0138a', 'III-0145', 'III-0069', 'III-0235', 'III-0239', 'III-0239a',
                       'III-0056', 'III-0134', 'III-0023', 'App.A §IV']),
        ])),
        ('land_changes', [
            collections.OrderedDict([('what', 'Manannan\'s mist lies on the eastern sea beyond the northern and eastern headlands (from the Setting-Out, LE 40), thinning in the last years; draw as a sea zone, not a coast change.'),
                                     ('cites', ['III-0023', 'III-0120', 'III-0239a'])]),
            collections.OrderedDict([('what', 'The oak grove that named Doire fhionn is gone, felled for the keels of the fleet (LE 5); the northern Doire shires cut their woods by coppice.'),
                                     ('cites', ['III-0009', 'III-0048'])]),
            collections.OrderedDict([('what', 'The Abhainn bheag below Ros fhionn is silted by a shifting bar (LE 1,159); the salt barges cannot reach its quays.'),
                                     ('cites', ['III-0166'])]),
            collections.OrderedDict([('what', 'The salt pans of Caol gharbh are under the sea (LE 1,734).'), ('cites', ['III-0226'])]),
        ]),
    ]))
    d = s.d
    d['cultures'] = [collections.OrderedDict([('key', 'dia-thirich'), ('name', dt('Na Dia-thìrich', 'culture')), ('name_en', 'the Dia-thìrich'),
                                              ('master_culture', 2), ('provinces', list(range(1, 124))),
                                              ('note', 'One people; nearly one household in five of the coal-right went with the fleet. The departed are beyond the mist and hold no land here.'),
                                              ('cites', ['III-0006', 'III-0029', 'III-0030', 'III-0033'])])]
    d['faiths'] = [
        collections.OrderedDict([('key', 'old-faith'), ('name', dt('An Creideamh Sean', 'faith')), ('name_en', 'the Old Faith and its orders'),
                                 ('master_religion', 1), ('type', 'Organized'), ('form', 'Polytheism'), ('deity', 'an Dagda first; each order its own god'),
                                 ('provinces', []), ('orders', []), ('cites', ['App.B §V'])]),
        collections.OrderedDict([('key', 'old-spirits'), ('name', dt('Na Seann Spioradan', 'faith')), ('name_en', 'the Old Spirits'),
                                 ('master_religion', 2), ('type', 'Folk'), ('form', 'Shamanism'), ('deity', 'the ancestors; na Sìthichean'),
                                 ('seat', {'burg': 315}), ('provinces', []),
                                 ('note', 'The spirit-house at Dùn ìseal with the names of the dead of the eastern shires on wooden posts, cut anew each generation; the guest-house at Allt an Àigh; the ancestor shrine and feast-market at Seann Tarr.'),
                                 ('cites', ['III-0056', 'III-0119a', 'III-0165', 'III-0175'])]),
    ]
    d['rites'] = [
        {'name': dt('An Tùrsa Geal', 'rite'), 'name_en': 'the white sorrow (the Mourning Custom)', 'note': 'Undyed wool and an empty place at a meal that is neither feast nor fast; kept in every harbour town.', 'cites': ['III-0031', 'III-0032']},
        {'name': None, 'name_en': 'the rite of the empty harbour, on Cidhe an Diosail at Seann Skell', 'note': 'Kept by eleven people in LE 1,803; Manannan\'s priests say their prayer for the shut sea on the same day.', 'cites': ['III-0036', 'III-0223', 'III-0238']},
    ]
    for k, o in ORDER_NAMES.items():
        dt(o['name'], 'order ' + k)
        d['faiths'][0]['orders'].append(collections.OrderedDict([('key', k), ('name', o['name']), ('name_en', o['name_en']), ('gods', o['gods']),
                                                                 ('seat', {'burg': o['seat']}), ('provinces', []), ('note', o['note']), ('cites', o['cites'])]))

    # faith of each shire: the master map's where the Old Faith and Old Spirits stand; the Tuathaich north-west, before the
    # Church, by its neighbours (inferred); orders by App.B's blocks, with the custody where Òrd Bhrìde stands today and at the vein-house
    NW_OLDFAITH = {14: 'manannan', 28: 'manannan', 120: 'manannan', 105: 'manannan', 75: 'manannan', 107: 'manannan'}
    NW_SPIRITS = [36, 7, 86, 23, 88, 122]
    faith_prov, order_prov = {}, {}
    for p in range(1, 124):
        mf = master_faith_of_province(p)
        if p in NW_OLDFAITH:
            faith_prov[p], order_prov[p] = 'old-faith', NW_OLDFAITH[p]
        elif p in NW_SPIRITS or mf in (2, 0):
            faith_prov[p] = 'old-spirits'
        else:
            faith_prov[p] = 'old-faith'
            o = present_order(p)
            order_prov[p] = {'bride': 'custody'}.get(o, o)
    order_prov[96] = 'custody'
    faith_prov[96] = 'old-faith'
    for p, f in faith_prov.items():
        (d['faiths'][0] if f == 'old-faith' else d['faiths'][1])['provinces'].append(p)
    for o in d['faiths'][0]['orders']:
        o['provinces'] = sorted(p for p, k in order_prov.items() if k == o['key'])

    # ---------------------------------------------------------------- polity
    s.polity('realm', dt('Dia-thìr', 'polity'), 'the realm of Dia-thìr (the crown empty; the Council of Custodians in its place)',
             form='a crown joined to the custody of the vein (from LE 859); the crown empty at the close of the age, and the Council of Custodians, the heads of the seven houses, sitting in its place',
             capital={'burg': 19},
             ruler={'name': None, 'title': 'the Council of Custodians (high custodian Tormod mac Ailein, first named in AE 2)',
                    'note': 'The last crowning in the annals is Gormshuil nic Thormoid\'s (LE 1,766); of her death, any heir and how the crown fell vacant nothing is told. Tormod mac Ailein is high custodian when the council grants the strangers leave; that he already sits at the snapshot is inferred.',
                    'cites': ['III-0231', 'III-0232', 'IV-0005', 'App.A §IV'], 'inferred': True},
             culture='dia-thirich', color='#1f4e8c (the azure of the custody\'s seal)',
             cites=['III-0138', 'III-0138a', 'IV-0005'])
    late = [p for p in range(1, 124) if province_seat_age(p) not in ('I', 'II', 'III', 'IV')]
    keep = [p for p in range(1, 124) if p not in late]
    fold = {p: nearest_province(p, keep) for p in late}
    fold[67] = 52
    shires = []
    for p in keep:
        members = [p] + [q for q, t in fold.items() if t == p]
        shires.append({'name': dt('Siorrachd %s' % PROVINCES[p]['name'], 'shire', 'place'), 'name_en': 'the shire of %s' % PROVINCES[p]['name'],
                       'seat': {'burg': PROVINCES[p]['burg']}, 'provinces': members, 'inferred': True})
    d['polities'][0]['admin_units'] = [
        {'name': None, 'name_en': 'the shires (siorrachdan)', 'kind': 'shire: the unit in which the crown\'s measures are kept; a year\'s grain at every seat under Iain Ciar',
         'note': 'The word siorrachd first appears at the sail-cloth levy (LE 9). The modern shires whose seats stand in this age are used; Doire chaol is folded back into Baile chiar and the two island shires into their nearest neighbours.',
         'cites': ['III-0013', 'III-0069', 'III-0119', 'III-0182', 'III-0205', 'III-0232', 'App.H §II'], 'units': shires},
        {'name': None, 'name_en': 'the seven houses of custody', 'kind': 'houses answerable to the vein-house for their galleries and their share of the burning',
         'cites': ['III-0034', 'III-0047', 'App.A §VII'], 'units': [
             {'name': dt('Clann Mhuirich', 'house', 'place'), 'name_en': 'Clann Mhuirich', 'seat': {'burg': 315}, 'provinces': [35], 'note': 'the Keepers\' house of the Holy Age; seldom named in this age', 'inferred': True},
             {'name': dt('Clann Fhearchair', 'house', 'place'), 'name_en': 'Clann Fhearchair', 'seat': {'burg': 273}, 'provinces': [111], 'note': 'the first king chosen by the houses; the double court at Baile Mòr dhomhain', 'cites': ['III-0058', 'III-0059']},
             {'name': dt('Clann Ìomhair', 'house', 'place'), 'name_en': 'Clann Ìomhair', 'seat': {'burg': 422}, 'provinces': [85], 'note': 'walled Dùn dhearg in stone, the first walls raised by a house', 'cites': ['III-0068']},
             {'name': dt('Clann Raghnaill', 'house', 'place'), 'name_en': 'Clann Raghnaill', 'seat': {'burg': 491}, 'provinces': [96], 'note': 'the claimant slain at Muileann chrom; from Dòmhnall Ruadh the crown and the vein-house together', 'cites': ['III-0104', 'III-0137', 'III-0138']},
             {'name': dt('Clann Thormoid', 'house', 'place'), 'name_en': 'Clann Thormoid', 'seat': None, 'provinces': [], 'note': 'no deed set down under its name in this age'},
             {'name': dt('Clann Choinnich', 'house', 'place'), 'name_en': 'Clann Choinnich', 'seat': None, 'provinces': [], 'note': 'rebuilt the bath-house at the hot springs; brought the silver petitions', 'cites': ['III-0130', 'III-0208', 'III-0233']},
             {'name': dt('Clann Lachlainn', 'house', 'place'), 'name_en': 'Clann Lachlainn', 'seat': None, 'provinces': [], 'note': 'named among the seven; no deed remembered'},
         ]},
        {'name': None, 'name_en': 'chartered towns', 'kind': 'towns with rights of their own', 'units': [
            {'name_en': 'Seann Warr, keeper of its own gates and tolls', 'seat': {'burg': 64}, 'provinces': [], 'cites': ['III-0105', 'III-0115']},
            {'name_en': 'Cathair fhada\'s market and tally-house', 'seat': {'burg': 297}, 'provinces': [], 'cites': ['III-0070a']},
            {'name_en': 'the market-court of Ros fhionn', 'seat': {'burg': 76}, 'provinces': [], 'cites': ['III-0168a']},
        ]},
    ]
    s.assign({'realm': list(range(1, 124))})
    d['province_polity_notes'] = collections.OrderedDict([
        ('realm', 'One realm over every shire. The windy coast (no shire) has no hearth of the realm on record; the north-west shore is thinly held since the dearth (LE 819).'),
    ])
    d['diplomacy'] = [
        {'a': 'realm', 'b': 'the departed', 'relation': 'none: no word since the broken tidings of two landfalls', 'note': 'Queen Beathag struck her sister Mòrag\'s line from the succession as no longer on Dia-thìr; Manannan\'s order prays that the sea be kept shut.',
         'cites': ['III-0027', 'III-0028', 'III-0212']},
        {'a': 'realm', 'b': 'sea-thieves of the north-west', 'relation': 'hostile', 'cites': ['III-0131', 'III-0133']},
    ]

    # ---------------------------------------------------------------- burgs
    SPECIAL = {
        19: dict(population=6000, kind='town', role='seat of the crown and of the Council of Custodians; the tally-houses, the firlot, the king-list; the lesser town beside Cathair mhòr', cites=['III-0069', 'III-0070', 'III-0148', 'IV-0005']),
        23: dict(population=10468, kind='city', walls=True, role='the largest town on the island since LE 969: the market of all the south, Macha\'s great house with its floor of black and white, the copper-workers', cites=['III-0148', 'III-0150', 'III-0198']),
        491: dict(population=975, kind='town', role='the vein-house above the town: keeper of Crom\'s stone and the custody-book, heir to the Keepers\' Hall; the lot-stones; Dòmhnall Ruadh\'s grave', cites=['III-0006', 'III-0034', 'III-0047', 'III-0138', 'III-0139']),
        489: dict(population=8500, kind='town', role='the port of the fleet: the roll of the willing, the first keel, the west quay renamed Cidhe an Diosail; the seat of Manannan\'s order', cites=['III-0004', 'III-0008', 'III-0021', 'III-0041', 'III-0120']),
        315: dict(population=2651, kind='town', role='the spirit-house of the Old Spirits with the ancestor-posts of the eastern shires; the old Hall', cites=['III-0056', 'III-0165', 'III-0216']),
        422: dict(population=3490, kind='town', walls=True, role='the walled seat of Clann Ìomhair, makers of the ceremonial blades (their folding lost LE 1,569)', cites=['III-0068', 'III-0209']),
        273: dict(population=1483, kind='town', role='Clann Fhearchair\'s town and the king\'s second court near the mountain; the white stone of its hills', cites=['III-0058', 'III-0059', 'III-0181a']),
        76: dict(population=189, kind='large village', role='once the richest place in the north-east on its salt (the fair of LE 959); its river silted, it keeps the market-court on the headland', cites=['III-0079', 'III-0147', 'III-0166', 'III-0168a']),
        166: dict(population=3500, kind='town', role='the first temple to Lia Fàil by name, roofed with northern slate; Queen Catrìona\'s own town', cites=['III-0087', 'III-0104', 'III-0114']),
        20: dict(population=3500, kind='town', role='the first house of the Hawk and the Book of the Hawk; the Hungry Hawk kept its house here after the schism', cites=['III-0062', 'III-0065', 'III-0140']),
        132: dict(population=2532, kind='town', walls=True, role='walled, with a market inside the landward gate; amber of the Hawk bay; the Fed Hawk\'s refuge', cites=['III-0088a', 'III-0142', 'III-0143']),
        64: dict(population=2044, kind='town', walls=True, role='kept its gates shut to all three claimants and holds its own gates and tolls by grant', cites=['III-0105', 'III-0115']),
        17: dict(population=3000, kind='town', role='the grain fleet of the cold way (laid up LE 1,634) and a house of disputation', cites=['III-0053', 'III-0128', 'III-0173', 'III-0215']),
        297: dict(population=2275, kind='town', role='its ridge market at every full moon and the tally-house of the south; its merchants go as one company to Muileann òg', cites=['III-0070a']),
        246: dict(population=368, kind='large village', role='the first paper mill; Beathag nic Thòmais\'s loft of old copies, left to the town on condition nothing in it be burned', cites=['III-0217', 'III-0218', 'III-0221']),
        443: dict(population=900, kind='large village', role='the salt port of the north-east after Ros fhionn silted, poorer since its pans went under the sea', cites=['III-0167', 'III-0226']),
        77: dict(population=2000, kind='town', walls=True, role='the house of disputation of the schools, shut for a generation after the table of years and reopened on condition', cites=['III-0074', 'III-0171', 'III-0172', 'III-0230']),
        119: dict(population=1200, kind='large village', role='a second harbour arm for the boats of Seann Tarr; the star-lore of its old steersmen, now lost', cites=['III-0014', 'III-0194']),
        249: dict(population=900, kind='large village', role='its harbour destroyed by Gailleann Ghlas (LE 1,399), not rebuilt; its boats sail from Cuan ruadh', cites=['III-0192']),
        305: dict(population=300, kind='village', role='half its houses empty since the sea-thieves and the poor harvests; its grain dues remitted', cites=['III-0132', 'III-0220']),
        143: dict(population=250, kind='village', role='the watch from the headland (lapsed); the timber from beyond the mist came ashore here', cites=['III-0039', 'III-0236']),
        355: dict(era_name=None, era_name_en='the coal-breakers\' mill of the eastern diggings', name_note='called Muileann chiar only from AE 82, when the silver guild settles its refiners here (IV-0172)',
                  population=300, kind='village', role='a coal-breaking mill for the houses\' galleries in the hills', cites=['IV-0172', 'gazetteer B355'], inferred=True),
        288: dict(population=400, kind='village', role='the potters of the grey-green glaze, lost with the last of Clann Mhic Phàil', cites=['III-0196', 'III-0203']),
        324: dict(population=1600, kind='large village', role='a shire seat on the wealth of its oyster beds', cites=['III-0119']),
        30: dict(population=2600, kind='town', role='burned twice: by Alasdair Bàn\'s ships in the Brothers\' War and by the great fire of LE 1,549; rebuilt with gable walls of stone', cites=['III-0178', 'III-0207']),
        34: dict(population=263, kind='large village', role='the ancestor shrine and its feast-market of honey and wax lights', cites=['III-0119a']),
    }
    pol_of = {int(k): v for k, v in d['province_polity'].items()}
    present = set()
    for i in sorted(BURGS):
        g = GAZ[i]
        if aidx(g['founded_age']) > aidx(AGE):
            s.absent(i, 'founded in Age %s%s' % (g['founded_age'], (' (%s)' % g['founded_event']) if g.get('founded_event') else ''),
                     ['gazetteer B%d' % i] + ([g['founded_event']] if g.get('founded_event') else []))
            continue
        p = BURGS[i]['prov']
        kw = dict(SPECIAL.get(i, {}))
        pop = kw.pop('population', None)
        if pop is None:
            pop = default_pop(i, AGE)
            if p in (28, 14, 105, 120, 75):
                pop = rnd(pop * 0.4, AGE)      # the dearth country, thinly held since LE 819 (III-0134, III-0220)
            elif p in (7, 36, 86, 23, 88, 107, 122):
                pop = rnd(pop * 0.6, AGE)      # the rest of the north-west, emptied toward the east and the inland shires
        f = faith_prov[p]
        s.burg(i, population=pop, kind=kw.pop('kind', None) or kind_for(pop, AGE), role=kw.pop('role', None) or generic_role(i),
               culture='dia-thirich', faith=f, order=order_prov.get(p) if f == 'old-faith' else None, polity=pol_of[p],
               cites=kw.pop('cites', None) or ['gazetteer B%d' % i], inferred=kw.pop('inferred', True), **kw)
        present.add(i)
    for b in d['burgs']:
        if b['id'] == 232:
            b['order'] = 'cloch'
            b['note'] = 'the second house of the Stone, which prays for the dead by name (LE 1,399)'
        if b['id'] == 326:
            b['order'] = 'seabhag'
            b['note'] = 'the southernmost house of the Hawk; its bell rings at each measured burning'

    # ---------------------------------------------------------------- new burgs
    s.new_burg('IV-N01', None, 'the guest-house at Allt an Àigh', ('marker', 1),
               population=20, kind='pilgrims\' guest-house', role='built by the keepers of the Old Spirits for those who come to drink at the right phase of the moon; its book names pilgrims from every shire',
               culture='dia-thirich', faith='old-spirits', polity='realm', reason='a guest-house beside the stream (LE 1,259); not a later town', cites=['III-0175'], inferred=True)
    s.new_burg('IV-N02', None, 'the ferry landing at Cidhe Beag', ('marker', 39),
               population=15, kind='ferry landing', role='a ferry family carries folk and goods down the Abhainn uaine by canoe and holds the landing for the rest of the age',
               culture='dia-thirich', faith='old-faith', polity='realm', reason='the ferry family settles at the landing in LE 1,619', cites=['III-0214'], inferred=True)

    # ---------------------------------------------------------------- routes
    named = {
        410: dict(first='I', name='Slighe-mhara àrsaidh', group='searoutes', cites=['I-0064a']),
        264: dict(first='III', name='Slighe Cnoc leathan', group='trails', cites=['II-0207']),
        3: dict(first='IV', name='An Rathad Tuath', group='roads', cites=['III-0145'], note='a crown coal-road over the pass by Muileann fhada, posted with the crown\'s sign; fresh horses at the waypoint houses'),
        17: dict(first='IV', name='Slighe Muileann dhearg', group='roads', cites=['III-0145'], note='a crown coal-road south from the hills by Muileann chrom'),
        98: dict(first='IV', name='Slighe Baile òg', group='roads', cites=['III-0145'], note='a crown coal-road down to the southern Seann Skell'),
        403: dict(first='IV', name='Seòlaid Ros fhionn', group='searoutes', cites=['III-0168b'], note='the salt boats of Ros fhionn round the north-east cape; the eastern boats keep it after the pans fail'),
        354: dict(first='IV', name='Slighe-mhara Caol fhiadhaich', group='searoutes', cites=['III-0189a'], note='the fishers of Caol fhiadhaich along the whole south coast and up the Abhainn uaine to Cidhe Beag'),
        349: dict(first='V', cites=['IV-0076a']),
        383: dict(first='VI', cites=['III-0215'], inferred=True),
        385: dict(first='VI', cites=['gazetteer B205'], inferred=True),
        50: dict(first='VI', cites=['V-0090']), 71: dict(first='VI', cites=['V-0090']),
    }
    for r in (16, 39, 52, 70, 111, 115, 130, 131, 446):
        named[r] = dict(first='IV', name=None, group='roads', cites=['III-0145', 'III-0145a'],
                        note='the carriers\' road down to Cathair dhearg, a crown coal-road (metalled and named Rathad na Mèinne by the Company in AE 34)')
    for r in (173, 175, 210, 229, 233, 248, 447):
        named[r] = dict(first='IV', name='Rathad na Banrighinn', group='roads', cites=['III-0114'],
                        note='Queen Catrìona\'s road south from the capital by Baile shean and Am Buabhall Fortanach, laid with stone')
    classify_routes(d, AGE, present, named, touched_rule(min_touch=1, allow_empty=True),
                    'A master trail or sea-lane is present when every town it touches stands in this age (or both end towns stand '
                    'and at most a quarter between are not yet towns); lanes touching no town are kept. The crown\'s coal-roads and '
                    'the queen\'s road are roads; the lanes the annals date later are absent. The cold way of the northern grain '
                    'barges (route 383) was laid up in LE 1,634 and is absent.')
    d['routes']['new'] = [
        collections.OrderedDict([('key', 'IV-R01'), ('name', None), ('name_en', 'the cairned drove road of Àth chiar'), ('group', 'trails'),
                                 ('points', [{'burg': 256}, {'burg': 12}, {'burg': 491}]), ('note', 'the drovers of Àth chiar drive cattle over the eastern hills to the mining towns each year: the first roads on the island marked with cairns'),
                                 ('cites', ['III-0093']), ('inferred', True)]),
        collections.OrderedDict([('key', 'IV-R02'), ('name', None), ('name_en', 'the grain barges down the Abhainn dhomhain'), ('group', 'rivers'),
                                 ('points', [{'burg': 19}, {'burg': 122}, {'burg': 489}]), ('note', 'forty-one barges counted at the bridge carrying the fleet\'s grain to the capital, on by the coast to Ros àrsaidh and up the Abhainn naomh to Seann Skell'),
                                 ('cites', ['III-0020']), ('inferred', True)]),
    ]

    # ---------------------------------------------------------------- markers
    M = {
        0: dict(note='Rebuilt in dressed stone by Clann Choinnich; the sick of any house admitted one day in seven.', cites=['III-0130']),
        1: dict(note='The Old Spirits renew the pilgrimage and build a guest-house beside the stream.', cites=['III-0175']),
        2: dict(note='Neck-rings for the heads of the seven houses; the silver fellowship keeps its craft within four families. Twice Clann Choinnich asked to smelt it with the coal, and was refused.', cites=['III-0052', 'III-0208', 'III-0233', 'III-0239']),
        3: dict(note='Widened for two carts; Queen Sìleas\'s name cut on the downstream parapet.', cites=['III-0071']),
        4: dict(note='Built anew at the salt-masters\' cost with their names on the keystones; fallen quiet since the salt went by sea, and the office of bridge-keeper done away with.', cites=['III-0081', 'III-0162', 'III-0168']),
        5: dict(note='Rebuilt in stone by Eilidh nic Chaluim, already known for its jugged buffalo; the queen\'s road runs past it.', cites=['III-0055', 'III-0114']),
        6: dict(note='Feeds the queen\'s progress with pan-fried spinach and black wine.', cites=['III-0234']),
        7: dict(note='Oatcakes fried in linseed oil and fire water for the coal-carters; its keeper fined for watering the fire water.', cites=['III-0073']),
        8: dict(note='Snowed in a whole season with a party of custodians\' reeves inside.', cites=['III-0187']),
        9: dict(note='Syrupped beef for the custodians\' reeves on their rounds.', cites=['III-0186']),
        10: dict(note='Where the ox-teams wait out the snow; the brothers made their peace under its roof.', cites=['III-0098', 'III-0180']),
        11: dict(note='Chartered with the seven great road-houses; the keepers settle their accounts here each year.', cites=['III-0184']),
        12: dict(era_name_en='the fire on the Baile chrom headland', icon='🔥', note='A driftwood fire over the thinned north-western coast.', cites=['II-0052'], inferred=True),
        13: dict(era_name_en='the light at Baile ìseal', icon='🔥', note='A driftwood and seal-fat fire.', cites=['II-0145'], inferred=True),
        14: dict(era_name_en='the light at Muileann bheag', icon='🔥', note='A driftwood fire kept by fisher-families.', cites=['II-0146'], inferred=True),
        15: dict(era_name_en='the light at Àth dhearg', icon='🔥', note='The way in toward Seann Tarr, whose harbour is gone.', cites=['II-0147', 'III-0192'], inferred=True),
        16: dict(era_name_en='the stone tower at Tobar dhearg', icon='🗼', note='The first sea-light raised above the ground; the village below roofed in slate after its fire.', cites=['II-0231', 'III-0090'], inferred=True),
        17: dict(era_name=None, era_name_en='the field of the Brothers\' War below Muileann ghlas', icon='⚔️', note='Iain Ciar defeated Alasdair Bàn here and took him alive (LE 1,274).', cites=['III-0179']),
        19: dict(note='Quarrymen broke into it and found a stair going down beyond their lamps; the custodians walled it up. The one who went down never told.', cites=['III-0149']),
        20: dict(note='Found again by charcoal-burners, with the same cut stair; walled up, and its entry bound in the custody-book to the other\'s.', cites=['III-0199']),
        21: dict(note='Seen near enough to foul the nets of the thinned north-west coast.', cites=['III-0170']),
        22: dict(note='The shepherds light no fires on the high pastures and at last forsake them; a reeve sent to make them see sense does not stay the night.', cites=['III-0083', 'III-0146']),
        23: dict(note='Kept by the druids of the schools, who walk its bounds each year: the one open rite of the schools.', cites=['III-0092']),
        24: dict(note='Its custody passed by royal grant to the priests of Macha; the other claimants left without contest.', cites=['III-0091']),
        25: dict(era_name_en='the sea-thieves\' water', note='Boats out of the small islands rob the coasting traders; a force of Queen Eilidh Bhàn burned their boats on Eilean dhubh and hanged Uilleam Ruadh.', cites=['III-0131', 'III-0133']),
        26: dict(note='The raiders\' islets of the east (no raid recorded in this age).', cites=['II-0175'], inferred=True),
        27: dict(note='The north-western strands, thinly held since the dearth.', cites=['III-0134'], inferred=True),
        28: dict(note='The priests of the Hawk cleared its moss and tried to read it, and wrote down that they tried.', cites=['III-0154']),
        29: dict(note='Cuimhnich an teine.', cites=['I-0071']),
        30: dict(note='The column of the saying.', cites=['I-0073']),
        31: dict(note='Measured into Ailean mac Dhùghaill\'s tables of the old ruins.', cites=['III-0152']),
        32: dict(note='Measured into Ailean mac Dhùghaill\'s tables.', cites=['III-0152']),
        33: dict(note='Measured by Ailean mac Dhùghaill: the altar faces the central mountains and not the sea.', cites=['III-0151']),
        34: dict(era_name=None, era_name_en='the loft of papers at Muileann chaol', icon='📚', note='Beathag nic Thòmais\'s loft over her mill, bought copies of the custody-book and the harbour rolls; the three copies of the landfall tidings side by side.', cites=['III-0217', 'III-0219', 'III-0221']),
        37: dict(era_name=None, era_name_en='the old games-field of the road-guards', note='The stone-walled field at Ceann leathan (the games are not recorded in this age).', cites=['II-0209'], inferred=True),
        38: dict(era_name=None, era_name_en='the harvest fair at Muileann òg', note='The merchants of the long city go to it as one company.', cites=['III-0070a']),
        39: dict(note='The ferry family\'s landing; the southern lane of the Caol fhiadhaich fishers ends here.', cites=['III-0214', 'III-0189a']),
        40: dict(note='The crossing days kept by the southern shires in writing; the panther year of LE 1,729 kept flocks in folds from Cnoc àrsaidh to the coast.', cites=['III-0072', 'III-0225']),
        41: dict(note='The custodian houses bury their heads here among graves older than any name on them.', cites=['III-0210']),
        44: dict(note='The headmen of Caol gharbh and Caol chrom settle the dues of the strait at the stone on the neck.', cites=['III-0167a']),
        46: dict(note='The meeting of the cups.', cites=['I-0154a'], inferred=True),
        48: dict(note='The Mason\'s Point.', cites=['I-0027a']),
    }
    for i in sorted(MARKERS):
        if i in M:
            s.marker(i, **M[i])
        else:
            d['markers']['absent'].append(i)
    NM = [
        ('IV-K01', dt('Cidhe an Diosail', 'marker'), 'the quay of the sunwise turn', ('burg', 489), '⛵', 'III-0041',
         'The west quay the fleet sailed from, lengthened in dressed stone; renamed so that trade might go on under the old name. The rite of the empty harbour and the prayer for the shut sea are kept here on one day.', ['III-0017', 'III-0023', 'III-0024', 'III-0040', 'III-0041', 'III-0223']),
        ('IV-K02', None, 'the vein-house and its lot-stones', ('burg', 491), '🏛️', 'III-0047',
         'Keeper of Crom\'s stone and the custody-book; the lot-stones for the galleries kept in a bag and shown to visitors; the seal of the trellis and the hollow stone.', ['III-0006', 'III-0047', 'III-0138a']),
        ('IV-K03', None, 'the spirit-house and the ancestor-posts', ('burg', 315), '🪵', 'III-0056',
         'The names of the dead of the eastern shires on posts cut anew each generation; burned by lightning and cut again from memory; cracked by the earthquake of LE 1,649.', ['III-0056', 'III-0165', 'III-0216']),
        ('IV-K04', None, 'the temple of Lia Fàil', ('burg', 166), '🐺', 'III-0087', 'The first temple to the Stone by name, roofed with slate brought by sea.', ['III-0086', 'III-0087']),
        ('IV-K05', None, 'Macha\'s great house', ('burg', 23), '🐎', 'III-0198', 'The largest roofed building of the age; its floor of black and white eleven years in the laying.', ['III-0198']),
        ('IV-K06', None, 'the house of the Hawk and the Book of the Hawk', ('burg', 20), '🦅', 'III-0065', 'Gormshuil nic Artair\'s first house; the Hungry Hawk kept it after the schism.', ['III-0062', 'III-0065', 'III-0140']),
        ('IV-K07', None, 'the ford of Àth shean', ('burg', 32), '⚔️', 'III-0106', 'Dùghall Garbh broke Raghnall Ruadh\'s host; some three hundred dead, most drowned in the ford.', ['III-0106']),
        ('IV-K08', None, 'the siege of Cathair dhomhain', ('burg', 26), '🏰', 'III-0108', 'Taken after forty days when the dead of the siege lines fouled its wells; the garrison freed on oath.', ['III-0108']),
        ('IV-K09', None, 'the battle of Muileann chrom', ('burg', 354), '⚔️', 'III-0110', 'Raghnall Ruadh fell here; his own custodians opened the vein-house the next day.', ['III-0110']),
        ('IV-K10', None, 'the battle of Cnoc naomh', ('burg', 318), '⚔️', 'III-0177', 'The battle that named the Brothers\' War.', ['III-0177']),
        ('IV-K11', None, 'the stone of the fourteen names', ('burg', 123), '🪦', 'III-0144', 'At the mouth of the fallen gallery of Cill ghlas.', ['III-0144']),
        ('IV-K12', None, 'the salt pans of Ros fhionn', ('burg', 76), '🧂', 'III-0079', 'Brine springs on the river flats; Ros fhionn salt was the measure of worth in the north-east.', ['III-0079', 'III-0147']),
        ('IV-K13', None, 'the paper mill', ('burg', 246), '📜', 'III-0218', 'The first paper on Dia-thìr, made from rags; the custody-book first copied onto paper.', ['III-0218']),
        ('IV-K14', None, 'the burned sea-thieves\' boats', ('cell', FEATURE_FIRST_CELL[3]), '🔥', 'III-0133', 'Queen Eilidh Bhàn\'s force burned the boats on the strand of Eilean dhubh.', ['III-0133']),
        ('IV-K15', None, 'the gates of Seann Warr', ('burg', 64), '🚪', 'III-0115', 'The grant of its own gates and tolls cut over the landward gate.', ['III-0115']),
        ('IV-K16', None, 'the felled grove of Doire fhionn', ('burg', 261), '🪓', 'III-0009', 'Felled for the keels of the fleet and drawn to the coast on ox-sleds; it never grew again.', ['III-0009', 'III-0048']),
        ('IV-K17', None, 'the house of disputation at Dùn thais', ('burg', 77), '🦌', 'III-0074', 'Carson an làmh seo? argued by rule; shut for a generation after the table of years.', ['III-0074', 'III-0171', 'III-0172', 'III-0230']),
        ('IV-K18', None, 'the timber from beyond the mist', ('burg', 143), '🪵', 'III-0236', 'Longer than any tree on the island, with nails no smith knows; carried to Seann Skell and burned.', ['III-0236']),
    ]
    for key, name, en, at, icon, eid, note, cites in NM:
        s.new_marker(key, name, en, at, icon=icon, event=eid, note=note, cites=cites)

    # ---------------------------------------------------------------- zones
    def Zz(key, name, en, typ, provs, note, cites, **kw):
        z = collections.OrderedDict([('key', key), ('name', name), ('name_en', en), ('type', typ)])
        z.update(kw)
        z['provinces'] = provs
        z['note'] = note
        z['cites'] = cites
        if name:
            dt(name, 'zone ' + key)
        return z
    d['zones'] = [
        Zz('IV-Z01', None, 'Manannan\'s mist on the eastern sea', 'sea', [], 'Hides Dia-thìr from every ship beyond it since the fleet sailed into it; thinner each winter at the snapshot.', ['III-0023', 'III-0120', 'III-0239a'], sea='the open sea west of the western headlands'),
        Zz('IV-Z02', None, 'the roll of the willing and the Setting-Out (LE 2–40)', 'earlier moment', [3, 38, 64, 15, 2, 1],
           'The willing entered on boards at Seann Skell by household; nearly one household in five of the coal-right went; nineteen hulls (or twenty-one).', ['III-0003', 'III-0004', 'III-0006', 'III-0021', 'III-0023']),
        Zz('IV-Z03', None, 'the cold hearths of the War of the Three Claimants (LE 558)', 'war', [p for p in range(1, 124) if p not in (96, 111, 85, 76)],
           'Raghnall Ruadh, holding the vein-house, denied the handful to every hearth and temple in the shires that stood against him; which shires is not told, so all but his own country are drawn.', ['III-0109'], inferred=True),
        Zz('IV-Z04', None, 'the swallowing cough and the closed coast road (LE 1,079–1,082)', 'plague', [59, 13, 43],
           'From Muileann dhomhain along the coast road to Seann Bhral; the queen closed the road and set reeves at the fords.', ['III-0158', 'III-0159', 'III-0160']),
        Zz('IV-Z05', None, 'the dearth on the north-west shore (LE 819), thinly held since', 'famine', [28, 14, 105, 120, 75],
           'Harvest after harvest failed; families left for the inland shires and the east. A reeve later counted fewer households than berths.', ['III-0134', 'III-0220'], master_zone=1),
        Zz('IV-Z06', None, 'the tremors of Cill ghlas (LE 379; LE 929)', 'fault', [96], 'Three wells cracked; later a gallery fell and killed fourteen.', ['III-0082', 'III-0144'], master_zone=3),
        Zz('IV-Z07', None, 'the dry years at Achadh shean (LE 1,479)', 'drought', [61], 'Three dry seasons; the crown carted grain in from the south; the wells shared by lot and by turn.', ['III-0200', 'III-0201'], master_zone=2),
        Zz('IV-Z08', None, 'the swell at Cnoc chaol (LE 724) and the floods of Cuan dhearg', 'wave', [120], 'A great swell with no storm took two children; An Gàire Dubh and a second flood at Cuan dhearg.', ['III-0126', 'III-0100', 'III-0229'], master_zone=4),
        Zz('IV-Z09', None, 'the Brothers\' War (LE 1,266–1,276)', 'war', [93, 21, 44, 31], 'The houses divided four to three between Iain Ciar and Alasdair Bàn.', ['III-0176', 'III-0177', 'III-0178', 'III-0179', 'III-0180']),
        Zz('IV-Z10', None, 'the coppice shires (LE 109)', 'law', [113, 66, 18, 19, 23, 40, 47, 10], 'No living oak felled without the reeve\'s mark in every shire with a Doire in its name.', ['III-0048'], inferred=True),
        Zz('IV-Z11', None, 'the salt country of Ros fhionn (LE 354–1,179)', 'trade', [79, 30, 50, 103, 99], 'Ros fhionn salt the common measure of worth in the north-eastern shires.', ['III-0079', 'III-0147', 'III-0166']),
        Zz('IV-Z12', None, 'the lordship of Seann Chwen for life (LE 1,276–1,291)', 'earlier moment', [31], 'Given to Alasdair Bàn at the brothers\' peace; returned to the crown at his death.', ['III-0180', 'III-0181']),
    ]
    d['labels'] = [
        {'text': None, 'text_en': 'the departed: north-about, beyond the mist', 'at': {'cell': FEATURE_FIRST_CELL[8]}, 'cites': ['III-0023', 'III-0027']},
        {'text': 'A Mhanannain, cùm a\' mhuir dùinte', 'text_en': 'Manannan, keep the sea shut', 'at': {'burg': 489}, 'cites': ['III-0212']},
        {'text': 'Dh\'fhalbh iad, agus cha do dh\'fhalbh iad', 'text_en': 'they went, and they did not go', 'at': {'burg': 489}, 'cites': ['III-0036', 'App.B §II']},
        {'text': None, 'text_en': 'the cold way of the grain barges (laid up LE 1,634)', 'at': {'burg': 215}, 'cites': ['III-0215']},
    ]
    for l in d['labels']:
        if l['text']:
            dt(l['text'], 'label', 'phrase')
    d['military']['hosts'] = [
        collections.OrderedDict([('name', None), ('name_en', 'the crown\'s riders on the coal-roads'), ('polity', 'realm'), ('station', {'burg': 19}),
                                 ('note', 'Fresh horses at the waypoint houses; a rider carries the council\'s word to the mountain between dawn and dark. No standing host: the houses fight with their followings when they fight.'),
                                 ('cites', ['III-0145a', 'App.C The older hosts'])]),
    ]
    d['military']['campaigns'] = [
        collections.OrderedDict([('name', None), ('name_en', 'the War of the Three Claimants'), ('date', 'LE 552–562'),
                                 ('sides', ['Catrìona nic Aonghais of Inis thais', 'Dùghall Garbh of Baile Mòr dhomhain', 'Raghnall Ruadh, master of the vein-house']),
                                 ('battles', [{'at': {'burg': 32}, 'cite': 'III-0106'}, {'at': {'burg': 26}, 'cite': 'III-0108'}, {'at': {'burg': 354}, 'cite': 'III-0110'}]),
                                 ('outcome', 'Catrìona Bhuadhach crowned; the ruling of the hearth'), ('cites', ['III-0104', 'III-0112', 'III-0113'])]),
        collections.OrderedDict([('name', None), ('name_en', 'the sea-thieves of the north-west'), ('date', 'LE 784–801'),
                                 ('sides', ['sea-thieves of the north-west shore', 'Queen Eilidh Bhàn\'s force']), ('outcome', 'boats burned on Eilean dhubh; Uilleam Ruadh hanged'), ('cites', ['III-0131', 'III-0133'])]),
        collections.OrderedDict([('name', dt('Cogadh nam Bràithrean', 'campaign')), ('name_en', 'the Brothers\' War'), ('date', 'LE 1,266–1,276'),
                                 ('sides', ['Iain Ciar', 'Alasdair Bàn']), ('battles', [{'at': {'burg': 318}, 'cite': 'III-0177'}, {'at': {'burg': 30}, 'cite': 'III-0178'}, {'at': {'burg': 360}, 'cite': 'III-0179'}]),
                                 ('outcome', 'peace at An Taigh-seinnse Mòr; Iain Ciar crowned'), ('cites', ['III-0176', 'III-0180', 'III-0183'])]),
    ]
    d['arms'] = [
        collections.OrderedDict([('polity', 'realm'), ('blazon', 'Azure trellised Or, a fess cotised argent, over all a mascle argent.'),
                                 ('note', 'The vein-house\'s seal, a trellis of gold on blue (the galleries) with a hollow lozenge (Crom\'s slab), sealed on the king\'s letters from the joining; the crown added only the white band. The arms of the kingdom still.'),
                                 ('cites', ['III-0138a', 'App.J §III'])]),
        collections.OrderedDict([('polity', 'the seven houses'), ('blazon', 'Azure trellised Or, over all a mascle argent (the custody\'s seal, without the crown\'s band).'),
                                 ('note', 'The seven houses sealed with the custody\'s seal; if they had badges of their own no roll remembers them.'), ('cites', ['App.J §I']), ('inferred', True)]),
    ]
    d['notes']['polities'] = collections.OrderedDict([
        ('realm', 'Since the Sundering took one household in five across the water, the realm has been ruled by the seven houses of custody and the crown they make, and since Dòmhnall Ruadh the ruler has been master of the vein-house too. For nine centuries one hand has held both the vein and the realm, and the Small-Burning Law has not changed. At the close of the age the crown is empty and the Council of Custodians sits in its place.'),
    ])
    d['notes']['burgs'] = collections.OrderedDict([
        ('489', 'Seann Skell of the west: the roll of the willing, the first keel, the sunwise turn in the river pool, and the quay renamed Cidhe an Diosail; now the seat of Manannan\'s order, whose priests pray the sea shut.'),
        ('491', 'Muileann dhearg: the vein-house above the town, where Crom\'s stone and the custody-book are kept and the lots for the galleries were drawn.'),
        ('23', 'Cathair mhòr: the greatest town on the island, the market of the south, and Macha\'s great house with its black and white floor.'),
        ('19', 'Cathair dhearg: the crown\'s seat and the council\'s, smaller than its southern neighbour.'),
        ('166', 'Inis thais: the first temple of Lia Fàil, and the town that gave the island Catrìona Bhuadhach.'),
    ])
    return s.finish()
