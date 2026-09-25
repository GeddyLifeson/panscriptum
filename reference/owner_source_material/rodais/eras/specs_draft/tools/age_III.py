"""Age III, the Holy Age (Flame Era): the island at FE 2,960, on the eve of the Sundering."""
# populations at the master's 50 people to the unit (eras/pop_sweep.py)
from common import *  # noqa: F401,F403

AGE = 'III'

# the nine great shares of the Roinn (FE 2), the Red Share, the Hall's ground and the Red Hill; inferred bounds
SHARES = collections.OrderedDict([
    ('S1', dict(name='Earrann Mhurchaidh', name_en='the great share of the north (Murchadh Mòr\'s)', seat=365,
                holder='Murchadh Mòr, the king\'s eldest living son', grounded=['II-0001b', 'II-0001c', 'book III'],
                provinces=[27, 83, 68, 113, 92, 119, 91, 23, 88, 54, 56, 62, 118, 115, 97, 104, 8, 98, 20, 47, 30, 102, 103, 50, 79, 99, 16])),
    ('S2', dict(name='Earrann Eithne', name_en='the lowland plain about Cathair mhòr (Eithne nic Ailein\'s)', seat=23,
                holder='Eithne nic Ailein, youngest of the nine', grounded=['II-0106b', 'II-0064b', 'book III'],
                provinces=[24, 31, 94, 55, 53, 21, 93, 42, 46, 18, 44, 90, 34, 12])),
    ('S3', dict(name='Earrann Ros dhomhain', name_en='the western share (seat on the harbour at Ros dhomhain)', seat=27,
                holder='not named by the tellers', grounded=['book III'],
                provinces=[5, 95, 22, 32, 52, 67, 29, 2, 15, 38, 64, 3, 77, 73, 117, 108])),
    ('S4', dict(name='Earrann Baile ghorm', name_en='the share of the salt shore (seat Baile ghorm)', seat=170,
                holder='not named; a cousin of the salt shore was cut through on the cord', grounded=['book III'],
                provinces=[25, 78, 72, 10, 17, 100, 19, 106, 11, 49])),
    ('S5', dict(name='Earrann Caol shean', name_en='the eastern share (the county of the silver seam lay in it)', seat=197,
                holder='not named', grounded=['book III'], inferred_seat=True,
                provinces=[48, 110, 87, 66, 58, 61, 41, 69, 82, 60, 70, 123, 89])),
    ('S6', dict(name='Earrann Muileann àrsaidh', name_en='the north-western share (inferred)', seat=244,
                holder='not named', grounded=[], inferred_seat=True,
                provinces=[7, 36, 86, 14, 28, 105, 75, 107, 120, 122])),
    ('S7', dict(name='Earrann Ceann àrsaidh', name_en='the share of the Abhainn fhionn and the hills east of the capital (inferred)', seat=88,
                holder='not named', grounded=[], inferred_seat=True,
                provinces=[74, 71, 40, 33, 81, 76, 96])),
    ('S8', dict(name='Earrann Tobar dhearg', name_en='the south-eastern share (inferred)', seat=398,
                holder='not named', grounded=[], inferred_seat=True,
                provinces=[4, 116, 63, 80, 121, 13, 59, 43, 109, 39, 37, 101, 57, 84])),
    ('S9', dict(name='Earrann Cnoc bheag', name_en='the share of the Abhainn ìseal and the Hawk bay (inferred)', seat=20,
                holder='not named', grounded=[], inferred_seat=True,
                provinces=[6, 9, 45, 51, 26, 111, 65])),
    ('RED', dict(name='An Earrann Dhearg', name_en='the Red Share of Ìomhar Dearg', seat=422,
                 holder='Ìomhar Dearg, who took Dùn dhearg with the sword the morning after the ford', grounded=['II-0001b', 'App.C Blàr Àth na Fala', 'book III'],
                 provinces=[85])),
    ('HALL', dict(name=None, name_en='the ground of the Hall (in no share)', seat=315, holder='the Keeper',
                  grounded=['II-0001b', 'II-0004'], provinces=[35, 112, 114])),
    ('HILL', dict(name=None, name_en='the Red Hill, claimed by three shares and serving none', seat=19, holder='its own holder',
                  grounded=['book III'], provinces=[1])),
])


