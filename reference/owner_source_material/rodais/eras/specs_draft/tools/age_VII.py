"""Age VII, the Age of Dubhan (Dubhan Era): the present, DE 27, at full era density."""
# populations: the drafts' own figures, never above a town's present size (eras/pop_sweep.py, round 2)
from common import *  # noqa: F401,F403
from age_VI import faith_setup, shires_unit, named_routes

AGE = 'VII'


def build():
    reset_names()
    s = Spec(AGE, collections.OrderedDict([
        ('age', 'VII'),
        ('age_name', {'name': dt('An Aois Dhubhain', 'age name'), 'name_en': 'the Age of Dubhan'}),
        ('era', {'abbr': 'DE', 'name': dt('Linn an Dubhain', 'era name'), 'name_en': 'the Dubhan Era'}),
        ('snapshot', collections.OrderedDict([
            ('date', '21 an Dùbhlachd, DE 27 (the present)'),
            ('plan_label', 'DE 27, the present (ERA_PLAN); the master map\'s own year'),
            ('y', 2026), ('m', 12), ('d', 21),
            ('last_event_shown', 'VI-0157'),
            ('next_event', None),
            ('description',
             "The coal is all but gone. Every lamp, engine, ship and lorry on the island runs on dubhan, the fuel one Tuathach "
             "made from the waste of the mines; the coin is pegged to it, a tithe laid for a war is taken at every pump, and "
             "this autumn the first tank-hull went out past the north-western capes under Dubhan's narrow charter while the priests "
             "of Manannan prayed the sea shut. Cathal reigns at Cathair dhearg over one hundred and twenty-three shires; nine "
             "regiments and four fleets raised for the Long War stand on the stations they were raised at; the western seams "
             "are flooded and capped, and a pass is needed on the northern road. The Moot at Caol mhòr meets under Peter Hale "
             "with a grievance five years old, and the holdouts of no shire went out onto the windy coast. The Rite's twelve "
             "hewers cut four baskets of altar-coal from the last face of the Sloc Mòr, the Library keeps the war sealed, and "
             "the north keeps its Church and the telling of Naomh Breandan's voyage."),
            ('cites', ['VI-0157', 'VI-0154', 'VI-0154a', 'VI-0154b', 'VI-0049', 'VI-0086', 'VI-0131', 'VI-0118', 'VI-0120', 'VI-0122',
                       'VI-0149', 'VI-0153', 'VI-0098a', 'VI-0144', 'VI-0155', 'VI-0128']),
        ])),
        ('land_changes', [collections.OrderedDict([('what', 'None: this is the master map (Rodos_finished.map) at full era density.'), ('cites', ['map Rodos_finished.map'])])]),
    ]))
    d = s.d
    d['cultures'] = [
        collections.OrderedDict([('key', 'dia-thirich'), ('name', dt('Na Dia-thìrich', 'culture')), ('name_en', 'the Dia-thìrich'), ('master_culture', 2),
                                 ('provinces', [p for p in range(1, 124) if master_culture_of_province(p) == 2]), ('cites', ['App.F Dia-thìrich', 'App.H §VI'])]),
        collections.OrderedDict([('key', 'tuathaich'), ('name', dt('Na Tuathaich', 'culture')), ('name_en', 'the Tuathaich'), ('master_culture', 1),
                                 ('provinces', [p for p in range(1, 124) if master_culture_of_province(p) == 1]), ('cites', ['App.F Tuathaich', 'App.H §VI'])]),
        collections.OrderedDict([('key', 'seann-dhaoine'), ('name', dt('Na Seann-Dhaoine', 'culture')), ('name_en', 'the Old Ones (names only)'), ('master_culture', 0),
                                 ('provinces', []), ('note', 'No town and no land; their names remain on towns and shires (Seann Skell, Seann Warr, Seann Toll and others).'), ('cites', ['App.F Seann-Dhaoine', 'App.H §VI'])]),
    ]
    burg_faith = faith_setup(d, AGE)
    units, arms = shires_unit(d, None)
    s.polity('kingdom', dt('Rìoghachd Dia-thìr', 'polity'), 'the Kingdom of Dia-thìr',
             form='Monarchy (the master map\'s form): a crowned ruler at Cathair dhearg with the council of twelve; the regiments\' commander seated on it (DE 23)',
             capital={'burg': 19},
             ruler={'name': dt('Cathal', 'ruler', 'person'), 'title': 'ruler of Rìoghachd Dia-thìr', 'note': 'crowned at Lùnastal, DE 3', 'cites': ['VI-0006']},
             culture='dia-thirich', color='#66c2a5 (the master map\'s state colour)',
             cites=['V-0007', 'VI-0154a', 'App.H §I'],
             treasury={'purses': 9568, 'head_due': 6375, 'market_due': 3193, 'cites': ['VI-0154a']},
             admin_units=[
                 {'name': None, 'name_en': 'the one hundred and twenty-three shires', 'kind': 'shire', 'units': units, 'cites': ['App.H §VII']},
             ])
    s.polity('moot', None, 'the Moot of the Tuathaich',
             form='an assembly of Tuathaich householders at Caol mhòr under a chosen speaker; no standing in Dia-thìreach law, and it has never asked for any',
             capital={'burg': 95},
             ruler={'name': 'Peter Hale', 'title': 'speaker of the Moot', 'note': 'the Moot\'s minute-books run unbroken from Walter Hale\'s first meeting; Martha Greaves of Doire ghlas followed Daniel Frayne in DE 8', 'cites': ['VI-0153', 'VI-0020']},
             culture='tuathaich', color='#dababf (the master map\'s Tuathaich culture colour)', suzerain='kingdom',
             cites=['V-0008', 'VI-0153', 'App.H §III'])
    s.assign({'kingdom': [p for p in range(1, 124) if p not in TUATH_SHIRES], 'moot': TUATH_SHIRES})
    d['province_polity_notes'] = collections.OrderedDict([
        ('moot', 'As in Age VI: shires of the kingdom, drawn apart because the Moot speaks for them. The master map has one state; the engine may draw the Moot as a label or a subordinate state.'),
        ('unclaimed', 'No shire; the windy coast (province 0 on the master map) pays no due and is held by no one; the holdouts of no shire went out onto it.'),
    ])
    d['diplomacy'] = [
        {'a': 'kingdom', 'b': 'moot', 'relation': 'defeated and unreconciled: seann-chunntas, an old reckoning none in power will settle and none has cancelled',
         'note': 'The motion for amends allowed to die; the request that Tuathaich witness be kept in the Library lies on the table; passes on the northern road since DE 26.',
         'cites': ['VI-0059', 'VI-0138', 'VI-0139', 'VI-0143', 'VI-0149']},
        {'a': 'kingdom', 'b': 'beyond the north-western capes', 'relation': 'the charter of export: dubhan only, loaded at Ros dhomhain; the kingdom does not know who buys', 'cites': ['VI-0154b']},
    ]
    pol_of = {int(k): v for k, v in d['province_polity'].items()}
    for i in sorted(BURGS):
        b = BURGS[i]
        f, order, body = burg_faith(i)
        feats = [k for k in ('port', 'capital', 'citadel', 'walls', 'temple') if b.get(k)]
        e = s.burg(i, population=b['pop'], kind=b['group'], role=GAZ[i]['known_for'],
                   culture='tuathaich' if b['culture'] == 1 else 'dia-thirich', faith=f, order=order, polity=pol_of[b['prov']],
                   cites=['gazetteer B%d' % i, 'map Rodos_finished.map record 15'])
        if feats:
            e['features'] = feats
        if body:
            e['church_body'] = body
    s.new_burg('VII-N01', None, 'the Àth leathan post', ('burg', 346),
               population=35, kind='regimental post', role='a company of the seventh regiment on the road below Àth leathan',
               culture='dia-thirich', faith='old-faith', polity='kingdom',
               reason='built by the seventh regiment after the Long War; called the Àth leathan post in the regimental lists and something else in the town',
               cites=['VI-0125', 'VI-0130'], inferred=False)

    # ---------------------------------------------------------------- routes: the master map, all present
    present = {b['id'] for b in d['burgs']}
    classify_routes(d, AGE, present, named_routes(), touched_rule(min_touch=1, allow_empty=True),
                    'Every master route is present, as on the master map. The named roads carry their names; the line (the old coal line) and its branches are added.')
    d['routes']['new'] = [
        collections.OrderedDict([('key', 'VII-R01'), ('name', None), ('name_en', 'the line (the coal line)'), ('group', 'railways'),
                                 ('points', [{'burg': 135}, {'burg': 354}, {'burg': 19}, {'burg': 27}]),
                                 ('note', 'the Rail Board dropped "coal" from its name; the last coal train ran DE 26 and it carries dubhan, wool and soldiers'), ('cites', ['VI-0022', 'VI-0037', 'VI-0148'])]),
        collections.OrderedDict([('key', 'VII-R02'), ('name', None), ('name_en', 'the western branch'), ('group', 'railways'),
                                 ('points', [{'burg': 19}, {'burg': 47}]), ('note', 'carried arms and dubhan west for the Long War'), ('cites', ['V-0058a', 'VI-0078'])]),
        collections.OrderedDict([('key', 'VII-R03'), ('name', None), ('name_en', 'the line to Ceann leathan'), ('group', 'railways'),
                                 ('points', [{'burg': 354}, {'burg': 22}]), ('cites', ['V-0135'])]),
        collections.OrderedDict([('key', 'VII-R04'), ('name', None), ('name_en', 'the Carters\' Road'), ('group', 'trails'),
                                 ('points', [{'burg': 142}, {'burg': 174}, {'burg': 55}]), ('cites', ['V-0148'])]),
        collections.OrderedDict([('key', 'VII-R05'), ('name', None), ('name_en', 'the dubhan tank-hulls up the west coast'), ('group', 'searoutes'), ('inferred', True),
                                 ('points', [{'burg': 170}, {'burg': 282}, {'burg': 143}]), ('note', 'the third fleet runs dubhan to the Tuathaich depots on the council\'s contract; the Moot pays the freight'),
                                 ('cites', ['VI-0107', 'VI-0135'])]),
    ]

    # ---------------------------------------------------------------- markers: all master markers present
    for i in sorted(MARKERS):
        m = MARKERS[i]
        note = re.sub(r'<[^>]+>', '', m.get('note', '') or '')
        note = re.sub('[\ud800-\udfff]', '', note)
        note = note.split('Its marks run:')[0].split('The old line reads:')[0].split('The signs run:')[0].strip()
        s.marker(i, note=note, cites=['map Rodos_finished.map record 35'])
    NM = [
        ('VII-K01', None, 'the dubhan works of Seann Skell', ('burg', 431), '🏭', 'VI-0008', 'The shipmasters\' works, the first outside the north; its chimney the tallest thing on the coast.', ['VI-0008', 'VI-0010', 'VI-0154']),
        ('VII-K02', None, 'the dubhan depots of the north', ('burg', 143), '🛢️', 'VI-0048', 'Depots at Caol mhòr, Doire ghlas and Ceann mhòr, supplied by sea; the north buys its fire from the south.', ['VI-0048']),
        ('VII-K03', None, 'the Hewers\' Row', ('burg', 313), '🏘️', 'VI-0033', 'The families moved from Muileann dhearg when its last face shut; most work at the dubhan tanks by the landing.', ['VI-0032', 'VI-0033']),
        ('VII-K04', None, 'the sealed archive of the Long War', ('marker', 34), '🔒', 'VI-0128', 'Sealed against all readers for fifty years; the second regiment keeps a guard the Library did not ask for.', ['VI-0128', 'VI-0147']),
        ('VII-K05', None, 'the stone of the regiments\' dead', ('burg', 23), '🪦', 'VI-0126', 'The names of the regiments\' dead of Àth leathan and Muileann ghlas, beside the market cross.', ['VI-0126']),
        ('VII-K06', None, 'the pass posts on the northern road', ('burg', 95), '🛂', 'VI-0149', 'The sixth regiment\'s posts at the boundary stones; the Tuathaich going south must show a pass.', ['VI-0149']),
        ('VII-K07', None, 'the capped western seams', ('burg', 346), '🚫', 'VI-0122', 'Flooded and capped with concrete by the Board\'s order, the seventh regiment standing by.', ['VI-0122']),
        ('VII-K08', None, 'the last face of the Sloc Mòr', ('burg', 135), '⛏️', 'VI-0144', 'One face kept open in the Rite\'s keeping; twelve hewers cut four baskets of altar-coal this year.', ['VI-0144', 'VI-0145', 'VI-0155']),
        ('VII-K09', None, 'the charter of export', ('burg', 27), '🛳️', 'VI-0154b', 'Dubhan loaded only here, a Treasury clerk taking the tithe on every barrel; the custodians of Òrd Bhrìde seal every hold.', ['VI-0154b']),
        ('VII-K10', None, 'the Tuathaich cairn', ('marker', 18), '🪨', 'VI-0130', 'Built on the field without leave; every time the patrols pass it has grown by a stone or two.', ['VI-0130']),
        ('VII-K11', None, 'the fifth regiment\'s barracks', ('burg', 64), '🏰', 'VI-0140', 'The first lasting quarters any regiment has had.', ['VI-0140']),
        ('VII-K12', None, 'the Leòmhann lamp', ('marker', 7), '🕯️', 'VI-0026', 'One wick lamp kept over the door beside the dubhan lamps; a wick lamp over an inn door is still called a Leòmhann.', ['VI-0026']),
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
    Z = []
    for zid, (key, cites) in {0: ('VII-Z00', ['IV-0152', 'IV-0154']), 1: ('VII-Z01', ['IV-0194', 'IV-0195a']), 2: ('VII-Z02', ['IV-0217', 'IV-0219']),
                              3: ('VII-Z03', ['IV-0269', 'IV-0272']), 4: ('VII-Z04', ['V-0017', 'V-0018'])}.items():
        z = ZONES[zid]
        Z.append(Zz(key, dt(z['name'], 'zone'), z['name'], z['type'], [], 'The master map\'s zone, as drawn.', cites + ['App.C Part III'], master_zone=zid))
    Z += [
        Zz('VII-Z05', dt('An Cogadh Fada', 'zone'), 'the Long War (DE 21–22)', 'war', [3, 105, 75, 107, 117, 44, 1],
           'The regiments against the holdouts of the five western towns; the column\'s road south-east to Muileann ghlas.', ['VI-0081', 'VI-0091', 'VI-0098', 'VI-0109', 'VI-0111', 'VI-0115', 'VI-0118']),
        Zz('VII-Z06', None, 'the holdout towns of the western hills', 'war', [3, 105, 75, 117], 'Àth leathan, Muileann àrsaidh, Cnoc thais, Àth naomh and Tobar dhearg of the hills; their pits flooded.', ['VI-0055', 'VI-0122']),
        Zz('VII-Z07', None, 'the windy coast, of no shire', 'unclaimed', [0], 'Sealers, fowlers and herders, near three hundred and forty by the Moot\'s tally; holdouts of Cnoc thais went out onto it and the regiments did not follow.', ['VI-0098a', 'App.H §V']),
        Zz('VII-Z08', None, 'the Tuathaich homeland and the pass line', 'homeland', TUATH_SHIRES, 'Behind the boundary stones; a pass needed to go south since DE 26.', ['V-0001', 'V-0003', 'VI-0149']),
    ]
    d['zones'] = Z
    d['labels'] = [
        {'text': 'seann-chunntas', 'text_en': 'the old reckoning', 'at': {'burg': 95}, 'cites': ['VI-0143']},
        {'text': 'chaidh am fadachadh', 'text_en': 'they got long-warred', 'at': {'marker': 18}, 'cites': ['VI-0119']},
        {'text': 'dubhan-tùsail', 'text_en': 'a first attempt that proved otherwise', 'at': {'burg': 197}, 'cites': ['VI-0036']},
    ]
    for l in d['labels']:
        dt(l['text'], 'label', 'phrase')

    # ---------------------------------------------------------------- military: the thirteen hosts
    RAISED = {"A' chiad rèisimeid": ('VI-0088', 2), "An dàrna rèisimeid": ('VI-0102', 338), "An treas rèisimeid": ('VI-0092', 23),
              "An ceathramh rèisimeid": ('VI-0103', 475), "An còigeamh rèisimeid": ('VI-0093', 64), "An siathamh rèisimeid": ('VI-0101', 20),
              "An seachdamh rèisimeid": ('VI-0084', 489), "An t-ochdamh rèisimeid": ('VI-0106', 103), "An naoidheamh rèisimeid": ('VI-0110', 431),
              "A' chiad chabhlach": ('VI-0089', 50), "An dàrna cabhlach": ('VI-0099', 431), "An treas cabhlach": ('VI-0107', 170),
              "An ceathramh cabhlach": ('VI-0090', 282)}
    EXTRA = {103: ['VI-0141'], 64: ['VI-0140'], 20: ['VI-0149'], 338: ['VI-0147'], 489: ['VI-0122', 'VI-0125'], 475: ['VI-0142'], 170: ['VI-0135']}
    tot = collections.Counter()
    for mil in STATE.get('military', []):
        base = mil['name'].split(' (')[0]
        eid, st = RAISED[base]
        e = collections.OrderedDict([('name', dt(base, 'host')), ('name_en', mil['name']), ('kind', 'fleet' if 'cabhlach' in base else 'regiment'),
                                     ('polity', 'kingdom'), ('station', {'burg': st}), ('raised', ann_date(eid)), ('strength', mil.get('a')),
                                     ('units', mil.get('u')), ('master_regiment', mil.get('i')), ('note', mil.get('note'))])
        tot.update(mil.get('u') or {})
        e['cites'] = [eid] + (EXTRA.get(st, []) if 'cabhlach' not in base or st == 170 else []) + ['App.C Part II', 'map Rodos_finished.map record 14']
        d['military']['hosts'].append(e)
    d['military']['totals'] = dict(tot, cites=['map Rodos_finished.map record 14'])
    d['military']['commander'] = {'name': dt('Somhairle mac Lachlainn', 'commander', 'person'), 'note': 'command of the new-formed regiments; seated on the council DE 23', 'cites': ['VI-0076', 'VI-0124']}
    d['military']['campaigns'] = [
        collections.OrderedDict([('name', dt('An Cogadh Fada', 'campaign')), ('name_en', 'the Long War'), ('date', 'DE 21–22'),
                                 ('master_campaign', 'An Cogadh Fada (map record 14, campaigns)'),
                                 ('sides', ['the kingdom: the Board\'s enforcers, the regiments and fleets, all on dubhan', 'the holdouts of Àth leathan, Muileann àrsaidh, Cnoc thais, Àth naomh and Tobar dhearg; Ruth Calder, Tom Varley, Owen Barrow (Tuathaich tellings)']),
                                 ('battles', [{'at': {'marker': 18}, 'cite': 'VI-0081'}, {'at': {'burg': 244}, 'cite': 'VI-0091'}, {'at': {'burg': 269}, 'cite': 'VI-0098'},
                                              {'at': {'burg': 372}, 'cite': 'VI-0109'}, {'at': {'marker': 17}, 'cite': 'VI-0115'}]),
                                 ('outcome', 'the holdouts broken; nine regiments and four fleets kept on their stations; the western seams capped'),
                                 ('cites', ['VI-0081', 'VI-0115', 'VI-0118', 'VI-0120', 'VI-0122', 'App.C An Cogadh Fada'])]),
        collections.OrderedDict([('name', None), ('name_en', 'the war on the raiders'), ('date', 'DE 13–24'),
                                 ('battles', [{'at': {'burg': 27}, 'cite': 'VI-0043'}, {'at': {'marker': 26}, 'cite': 'VI-0100'}, {'at': {'marker': 13}, 'cite': 'VI-0133'}, {'at': {'marker': 27}, 'cite': 'VI-0134'}]),
                                 ('cites', ['VI-0043', 'VI-0044', 'VI-0100', 'VI-0133', 'VI-0134'])]),
    ]
    d['arms'] = [collections.OrderedDict([('polity', 'kingdom'), ('blazon', 'Azure trellised Or, a fess cotised argent, over all a mascle argent.'),
                                          ('master_coa', STATE.get('coa')), ('note', 'The mint\'s seal pressed plain from DE 15, without coal ink; the roll of arms is unchanged.'), ('cites', ['App.J §III', 'VI-0050', 'VI-0051'])]),
                 collections.OrderedDict([('polity', 'moot'), ('blazon', None), ('note', 'No arms on the roll.'), ('cites', ['App.J §I'])])]
    for p in range(1, 124):
        bl, note = arms[p]
        d['arms'].append(collections.OrderedDict([('shire', p), ('shire_name', PROVINCES[p]['name']), ('blazon', bl),
                                                  ('shield', 'heater' if p in TUATH_SHIRES or p == 91 else 'wedge'), ('master_coa', PROVINCES[p].get('coa')),
                                                  ('note', note or None), ('cites', ['App.J §IV'])]))
    d['notes']['polities'] = collections.OrderedDict([
        ('kingdom', 'The kingdom that the vein founded now runs on a fuel made by a Tuathach, and says so only in its coin. It fought its one war against its own people over the last coal of the west, and keeps the regiments it raised for it on their stations, paid from a tithe that was laid for the war and never lifted. Cathal reigns; the council keeps its twelve seats and one soldier.'),
        ('moot', 'The Moot meets at Caol mhòr under Peter Hale, great-grandson of its first speaker. It stood apart from the Long War and fed the hungry who came to its towns, and its motion for amends was allowed to die. Its minute-books run unbroken from Walter Hale\'s first meeting; its request that the Tuathaich tellings be kept in the Library still lies on the table.'),
    ])
    d['notes']['burgs'] = collections.OrderedDict([(str(i), GAZ[i]['history']) for i in (19, 489, 431, 27, 95, 246, 135, 23)])
    return s.finish()
