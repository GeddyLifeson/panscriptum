"""Age VI, the Age of the Kingdom (Severance Era): the island on the eve of the first working dubhan."""
from common import *  # noqa: F401,F403

AGE = 'VI'
OLD_CONGREGATIONS = {140, 209, 367, 112, 234, 327, 329, 399, 468, 9, 235, 176}


def faith_setup(d, age):
    ORD = collections.OrderedDict([
        ('bride', dict(name='Òrd Bhrìde', name_en='the Coal Rite, the order of Brìde\'s flame and Crom\'s stone', gods='Brìde; Crom Cruaich, the Monster of the Gates',
                       seat=431, note='Given a settled doctrine in SE 6 and a high custodian, the Àrd-choimheadaiche, at the southern Seann Skell; it protests at the kingdom\'s use of the vein, and then blesses it.',
                       cites=['V-0028', 'V-0029', 'V-0052'])),
        ('seabhag', dict(name='Òrd an t-Seabhaig', name_en='the order of the Hawk of Acaill', gods='Mòd, the Hungry Hawk; Fionntan mac Bòchra', seat=20,
                         note='Refused the Rite\'s written order; named its own custodian at Inis ìseal and wrote its own order down; took a place under the high custodian keeping its order.',
                         cites=['V-0030', 'V-0131', 'V-0132', 'V-0166'])),
        ('sgoiltean', dict(name='Scoiltean nan Draoidhean', name_en='the druid schools (revived SE 46)', gods='Flidais; Camaran, the Royal Stag', seat=77,
                           note='Opened again when the vein began to fail; Seonaid nic Ghill-Eathain lectures in Flidais\'s wood; a house at Caol shean.',
                           cites=['V-0162', 'V-0163', 'V-0165'])),
        ('macha', dict(name='Òrd Mhacha', name_en='the order of Macha, keeper of the regalia', gods='Macha; the two horses of one yoke', seat=19,
                       note='Crowned Niall by its rite and keeps the regalia; refused the Rite a share in the keeping.', cites=['V-0012', 'V-0033'])),
        ('cloch', dict(name='Òrd na Cloiche', name_en='the order of the Stone', gods='Lia Fàil, called Clach', seat=166,
                       note='Its houses serve as banks as well as churches; sent the Rite a letter wishing it well.', cites=['V-0027', 'V-0031', 'V-0119', 'V-0219'])),
        ('manannan', dict(name='Òrd Mhanannain', name_en='the order of Manannan', gods='Manannan mac Lir', seat=489,
                          note='Says the lord of the sea has shut the eastern sea again; the house at Seann Bhral turned away the Tuathaich from its feast.', cites=['V-0011', 'V-0103'])),
    ])
    d['faiths'] = [
        collections.OrderedDict([('key', 'old-faith'), ('name', dt('An Creideamh Sean', 'faith')), ('name_en', 'the Old Faith'), ('master_religion', 1),
                                 ('type', 'Organized'), ('form', 'Polytheism'), ('deity', 'an Dagda'), ('provinces', []), ('orders', []), ('cites', ['App.B §I', 'App.B §V'])]),
        collections.OrderedDict([('key', 'old-spirits'), ('name', dt('Na Seann Spioradan', 'faith')), ('name_en', 'the Old Spirits'), ('master_religion', 2),
                                 ('type', 'Folk'), ('form', 'Shamanism'), ('deity', 'na Sìthichean'), ('seat', {'burg': 18}), ('provinces', []),
                                 ('note', 'The ancestors\' hall at Seann Dunn where forty families name their ancestors aloud; the walk to Allt an Àigh.'), ('cites', ['V-0048', 'V-0049', 'V-0094', 'App.B §VI'])]),
        collections.OrderedDict([('key', 'church'), ('name', dt('An Eaglais', 'faith')), ('name_en', 'the Church'), ('master_religion', 3),
                                 ('type', 'Organized'), ('form', 'Monotheism'), ('deity', 'Crìosd'), ('provinces', []),
                                 ('bodies', [
                                     {'key': 'mission-line', 'name_en': 'the churches of the Mission\'s line', 'seat': {'burg': 142}, 'cites': ['V-0044', 'V-0045']},
                                     {'key': 'eaglais-nan-tuathach', 'name': dt('Eaglais nan Tuathach', 'church body'), 'name_en': 'the old congregations of the north coast', 'seat': {'burg': 209}, 'cites': ['V-0042', 'App.B §VII']},
                                     {'key': 'oidhche-ghlas', 'name': dt('Rùn-dìomhair na h-Oidhche Glaise', 'church body'), 'name_en': 'the vigil of the Grey Night', 'seat': {'burg': 305}, 'cites': ['V-0043', 'V-0108', 'V-0123']},
                                 ]),
                                 ('cites', ['V-0042', 'V-0044', 'App.B §VII'])]),
        collections.OrderedDict([('key', 'none'), ('name', dt('Gun chreideamh', 'faith')), ('name_en', 'without a faith (the windy coast and the empty islets)'), ('master_religion', 0),
                                 ('provinces', []), ('note', 'Families on the far north-western cape with no house of any faith; Eilean ghorm and the smallest islets with no one to ask.'), ('cites', ['V-0034a'])]),
    ]
    for k, o in ORD.items():
        dt(o['name'], 'order ' + k)
        d['faiths'][0]['orders'].append(collections.OrderedDict([('key', k), ('name', o['name']), ('name_en', o['name_en']), ('gods', o['gods']),
                                                                 ('seat', {'burg': o['seat']}), ('provinces', []), ('note', o['note']), ('cites', o['cites'])]))
    FK = {1: 'old-faith', 2: 'old-spirits', 3: 'church', 0: 'none'}
    for p in range(1, 124):
        f = FK[master_faith_of_province(p)]
        next(x for x in d['faiths'] if x['key'] == f)['provinces'].append(p)
    for o in d['faiths'][0]['orders']:
        o['provinces'] = sorted(p for p in range(1, 124) if master_faith_of_province(p) == 1 and present_order(p) == o['key'])

    def burg_faith(i):
        f = FK[burg_master_faith(i)]
        order = body = None
        if f == 'old-faith':
            order = present_order(BURGS[i]['prov'])
            if i == 326:
                order = 'bride'
            if i == 25:
                order = 'seabhag'
        if f == 'church':
            body = 'oidhche-ghlas' if i == 305 else ('eaglais-nan-tuathach' if i in OLD_CONGREGATIONS else 'mission-line')
        return f, order, body
    return burg_faith