def build():
    reset_names()
    s = Spec(AGE, collections.OrderedDict([
        ('age', 'III'),
        ('age_name', {'name': dt('An Aois Naomh', 'age name'), 'name_en': 'the Holy Age'}),
        ('era', {'abbr': 'FE', 'name': dt('Linn an Teine', 'era name'), 'name_en': 'the Flame Era'}),
        ('snapshot', collections.OrderedDict([
            ('date', '5 am Faoilleach, FE 2,960'),
            ('plan_label', 'FE 2,960 (ERA_PLAN): the last day of the Flame Era, the eve of the finding of land (LE 1)'),
            ('y', -39), ('m', 1), ('d', 5),
            ('last_event_shown', 'II-0249'),
            ('next_event', 'III-0001'),
            ('description',
             "Three thousand years after Ailean fell at the Ford of Blood, the island is one realm with two keepers. The "
             "ban-rìgh of the house of Tormod rules from the red hall at Cathair dhearg over the roads, the granaries and the "
             "peace of the lowlands, and the Keeper at Dùn ìseal keeps Brìde's flame, Crom's stone and the galleries, and set "
             "the stone cup in the ruler's hands; neither may do the other's work. The nine great shares of the Roinn are names "
             "on the boundary stones and in the provincial rolls; the provinces they became have granaries in their seats and "
             "copies of the laws. The Four Houses of custody hold Dùn ìseal, Dùn dhearg, Seann Dunn and Seann Tarr; the silver "
             "town keeps its own seam; Caol leathan keeps half its tolls and Cathair dhomhain its charter; and the north-west "
             "fisher-families pay the road-guard only when it comes. The Small-Burning Law has not changed a word since Fionnlagh "
             "Dall filled the cup, and no family's lives run longer than any other's. The one folk-faith has parted into eight "
             "companies that sit apart on the council. Raiders keep the north-western and eastern waters, five beacons burn "
             "driftwood and seal-oil, and the waypoint houses keep the road-peace on every carriers' road."),
            ('cites', ['II-0078', 'II-0247', 'II-0248', 'II-0249', 'II-0170', 'II-0213', 'II-0046', 'II-0152', 'II-0099',
                       'II-0138', 'II-0197', 'II-0221', 'II-0222', 'II-0027', 'II-0038', 'App.H §II']),
        ])),
        ('land_changes', [
            collections.OrderedDict([('what', 'No change to coast, rivers or heights. Talla na Lasrach stands over the flame at Dùn ìseal; stone bridges carry the carriers\' roads over the Abhainn dhomhain at Cathair dhearg, above Ros fhionn, below Dùn chrom, at Ceann àrsaidh and at Doire mhin.'),
                                     ('cites', ['II-0004', 'II-0032', 'II-0033', 'II-0192', 'II-0193', 'II-0194'])]),
            collections.OrderedDict([('what', 'The fields of Achadh mhòr were burned to the stubble in FE 556 and have long since been sown again.'),
                                     ('cites', ['II-0064b'])]),
        ]),
    ]))
    d = s.d

    # ---------------------------------------------------------------- cultures and faiths
    d['cultures'] = [collections.OrderedDict([('key', 'dia-thirich'), ('name', dt('Na Dia-thìrich', 'culture')), ('name_en', 'the Dia-thìrich'),
                                              ('master_culture', 2), ('provinces', list(range(1, 124))),
                                              ('note', 'One people in every province; the long years have gone out of the king\'s kin, and no family\'s lives run longer than another\'s (the last age of even population).'),
                                              ('cites', ['II-0249'])])]
    ORD = collections.OrderedDict([
        ('hall', dict(name='Òrd Bhrìde', name_en='the Hall\'s rite: the Keepers of Brìde\'s flame and Crom\'s stone', gods='Brìde of the flame; Crom Cruaich of the stone',
                      seat=315, note='The first order on Dia-thìr to govern rite and people; its Law runs in every province alike. It will not keep Allt an Àigh, the silver, or the old places.', cites=['II-0001', 'II-0002', 'II-0027', 'II-0248'])),
        ('dawn-hawk', dict(name=None, name_en='the dawn-hawk of the north coast (root of Òrd an t-Seabhaig)', gods='Mòd, the Hawk of Acaill; Fionntan mac Bòchra',
                           seat=132, note='Fowler families burn their handful at dawn with the hawk on the wrist; the rite has spread up the Abhainn ìseal. It refused the Hall\'s cutter in FE 2,840, the first outright refusal.', cites=['II-0158', 'II-0159', 'II-0216'])),
        ('wood-watchers', dict(name=None, name_en='the wood-watchers, the rite of Macha (root of Òrd Mhacha)', gods='Macha; the two horses of one yoke, Liath Macha and Dubh Sainglenn',
                               seat=19, note='Watchers of the western wood since FE 1,569; judge their own quarrels under the trees; a wood-watcher reads the omens of the red hall since Anna Ruadh.', cites=['II-0114', 'II-0118', 'II-0210', 'II-0220'])),
        ('wolf-sworn', dict(name=None, name_en='the wolf-sworn, the Fianna of the Stone (root of Òrd na Cloiche)', gods='Lia Fàil, the stone that cries out under the rightful king',
                            seat=1, note='Road-guards who swore on the white wolf-stone at the gate of Caol leathan; a hall about it since FE 2,843, a second stone at Inis thais.', cites=['II-0100', 'II-0161', 'II-0217'])),
        ('sting-oath', dict(name='Òrd Mhanannain', name_en='the sting-oath, called only true (Manannan\'s court; root of Òrd Mhanannain)', gods='Manannan mac Lir, lord of the sea; the yellow scorpion of his Cup of Truth',
                            seat=489, note='The harbour court of Seann Skell made the sting-oath a creed in FE 2,846 and dates the order from it; Seann Vell of the west carved the scorpion in yellow stone.', cites=['II-0086', 'II-0160', 'II-0218', 'II-0219'])),
        ('stag-elder', dict(name=None, name_en='the elder school of the stag (root of Scoiltean nan Draoidhean)', gods='Flidais, lady of the deer (the stag\'s name, Camaran, is later)',
                            seat=343, note='Asks why the vein answers some hands; strike-books; the first stone temple of the stag at Dùn thais (FE 2,889).', cites=['II-0021', 'II-0065', 'II-0125', 'II-0233'])),
        ('stag-younger', dict(name=None, name_en='the younger school of the stag at Muileann chaol', gods='Flidais',
                              seat=246, note='Holds that the vein answers labour and not birth; writes no parentage in its strike-books.', cites=['II-0163', 'II-0164', 'II-0165'])),
    ])
    d['faiths'] = [
        collections.OrderedDict([('key', 'old-faith'), ('name', dt('An Creideamh Sean', 'faith')), ('name_en', 'the Old Faith (the orders, as they stand in FE 2,960)'),
                                 ('master_religion', 1), ('type', 'Organized'), ('form', 'Polytheism'), ('deity', 'an Dagda first; Caoran the maker named after him'),
                                 ('provinces', []), ('orders', []),
                                 ('note', 'The one folk-faith of the island began plainly to part in FE 2,855; the council sits in companies by rite, and the Keeper complains he keeps the flame for eight peoples. The companies below are the roots of the orders the later ages name.'),
                                 ('cites', ['II-0215', 'II-0221', 'II-0222', 'App.B §II'])]),
        collections.OrderedDict([('key', 'old-spirits'), ('name', dt('Na Seann Spioradan', 'faith')), ('name_en', 'the Old Spirits (the ancestor-keeping of the old folk)'),
                                 ('master_religion', 2), ('type', 'Folk'), ('form', 'Shamanism'), ('deity', 'the ancestors, the weather, the sìth of hills and mounds'),
                                 ('provinces', []),
                                 ('note', 'The eldest folk-way, kept at the hearths without priests since the Binding; by the close of the age a company of its own on the council, "with no hawk, wolf, sting or stag in it".'),
                                 ('cites', ['II-0005', 'II-0013', 'II-0054', 'II-0246'])]),
    ]
    for k, o in ORD.items():
        e = collections.OrderedDict([('key', k), ('name', o['name']), ('name_en', o['name_en']), ('gods', o['gods']),
                                     ('seat', {'burg': o['seat']}), ('provinces', []), ('note', o['note']), ('cites', o['cites'])])
        if o['name']:
            dt(o['name'], 'order ' + k)
        d['faiths'][0]['orders'].append(e)
    order_provs = {
        'hall': [35, 112, 114, 96, 116, 110, 87, 90],
        'dawn-hawk': [51, 6, 9, 45],
        'wood-watchers': [1, 106, 49, 52, 67],
        'wolf-sworn': [2, 15],
        'sting-oath': [3, 64, 77, 120, 38, 73],
        'stag-elder': [16, 58, 61, 48, 66, 89, 41],
        'stag-younger': [],
    }

    # ---------------------------------------------------------------- polities
    s.polity('realm', dt('Rìoghachd Cathair dhearg', 'polity'), 'the realm of the red hall (the ban-rìgh of the lowlands)',
             inferred_name=True,
             form='kingship of the lowlands under the division of keeping: the ruler keeps the roads, granaries and peace; made by the stone cup at Dùn ìseal; the house of Tormod reigning',
             capital={'burg': 19},
             ruler={'name': dt('Beathag nic Dhòmhnaill', 'ruler', 'person'), 'title': 'ban-rìgh',
                    'note': 'daughter of Mòr nic Coinnich, the last name in the Holy Age king-list (crowned FE 2,929); Mòr\'s reign ends c. FE 2,949–2,959 by App.A, and Beathag is queen when land is found in LE 1',
                    'cites': ['II-0247', 'III-0002', 'App.A crowned rulers of the Age of Sundering'], 'inferred': True},
             culture='dia-thirich', color='#b03a2e (the red stone of the hall)',
             cites=['II-0077', 'II-0078', 'II-0135', 'II-0185', 'II-0247'])
    s.polity('hall', dt('Talla na Lasrach', 'polity'), 'the Hall of the Flame (the Keepers at Dùn ìseal)',
             form='custody over the vein: the Keeper of Brìde\'s flame and Crom\'s stone, chosen from the Four Houses of custody; no spears',
             capital={'burg': 315},
             ruler={'name': dt('Catrìona nic Mhuirich', 'ruler', 'person'), 'title': 'Keeper',
                    'note': 'the last of the one hundred and forty names on the Keepers\' roll (in office FE 2,929); her successor, if any, is not named', 'cites': ['II-0247', 'II-0248'], 'inferred': True},
             culture='dia-thirich', color='#e0a526 (flame gold)',
             cites=['II-0001', 'II-0004', 'II-0046', 'II-0078', 'II-0248'])
    s.polity('north-west', None, 'the fisher-families of the north-west (under their headman at Caol mhòr)',
             form='fisher-families under a headman of their own; they send tolls to Cathair dhearg only in the years the road-guard comes to take them',
             capital={'burg': 95}, ruler={'name': None, 'note': 'a headman, not named'}, culture='dia-thirich', color='#4f7d8c (sea-grey)',
             suzerain='realm', cites=['II-0197', 'II-0198', 'II-0200'])

    # provinces of the rìghrean: the modern shires whose seats stand in this age, the others folded in
    late = [p for p in range(1, 124) if province_seat_age(p) not in ('I', 'II', 'III')]
    keep = [p for p in range(1, 124) if p not in late]
    fold = {p: nearest_province(p, keep) for p in late}
    fold[67] = 52
    NW = [7, 36, 86, 14, 28, 105, 75, 107, 120, 122]
    HALL = [35, 114]
    assign = {'hall': HALL, 'north-west': NW}
    used = set(HALL) | set(NW)
    assign['realm'] = [p for p in range(1, 124) if p not in used]
    s.assign(assign)
    realm = d['polities'][0]
    prov_units = []
    for p in keep:
        if p in HALL or p in NW:
            continue
        members = [p] + [q for q, t in fold.items() if t == p and q not in NW]
        prov_units.append({'name': dt('Mòr-roinn %s' % PROVINCES[p]['name'], 'province unit', 'place'), 'name_en': 'the province of %s' % PROVINCES[p]['name'],
                           'kind': 'province of the rìghrean (granary seat)', 'seat': {'burg': PROVINCES[p]['burg']}, 'provinces': members,
                           'inferred': True})
    realm['admin_units'] = [
        {'name': None, 'name_en': 'the houses of custody and the great lordships', 'kind': 'lordships within the realm', 'units': [
            {'name': dt('Sliochd Ìomhair', 'house', 'place'), 'name_en': 'the house of Ìomhar (the old kings\' house; graves and granaries of Dùn dhearg)', 'seat': {'burg': 422}, 'provinces': [85, 57, 84], 'cites': ['II-0046', 'II-0056', 'II-0136', 'II-0182'], 'inferred': True},
            {'name': dt('Sliochd Thormoid', 'house', 'place'), 'name_en': 'the house of Tormod (the ruling house; temple at Seann Dunn)', 'seat': {'burg': 18}, 'provinces': [110], 'cites': ['II-0046', 'II-0047', 'II-0185', 'II-0187']},
            {'name': dt('Sliochd Raghnaill', 'house', 'place'), 'name_en': 'the house of Raghnall (boats and beacons of the north-east)', 'seat': {'burg': 34}, 'provinces': [103, 69, 82, 60], 'cites': ['II-0046', 'II-0048', 'II-0175', 'II-0240', 'II-0241'], 'inferred': True},
            {'name': dt('Sliochd Fhearchair', 'house', 'place'), 'name_en': 'the silversmiths\' house of Muileann chiar (the silver is not the mountain\'s, nor the crown\'s)', 'seat': {'burg': 419}, 'provinces': [], 'cites': ['II-0150', 'II-0152']},
            {'name': None, 'name_en': 'the lords of Caol leathan (half the western tolls)', 'seat': {'burg': 1}, 'provinces': [2], 'cites': ['II-0091', 'II-0099']},
            {'name': None, 'name_en': 'Cathair dhomhain, chartered to its own tolls', 'seat': {'burg': 26}, 'provinces': [32], 'cites': ['II-0138']},
            {'name': None, 'name_en': 'the lords of the deep river (the fords of Baile Mòr dhomhain)', 'seat': {'burg': 273}, 'provinces': [111], 'cites': ['II-0106a']},
            {'name': None, 'name_en': 'the lords of the western plain (Baile Mòr fhionn)', 'seat': {'burg': 204}, 'provinces': [2, 108], 'cites': ['II-0134a'], 'inferred': True},
        ]},
        {'name': None, 'name_en': 'the provinces of the rìghrean', 'kind': 'provinces with granaries and copies of the laws',
         'note': 'The rolls counted a hundred and thirty-one provinces at the Roinn; the modern shires whose seats stand in this age are used, and the shires whose seats come later are folded into the nearest. Their bounds run on the stones of the Peace of the Threshold.',
         'cites': ['II-0170', 'II-0213', 'II-0229', 'App.H §II'], 'units': prov_units},
    ]
    d['polities'][1]['admin_units'] = [
        {'name': None, 'name_en': 'the ground of the Hall and the galleries', 'kind': 'custody', 'provinces': [35], 'cites': ['II-0001b', 'II-0004', 'II-0078']},
        {'name': None, 'name_en': 'the slab at Tobar dhìreach and the schools\' hill', 'kind': 'custody', 'provinces': [114], 'cites': ['I-0247', 'II-0065'], 'inferred': True},
        {'name': dt('Na Naoi Teallaichean', 'hall unit', 'place'), 'name_en': 'the nine hearths about the mountain\'s foot', 'kind': 'households of custody (not bounded)', 'provinces': [35, 112, 96, 87],
         'cites': ['II-0003'], 'inferred': True},
    ]
    d['province_polity_notes'] = collections.OrderedDict([
        ('hall', 'Dùn ìseal and the slab country. The mountain districts round Muileann chiar (112) are the Hall\'s carriers\' country but their granaries are the realm\'s under the shared-meal law, so they are the realm\'s here.'),
        ('north-west', 'Inferred extent of the fisher-families\' country; the realm\'s road-guard comes seldom.'),
        ('unclaimed', 'None of the 123 shires; the windy coast (no shire) is unclaimed.'),
    ])
    d['diplomacy'] = [
        {'a': 'realm', 'b': 'hall', 'relation': 'the division of keeping', 'since': ann_date('II-0078'),
         'note': 'The Keeper keeps the flame and the galleries; the ruler the roads, granaries and peace. The ruler may not enter the galleries and the Keeper may not raise spears. Since Gilleasbuig Mòr the Keeper sets the stone cup in the ruler\'s hands.', 'cites': ['II-0078', 'II-0185', 'II-0247']},
        {'a': 'realm', 'b': 'north-west', 'relation': 'tributary when the road-guard comes', 'cites': ['II-0197']},
        {'a': 'realm', 'b': 'raiders', 'relation': 'hostile (outlaws of the north-western and eastern waters)', 'cites': ['II-0050', 'II-0175', 'II-0201'], 'note': 'not a polity; listed for the map\'s pirate waters'},
    ]

    # ---------------------------------------------------------------- burgs
    pol_of = {int(k): v for k, v in d['province_polity'].items()}
    order_of = {}
    for k, ps in order_provs.items():
        for p in ps:
            order_of[p] = k
    faith_prov = {}
    for p in range(1, 124):
        mf = master_faith_of_province(p)
        if p in order_of:
            faith_prov[p] = 'old-faith'
        elif mf == 2:
            faith_prov[p] = 'old-spirits'
        elif mf == 3 or mf == 0:
            faith_prov[p] = 'old-spirits'
        else:
            faith_prov[p] = 'old-faith'
            order_of.setdefault(p, 'hall')
    for p, f in faith_prov.items():
        if f == 'old-faith':
            d['faiths'][0]['provinces'].append(p)
        else:
            d['faiths'][1]['provinces'].append(p)
    for o in d['faiths'][0]['orders']:
        o['provinces'] = sorted(p for p, k in order_of.items() if k == o['key'] and faith_prov[p] == 'old-faith')
    d['faiths'][0]['orders'][6]['provinces'] = []
    d['faiths'][0]['orders'][6]['towns'] = [246]

    SPECIAL = {
        19: dict(population=514, kind='town', role='seat of the realm since Beathag Mhòr: the red hall on the rise above the harbour, the clerks\' room, the bridge-foot of the Abhainn dhomhain', cites=['II-0135', 'II-0137', 'II-0155', 'II-0213']),
        315: dict(population=600, kind='large village', role='Talla na Lasrach over the flame, the stone cup on its threshold, the galleries, the market under the Hall on the quarter days', cites=['II-0004', 'II-0026', 'II-0064a', 'II-0248']),
        422: dict(population=500, kind='town', role='the old kings\' hill: Goraidh Mòr\'s hall with a granary at each corner, the graves of the house of Ìomhar and of the kings; its reeves keep their own accounts', cites=['II-0056', 'II-0079', 'II-0136', 'II-0182', 'II-0185']),
        26: dict(population=710, kind='town', role='the older and larger harbour at the mouth of the western road; chartered to its own tolls; strict keeper of the Law\'s measure; refuses the wood-watchers', cites=['II-0075', 'II-0138', 'II-0211']),
        23: dict(population=630, kind='town', walls=True, role='the first walled town on the island; Eithne\'s hall; the first granary behind a wall', cites=['II-0067', 'II-0106b', 'II-0174']),
        94: dict(population=327, kind='town', role='a city on the southern fishing and the silver of the eastern road; the first stone quay on the island', cites=['II-0230']),
        17: dict(population=430, kind='town', role='the gathering-place of the northern wool trade, with its own road-guard; the wool-fair at every shearing', cites=['II-0106', 'II-0234']),
        489: dict(population=630, kind='town', role='the western river port where the sting-oath became a creed and Manannan\'s court was held', cites=['II-0218']),
        419: dict(population=89, kind='large village', role='the silver town of Sliochd Fhearchair: the seam, the weights every trader uses, the stamped rings', cites=['II-0015', 'II-0016', 'II-0064', 'II-0127', 'II-0152', 'II-0153']),
        1: dict(population=430, kind='town', role='the lords\' harbour of the western strait; half the western tolls; the wolf-sworn\'s hall about the white stone at the gate', cites=['II-0091', 'II-0098', 'II-0099', 'II-0100', 'II-0217']),
        166: dict(population=340, kind='large village', role='the shrine to the ancestors lost at sea, where the handful is burned on the shore; the second wolf-stone', cites=['II-0069', 'II-0161']),
        273: dict(population=290, kind='large village', role='at the foot of the high pass: the market at the fords on the day after each new moon', cites=['II-0057', 'II-0106a']),
        18: dict(population=260, kind='large village', role='seat of Sliochd Thormoid: hall and temple with a court for pilgrims, its coal-lamp said to burn fuller than the measure', cites=['II-0047', 'II-0059', 'II-0187']),
        34: dict(population=190, kind='large village', role='seat of Sliochd Raghnaill: boats and not galleries, the first household sentenced under the Law, the refused fisher-families', cites=['II-0028', 'II-0048', 'II-0144', 'II-0203']),
        343: dict(population=140, kind='village', role='the house of the stag\'s people north of the mountain, keepers of the strike-books', cites=['II-0065', 'II-0125', 'II-0162']),
        246: dict(population=85, kind='village', role='the school of Donnchadh mac Iain, the younger school of the stag', cites=['II-0163', 'II-0165']),
        77: dict(population=260, kind='large village', walls=True, role='walled; the first stone temple of the stag\'s people', cites=['II-0233']),
        22: dict(population=260, kind='large village', role='the market of the southern fishing; the road-guards\' games in a stone-walled field', cites=['II-0068', 'II-0129', 'II-0209']),
        276: dict(population=150, kind='village', role='the slab over the crack; Clann na Ceiste keep the lines', cites=['I-0247', 'IV-0251a']),
        432: dict(population=35, kind='village', role='the grave-keepers of Tuam Cnoc dhìreach, paid by the Hall a handful of coal a season', cites=['II-0044']),
        229: dict(population=70, kind='village', role='the roofed bath-house over the warm springs and its keeper for Dian Cècht', cites=['II-0063', 'II-0224']),
        151: dict(population=83, kind='village', role='rebuilt as a market town after the War of the Roads; the harvest fair at Lùnastal', cites=['II-0093', 'II-0130']),
        365: dict(population=480, kind='town', role='great enough on the fishing to send its own member to the council at Dùn ìseal, seated at the foot of the hall', cites=['II-0235']),
        37: dict(population=200, kind='large village', role='the home of the northern fishing fleet', cites=['II-0236']),
        241: dict(population=85, kind='village', role='the timber watch-tower against the island raiders, manned by the fisher-kin of Sliochd Raghnaill', cites=['II-0240']),
        119: dict(population=180, kind='village', role='gives boats and men to the watch; a place on the council beside Sliochd Raghnaill', cites=['II-0241']),
        95: dict(population=200, kind='large village', role='the fisher-families of the north-west gather here under their own headman', cites=['II-0197']),
    }
    present = set()
    for i in sorted(BURGS):
        g = GAZ[i]
        if aidx(g['founded_age']) > aidx(AGE) and i not in SPECIAL:
            s.absent(i, 'founded in Age %s%s' % (g['founded_age'], (' (%s)' % g['founded_event']) if g.get('founded_event') else ''),
                     ['gazetteer B%d' % i] + ([g['founded_event']] if g.get('founded_event') else []))
            continue
        p = BURGS[i]['prov']
        pol = pol_of.get(p, 'unclaimed')
        if i == 419:
            pol = 'realm'
        kw = dict(SPECIAL.get(i, {}))
        pop = kw.pop('population', None) or default_pop(i, AGE)
        kind = kw.pop('kind', None) or kind_for(pop, AGE)
        role = kw.pop('role', None) or generic_role(i)
        cites = kw.pop('cites', None) or ['gazetteer B%d' % i]
        faith = faith_prov[p]
        order = order_of.get(p) if faith == 'old-faith' else None
        if i == 246:
            order = 'stag-younger'
        s.burg(i, population=pop, kind=kind, role=role, culture='dia-thirich', faith=faith, order=order, polity=pol,
               cites=cites, inferred=(i not in SPECIAL) or True, **kw)
        present.add(i)

    # ---------------------------------------------------------------- new burgs
    s.new_burg('III-N01', None, 'the masons\' lodge by the western crossing', ('burg', 27),
               population=40, kind='lodge', role='the bridge-masons\' fellowship, sworn on the stone cup: no span closed in the dark, none paid for in coal',
               culture='dia-thirich', faith='old-faith', polity='realm', reason='the lodge is kept near the western crossing in the country of Ros dhomhain; not a later town',
               cites=['II-0034'], inferred=True)
    s.new_burg('III-N02', None, 'the pilgrims\' guest-shelters at Allt an Àigh', ('marker', 1),
               population=15, kind='pilgrim shelter', role='pilgrims of every rite walk here by night in the right quarter of the moon',
               culture='dia-thirich', faith='old-spirits', polity='realm', reason='the stream is kept by the ancestors and the weather; a guest-house is built only in LE 1,259, so the shelter here is inferred',
               cites=['II-0011', 'II-0012', 'II-0223', 'III-0175'], inferred=True)
    s.new_burg('III-N03', None, 'the summer shelters on Eilean ruadh', ('burg', 127),
               population=0, kind='seasonal shelter', role='coast families take sheep over for the summer grazing and bring them back before the storms; turf shelters used again by later herders',
               culture='dia-thirich', faith='old-spirits', polity='north-west', reason='summer herders on Eilean ruadh (FE 2,791)', cites=['II-0204'], inferred=True)

    # ---------------------------------------------------------------- routes
    named = {
        410: dict(first='I', name='Slighe-mhara àrsaidh', group='searoutes', cites=['I-0064a']),
        264: dict(first='III', name='Slighe Cnoc leathan', group='trails', cites=['II-0207'], note='the road to Cnoc leathan kept by the sunny house under Anna Ruadh\'s charter'),
        3: dict(first='III', name=None, group='trails', cites=['II-0057', 'II-0105'], note='the carriers\' way north over the high pass (named An Rathad Tuath in the Sundering)'),
        50: dict(first='VI', cites=['V-0090']), 71: dict(first='VI', cites=['V-0090']),
        403: dict(first='IV', cites=['III-0168b']), 354: dict(first='IV', cites=['III-0189a']), 349: dict(first='V', cites=['IV-0076a']),
        383: dict(first='IV', last='IV', cites=['III-0215']), 385: dict(first='VI', cites=['gazetteer B205'], inferred=True),
        17: dict(first='IV', cites=['III-0145'], track_before=True), 98: dict(first='IV', cites=['III-0145'], track_before=True),
    }
    for r in (16, 39, 52, 70, 111, 115, 130, 131, 446):
        named[r] = dict(first='III', name=None, group='trails', cites=['II-0030', 'II-0035', 'II-0145'][:2],
                        note='part of the carriers\' road from the mountain down to the western bridge-foot (the later Rathad na Mèinne)', inferred=True)
    for r in (173, 175, 210, 229, 233, 248, 447):
        named[r] = dict(first='IV', cites=['III-0114'], track_before=True)
    classify_routes(d, AGE, present, named, touched_rule(min_touch=1, allow_empty=True),
                    'A master trail or sea-lane is present when every town it touches stands in this age (or both end towns stand '
                    'and at most a quarter of the sites between are not yet towns). Short lanes touching no town are kept: the '
                    'carriers\' paths and the coasting boats of this age go everywhere. Roads and lanes the annals date later are '
                    'absent, or run as plain tracks where their towns already stand.')
    d['routes']['new'] = [
        collections.OrderedDict([('key', 'III-R01'), ('name', None), ('name_en', 'the pilgrims\' path from Caol shean to Allt an Àigh'), ('group', 'trails'),
                                 ('points', [{'burg': 197}, {'marker': 1}]), ('note', 'walked by night so pilgrims reach the water in the right quarter of the moon; paved anew by pilgrims of four rites in one season'),
                                 ('cites', ['II-0012', 'II-0223'])]),
        collections.OrderedDict([('key', 'III-R02'), ('name', None), ('name_en', 'the carriers\' path to Ceann chaol'), ('group', 'trails'),
                                 ('points', [{'burg': 315}, {'burg': 397}]), ('note', 'cut from the mountain down to the harbour with steps hewn at the steep places; the Hall\'s baskets go down, dried fish comes up'),
                                 ('cites', ['II-0030'])]),
        collections.OrderedDict([('key', 'III-R03'), ('name', None), ('name_en', 'the diggers\' road'), ('group', 'trails'),
                                 ('points', [{'burg': 3}, {'marker': 41}]), ('note', 'kept in repair by the families of the Làrach an Dùin diggers as their penance, from Baile ghorm to Tuam Cnoc dhìreach'),
                                 ('cites', ['II-0169'])]),
        collections.OrderedDict([('key', 'III-R04'), ('name', None), ('name_en', 'the river-boats of the Abhainn uaine'), ('group', 'rivers'),
                                 ('points', [{'marker': 39}, {'burg': 354}]), ('note', 'flat hide boats carry grain and salt fish up from the landing at Cidhe Beag; the boatmen\'s fellowship is sworn on a paddle'),
                                 ('cites', ['II-0131', 'II-0132', 'II-0133'])]),
        collections.OrderedDict([('key', 'III-R05'), ('name', None), ('name_en', 'round the islands (Sliochd Raghnaill\'s voyage)'), ('group', 'searoutes'),
                                 ('points', [{'burg': 34}, {'cell': 3856}, {'cell': 3384}, {'cell': 420}, {'burg': 34}]),
                                 ('note', 'boats of Seann Tarr sail round the offshore islands, Eilean ruadh, Eilean dhearg and Eilean fhada among them, in one season; no crew goes further'),
                                 ('cites', ['II-0203', 'II-0049']), ('inferred', True)]),
        collections.OrderedDict([('key', 'III-R06'), ('name', None), ('name_en', 'the western road (salt inland from Cuan shean)'), ('group', 'trails'),
                                 ('points', [{'burg': 282}, {'burg': 134}, {'burg': 19}]), ('note', 'Cuan shean\'s salt goes inland along the western road and keeps the fish of half the island'),
                                 ('cites', ['II-0070', 'II-0071']), ('inferred', True)]),
    ]

    # ---------------------------------------------------------------- markers
    M = {
        0: dict(note='A roofed bath-house over the springs with sleeping-places for the sick; the Hall\'s keeper of the springs tends them in Dian Cècht\'s name, and bathes the sick of every rite.', cites=['II-0014', 'II-0063', 'II-0224']),
        1: dict(note='Named for fortune; the Hall declined it for the ancestors and the weather. Pilgrims of every rite walk to it.', cites=['II-0011', 'II-0013', 'II-0223']),
        2: dict(era_name=None, era_name_en='the silver seam of Muileann chiar', note='Found near the great vein but apart from it; not holy, and so not the crown\'s either.', cites=['II-0015', 'II-0017', 'II-0152']),
        3: dict(era_name=None, era_name_en='the western crossing of the Abhainn dhomhain', note='First bridged FE 157, rebuilt in wider stone by Mòrag nan Rathad and a third time for carts; Ailean Clachair\'s hearth-sign in the keystone.', cites=['II-0032', 'II-0083', 'II-0190']),
        4: dict(era_name=None, era_name_en='Ailean Clachair\'s crossing', note='A single span of fitted stone above Ros fhionn; the founder\'s hearth-sign still sharp in the keystone.', cites=['II-0033', 'II-0191']),
        5: dict(era_name=dt('Taigh Mòr nic Dhùghaill', 'marker 5'), era_name_en='Mòr nic Dhùghaill\'s house', note='The first waypoint house, serving jugged buffalo; the War of the Roads ended under its roof. Named Am Buabhall Fortanach by the Sundering.', cites=['II-0036', 'II-0099', 'II-0206', 'III-0055']),
        6: dict(era_name=None, era_name_en='the sunny house', note='A waypoint house facing south on the eastern road; the only one with a royal charter, for the upkeep of Slighe Cnoc leathan.', cites=['II-0072', 'II-0207']),
        7: dict(era_name=None, era_name_en='the house on the northern road', note='Built by Catrìona Ghlic for the carriers of the Hall\'s baskets; serves fire-water.', cites=['II-0104', 'II-0196']),
        8: dict(era_name=None, era_name_en='the house on the cold road', note='A stone house on the open moor for carriers caught by snow.', cites=['II-0105']),
        9: dict(era_name=None, era_name_en='the golden house', note='The first waypoint house raised by a ruler, Mòrag nan Rathad.', cites=['II-0082']),
        10: dict(era_name=None, era_name_en='the house at the middle of the road', note='A turf longhouse with a hearth at each end; where the road-toll was first gathered and the census of hands was counted.', cites=['II-0037', 'II-0080', 'II-0141']),
        11: dict(note='The oldest house under the road-peace, rebuilt in stone; so far from any town that one is never nearer it than halfway.', cites=['II-0038', 'II-0195']),
        12: dict(era_name_en='the fire on the Baile chrom headland', icon='🔥', note='Relit after the boat was lost in calm water, fed with driftwood as the Law requires.', cites=['II-0051', 'II-0052']),
        13: dict(era_name_en='the light at Baile ìseal', icon='🔥', note='Rebuilt to bring the eastern boats home; driftwood and seal fat.', cites=['II-0145', 'II-0029']),
        14: dict(era_name_en='the light at Muileann bheag', icon='🔥', note='Kept by north-western fisher-families who pay no toll in return.', cites=['II-0146']),
        15: dict(era_name_en='the light at Àth dhearg', icon='🔥', note='Rebuilt by Sliochd Raghnaill to mark the way in to Seann Tarr.', cites=['II-0147']),
        16: dict(era_name_en='the stone tower at Tobar dhearg', icon='🗼', note='The first sea-light raised above the ground, burning the seal-oil of the north-west; no coal may feed a beacon.', cites=['II-0029', 'II-0231']),
        19: dict(note='Lost: the western shaft is known only in the old tales at this date; quarrymen break into it in the Age of Sundering.', cites=['I-0037', 'III-0149']),
        20: dict(note='Lost: found again by charcoal-burners in the Age of Sundering.', cites=['I-0120', 'III-0199']),
        21: dict(note='A boat of Baile chrom lost in calm water (FE 405); the second sighting (FE 2,761), and a second boat lost.', cites=['II-0051', 'II-0202']),
        22: dict(note='The Keepers forbid any fire, of wood or coal, in sight of these hills; the ban is never lifted.', cites=['II-0007']),
        23: dict(era_name_en='the stag\'s grove', note='Sìleas nic Coinnich taught here; the wood-watchers cut a black-barked tree; the woods were divided and this one kept by the stag\'s people, with stones at its edges.', cites=['II-0022', 'II-0115', 'II-0118']),
        24: dict(era_name_en='the dark wood of the wood-watchers', note='Watchers of the black horned beast since FE 1,569; kept by them by the division of the woods; they judge their own quarrels under the trees.', cites=['II-0114', 'II-0118', 'II-0220']),
        25: dict(era_name_en='the outlaws\' water of the north-west', note='Households stripped of their right for a third offence took to boats and raid the fishing strands.', cites=['II-0050']),
        26: dict(era_name_en='the raiders\' islets of the east', note='Outlaws raid the eastern strands; Sliochd Raghnaill burned two of their boats.', cites=['II-0175']),
        27: dict(era_name_en='the raided strands of the north-west', note='Raiders took a season\'s dried fish; the sting-sworn merchants of Ros bheag paid for two armed boats.', cites=['II-0201']),
        28: dict(note='Fenced with stakes against the cattle; the stag-scholars set their letters beside its marks and they matched nothing.', cites=['II-0062', 'II-0089']),
        29: dict(note='The pillar of Cuimhnich an teine.', cites=['I-0071']),
        30: dict(note='Scholars of the stag could not read it; the people of Cnoc ghorm told them what it said.', cites=['II-0167']),
        31: dict(note='Ruin, listed by Coinneach Mòr\'s walkers with who does not own it.', cites=['II-0061']),
        32: dict(note='Ruin; the men of Baile ghorm dug it for riches and found ash, and were sentenced as though they had broken the Law.', cites=['II-0061', 'II-0168']),
        33: dict(note='The Keepers set no foot in it: Beathag Bhàn found its altar already turned toward the mountain and declared it not the Hall\'s.', cites=['II-0008']),
        34: dict(era_name=None, era_name_en='the school of the strike-books', icon='📚', note='Donnchadh mac Iain and his hearers at Muileann chaol keep their own strike-books without parentage.', cites=['II-0163', 'II-0165']),
        37: dict(era_name=None, era_name_en='the road-guards\' games', icon='🤺', note='The road-guards fight with blunted staves for a silver ring; Anna Ruadh gave the field stone walls. The first winner remembered is Mòrag Dhubh of Cnoc mhòr.', cites=['II-0129', 'II-0209']),
        38: dict(era_name=None, era_name_en='the harvest fair at Muileann òg', icon='🎪', note='Held each harvest at Lùnastal for the trade of the western and southern roads, on the old ford-ground.', cites=['II-0130']),
        39: dict(era_name=None, era_name_en='the landing on the Abhainn uaine', note='Built so the grain of the lowlands may go upriver by boat; the carriers protested and lost.', cites=['II-0131']),
        40: dict(note='The crossing runs over the carriers\' southern road: no panther may be killed on the road in its season, and the carriers wait in the waypoint houses.', cites=['II-0055', 'II-0239']),
        41: dict(note='Fionnlagh Dall carried here eleven days and laid among graves older than any name; hallowed over his grave; grave-keepers settled beside it.', cites=['II-0042', 'II-0043', 'II-0044']),
        46: dict(note='The meeting of the cups; the Hall\'s cup of Fionnlagh Dall now stands on the threshold of Talla na Lasrach.', cites=['I-0154a', 'II-0026'], inferred=True),
        48: dict(note='The Mason\'s Point.', cites=['I-0027a']),
    }
    for i in sorted(MARKERS):
        if i in M:
            s.marker(i, **M[i])
        else:
            d['markers']['absent'].append(i)
    ford = near_cell(('burg', 422), 85)
    NM = [
        ('III-K01', dt('Blàr Àth na Fala', 'marker'), 'the Ford of Blood (FE 1)', ('cell', ford), '⚔️', 'I-0098a',
         'Where Ailean Mòr held the ford alone three days against the host of the east and fell on the third night; Ìomhar Dearg took Dùn dhearg the next morning.', ['I-0098a', 'App.C Blàr Àth na Fala']),
        ('III-K02', dt('Talla na Lasrach', 'marker'), 'the Hall of the Flame', ('burg', 315), '🔥', 'II-0004',
         'A long hall of dry stone and turf over Brìde\'s flame, one door toward the vein and none toward the sea; the stone cup of Fionnlagh Dall on its threshold, where the Peace of the Threshold was sworn.', ['II-0001', 'II-0004', 'II-0026', 'II-0064c']),
        ('III-K03', None, 'the double stones of Dùn thais (first blood of the heirs)', ('burg', 77), '🪨', 'II-0001c',
         'The Roinn put the fort on the line between the north and the Red Share; a stone was set on each side of the bank and neither share let the other\'s stand. Aonghas Bàn mac Mhurchaidh was killed here in FE 3.', ['II-0001c', 'book III']),
        ('III-K04', None, 'the stone of the two oaths', ('burg', 395), '🪨', 'II-0064b',
         'A boundary stone of the Roinn cut on two faces with the signs of two shares, now in the wall of the maor\'s house; the shire says it is the stone Fearghas Dà-Mhionn was sworn by. His fields were burned here in FE 556.', ['II-0064b', 'App.H §II']),
        ('III-K05', None, 'the boundary stones of the woods (east)', ('marker', 23), '🪨', 'II-0118',
         'The terms of the division of the woods cut in stag-letters; two of the eastern stones remain.', ['II-0118']),
        ('III-K06', None, 'the boundary stones of the woods (west)', ('marker', 24), '🪨', 'II-0118',
         'The western wood kept by the wood-watchers, each side free to walk the other\'s wood unarmed and without cutting.', ['II-0118']),
        ('III-K07', None, 'the weather-cairns of Cnoc ghlas', ('burg', 390), '🌥️', 'II-0006',
         'Watchers read the cloud on the high passes and tell the Hall when the galleries may open; they saw the late snow of FE 2,472.', ['II-0006', 'II-0177']),
        ('III-K08', None, 'the ancestor-cairn of Cathair naomh', ('burg', 192), '🪨', 'II-0054',
         'The greatest ancestor-cairn in the north, a stone brought at every burial.', ['II-0054']),
        ('III-K09', None, 'the red hall', ('burg', 19), '🏛️', 'II-0137',
         'Beathag Mhòr\'s hall of red stone above the harbour, the hearth-sign cut in its lintel; its clerks keep the king-list year by year.', ['II-0137', 'II-0155', 'II-0157']),
        ('III-K10', None, 'Goraidh Mòr\'s hall and the kings\' graves', ('burg', 422), '⚱️', 'II-0079',
         'A timber hall with a granary at each corner; the house of Ìomhar and the kings of the house of Tormod are buried here.', ['II-0079', 'II-0148', 'II-0188', 'II-0212']),
        ('III-K11', None, 'the white wolf-stone at the gate', ('burg', 1), '🐺', 'II-0100',
         'The road-guards\' white stone carved as a wolf, with the wolf-sworn\'s hall about it; later called Lia Fàil.', ['II-0100', 'II-0217']),
        ('III-K12', None, 'the shrine of the drowned', ('burg', 166), '🕯️', 'II-0069',
         'Its keepers burn the season\'s handful on the shore so the drowned may see it; a second wolf-stone of white quartz dragged from the mountain.', ['II-0069', 'II-0161']),
        ('III-K13', None, 'the ford of the forty', ('burg', 500), '⚔️', 'II-0095',
         'The men of Caol leathan held the ford a day against Iain Garbh; forty lay dead of both sides.', ['II-0095']),
        ('III-K14', None, 'the toll-house at Àth ghlas', ('burg', 393), '🪙', 'II-0128',
         'Road-guards paid in the new silver rings; its keeper the first sent from the rìgh\'s hall.', ['II-0128']),
        ('III-K15', None, 'the watch-tower of Baile ruadh', ('burg', 241), '🗼', 'II-0240',
         'The only tower of war the age builds.', ['II-0240']),
        ('III-K16', None, 'the bridge below Dùn chrom', ('burg', 255), '🌉', 'II-0192', 'Joins the southern road to the western; half the road-toll.', ['II-0192']),
        ('III-K17', None, 'the bridge at Ceann àrsaidh', ('burg', 88), '🌉', 'II-0193', 'The fourth stone crossing of the lowlands, built by forty of the fisher-kin of Sliochd Raghnaill.', ['II-0193']),
        ('III-K18', None, 'the bridge at Doire mhin', ('burg', 316), '🌉', 'II-0194', 'The first mason\'s mark known: Beathag Clachair\'s name beside the hearth-sign.', ['II-0194']),
        ('III-K19', None, 'the stone quay of Seann Vell', ('burg', 94), '⚓', 'II-0230', 'The first stone quay on the island.', ['II-0230']),
        ('III-K20', None, 'the stag-letters', ('burg', 78), '🔤', 'II-0088', 'The cutters\' tally-notches made into signs for sounds: the ogham, the gift of Ogma.', ['II-0023', 'II-0088']),
        ('III-K21', None, 'the temple of Sliochd Thormoid', ('burg', 18), '🛕', 'II-0187', 'The house\'s shrine enlarged into a temple with a court for pilgrims.', ['II-0047', 'II-0187']),
        ('III-K22', None, 'the mill-shrine', ('burg', 326), '⚙️', 'II-0232', 'A mill and a shrine under one roof; the miller keeps the handful by his stones.', ['II-0232']),
        ('III-K23', None, 'the school of letters at Inis bheag', ('burg', 62), '📜', 'II-0156', 'Letters taught to fishers\' children who will never cut coal.', ['II-0156']),
        ('III-K24', None, 'the sealed high gallery', ('burg', 315), '⛏️', 'II-0074', 'A roof fall killed four cutters; walled up, and oak props set in every gallery after.', ['II-0074', 'II-0122']),
    ]
    for key, name, en, at, icon, eid, note, cites in NM:
        s.new_marker(key, name, en, at, icon=icon, event=eid, note=note, cites=cites)

    # ---------------------------------------------------------------- zones
    Z = []
    for k, sh in SHARES.items():
        if sh['name']:
            dt(sh['name'], 'share ' + k, 'place')
        Z.append(collections.OrderedDict([
            ('key', 'III-Z-%s' % k), ('name', sh['name']), ('name_en', sh['name_en']), ('type', 'earlier moment: the Roinn (FE 2)'),
            ('date', ann_date('II-0001b')), ('seat', {'burg': sh['seat']}), ('holder_at_the_roinn', sh['holder']),
            ('provinces', sh['provinces']),
            ('note', 'One of the nine great shares, earrannan mòra, cut on the cord at Dùn ìseal; parted again into countries, provinces, counties and holdings; bounded with stones cut with its sign.' if k.startswith('S') else
             {'RED': 'Won with the sword before the parting and let stand over the protest of four lines; passed whole, never cut.',
              'HALL': 'The ground of the Hall is in no share; a county of the eastern share held the silver seam here.',
              'HILL': 'Its holder said the Red Hill had sworn to Ailean and was sworn to no one; three shares claimed it and none kept it.'}[k]),
            ('cites', ['II-0001b', 'II-0001d', 'App.H §II'] + sh['grounded']),
            ('inferred', True),
        ]))
    allp = sorted(p for sh in SHARES.values() for p in sh['provinces'])
    assert allp == list(range(1, 124)), (len(allp), sorted(set(range(1, 124)) - set(allp)), [p for p in allp if allp.count(p) > 1])
    more = [
        ('III-Z10', dt('Aimhreit nan Oighrean', 'zone'), 'the strife of the heirs (FE 3–556)', 'war', list(range(1, 124)),
         'Raids, burnings and killings between the lines of the king\'s blood for some five hundred and fifty years; the Hall\'s ground the one place no feud could follow a man.', ['II-0001c', 'II-0064c', 'App.C Aimhreit nan Oighrean']),
        ('III-Z11', dt('Cogadh an Dà Mhionn', 'zone'), 'the War of the Two Oaths (c. FE 516–556)', 'war', [24, 31, 94, 12, 34, 85, 57, 84, 90],
         'Every holding sworn to both Eithne\'s line and Ìomhar\'s had to choose; it ended at Achadh mhòr and the middle of the island went hungry.', ['II-0064b', 'App.C Aimhreit nan Oighrean']),
        ('III-Z12', None, 'the War of the Roads (FE 999–1,006)', 'war', [85, 44, 67, 22, 2, 52, 32],
         'Iain Garbh of Dùn dhearg against Lachlann Ciar of Caol leathan, over the western tolls.', ['II-0093', 'II-0095', 'II-0096', 'II-0097', 'II-0098', 'II-0099']),
        ('III-Z13', None, 'the Silver Feud (FE 1,745–1,749)', 'feud', [35, 112],
         'No silver left Muileann chiar for three seasons; no one was killed.', ['II-0150', 'II-0151', 'II-0152']),
        ('III-Z14', None, 'the poor season in the mountain (FE 2,472–2,474)', 'famine averted', [112],
         'The galleries opened late and closed early; the shared-meal law held and the granaries of Dùn dhearg and the south sent grain up unasked.', ['II-0177', 'II-0178', 'II-0179', 'II-0180', 'II-0182']),
        ('III-Z15', None, 'drought at Achadh shean (FE 2,900)', 'drought', [61],
         'The district granary emptied; grain came from Baile chaol and Cuan ruadh and was repaid to the last measure.', ['II-0237', 'II-0238']),
        ('III-Z16', None, 'the hawk coast (the dawn-hawk\'s spread, FE 1,999–2,072)', 'faith', [51, 6, 9, 45],
         'From Seann Skell on the northern shore up the Abhainn ìseal to Inis ìseal and Cnoc bheag.', ['II-0158', 'II-0159']),
        ('III-Z17', None, 'the sting-oath coast (FE 879–2,849)', 'faith', [64, 77, 3, 120, 38, 73],
         'From Baile àrsaidh up the western coast to Ros bheag, a creed at Seann Skell, a yellow scorpion at Seann Vell.', ['II-0086', 'II-0160', 'II-0218', 'II-0219']),
    ]
    for key, name, en, typ, provs, note, cites in more:
        Z.append(collections.OrderedDict([('key', key), ('name', name), ('name_en', en), ('type', typ), ('provinces', provs), ('note', note), ('cites', cites)]))
    Z.append(collections.OrderedDict([('key', 'III-Z18'), ('name', dt('Cuid nam Marbh', 'zone')), ('name_en', 'the portion of the dead'), ('type', 'earlier moment: the Roinn (FE 2)'),
                                      ('provinces', []), ('note', 'Set aside out of all nine shares for the lines of the king\'s dead children; not a territory of its own, so no provinces are drawn.'),
                                      ('cites', ['II-0001b', 'II-0001d'])]))
    d['zones'] = Z
    d['labels'] = [
        {'text': 'Roinn na Rìoghachd', 'text_en': 'the parting of the kingdom (FE 2)', 'at': {'burg': 315}, 'cites': ['II-0001b']},
        {'text': 'Sìth an Stairsnich', 'text_en': 'the Peace of the Threshold (FE 556)', 'at': {'burg': 315}, 'cites': ['II-0064c']},
        {'text': None, 'text_en': 'the reverent centuries', 'at': {'burg': 273}, 'cites': ['II-0058']},
    ]
    for l in d['labels']:
        if l['text']:
            dt(l['text'], 'label', 'phrase')

    # ---------------------------------------------------------------- military
    d['military']['hosts'] = [
        collections.OrderedDict([('name', None), ('name_en', 'the road-guards of the realm (riders)'), ('polity', 'realm'), ('station', {'burg': 422}),
                                 ('note', 'Paid in stamped silver rings; they ride the lowland roads on small horses of the southern grass country and meet each year at Ceann leathan.'), ('cites', ['II-0080', 'II-0127', 'II-0190a', 'II-0129'])]),
        collections.OrderedDict([('name', None), ('name_en', 'the wolf-sworn road-guards of Caol leathan (the Fianna)'), ('polity', 'realm'), ('station', {'burg': 1}),
                                 ('note', 'Sworn on the white wolf-stone at the gate; their hall is becoming an order.'), ('cites', ['II-0100', 'II-0217'])]),
        collections.OrderedDict([('name', None), ('name_en', 'the road-guard of Inis mhòr'), ('polity', 'realm'), ('station', {'burg': 17}),
                                 ('note', 'Granted by Catrìona Ghlic at the town\'s asking.'), ('cites', ['II-0106'])]),
        collections.OrderedDict([('name', None), ('name_en', 'the armed boats of Sliochd Raghnaill'), ('polity', 'realm'), ('station', {'burg': 34}),
                                 ('note', 'Armed against the island raiders; the watch-tower at Baile ruadh and the boats of Cuan ruadh with them.'), ('cites', ['II-0175', 'II-0240', 'II-0241'])]),
        collections.OrderedDict([('name', None), ('name_en', 'the two armed boats of the Ros bheag merchants'), ('polity', 'realm'), ('station', {'burg': 63}),
                                 ('note', 'Paid for by the sting-sworn merchants to watch the north-western strands.'), ('cites', ['II-0201'])]),
    ]
    d['military']['campaigns'] = [
        collections.OrderedDict([('name', dt('Blàr Àth na Fala', 'campaign')), ('name_en', 'the Battle of the Ford of Blood'), ('date', ann_date('I-0098a')), ('at', {'cell': ford}),
                                 ('sides', ['Ailean Mòr, alone', 'the host of Dùn dhearg and the east']), ('outcome', 'the king falls on the third night; Ìomhar Dearg takes Dùn dhearg'), ('cites', ['I-0098a'])]),
        collections.OrderedDict([('name', dt('Aimhreit nan Oighrean', 'campaign')), ('name_en', 'the strife of the heirs'), ('date', 'FE 3–556'),
                                 ('sides', ['the line of Murchadh', 'the line of Ìomhar', 'then nearly every line of the king\'s blood']), ('outcome', 'the Peace of the Threshold'), ('cites', ['II-0001c', 'II-0064c'])]),
        collections.OrderedDict([('name', dt('Cogadh an Dà Mhionn', 'campaign')), ('name_en', 'the War of the Two Oaths'), ('date', 'c. FE 516–556'), ('at', {'burg': 395}),
                                 ('sides', ['Eithne nic Ailein\'s line (Cathair mhòr)', 'the line of Ìomhar (the Red Share)']), ('outcome', 'the burning of Achadh mhòr; the Peace'), ('cites', ['II-0064b', 'II-0064c'])]),
        collections.OrderedDict([('name', None), ('name_en', 'the War of the Roads'), ('date', 'FE 999–1,006'), ('at', {'burg': 151}),
                                 ('sides', ['Iain Garbh of Dùn dhearg, the road-guards and the lowland levies', 'Lachlann Ciar and the men of Caol leathan']),
                                 ('outcome', 'the peace at Mòr nic Dhùghaill\'s house: half the tolls each way'), ('cites', ['II-0093', 'II-0095', 'II-0096', 'II-0097', 'II-0098', 'II-0099'])]),
        collections.OrderedDict([('name', None), ('name_en', 'the Silver Feud'), ('date', 'FE 1,745–1,749'), ('at', {'burg': 419}),
                                 ('sides', ['Ruairidh Liath', 'Sliochd Fhearchair']), ('outcome', 'one ring in ten; the Muileann chiar weight made law'), ('cites', ['II-0150', 'II-0151', 'II-0152', 'II-0153'])]),
        collections.OrderedDict([('name', None), ('name_en', 'the raids in the eastern waters and on the western strands'), ('date', 'FE 2,455; FE 2,747'),
                                 ('sides', ['outlaws in boats', 'Sliochd Raghnaill; the Ros bheag merchants']), ('cites', ['II-0175', 'II-0201'])]),
    ]
    d['arms'] = [
        collections.OrderedDict([('polity', 'realm'), ('blazon', None), ('signs', 'the masons\' hearth-sign cut in the lintel of the red hall (inferred as the hall\'s mark)'),
                                 ('note', 'No arms yet: the first arms on the island are the vein-house\'s seal in the Age of Sundering. The hall\'s clerks stamp its mark on the silver rings.'), ('cites', ['II-0127', 'II-0137', 'App.J §I']), ('inferred', True)]),
        collections.OrderedDict([('polity', 'hall'), ('blazon', None), ('signs', 'the stone cup of Fionnlagh Dall'), ('note', 'No arms.'), ('cites', ['II-0026', 'App.J §I'])]),
        collections.OrderedDict([('polity', 'north-west'), ('blazon', None), ('signs', None), ('note', 'No arms.'), ('cites', ['App.J §I'])]),
        collections.OrderedDict([('polity', 'order signs'), ('blazon', None), ('signs', 'the white wolf-stone of Caol leathan; the yellow scorpion of Seann Vell; the hawk of the dawn-burning'),
                                 ('note', 'Signs of the companies and towns, none borne on a shield.'), ('cites', ['II-0100', 'II-0219', 'II-0158', 'App.J §I'])]),
    ]
    d['notes']['polities'] = collections.OrderedDict([
        ('realm', 'The realm of the red hall began in the granaries of Dùn dhearg, whose households called Goraidh mac Ìomhair their rìgh, and moved to Cathair dhearg under Beathag Mhòr. By the division of keeping its rulers keep the roads, the granaries and the peace of the lowlands and never enter the galleries. The Four Houses chose Gilleasbuig Mòr when the line of Goraidh failed, and the house of Tormod has held the hall since, each ruler taking the stone cup from the Keeper.'),
        ('hall', 'Talla na Lasrach at Dùn ìseal keeps Brìde\'s flame and Crom\'s stone, the galleries and the Small-Burning Law, as the heirs of Ailean swore when they could not part the vein. Its Keepers raise no spears, bless no war and judge every hand that claims the handful. By the close of the age it keeps the flame for eight peoples, each of whom thinks itself the only keeper.'),
        ('north-west', 'The fisher-families of the north-west gather at Caol mhòr under a headman of their own and send their tolls to Cathair dhearg only when the road-guard comes for them. Their seal-oil lights the western harbours and their boats watch for the Sea-Watcher. Little is written of them, and most of it is complaint.'),
    ])
    d['notes']['burgs'] = collections.OrderedDict([
        ('19', 'Cathair dhearg: the red hall above the harbour, the bridge at the foot of the carriers\' road and a wood-watcher reading the hall\'s omens; seat of the realm since FE 1,699.'),
        ('315', 'Dùn ìseal: Talla na Lasrach, the galleries under the summit ridge, the stone cup on the threshold, and the market under the Hall on the four quarter days.'),
        ('26', 'Cathair dhomhain: the older, larger harbour a few miles from the new seat, chartered to its own tolls and proud of its strict measure.'),
        ('422', 'Dùn dhearg: the hill of the first rìgh, its granaries, and the graves of the kings.'),
        ('23', 'Cathair mhòr: the first walled town, Eithne\'s old hall and a granary behind the wall.'),
        ('419', 'Muileann chiar: the silver town, whose weights are the only lawful weights on the roads.'),
        ('94', 'Seann Vell of the south-east: a city of fish and silver with the first stone quay.'),
    ])
    return s.finish()