def shires_unit(d, arms_note):
    arms = shire_arms()
    units = []
    for p in range(1, 124):
        pr = PROVINCES[p]
        units.append({'name': dt(pr['fullName'], 'shire', 'place'), 'name_en': 'the shire of %s' % pr['name'], 'seat': ({'burg': pr['burg']} if pr.get('burg') else None),
                      'provinces': [p]})
    return units, arms


def named_routes():
    named = {
        410: dict(first='I', name='Slighe-mhara àrsaidh', group='searoutes', cites=['I-0064a']),
        264: dict(first='III', name='Slighe Cnoc leathan', group='trails', cites=['II-0207']),
        3: dict(first='IV', name='An Rathad Tuath', group='roads', cites=['III-0145']),
        17: dict(first='IV', name='Slighe Muileann dhearg', group='trails', cites=['III-0145']),
        98: dict(first='IV', name='Slighe Baile òg', group='trails', cites=['III-0145']),
        403: dict(first='IV', name='Seòlaid Ros fhionn', group='searoutes', cites=['III-0168b']),
        354: dict(first='IV', name='Slighe-mhara Caol fhiadhaich', group='searoutes', cites=['III-0189a']),
        349: dict(first='V', name='Seòlaid Ceann òg', group='searoutes', cites=['IV-0076a']),
        301: dict(first='V', name='Ceum Ros àrsaidh', group='trails', cites=['IV-0364']),
        383: dict(first='VI', name='Slighe-uisce fhuar', group='searoutes', cites=['III-0215'], inferred=True, note='the cold way of the north coast, laid up in LE 1,634; kept on the master map, so drawn here as sailed again (inferred)'),
        385: dict(first='VI', name='Slighe-mhara chritheanach', group='searoutes', cites=['gazetteer B205'], inferred=True, note='the pilgrims\' boats of the Rite from the southern Seann Skell round to Caol naomh'),
        50: dict(first='VI', name='Rathad na Fèille', group='roads', cites=['V-0090'], note='the fair road from Cathair dhearg to Muileann òg, widened and metalled for the carts of the fair; Dùn chrom takes a toll at its gate'),
        71: dict(first='VI', name='Rathad na Fèille', group='roads', cites=['V-0090']),
    }
    for r in (16, 39, 52, 70, 111, 115, 130, 131, 446):
        named[r] = dict(first='V', name='Rathad na Mèinne', group='roads', cites=['IV-0088a', 'V-0090'])
    for r in (173, 175, 210, 229, 233, 248, 447):
        named[r] = dict(first='IV', name='Rathad na Banrighinn', group='roads', cites=['III-0114'])
    return named


def build():
    reset_names()
    s = Spec(AGE, collections.OrderedDict([
        ('age', 'VI'),
        ('age_name', {'name': dt('An Aois Rìoghachd', 'age name'), 'name_en': 'the Age of the Kingdom'}),
        ('era', {'abbr': 'SE', 'name': dt('Linn an Dealachaidh', 'era name'), 'name_en': 'the Severance Era'}),
        ('snapshot', collections.OrderedDict([
            ('date', '18 an t-Ògmhios, SE 71 (the eve of the first working dubhan, DE 1)'),
            ('plan_label', 'SE 70 (ERA_PLAN); the annals run the Severance Era to SE 71, whose midsummer opens the Dubhan Era'),
            ('y', 2000), ('m', 6), ('d', 18),
            ('last_event_shown', 'V-0237'),
            ('next_event', 'VI-0001'),
            ('description',
             "Seventy years after the Severance, Rìoghachd Dia-thìr is a kingdom of one hundred and twenty-three shires under "
             "Mairead, with its council of twelve, its maoir, its circuit justices, its Mine Board and its Rail Board. The "
             "Tuathaich, the children of the humans, hold the north behind boundary stones no wall follows; their Moot at "
             "Caol mhòr keeps its minutes and has no standing in the kingdom's law, and its register counts the hewers the "
             "kingdom's books do not. The vein that founded the kingdom is plainly failing: the Sloc Mòr's lowest galleries "
             "are flooded, the Guild of Hewers binds no apprentices, the search for a second vein sank forty-one dry shafts, "
             "Muileann dhearg has lost a third of its households, and coal at the fair has doubled in price. The coal line runs "
             "from the Sloc Mòr to the capital and on to Ceann leathan and Seann Bhral, and the western pits of the Tuathaich "
             "work on under their own pit captains. The Rite keeps its doctrine at the southern Seann Skell, the druid schools "
             "are open again and asking their oldest question, and in the north a boy called Dubhan is grown."),
            ('cites', ['V-0007', 'V-0009', 'V-0014', 'V-0139a', 'V-0199', 'V-0001', 'V-0003', 'V-0008', 'V-0150', 'V-0192',
                       'V-0200', 'V-0177', 'V-0196', 'V-0208', 'V-0236', 'V-0230', 'V-0231', 'V-0162', 'V-0149']),
        ])),
        ('land_changes', [
            collections.OrderedDict([('what', 'The drowned strand of Cnoc chaol: the old town\'s site left as the Great Wave left it (SE 4); the town rebuilt higher up the hill.'), ('cites', ['V-0017', 'V-0020'])]),
            collections.OrderedDict([('what', 'The dry shafts of the search for a second vein, forty-one of them from the hills above Dùn dhearg to the moors south of Baile ruadh, those at Baile ruadh fenced by the shire.'), ('cites', ['V-0177', 'V-0180'])]),
            collections.OrderedDict([('what', 'The lowest galleries of the Sloc Mòr let flood (SE 61).'), ('cites', ['V-0208'])]),
            collections.OrderedDict([('what', 'The breakwater across the strait between Caol chrom and Caol gharbh, the longest on the island (SE 48–56).'), ('cites', ['V-0167'])]),
        ]),
    ]))
    d = s.d
    d['cultures'] = [
        collections.OrderedDict([('key', 'dia-thirich'), ('name', dt('Na Dia-thìrich', 'culture')), ('name_en', 'the Dia-thìrich'), ('master_culture', 2),
                                 ('provinces', [p for p in range(1, 124) if master_culture_of_province(p) == 2]), ('cites', ['App.F Dia-thìrich'])]),
        collections.OrderedDict([('key', 'tuathaich'), ('name', dt('Na Tuathaich', 'culture')), ('name_en', 'the Tuathaich (the northerners)'), ('master_culture', 1),
                                 ('provinces', [p for p in range(1, 124) if master_culture_of_province(p) == 1]),
                                 ('note', 'The descendants of the humans left on the island, settled by law in the north; they keep the Church and their own schools in the humans\' tongue, and many of their towns are Dia-thìreach towns emptied at the Severance.'),
                                 ('cites', ['V-0001', 'V-0066', 'App.F Tuathaich'])]),
    ]
    burg_faith = faith_setup(d, AGE)

    units, arms = shires_unit(d, None)
    s.polity('kingdom', dt('Rìoghachd Dia-thìr', 'polity'), 'the Kingdom of Dia-thìr',
             form='a monarchy restored after the Severance: a crowned ruler, a royal council of twelve from the custodian families and the captains of the war, maoir in the shires, circuit justices',
             capital={'burg': 19},
             ruler={'name': dt('Mairead', 'ruler', 'person'), 'title': 'ruler of Rìoghachd Dia-thìr', 'note': 'crowned SE 58 after Eòghan; fourth of the restored line', 'cites': ['V-0199', 'App.A rulers of Rìoghachd Dia-thìr']},
             culture='dia-thirich', color='#66c2a5 (the master map\'s state colour)',
             cites=['V-0007', 'V-0009', 'V-0012', 'V-0014', 'V-0015'],
             admin_units=[
                 {'name': None, 'name_en': 'the shires (siorrachdan), each under a maor', 'kind': 'shire', 'units': units,
                  'note': 'Drawn SE 3 on the humans\' district lines; Doire chaol cut from Baile chiar in SE 38, making 123.', 'cites': ['V-0014', 'V-0015', 'V-0139a', 'App.H §II']},
                 {'name': None, 'name_en': 'the market towns', 'kind': 'market right', 'units': [
                     {'name_en': 'the market of %s' % BURGS[b]['name'], 'seat': {'burg': b}, 'cites': [c]} for b, c in
                     [(22, 'II-0068'), (26, 'II-0138'), (76, 'III-0147'), (132, 'III-0088a'), (63, 'II-0160'), (34, 'III-0119a'), (315, 'II-0064a'),
                      (273, 'II-0106a'), (136, 'III-0126a'), (204, 'II-0134a'), (297, 'III-0070a'), (143, 'V-0014c'), (113, 'III-0135a'), (160, 'V-0044a'), (233, 'III-0156a')]],
                  'note': 'Fifteen of the sixteen; Caol ruadh is chartered only in DE 23.', 'cites': ['App.G §III']},
                 {'name': None, 'name_en': 'the Boards', 'kind': 'crown boards', 'units': [
                     {'name_en': 'the Mine Board (offices at Cathair mhòr, in the stone house of Mac Ùisdein)', 'seat': {'burg': 23}, 'cites': ['V-0107', 'V-0179']},
                     {'name_en': 'the Rail Board', 'seat': {'burg': 19}, 'cites': ['V-0039']},
                     {'name_en': 'the Lighthouse Board', 'seat': None, 'cites': ['V-0075', 'V-0095']}]},
             ])
    s.polity('moot', None, 'the Moot of the Tuathaich (the northern homeland)',
             form='an assembly of Tuathaich householders at Caol mhòr with a chosen speaker; no standing in Dia-thìreach law; it keeps its own minutes, schools, granaries and register of the pits',
             capital={'burg': 95},
             ruler={'name': 'Daniel Frayne', 'title': 'speaker of the Moot', 'note': 'the first speaker born after the Severance; speaker from SE 55', 'cites': ['V-0189']},
             culture='tuathaich', color='#dababf (the master map\'s Tuathaich culture colour)', suzerain='kingdom',
             name_note='the Moot has no Dia-thìris name in the record; the Tuathaich name for themselves is not written',
             cites=['V-0001', 'V-0003', 'V-0008', 'V-0127', 'V-0150', 'V-0189'])
    s.assign({'kingdom': [p for p in range(1, 124) if p not in TUATH_SHIRES], 'moot': TUATH_SHIRES})
    d['province_polity_notes'] = collections.OrderedDict([
        ('moot', 'The eleven Tuathaich shires are shires of the kingdom with Dia-thìreach maoir lodged in their seats; they are drawn apart because the Moot speaks for them and the kingdom\'s law does not reach their own record. Their bounds with the Dia-thìreach shires are the boundary stones on the north roads.'),
        ('unclaimed', 'No shire; the windy coast of the far north-west (no province on the master map) is in no shire and pays no due.'),
    ])
    d['diplomacy'] = [
        {'a': 'kingdom', 'b': 'moot', 'relation': 'a homeland held apart without standing in law', 'since': ann_date('V-0001'),
         'note': 'The border wall was refused as needless; "They do not come south." Maoir in the seat towns; licences to fish the southern grounds kept for Dia-thìreach boats; Tuathaich goods sold at the fair only through Dia-thìreach factors, on their own day since SE 55.',
         'cites': ['V-0003', 'V-0046', 'V-0047', 'V-0089', 'V-0118', 'V-0190']},
        {'a': 'kingdom', 'b': 'raiders off Cathair gheal', 'relation': 'hostile; no help sent to the Tuathaich towns', 'cites': ['V-0055', 'V-0085']},
    ]

    pol_of = {int(k): v for k, v in d['province_polity'].items()}
    SPECIAL = {
        135: dict(role='the Sloc Mòr, the great shaft of the vein: the Crown\'s since SE 60, its lowest galleries flooded; the Guild of Hewers\' town', cites=['V-0051', 'V-0060', 'V-0204', 'V-0208']),
        23: dict(role='the Mine Board\'s offices in the stone house of Mac Ùisdein; the market cross', cites=['V-0086', 'V-0107', 'V-0117', 'V-0179']),
        246: dict(role='Leabharlann Muileann chaol, with the chests of the provinces and a fourth floor left empty for what was not sent', cites=['V-0070', 'V-0071', 'V-0226', 'V-0228']),
        95: dict(role='the Moot\'s town: its minute-books, its register of the pits, its granaries', cites=['V-0008', 'V-0150']),
        431: dict(role='the seat of the high custodian of Òrd Bhrìde and the order\'s greatest house', cites=['V-0029']),
        491: dict(role='the vein-town that doubled in the first years and has lost a third of its households to the ports; its druid hall shut and its bell sold', cites=['V-0053', 'V-0141', 'V-0196']),
        354: dict(role='the shunting yards of the coal line and the rows of the yard families', cites=['V-0058', 'V-0214']),
        209: dict(role='Agnes Pike\'s school, the Moot\'s wool mills, the heart of the Church in the north', cites=['V-0066', 'V-0202']),
        305: dict(role='the town of the Grey Night vigil, kept indoors since the magistrate\'s fine', cites=['V-0043', 'V-0108']),
    }
    for i in sorted(BURGS):
        p = BURGS[i]['prov']
        f, order, body = burg_faith(i)
        kw = dict(SPECIAL.get(i, {}))
        pop = default_pop(i, AGE)
        e = s.burg(i, population=pop, kind=kind_for(pop, AGE), role=kw.pop('role', None) or generic_role(i),
                   culture='tuathaich' if BURGS[i]['culture'] == 1 else 'dia-thirich', faith=f, order=order, polity=pol_of[p],
                   cites=kw.pop('cites', None) or ['gazetteer B%d' % i], inferred=True)
        if body:
            e['church_body'] = body

    # ---------------------------------------------------------------- routes
    named = named_routes()
    present = {b['id'] for b in d['burgs']}
    classify_routes(d, AGE, present, named, touched_rule(min_touch=1, allow_empty=True),
                    'Every master route is present: every town stands. The named roads carry their names; the coal line and its branches are added.')
    d['routes']['new'] = [
        collections.OrderedDict([('key', 'VI-R01'), ('name', None), ('name_en', 'the coal line'), ('group', 'railways'),
                                 ('points', [{'burg': 135}, {'burg': 354}, {'burg': 19}, {'burg': 27}]),
                                 ('note', 'mended as far as Muileann chrom (SE 8) and carried up the valley to the Sloc Mòr (SE 12); the Rail Board\'s sidings at Muileann chrom'), ('cites', ['V-0039', 'V-0056', 'V-0058'])]),
        collections.OrderedDict([('key', 'VI-R02'), ('name', None), ('name_en', 'the western branch of the coal line'), ('group', 'railways'),
                                 ('points', [{'burg': 19}, {'burg': 47}]), ('note', 'west from Cathair dhearg to the port of Seann Bhral (SE 13); its spur north to the pits at Àth leathan was shut in SE 68'), ('cites', ['V-0058a', 'V-0229'])]),
        collections.OrderedDict([('key', 'VI-R03'), ('name', None), ('name_en', 'the coal line to Ceann leathan'), ('group', 'railways'),
                                 ('points', [{'burg': 354}, {'burg': 22}]), ('note', 'carried through to the port so coal may ship from a second harbour (SE 36)'), ('cites', ['V-0135'])]),
        collections.OrderedDict([('key', 'VI-R04'), ('name', None), ('name_en', 'the Carters\' Road'), ('group', 'trails'),
                                 ('points', [{'burg': 142}, {'burg': 174}, {'burg': 55}]), ('note', 'the carters of the northern wool go to the fair by Cnoc ghorm, Àth fhada and the old road down to Inis àrsaidh; the Tuathaich villages on the way open inns. In the south it has no name.'),
                                 ('cites', ['V-0147', 'V-0148'])]),
        collections.OrderedDict([('key', 'VI-R05'), ('name', None), ('name_en', 'the eastern salt drove road'), ('group', 'trails'),
                                 ('points', [{'burg': 492}, {'burg': 285}]), ('note', 'the salt of Àth bheag goes inland by the old drove road past Baile ìseal'), ('cites', ['V-0124']), ('inferred', True)]),
    ]

    # ---------------------------------------------------------------- markers
    MN = {
        17: ('the Long War battle of Muileann ghlas is DE 22', ['VI-0115']), 18: ('the Long War battle of Àth leathan is DE 21', ['VI-0081']),
    }
    for i in sorted(MARKERS):
        if i in MN:
            d['markers']['absent'].append({'id': i, 'reason': MN[i][0], 'cites': MN[i][1]})
            continue
        e = {}
        if i == 34:
            e = dict(note='Founded SE 16; Ailean Leabhar, then Mòrag nic Coinnich, then Raghnall mac Mhuirich keepers; enlarged SE 67.', cites=['V-0070', 'V-0071', 'V-0144', 'V-0226', 'V-0235'])
        elif i == 37:
            e = dict(note='First fought SE 23; edged tools banned SE 54; its greatest crowd SE 45, won by Ealasaid nic Coinnich.', cites=['V-0096', 'V-0160', 'V-0186'])
        elif i == 38:
            e = dict(note='The fair first held SE 21 under Oighrig nic Mhathain\'s rules; the northern day SE 55; the coal price doubled SE 70.', cites=['V-0088', 'V-0089', 'V-0190', 'V-0236'])
        elif i in (12, 13, 14, 15, 16):
            e = dict(note='One of the five lights, burning coal-lit flame; Dia-thìreach keepers by royal warrant.', cites=['V-0075'] + (['V-0187', 'V-0188'] if i == 16 else []) + (['V-0158'] if i == 13 else []))
        elif i == 36:
            e = dict(note='First recorded SE 25 near Seann Chwen.', cites=['V-0102'])
        elif i == 35:
            e = dict(note='Recorded SE 53 on the common near Inis àrsaidh.', cites=['V-0184'])
        elif i == 0:
            e = dict(note='The Guild of Hewers\' bath-house for miners sick with the dust.', cites=['V-0074'])
        elif i == 2:
            e = dict(note='The silver found richer at depth (SE 37); the guild chartered under the restored custom; Iain Mapa measured its faces.', cites=['V-0137', 'V-0195'])
        elif i == 41:
            e = dict(note='Closed to new graves by the shire of Ceann mhin (SE 9).', cites=['V-0041'])
        else:
            e = dict(note=None, cites=['map Rodos_finished.map record 35'])
        s.marker(i, **{k: v for k, v in e.items() if v is not None})
    NM = [
        ('VI-K01', None, 'the Sloc Mòr', ('burg', 135), '⛏️', 'V-0051', 'The great shaft: the Crown\'s concession to Mac Ùisdein, then the Crown\'s alone; its lowest galleries flooded; its great pumps sold to Seann Bhral.', ['V-0051', 'V-0204', 'V-0208', 'V-0209']),
        ('VI-K02', None, 'the boundary stones on the north roads', ('burg', 95), '🪨', 'V-0003', 'Set where the Tuathaich country begins; no wall follows them.', ['V-0003', 'V-0046']),
        ('VI-K03', dt('An Tràigh Bhàthte', 'marker'), 'the drowned strand', ('burg', 364), '🌊', 'V-0020', 'The old site of Cnoc chaol, left as the Great Wave left it; no one builds there.', ['V-0017', 'V-0020']),
        ('VI-K04', None, 'the mint', ('burg', 19), '🪙', 'V-0024', 'In the old human counting-house; each coin\'s seal pressed with ink of coal dust.', ['V-0023', 'V-0024']),
        ('VI-K05', None, 'the forty-one dry shafts', ('burg', 241), '🕳️', 'V-0177', 'The search for a second vein, from the hills above Dùn dhearg to the moors south of Baile ruadh; the same hills were searched and barren in the Holy Age.', ['V-0176', 'V-0177', 'V-0180']),
        ('VI-K06', None, 'the fall at Muileann dhearg', ('burg', 491), '🪦', 'V-0141', 'Thirty-one hewers dead along a line marked sound: the same fault as the Rending.', ['V-0141']),
        ('VI-K07', None, 'the church at Cnoc ghorm', ('burg', 142), '⛪', 'V-0044', 'The greatest church in the north and its school; the northern feast of the boats.', ['V-0044', 'V-0045', 'V-0104']),
        ('VI-K08', None, 'the Moot at Caol mhòr', ('burg', 95), '🗳️', 'V-0008', 'Tuathaich householders and their speaker; minutes unbroken since the first meeting.', ['V-0008']),
        ('VI-K09', None, 'the market cross of Mac Ùisdein', ('burg', 23), '✝️', 'V-0086', 'The house\'s name on all four faces; the wool and coal markets moved to its foot.', ['V-0086']),
        ('VI-K10', None, 'the ancestors\' hall of Seann Dunn', ('burg', 18), '🪵', 'V-0094', 'Forty families name their ancestors aloud each year.', ['V-0094']),
        ('VI-K11', None, 'the Leòid ruling', ('burg', 47), '⚖️', 'V-0038', 'Land held by Tuathaich under human title passes to the Crown; the right to work it stays with the holders.', ['V-0038', 'V-0203']),
        ('VI-K12', None, 'the waterworks of Muileann bhàn', ('burg', 502), '💧', 'V-0037', 'The first public waterworks of the kingdom.', ['V-0037']),
        ('VI-K13', None, 'the copper workings of Àth fhiadhaich', ('burg', 12), '🟠', 'V-0205', 'Not the vein; the town\'s Seann Spioradan house gives them no blessing.', ['V-0205', 'V-0206']),
        ('VI-K14', None, 'Ciorstaidh nic Artair\'s reef post', ('marker', 16), '🔔', 'V-0188', 'An iron post on the reef, painted and hung with a bell.', ['V-0187', 'V-0188']),
        ('VI-K15', None, 'the lifeboat of Cuan bheag', ('burg', 38), '🛟', 'V-0082', 'Bought by the Moot\'s subscription after eleven fishermen drowned; the council paid a third.', ['V-0082']),
    ]
    for key, name, en, at, icon, eid, note, cites in NM:
        s.new_marker(key, name, en, at, icon=icon, event=eid, note=note, cites=cites)

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
        Zz('VI-Z01', dt('Tonn Mhòr Cnoc chaol', 'zone'), 'the Great Wave (SE 4)', 'tsunami', [120, 93, 55], 'Cnoc chaol, Cuan dhearg and Achadh mhin laid waste in one night; a little over nine hundred dead; the wave ran up the gulf to Ros gharbh.', ['V-0017', 'V-0018', 'V-0019', 'V-0022'], master_zone=4),
        Zz('VI-Z02', None, 'the Tuathaich homeland (SE 1)', 'homeland', TUATH_SHIRES, 'Fixed by law; a confinement, yet their children\'s children call it home.', ['V-0001', 'V-0003']),
        Zz('VI-Z03', None, 'the windy coast (in no shire)', 'unclaimed', [0], 'The shire lines stop at the great moss where the humans\' survey stopped; sealers, fowlers and herders, uncounted.', ['V-0014a', 'App.H §V']),
        Zz('VI-Z04', None, 'the Depletion: the vein\'s last unworked stretches (SE 56)', 'mining', [76, 96, 112, 35], 'Catrìona nic Neacail\'s map fits on one sheet.', ['V-0105', 'V-0106', 'V-0192', 'V-0193']),
        Zz('VI-Z05', None, 'dry years at Achadh shean (SE 43)', 'drought', [61], 'Grain sent up the coal line; no one died of hunger; twelve wells dug along the drove road.', ['V-0154', 'V-0155', 'V-0156'], master_zone=2),
        Zz('VI-Z06', None, 'the Cill ghlas district reopened (SE 15)', 'mining', [96, 112], 'Declared safe; new shafts well back from the old fault line.', ['V-0067', 'V-0141'], master_zone=3),
        Zz('VI-Z07', None, 'the stone\'s shires (their own count, SE 65)', 'faith', [10, 17, 25, 72, 78, 108], 'The houses of the Stone publish a count of their people that agrees with the kingdom\'s within a hundred.', ['V-0219']),
        Zz('VI-Z08', None, 'the panthers\' host (SE 62)', 'omen', [25, 78], 'A great host of panthers crosses the south-west near Baile dhomhain.', ['V-0210', 'V-0212']),
    ]
    d['labels'] = [
        {'text': 'mar a thàinig Niall', 'text_en': 'the way Niall came', 'at': {'burg': 19}, 'cites': ['V-0013']},
        {'text': 'a chur san Leabharlann', 'text_en': 'to put it in the Library', 'at': {'marker': 34}, 'cites': ['V-0072']},
        {'text': None, 'text_en': '"They do not come south."', 'at': {'burg': 95}, 'cites': ['V-0047']},
    ]
    for l in d['labels']:
        if l['text']:
            dt(l['text'], 'label', 'phrase')
    d['military']['hosts'] = [
        collections.OrderedDict([('name', None), ('name_en', 'the Crown\'s patrol boats'), ('polity', 'kingdom'), ('station', {'burg': 27}),
                                 ('note', 'Slower than the raiders until the dubhan refits of DE 13; the chandlers of Ceann àrsaidh supply them.'), ('cites', ['V-0063', 'V-0157', 'VI-0043'])]),
        collections.OrderedDict([('name', None), ('name_en', 'the Severance companies (on paper only)'), ('polity', 'kingdom'), ('station', {'burg': 19}),
                                 ('note', 'Stood down in SE 1 and never abolished; their rolls in the council\'s chests. For ninety years the regiments stand on paper alone.'), ('cites', ['V-0002', 'App.C The older hosts'])]),
        collections.OrderedDict([('name', None), ('name_en', 'the armed boats of Cathair gheal'), ('polity', 'moot'), ('station', {'burg': 476}),
                                 ('note', 'The Tuathaich fishermen armed their own boats and drove the raiders from the bay; fined for bearing arms without licence.'), ('cites', ['V-0085'])]),
    ]
    d['military']['campaigns'] = [
        collections.OrderedDict([('name', None), ('name_en', 'the raiders off Cathair gheal'), ('date', 'SE 12–20'), ('at', {'marker': 27}),
                                 ('sides', ['ships that fly no flag, some manned by men who served the Administration', 'the fishermen of Cathair gheal']), ('cites', ['V-0055', 'V-0085'])]),
        collections.OrderedDict([('name', None), ('name_en', 'raiders at Baile ìseal'), ('date', 'SE 44'), ('at', {'burg': 492}), ('note', 'the salt-sheds of Àth bheag burned; the patrol boats came two days later'), ('cites', ['V-0157'])]),
    ]
    d['arms'] = [collections.OrderedDict([('polity', 'kingdom'), ('blazon', 'Azure trellised Or, a fess cotised argent, over all a mascle argent.'),
                                          ('note', 'Cut anew from the old seal of the custody for the roll of arms, Clàr nan Suaicheantas (SE 4).'), ('cites', ['V-0015b', 'App.J §III'])]),
                 collections.OrderedDict([('polity', 'moot'), ('blazon', None), ('note', 'The Moot has no arms on the roll; the Tuathaich shires keep the heater shield of the humans\' district seals.'), ('cites', ['App.J §I', 'App.J §IV'])])]
    for p in range(1, 124):
        bl, note = arms[p]
        d['arms'].append(collections.OrderedDict([('shire', p), ('shire_name', PROVINCES[p]['name']), ('blazon', bl),
                                                  ('shield', 'heater' if p in TUATH_SHIRES or p == 91 else 'wedge'),
                                                  ('note', note or None), ('cites', ['App.J §IV'] + (['V-0132a'] if p == 6 else []))]))
    d['notes']['polities'] = collections.OrderedDict([
        ('kingdom', 'The council of the rising made itself a kingdom, crowned Niall by Macha\'s rite, drew the shires on the humans\' lines and struck its own coin with coal-dust in the seal. It works the vein as the Company worked it, with the names changed, and in the Crown\'s name alone since SE 60. The vein is failing under it, and Mairead is its fourth ruler.'),
        ('moot', 'The Tuathaich householders meet at Caol mhòr under a speaker they choose, and keep minutes, schools, a register of the pit dead and granaries the kingdom never licensed and never shut. The Moot has no standing in law and has never asked for any. Its speaker is Daniel Frayne of Muileann leathan.'),
    ])
    d['notes']['burgs'] = collections.OrderedDict([
        ('19', 'Cathair dhearg: the crown, the council of twelve, the mint in the old counting-house and the Rail Board.'),
        ('135', 'Achadh dhomhain: the Sloc Mòr and the Guild of Hewers, which binds no apprentices now.'),
        ('246', 'Muileann chaol: the Library, where the chests of the provinces fill three floors and the fourth is left empty.'),
        ('95', 'Caol mhòr: the Moot\'s town and the largest of the Tuathaich.'),
        ('431', 'Seann Skell of the south: the high custodian\'s seat and the Rite\'s greatest house.'),
    ])
    return s.finish()
