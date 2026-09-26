"""Age V, the Age of Strangers (Anchor Era): the island on the day of the Severance."""
# populations: the drafts' own figures, never above a town's present size (eras/pop_sweep.py, round 2)
from common import *  # noqa: F401,F403

AGE = 'V'
TUATH_SHIRES = [7, 14, 23, 28, 36, 75, 86, 88, 105, 107, 122]
HUMAN_TOWNS = {476: 'the human market town of the concession, with its magistrate\'s stone hall and chapel; it kept its gates and militia out of the war',
               54: 'a town of the concession that blocked its road with carts against both sides to the end of the war',
               160: 'a fort and mill of the Administration guarding the northern landing'}
MIXED_TOWNS = {142: 'the Dia-thìreach village with the human farms and mill of the concession beside it',
               143: 'a Dia-thìreach harbour with the concession\'s human fishing families and their tobacco slopes behind it',
               105: 'the old joint town of two tongues; its children of both peoples would not say which they were'}


def build():
    reset_names()
    s = Spec(AGE, collections.OrderedDict([
        ('age', 'V'),
        ('age_name', {'name': dt('An Aois Choigreach', 'age name'), 'name_en': 'the Age of Strangers'}),
        ('era', {'abbr': 'AE', 'name': dt('Linn an Acair', 'era name'), 'name_en': 'the Anchor Era'}),
        ('snapshot', collections.OrderedDict([
            ('date', '1 am Faoilleach, AE 151 (the Severance)'),
            ('plan_label', 'AE 151 (ERA_PLAN): the war ends and the crossing is shut; the next age opens when the northern homeland is fixed by law (SE 1, 22 am Màrt)'),
            ('y', 1930), ('m', 1), ('d', 1),
            ('last_event_shown', 'IV-0377'),
            ('next_event', 'V-0001'),
            ('description',
             "The War of the Hills is over and the crossing is shut. The Administration is gone: its last Commissioner sailed "
             "west from Cuan shean with his officers, the Residency above Ros dhomhain stands stripped, the Company's ledgers are "
             "ash, and its steamships no longer come. The custodians sit again in their council hall at Cathair dhearg, and the "
             "council of the mining country chosen in the forest at Cnoc bheag, with Eilidh nic Raghnaill for its voice, holds the "
             "hills, the east, the capital and every coast; its companies, the silver guild's riflemen and the hawk-faithful stand "
             "to arms still. Under the truce of Àth àrsaidh the humans left on Dia-thìr, a few thousand of them, go north in "
             "columns under safe-conduct into the country of the old concession, where Cathair gheal kept its gates and the "
             "Dia-thìrich of the north-west are choosing whether to stay or go south. The pits are flooded or idle, the coal line "
             "is broken in three places, the Small-Burning Law is long lapsed, and four children of the coal-blood are alive. The "
             "five beacons burn coal again, and their daybooks count no ships."),
            ('cites', ['IV-0377', 'IV-0374', 'IV-0362', 'IV-0355', 'IV-0331', 'IV-0322', 'IV-0369', 'IV-0370', 'IV-0371',
                       'IV-0346', 'IV-0341', 'V-0039', 'IV-0063', 'IV-0266', 'IV-0375']),
        ])),
        ('land_changes', [
            collections.OrderedDict([('what', 'Manannan\'s mist lifted in the winter of the Crossing (AE 1); the northern water is open at the snapshot, but no ship will come again.'),
                                     ('cites', ['IV-0001a', 'IV-0377', 'V-0011'])]),
            collections.OrderedDict([('what', 'The Rending: the earth torn open along a fault about Cill ghlas (AE 137); the district fenced and closed, left to the thorn.'),
                                     ('cites', ['IV-0269', 'IV-0271', 'IV-0272'])]),
            collections.OrderedDict([('what', 'The Abhainn uaine silted black with the washing of coal (AE 33); its salmon runs failed.'), ('cites', ['IV-0085'])]),
            collections.OrderedDict([('what', 'The oak woods about Cathair fhada felled for pit-props (AE 24).'), ('cites', ['IV-0070'])]),
            collections.OrderedDict([('what', 'Spoil-heaps at the camps and deep workings of the Muileann chrom district; the lower galleries of the eastern pits at Ros fhionn flooded (AE 150).'),
                                     ('cites', ['IV-0144', 'IV-0341'])]),
        ]),
    ]))
    d = s.d
    d['cultures'] = [
        collections.OrderedDict([('key', 'dia-thirich'), ('name', dt('Na Dia-thìrich', 'culture')), ('name_en', 'the Dia-thìrich'), ('master_culture', 2),
                                 ('provinces', [p for p in range(1, 124) if p != 105]), ('cites', ['App.F Dia-thìrich'])]),
        collections.OrderedDict([('key', 'humans'), ('name', None), ('name_en', 'the humans of an Tìr Thall (called the Tuathaich from the Severance)'), ('master_culture', 1),
                                 ('provinces', [105]),
                                 ('note', 'A few thousand left on the island: the concession families of the north-west, and the families of Ros bheag, Cuan shean, Baile dhìreach and the south-west now in the columns going north. With the Dia-thìrich of the north-west who stay under the truce and cast in their lot with them, the northern shires hold some hundred thousand people at the Severance, and all of them are the forebears of the Tuathaich. Their homeland is called an Tìr Thall; their own name for it was never written down.'),
                                 ('cites', ['IV-0007', 'IV-0060', 'IV-0363', 'IV-0371', 'IV-0377', 'App.F humans'])]),
    ]
    ORD = collections.OrderedDict([
        ('custody', dict(name='Òrd Bhrìde', name_en='the custodians\' rites of the vein (no ordered body; shrines at the pit-mouths)', gods='Brìde; Crom Cruaich', seat=461,
                         note='The Law lapsed when its keeping stopped paying; crews leave the first coal of each new gallery at the shrine of Cill dhìreach; the shrine of Cill ghlas where the word fuil-ghuail was agreed was swallowed by the Rending.',
                         cites=['IV-0063', 'IV-0150', 'IV-0151', 'IV-0251', 'IV-0271'])),
        ('seabhag', dict(name='Òrd an t-Seabhaig', name_en='the order of the Hawk', gods='Mòd, the Hungry Hawk', seat=132,
                         note='Barred from the camps, its sermons carried in the crews; Ìomhar Seabhag\'s shrines served the Lamp-Watch and mustered the hawk company for the war.',
                         cites=['IV-0066', 'IV-0095', 'IV-0162', 'IV-0284', 'IV-0348'])),
        ('sgoiltean', dict(name='Scoiltean nan Draoidhean', name_en='the druid schools (silent since their last master, AE 123)', gods='Flidais', seat=77,
                           note='The hall at Dùn thais shut by Tolley; the masters taught under the trees of Flidais\'s wood until the last of them died; the register ends.',
                           cites=['IV-0186', 'IV-0188', 'IV-0247'])),
        ('macha', dict(name='Òrd Mhacha', name_en='the order of Macha, split over the humans\' coin', gods='Macha; the two horses', seat=19,
                       note='The capital\'s priests blessed the Residency\'s coin; the dissenters went to the sacred forest at Cnoc bheag and sheltered the forest council; the capital\'s temple sheltered the locked-out custodians.',
                       cites=['IV-0175', 'IV-0179', 'IV-0315', 'IV-0322'])),
        ('cloch', dict(name='Òrd na Cloiche', name_en='the order of the Stone', gods='Lia Fàil', seat=166,
                       note='Sent no men to the war but shut Inis thais to the Company\'s ships and gave the hawk-faithful the Fianna\'s roads.', cites=['IV-0342e'])),
        ('manannan', dict(name='Òrd Mhanannain', name_en='the order of Manannan', gods='Manannan mac Lir', seat=489,
                          note='Held the Crossing the price of a prayer grown slack; its priests at Ceann mhòr taught the first human fishing families the night prayer, and disowned the vigil it became.',
                          cites=['IV-0001a', 'IV-0118', 'IV-0262a'])),
    ])
    d['faiths'] = [
        collections.OrderedDict([('key', 'old-faith'), ('name', dt('An Creideamh Sean', 'faith')), ('name_en', 'the Old Faith'), ('master_religion', 1),
                                 ('type', 'Organized'), ('form', 'Polytheism'), ('deity', 'an Dagda'), ('provinces', []), ('orders', []), ('cites', ['App.B §V'])]),
        collections.OrderedDict([('key', 'old-spirits'), ('name', dt('Na Seann Spioradan', 'faith')), ('name_en', 'the Old Spirits'), ('master_religion', 2),
                                 ('type', 'Folk'), ('form', 'Shamanism'), ('deity', 'the ancestors; na Sìthichean'), ('provinces', []),
                                 ('note', 'The first faith to refuse the Company\'s coal on grounds of belief; the pilgrims of Allt an Àigh through the Long Drought.'),
                                 ('cites', ['IV-0067', 'IV-0222', 'IV-0223'])]),
        collections.OrderedDict([('key', 'church'), ('name', dt('An Eaglais', 'faith')), ('name_en', 'the Church (the Mission)'), ('master_religion', 3),
                                 ('type', 'Organized'), ('form', 'Monotheism'), ('deity', 'Crìosd'), ('provinces', [105]),
                                 ('note', 'Brought over the sea at the Crossing; the Mission\'s chapel on the quay at Ros dhomhain, a chapel in every camp, its house in the north at Cathair gheal. Its clergy left with Strake; its converts among the overseers\' children stay. The vigil of the Grey Night is kept by human labourers near Baile chrom, and called irregular.'),
                                 ('bodies', [
                                     {'name_en': 'the Mission', 'seat': {'burg': 27}, 'cites': ['IV-0044', 'IV-0121', 'IV-0362']},
                                     {'name': dt('Rùn-dìomhair na h-Oidhche Glaise', 'church body'), 'name_en': 'the vigil of the Grey Night', 'seat': {'burg': 305}, 'cites': ['IV-0262', 'IV-0262a']},
                                 ]),
                                 ('cites', ['IV-0001', 'IV-0044', 'IV-0095', 'IV-0116', 'IV-0262'])]),
    ]
    for k, o in ORD.items():
        dt(o['name'], 'order ' + k)
        d['faiths'][0]['orders'].append(collections.OrderedDict([('key', k), ('name', o['name']), ('name_en', o['name_en']), ('gods', o['gods']),
                                                                 ('seat', {'burg': o['seat']}), ('provinces', []), ('note', o['note']), ('cites', o['cites'])]))
    NW_OLDFAITH = {14: 'manannan', 28: 'manannan', 120: 'manannan', 75: 'manannan', 107: 'manannan'}
    faith_prov, order_prov = {}, {}
    for p in range(1, 124):
        mf = master_faith_of_province(p)
        if p == 105:
            faith_prov[p] = 'church'
        elif p in NW_OLDFAITH:
            faith_prov[p], order_prov[p] = 'old-faith', NW_OLDFAITH[p]
        elif p in (36, 7, 86, 23, 88, 122) or mf in (2, 0):
            faith_prov[p] = 'old-spirits'
        else:
            faith_prov[p] = 'old-faith'
            o = present_order(p)
            order_prov[p] = {'bride': 'custody'}.get(o, o)
    for p, f in faith_prov.items():
        if f == 'old-faith':
            d['faiths'][0]['provinces'].append(p)
        elif f == 'old-spirits':
            d['faiths'][1]['provinces'].append(p)
    for o in d['faiths'][0]['orders']:
        o['provinces'] = sorted(p for p, k in order_prov.items() if k == o['key'])

    # ---------------------------------------------------------------- polities
    s.polity('council', dt('Comhairle nan Coimheadaichean', 'polity'), 'the council of the custodians and the rising',
             inferred_name=True,
             form='the Council of Custodians, sitting again in its hall at Cathair dhearg with its high custodian\'s seat empty, and the council of the mining country chosen in the forest at Cnoc bheag, which fought the war; custodians, crew-leaders of the Lamp-Watch and dissenting priests of Macha',
             capital={'burg': 19},
             ruler={'name': dt('Eilidh nic Raghnaill', 'ruler', 'person'), 'title': 'speaker of the forest council',
                    'note': 'a crew-leader of Baile thais and one of the Lamp-Watch; drafted the second petition. The high custodian\'s seat has been empty since AE 105.',
                    'cites': ['IV-0281', 'IV-0322', 'IV-0216', 'App.A §V']},
             culture='dia-thirich', color='#1f4e8c (the old custody blue)',
             cites=['IV-0322', 'IV-0331', 'IV-0352', 'IV-0360', 'IV-0369', 'V-0002', 'V-0009'],
             admin_units=[
                 {'name': dt('Comhairle na Coille', 'unit', 'place'), 'name_en': 'the forest council of the mining country', 'kind': 'war council', 'seat': {'marker': 24},
                  'provinces': [76, 96, 112, 42, 35, 87], 'cites': ['IV-0322'], 'inferred': True},
                 {'name': None, 'name_en': 'the custodians of the settlements (nineteen at the first petition, thirty-one at the second)', 'kind': 'settlement custodians',
                  'provinces': [], 'cites': ['IV-0205', 'IV-0281']},
             ])
    s.polity('north', None, 'the humans\' northern country (the concession and the north-west, under the truce of Àth àrsaidh)',
             form='the human families left on Dia-thìr, withdrawing north under the council\'s safe-conduct; the concession towns left standing; no Commissioner, no Company; the magistrate of Cathair gheal the only officer left',
             capital={'burg': 476},
             ruler={'name': None, 'title': 'the magistrate of Cathair gheal', 'note': 'not named; he wrote to both sides asking to be left alone, and the council granted it', 'cites': ['IV-0116', 'IV-0346']},
             culture='humans', color='#8c8c5a (the grey-green of the concession pasture)', name_note='the chronicles give this country no name; it becomes the Tuathaich homeland in SE 1',
             cites=['IV-0060', 'IV-0346', 'IV-0347', 'IV-0369', 'IV-0370', 'IV-0371', 'IV-0377', 'V-0001'])
    s.polity('silver-guild', None, 'the silver guild of Muileann chiar',
             form='a guild of refiners holding the silver seam and the town under the Silver Compact (AE 44); armed with rifles from the eastern raiders; declared for the council',
             capital={'burg': 419}, ruler={'name': None, 'note': 'Ùna nic Choinnich led it at the compact; its head at the snapshot is not named', 'cites': ['IV-0102']},
             culture='dia-thirich', color='#c0c0c8 (silver)', provinces_note='holds its town and seam within the council\'s country, no shire of its own',
             cites=['IV-0103', 'IV-0143', 'IV-0320', 'IV-0337'])
    s.polity('administration', None, 'the Administration of an Tìr Thall and the Company (gone at the snapshot)',
             form='a Commissioner at the Residency above Ros dhomhain governing by districts drawn for the pits, the customs and the Levy; the Company its partner and at last its master',
             status='withdrawn: Strake left the Residency (AE 150) and sailed from Cuan shean for an Tìr Thall with the last ship able to cross; its districts are drawn below as an earlier moment',
             capital=None,
             ruler={'name': 'Lionel Strake', 'title': 'Commissioner (the last)', 'note': 'sailed for an Tìr Thall; nothing on Dia-thìr tells of his coming anywhere', 'cites': ['IV-0314', 'IV-0362', 'IV-0374']},
             culture='humans', color='#6e2c2c (the Company\'s ledger red, inferred)',
             cites=['IV-0030', 'IV-0031', 'IV-0032', 'IV-0246', 'IV-0374'],
             admin_units=[{'name': None, 'name_en': 'the districts of the Administration (AE 122 to AE 146)', 'kind': 'district; the council kept most of their lines as shires in SE 3',
                           'units': [], 'cites': ['IV-0246', 'IV-0246a', 'App.H §II']}])
    dist = d['polities'][3]['admin_units'][0]['units']
    for p in range(1, 124):
        if p == 67:
            continue
        seat = PROVINCES[p].get('burg')
        if p == 60:
            seat = 387
        members = [p] + ([67] if p == 52 else [])
        e = {'name_en': 'the district of %s' % (BURGS[seat]['name'] if seat else PROVINCES[p]['name']), 'seat': ({'burg': seat} if seat else None), 'provinces': members}
        if p in (122, 123):
            e['note'] = 'a customs station on the island, a district of its own'
        if p == 120:
            e['note'] = 'the outer coasts, ruled from the harbour office at Seann Vell on Eilean ruadh; its surveyors stopped at the great moss'
        if p == 60:
            e['note'] = 'district seat at Baile Mòr ruadh; the kingdom set the seat back at the old harbour'
        dist.append(e)
    s.assign({'council': [p for p in range(1, 124) if p not in TUATH_SHIRES], 'north': TUATH_SHIRES})
    d['province_polity_notes'] = collections.OrderedDict([
        ('north', 'The shires that became the Tuathaich homeland (App.H). At the snapshot the concession (105) is human; the rest are Dia-thìreach towns whose people are choosing to stay or go south as the columns arrive.'),
        ('council', 'Every other shire. The silver guild holds its seam and town inside the council\'s country; the windy coast (no shire) is held by no one.'),
    ])
    d['diplomacy'] = [
        {'a': 'council', 'b': 'north', 'relation': 'truce (the truce of Àth àrsaidh)', 'since': ann_date('IV-0369'),
         'note': 'The humans withdraw into the north-west under the council\'s safe-conduct; the council leaves the concession towns standing. No column was attacked, and none was helped.', 'cites': ['IV-0369', 'IV-0371']},
        {'a': 'council', 'b': 'silver-guild', 'relation': 'allies', 'since': ann_date('IV-0337'), 'cites': ['IV-0337', 'IV-0340']},
        {'a': 'council', 'b': 'administration', 'relation': 'war, ended', 'since': ann_date('IV-0324'), 'note': 'The war ended and the crossing shut on the day of the snapshot.', 'cites': ['IV-0324', 'IV-0377']},
        {'a': 'north', 'b': 'administration', 'relation': 'abandoned', 'note': 'Cathair gheal sent none of its militia to the Residency; Strake did not answer its letter.', 'cites': ['IV-0346']},
        {'a': 'silver-guild', 'b': 'eastern raiders', 'relation': 'trade in rifles for bar silver', 'cites': ['IV-0320', 'IV-0321']},
    ]

    # ---------------------------------------------------------------- burgs
    SPECIAL = {
        19: dict(population=6000, kind='town', role='the custodians\' hall, its locks broken; the bridge barricaded with coal-carts in the rising; hungry since the winter, the grain shared by household', cites=['IV-0331', 'IV-0354', 'IV-0376']),
        27: dict(population=18855, kind='city', role='the capital\'s great harbour: the Residency above it stripped, the Company\'s quays and deep-water quay, the burned counting-house and the Mission chapel; the harbour quarter opened its gates to the council', cites=['IV-0031', 'IV-0044', 'IV-0211', 'IV-0356', 'IV-0360', 'IV-0362']),
        354: dict(population=1601, kind='city', role='the heart of the Company\'s pits: overseers\' town, weigh-house burned, the store taken at first light by Mòrag nic Iain\'s crews; the coal line runs from here', cites=['IV-0040', 'IV-0092', 'IV-0243a', 'IV-0325', 'IV-0358']),
        44: dict(population=940, kind='town', role='the strike town and home of the Lamp-Watch: the walled pithead held eleven days, the book of complaints', cites=['IV-0166', 'IV-0208', 'IV-0213', 'IV-0234', 'IV-0327']),
        419: dict(population=91, kind='town', role='the silver guild\'s town under the Silver Compact; rose for the council and escorted the Company\'s agents to the coast', cites=['IV-0103', 'IV-0171', 'IV-0337']),
        135: dict(population=990, kind='town', role='the camp of the deep galleries under the hill, houses built of spoil; the green acre where the Green Death was first marked; the Sloc Mòr is here', cites=['IV-0144', 'IV-0153']),
        224: dict(population=76, kind='large village', role='the first town drawn on paper, a Company camp on a grid; two streets pulled down for a spoil-tip', cites=['IV-0087', 'IV-0318']),
        383: dict(population=118, kind='large village', role='the Company\'s camp of timber huts at the ford below the new workings, the first settlement made for the pit alone', cites=['IV-0077', 'IV-0163']),
        476: dict(population=610, kind='town', walls=True, role=HUMAN_TOWNS[476], cites=['IV-0116', 'IV-0199', 'IV-0287', 'IV-0346']),
        54: dict(population=73, kind='large village', role=HUMAN_TOWNS[54], cites=['IV-0347']),
        160: dict(population=80, kind='large village', walls=True, role=HUMAN_TOWNS[160], cites=['gazetteer B160', 'IV-0288']),
        63: dict(population=2996, kind='town', role='the last seat of the Administration, hungry behind its walls; the last ship from the east anchored here; its human families gone north in the columns', cites=['IV-0363', 'IV-0365', 'IV-0368', 'IV-0371']),
        282: dict(population=4389, kind='town', role='where the humans first came ashore and whence the last Commissioner sailed; its custodians shut the harbour to the Company\'s ships', cites=['IV-0002', 'IV-0366', 'IV-0374']),
        304: dict(population=1273, kind='town', role='the truce was agreed here, on the edge of the concession', cites=['IV-0369']),
        303: dict(population=593, kind='town', role='the greatest town of the north-west, named in the truce to receive the columns; its Dia-thìrich given the choice of staying or going south', cites=['IV-0370']),
        313: dict(population=527, kind='large village', role='its coal stage shelled by a Company steamship from the river and the fishing town behind it set burning; twenty-three dead', cites=['IV-0090', 'IV-0342']),
        255: dict(population=2346, kind='town', role='the rope-walks turned to winding-rope; the constables\' barracks; it shut its gates behind Ashdown and nursed his wounded', cites=['IV-0082', 'IV-0283', 'IV-0336']),
        105: dict(population=216, kind='large village', role=MIXED_TOWNS[105], cites=['IV-0022', 'IV-0110', 'IV-0367']),
        142: dict(population=3334, kind='town', role=MIXED_TOWNS[142], cites=['IV-0117']),
        143: dict(population=4323, kind='town', role=MIXED_TOWNS[143], cites=['IV-0118', 'IV-0122a', 'IV-0262a']),
        305: dict(population=3000, kind='town', role='the hunger was worst here, within sight of the new beacon; the Mission kitchen; the human labourers\' vigil of the Grey Night in the fields near it', cites=['IV-0195', 'IV-0199', 'IV-0262']),
        246: dict(population=368, kind='large village', role='the cellars of the custodians\' rolls, beyond the Residency\'s reach; the rolls of the age sent here at the war\'s end; the Line of Aisling found', cites=['IV-0248', 'IV-0251a', 'IV-0376']),
        152: dict(population=306, kind='large village', role='the Company\'s second coal port, end of the mule tram-road', cites=['IV-0148', 'IV-0236']),
        351: dict(population=423, kind='town', role='the Company\'s coal quay, seized by the crews and its mouth blocked with two sunk barges', cites=['IV-0041', 'IV-0326']),
        397: dict(population=588, kind='large village', role='the deep-water quay for the eastern coal; a village of forty houses become a town of four hundred', cites=['IV-0212']),
        26: dict(population=4005, kind='city', role='the Company\'s first warehouse, broken open for the council\'s companies', cites=['IV-0033', 'IV-0332']),
        77: dict(population=4595, kind='city', role='the druid school\'s hall shut; the grey fever took the Administration\'s physician; the masters\' houses opened as sick-rooms', cites=['IV-0186', 'IV-0247', 'IV-0278']),
        132: dict(population=2532, kind='town', role='Ìomhar Seabhag\'s hawk-shrine, where the hawk company was called', cites=['IV-0284', 'IV-0348']),
        489: dict(population=27914, kind='city', role='the hawk company mustered here and held the road from Ros bheag to the north-west', cites=['IV-0349']),
    }
    ABSENT = {
        101: ('emptied under the edict of seizure for a shaft beneath the hill (AE 147); its last households carried out by constables', ['IV-0317', 'IV-0309'], 'emptied'),
        140: ('its families walked south to the camps in the Great Hunger (AE 97); the village stands empty for a generation, resettled after the Severance', ['IV-0201', 'gazetteer B140'], 'emptied'),
        123: ('swallowed by the Rending with its shrine (AE 137); the district fenced and closed; rebuilt on the far side of the crack after the district reopens (SE 15)', ['IV-0269', 'IV-0271', 'IV-0272', 'V-0067', 'gazetteer B123'], 'lost in the Rending'),
        228: ('in the closed district of the Rending: without work, emptied toward Baile thais and Muileann dhearg', ['IV-0272', 'gazetteer B228'], 'emptied'),
        423: ('emptied when the Rending closed the district for a generation', ['IV-0272', 'gazetteer B423'], 'emptied'),
    }
    pol_of = {int(k): v for k, v in d['province_polity'].items()}
    present = set()
    for i in sorted(BURGS):
        g = GAZ[i]
        if i in ABSENT:
            r, c, st = ABSENT[i]
            s.absent(i, r, c, state=st)
            continue
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
                pop = rnd(pop * 0.5, AGE)      # the famine country of Gorta Baile chrom (IV-0195a)
            elif p in TUATH_SHIRES:
                pop = rnd(pop * 0.7, AGE)
        culture = 'humans' if i in HUMAN_TOWNS else 'dia-thirich'
        f = 'church' if i in HUMAN_TOWNS else faith_prov[p]
        if p == 105 and i not in HUMAN_TOWNS:
            f = 'old-faith' if master_faith_of_province(p) == 1 else 'old-spirits'
            f = 'old-faith'
        order = order_prov.get(p) if f == 'old-faith' else None
        if p == 105 and f == 'old-faith':
            order = 'manannan'
        pol = 'silver-guild' if i == 419 else pol_of[p]
        note = None
        if i in MIXED_TOWNS:
            note = 'a town of both peoples at the snapshot'
        s.burg(i, population=pop, kind=kw.pop('kind', None) or kind_for(pop, AGE), role=kw.pop('role', None) or generic_role(i),
               culture=culture, faith=f, order=order, polity=pol, cites=kw.pop('cites', None) or ['gazetteer B%d' % i],
               inferred=True, note=note, **kw)
        present.add(i)

    # ---------------------------------------------------------------- new burgs
    s.new_burg('V-N01', None, 'the columns\' camp at Baile Mòr ruadh', ('burg', 303),
               population=3000, kind='refugee camp', role='the human families of Ros bheag, Cuan shean, Baile dhìreach and the south-west, received here under the truce',
               culture='humans', faith='church', polity='north',
               reason='the truce names Baile Mòr ruadh as the place where the columns are received; a few thousand humans in all, most of whom had never lived in the north',
               cites=['IV-0363', 'IV-0370', 'IV-0371', 'IV-0373'], inferred=True)
    s.new_burg('V-N02', None, 'the Residency above Ros dhomhain', ('burg', 27),
               population=0, kind='government house (empty)', role='the Commissioners\' house of dressed stone on the rise above the harbour, with its field; stripped of all but its furniture when the council\'s companies entered',
               culture='humans', faith='church', polity='council',
               reason='a separate house and grounds above the town from AE 9; entered by the council the morning after Strake left (AE 150); not a later town',
               cites=['IV-0031', 'IV-0315a', 'IV-0334', 'IV-0360', 'IV-0362'], inferred=True)
    s.new_burg('V-N03', None, 'the camp of Cnoc fhiadhaich workings', ('burg', 280),
               population=800, kind='mining camp', role='the Company\'s working opened round Doire mhòr\'s fields; the gallery that killed eleven; the coughing sickness',
               culture='dia-thirich', faith='old-faith', polity='council',
               reason='the camp at the working is distinct from the hunters\' village of Cnoc fhiadhaich (burg 280); it is gone by the present day',
               cites=['IV-0047', 'IV-0072', 'IV-0073'], inferred=True)

    # ---------------------------------------------------------------- routes
    named = {
        410: dict(first='I', name='Slighe-mhara àrsaidh', group='searoutes', cites=['I-0064a']),
        264: dict(first='III', name='Slighe Cnoc leathan', group='trails', cites=['II-0207']),
        3: dict(first='IV', name='An Rathad Tuath', group='roads', cites=['III-0145']),
        17: dict(first='IV', name='Slighe Muileann dhearg', group='roads', cites=['III-0145']),
        98: dict(first='IV', name='Slighe Baile òg', group='roads', cites=['III-0145']),
        403: dict(first='IV', name='Seòlaid Ros fhionn', group='searoutes', cites=['III-0168b']),
        354: dict(first='IV', name='Slighe-mhara Caol fhiadhaich', group='searoutes', cites=['III-0189a', 'IV-0090a'], note='the Company\'s coal ships from the river mouth at Ceann leathan west to the open sea'),
        349: dict(first='V', name='Seòlaid Ceann òg', group='searoutes', cites=['IV-0076a'], note='the traders\' lane from the quay at Ceann òg round the north and west to the capital\'s water; ships for an Tìr Thall left it off the north-west'),
        301: dict(first='V', name='Ceum Ros àrsaidh', group='trails', cites=['IV-0364'], note='the coast road north of Ros bheag, held by Strake\'s constables at Ros àrsaidh'),
        383: dict(first='VI', cites=['III-0215'], inferred=True),
        385: dict(first='VI', cites=['gazetteer B205'], inferred=True),
        50: dict(first='VI', cites=['V-0090']), 71: dict(first='VI', cites=['V-0090']),
    }
    for r in (16, 39, 52, 70, 111, 115, 130, 131, 446):
        named[r] = dict(first='V', name='Rathad na Mèinne', group='roads', cites=['IV-0088a'],
                        note='the mine road, metalled by the Company\'s gangs wide enough for coal-carts both ways; cut at its half-way stage by An Taigh-seinnse Mòr in the war')
    for r in (173, 175, 210, 229, 233, 248, 447):
        named[r] = dict(first='IV', name='Rathad na Banrighinn', group='roads', cites=['III-0114'])
    classify_routes(d, AGE, present, named, touched_rule(min_touch=1, allow_empty=True),
                    'A master trail or sea-lane is present when every town it touches stands in this age (or both end towns stand '
                    'and at most a quarter between are not). The mine road, the queen\'s road and the crown\'s old coal-roads are '
                    'roads; the Company\'s railway and tram-road are added. The fair road (SE 21) and the lanes dated later are absent.')
    d['routes']['new'] = [
        collections.OrderedDict([('key', 'V-R01'), ('name', None), ('name_en', 'the coal line (carbad-iarainn)'), ('group', 'railways'),
                                 ('points', [{'burg': 354}, {'burg': 19}, {'burg': 27}]),
                                 ('note', 'the Company\'s railway from the pits at Muileann chrom by Cathair dhearg to the deep-water quay at Ros dhomhain (AE 120); broken in three places in the war, mended by the kingdom in SE 8'),
                                 ('state', 'broken'), ('cites', ['IV-0243a', 'V-0039'])]),
        collections.OrderedDict([('key', 'V-R02'), ('name', None), ('name_en', 'the mule tram-road to Ros dhìreach'), ('group', 'railways'),
                                 ('points', [{'burg': 501}, {'burg': 152}]),
                                 ('note', 'Vane\'s iron tram-road drawn by mules from the southern workings down to the coal port (AE 115); left to the mules when the coal line opened'),
                                 ('cites', ['IV-0236', 'IV-0243a']), ('inferred', True)]),
        collections.OrderedDict([('key', 'V-R03'), ('name', None), ('name_en', 'the eastern coal road'), ('group', 'roads'),
                                 ('points', [{'burg': 76}, {'burg': 62}, {'burg': 144}]),
                                 ('note', 'coal from the eastern workings carted over the rebuilt Drochaid Ros fhionn to the river quays of Inis bheag and Baile mhin; fallen silent since the eastern pits flooded in the war'),
                                 ('state', 'idle'), ('cites', ['IV-0123', 'IV-0124', 'IV-0125', 'IV-0341'])]),
        collections.OrderedDict([('key', 'V-R04'), ('name', None), ('name_en', 'the coal barges of the Abhainn uaine'), ('group', 'rivers'),
                                 ('points', [{'burg': 313}, {'marker': 39}, {'burg': 22}]),
                                 ('note', 'the barges from the landing at Seann Toll and Cidhe Beag down to Ceann leathan, where the Company\'s ships loaded; no coal has left the hills by water since the quay at Ceann fhada was seized'),
                                 ('state', 'idle'), ('cites', ['IV-0084', 'IV-0090', 'IV-0090a', 'IV-0326'])]),
        collections.OrderedDict([('key', 'V-R05'), ('name', None), ('name_en', 'the Company\'s cart-road round Doire mhòr'), ('group', 'trails'),
                                 ('points', [{'burg': 354}, {'new_burg': 'V-N03'}]),
                                 ('note', 'run round the fields of Doire mhòr and not through them, to the working at Cnoc fhiadhaich'), ('cites', ['IV-0047'])]),
        collections.OrderedDict([('key', 'V-R06'), ('name', None), ('name_en', 'the road of the columns north'), ('group', 'trails'),
                                 ('points', [{'burg': 63}, {'burg': 412}, {'burg': 346}, {'burg': 303}]),
                                 ('note', 'the human families marched north along the western roads under guard of the council\'s companies; counted over at the ford of Àth chrom, camped a night at Àth leathan'),
                                 ('cites', ['IV-0371', 'IV-0372', 'IV-0373'])]),
    ]

    # ---------------------------------------------------------------- markers
    M = {
        0: dict(note='The Administration\'s bath-house for its officers; the Dia-thìrich let in on certain days and charged a penny.', cites=['IV-0170']),
        1: dict(note='It ran on through the three dry years; the Administration\'s watchman posted to charge for the water was called back after one season.', cites=['IV-0222']),
        2: dict(note='Held by the guild under the Silver Compact; the guild armed with rifles through the eastern raiders.', cites=['IV-0101', 'IV-0103', 'IV-0320']),
        3: dict(note='Rebuilt by Company masons wide enough for coal-carts two abreast; barricaded with the carts themselves when the capital rose.', cites=['IV-0057', 'IV-0331']),
        4: dict(note='Rebuilt by the Company for the eastern coal road; silent since the eastern pits flooded.', cites=['IV-0123', 'IV-0341']),
        5: dict(note='Barred at dusk, a watch on the roof; its keeper Tormod Buabhall sends a list of travellers up the road each week.', cites=['IV-0294']),
        6: dict(note='The singing house of Fearchar Bàrd\'s songs, walled and watched.', cites=['IV-0210', 'IV-0293']),
        7: dict(note='Six new ostlers who know nothing of horses.', cites=['IV-0292']),
        8: dict(note='A loft for sleeping men, never empty and never the same men twice.', cites=['IV-0296']),
        9: dict(note='A walled well in its yard, against thieves, its keeper says.', cites=['IV-0291']),
        10: dict(note='Opened again by Seònaid Bhàn; kept by Aonghas, who shut its gates across the coal road in the war.', cites=['IV-0088', 'IV-0300', 'IV-0329']),
        11: dict(note='The Lamp-Watch\'s post-house to the silver town; the guild pays its keeper\'s rent.', cites=['IV-0297']),
        12: dict(era_name=None, note='The fifth and last tower, built by the Levy\'s masons of Cnoc thais; a coal flame; the ring whole.', cites=['IV-0189', 'IV-0190', 'IV-0193']),
        13: dict(note='The second tower (AE 27); dark in the war, lit again at the council\'s order.', cites=['IV-0075', 'IV-0350', 'IV-0375']),
        14: dict(note='The fourth tower, the first to burn coal.', cites=['IV-0138']),
        15: dict(note='The third tower; Tormod mac Pheadair\'s daybook of ships.', cites=['IV-0106', 'IV-0107']),
        16: dict(note='The first tower (AE 15), over the old fire-tower; put out in the war and lit again.', cites=['IV-0048', 'IV-0350', 'IV-0375']),
        19: dict(note='Walled up since the Sundering.', cites=['III-0149']),
        20: dict(note='Walled up since the Sundering.', cites=['III-0199']),
        21: dict(note='Seen by the crew of a Company brig and filed with the complaints about pirates.', cites=['IV-0127']),
        22: dict(note='Two Company surveyors went up against the villagers\' counsel and were not seen again.', cites=['IV-0128', 'IV-0129']),
        23: dict(note='The druid masters taught under the trees when they could no longer teach in a hall.', cites=['IV-0188']),
        24: dict(note='The dissenting priests of Macha settled here; the council of the mining country was made here.', cites=['IV-0179', 'IV-0322']),
        25: dict(note='A Company brig boarded and stripped; the raiders never known.', cites=['IV-0050']),
        26: dict(note='A Company coal ship burned; the silver guild\'s rifles come ashore here.', cites=['IV-0108', 'IV-0321']),
        27: dict(note='No raid recorded in this age.', cites=['II-0201'], inferred=True),
        28: dict(note='Copied by Samuel Wren and sent over the sea; no answer came.', cites=['IV-0051']),
        29: dict(note='Copied by Edwin Lowe; not the same script as the obelisk\'s.', cites=['IV-0141']),
        30: dict(note='Lowe\'s last copy.', cites=['IV-0142']),
        31: dict(note='Ruin.', cites=['I-0059']),
        32: dict(note='Ruin.', cites=['I-0061']),
        33: dict(note='Edwin Lowe dug here a season: cut stone, burnt bone, marks he could not read.', cites=['IV-0140']),
        34: dict(era_name=None, era_name_en='the custodians\' cellars at Muileann chaol', icon='📚', note='The rolls of the east kept in three families\' houses; the Line of Aisling found in the roll of the camp at Àth ìseal.', cites=['IV-0248', 'IV-0251a', 'IV-0376']),
        37: dict(era_name=None, era_name_en='the old games-field at Ceann leathan', note='No games recorded in this age.', cites=['II-0209'], inferred=True),
        39: dict(note='Widened with cut stone for the coal barges; its shrine moved uphill.', cites=['IV-0084']),
        40: dict(note='The herders keep the crossing days.', cites=['III-0072'], inferred=True),
        41: dict(note='The old burial ground.', cites=['I-0075'], inferred=True),
        42: dict(note='The crew-leaders of the northern pits fixed the week of their rising here; a cairn of spoil-stones.', cites=['IV-0327a']),
        43: dict(note='The custodians of Muileann dhomhain lent the folk of the closed district the land at the fence.', cites=['IV-0272a']),
        44: dict(note='The stone on the neck of the strait.', cites=['III-0167a']),
        45: dict(note='Where the boats of Achadh àrsaidh met the three ships out of the thinning mist.', cites=['IV-0001a']),
        46: dict(note='The meeting of the cups.', cites=['I-0154a'], inferred=True),
        47: dict(note='The Leaden Hawk company ended its road at Inis thais, six days out of Cuan dhearg.', cites=['IV-0342a', 'IV-0342e']),
        48: dict(note='The Mason\'s Point.', cites=['I-0027a']),
    }
    for i in sorted(MARKERS):
        if i in M:
            s.marker(i, **M[i])
        else:
            d['markers']['absent'].append({'id': i, 'reason': {17: 'the Long War battle is DE 22', 18: 'the Long War battle is DE 21', 35: 'first recorded SE 53', 36: 'first recorded SE 25',
                                                               38: 'the old barter market closed after its last season (AE 131); the ground stands empty until the fair of SE 21'}.get(i, 'later'),
                                           'cites': {38: ['IV-0257', 'V-0088'], 17: ['VI-0115'], 18: ['VI-0081'], 35: ['V-0184'], 36: ['V-0102']}.get(i, [])})
    NM = [
        ('V-K01', None, 'the Mission chapel and school', ('burg', 27), '⛪', 'IV-0044', 'The first church on the island, of timber on the quay, with the first iron bell; the Mission school; Matthew Dunne\'s sermon against the night shift.', ['IV-0044', 'IV-0121', 'IV-0241']),
        ('V-K02', None, 'the Company\'s deep-water quay and steelyard', ('burg', 27), '⚓', 'IV-0211', 'Built for the iron steamships that burn the island\'s coal to carry it away; the great steelyard where the yield was weighed by the ton.', ['IV-0147', 'IV-0211']),
        ('V-K03', None, 'the Rending', ('cell', near_cell(('burg', 123), 96)), '🕳️', 'IV-0269', 'The earth tore open along the fault under a common working driven with blasting-powder; the old cutting and its shrine swallowed; dozens dead.', ['IV-0267', 'IV-0269', 'IV-0271']),
        ('V-K04', None, 'the fight at the ford of Àth chiar', ('burg', 163), '⚔️', 'IV-0335', 'Ashdown\'s column met at the ford; forty of his and nineteen of the rebels\' dead, all named in the council\'s roll.', ['IV-0335']),
        ('V-K05', None, 'the store at Baile thais', ('burg', 44), '🏚️', 'IV-0327', 'The walled pithead held eleven days; the constables sent to the coast unharmed.', ['IV-0213', 'IV-0327']),
        ('V-K06', None, 'the shelling of Seann Toll', ('burg', 313), '💥', 'IV-0342', 'The first time the humans turned the island\'s own coal, burning in their boilers, against a Dia-thìreach town.', ['IV-0342']),
        ('V-K07', None, 'the fight at Cnoc ghorm', ('burg', 392), '⚔️', 'IV-0359', 'The Administration\'s last sally toward the mining country, driven back.', ['IV-0359']),
        ('V-K08', None, 'the truce of Àth àrsaidh', ('burg', 304), '🕊️', 'IV-0369', 'The humans to withdraw into the north-west under safe-conduct; the concession towns left standing.', ['IV-0369']),
        ('V-K09', None, 'the beacon hill of the stoppage', ('cell', near_cell(('burg', 101), 76)), '🔥', 'IV-0306', 'The sign for the day the pits stopped, lit by Beathag Dhubh\'s people\'s children; the constables burned the heather of the hill.', ['IV-0306', 'IV-0309']),
        ('V-K10', None, 'the green acre', ('burg', 135), '🪦', 'IV-0153', 'The field beyond the spoil-heaps where the first forty dead of the Green Death were buried.', ['IV-0153']),
        ('V-K11', None, 'the burned flying-machine shed', ('cell', near_cell(('burg', 27), 5, {BURGS[27]['cell']})), '✈️', 'IV-0360', 'Strake\'s iron bird, flown to count the workings from the air; burned in its shed when the harbour quarter changed sides. Nothing has flown over Dia-thìr since that was not a bird.', ['IV-0315a', 'IV-0360']),
        ('V-K12', None, 'the ford where the columns were counted', ('burg', 412), '🧮', 'IV-0372', 'The last count the Dia-thìrich make of the humans on Dia-thìr in this age.', ['IV-0372']),
        ('V-K13', None, 'the grey-night fields', ('cell', near_cell(('burg', 305), 28)), '🪿', 'IV-0262', 'Human labourers near Baile chrom keep vigil by night in the fields, in silence, under the sign of a grey goose.', ['IV-0262', 'IV-0262a']),
        ('V-K14', None, 'the pit shrine of Cill dhìreach', ('burg', 461), '⛏️', 'IV-0150', 'The first piece of coal from each new gallery left here; the Company allows it, for it costs a stone a gallery.', ['IV-0150']),
        ('V-K15', None, 'the book of Baile thais and the Lamp-Watch', ('burg', 44), '📖', 'IV-0208', 'The oldest writing of grievance, set down by many hands; the burial club under whose cover the Lamp-Watch met.', ['IV-0208', 'IV-0234']),
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
        Zz('V-Z01', dt('A\' Phlàigh Uaine', 'zone'), 'the Green Death (AE 73)', 'disease', [6, 76, 96, 9], 'Through the mining camps and along the coal roads; twenty-six settlements had cases.', ['IV-0152', 'IV-0153', 'IV-0154'], master_zone=0),
        Zz('V-Z02', dt('Gorta Baile chrom', 'zone'), 'the Great Hunger (AE 94)', 'famine', [28, 14, 105, 75], 'Thirty-four settlements; worse because the Levy had taken the hands.', ['IV-0194', 'IV-0195', 'IV-0195a'], master_zone=1),
        Zz('V-Z03', dt('Tiormachd Achadh shean', 'zone'), 'the Long Drought (AE 106–108)', 'drought', [61, 66, 60, 82, 58], 'Three dry years; the custodians counted ten districts of the east.', ['IV-0217', 'IV-0218', 'IV-0219'], master_zone=2),
        Zz('V-Z04', dt('Scàineadh Cill ghlas', 'zone'), 'the Rending and the closed district (AE 137)', 'fault', [96, 112], 'The Company fenced the district and left it to the thorn.', ['IV-0269', 'IV-0272'], master_zone=3),
        Zz('V-Z05', None, 'the northern concession (AE 20)', 'grant', [105], 'Upland pasture about Muileann àrsaidh for human families who would not work in the pits.', ['IV-0060']),
        Zz('V-Z06', None, 'the Levy country (AE 88–97)', 'law', [7, 28, 105, 14, 36, 75, 86, 107, 3, 117, 73], 'One in five of the able grown folk of the western and northern villages sent to the pits for two years; set aside too late for the harvest.', ['IV-0181', 'IV-0183', 'IV-0200']),
        Zz('V-Z07', None, 'the lines at midsummer AE 150', 'front', [], 'The council held the hills, the east and the capital; Strake held the Residency, the harbour quarter below it and the western ports.', ['IV-0352'],
           sides={'council': [p for p in range(1, 124) if p not in (5, 77, 38, 3, 64, 15, 2, 73, 117, 120, 108)], 'administration': [5, 77, 38, 3, 64, 15, 2, 73, 117, 120, 108]}, inferred=True),
        Zz('V-Z08', None, 'the mining country of the rising (AE 149)', 'war', [76, 96, 112, 42, 35, 87, 44, 34, 55], 'Where the war opened: Muileann chrom, Ceann fhada, Baile thais, the northern pits.', ['IV-0324', 'IV-0325', 'IV-0326', 'IV-0327', 'IV-0328']),
        Zz('V-Z09', None, 'the lifted mist (AE 1)', 'sea', [], 'The mist that lay on the eastern sea since the Sundering lifted from the northern water in the winter of the Crossing.', ['IV-0001a'], sea='the eastern sea'),
    ]
    d['labels'] = [
        {'text': None, 'text_en': 'the Severance', 'at': {'burg': 282}, 'cites': ['IV-0374', 'IV-0377']},
        {'text': 'eun-iarainn', 'text_en': 'the iron bird (burned)', 'at': {'burg': 27}, 'cites': ['IV-0315a', 'IV-0360']},
        {'text': 'fuil-ghuail', 'text_en': 'coal-blood (the word agreed at Cill ghlas, AE 126)', 'at': {'burg': 135}, 'cites': ['IV-0250', 'IV-0251']},
    ]
    for l in d['labels']:
        if l['text']:
            dt(l['text'], 'label', 'phrase')

    # ---------------------------------------------------------------- military
    H = []

    def host(name_en, pol, at, note, cites, name=None):
        H.append(collections.OrderedDict([('name', name), ('name_en', name_en), ('polity', pol), ('station', at), ('note', note), ('cites', cites)]))
        if name:
            dt(name, 'host')
    host('the council\'s companies', 'council', {'burg': 19}, 'Raised by the council in the war; stood down at Cathair dhearg in SE 1 and never abolished. Their rolls go to the council unburned.', ['IV-0332', 'V-0002'])
    host('the crews of Muileann chrom under Mòrag nic Iain', 'council', {'burg': 354}, 'Took the walled store at first light; eleven constables yielded without a shot.', ['IV-0325'])
    host('the silver guild\'s riflemen', 'silver-guild', {'burg': 419}, 'Opened the guild\'s armoury; took the constable post at Dùn ìseal after one exchange of fire.', ['IV-0337', 'IV-0338'])
    host('the riflemen of Cnoc leathan', 'council', {'burg': 167}, 'Joined the silver guild\'s companies and hold the eastern road.', ['IV-0340'])
    host('the hawk company', 'council', {'burg': 489}, 'The hawk-faithful mustered at Seann Skell, holding the road between Ros bheag and the north-west.', ['IV-0348', 'IV-0349'])
    host('the Leaden Hawk company', 'council', {'burg': 166}, 'Seven hawk-faithful crewmen who carried the council\'s letters to the Hawk coast; joined the hawk company.', ['IV-0342a', 'IV-0342e'], name='Buidheann an t-Seabhaig Luaidhe')
    host('the Lamp-Watch', 'council', {'burg': 44}, 'The pit crews\' fellowship under cover of a burial club; the road-houses were its waystations.', ['IV-0234', 'IV-0290'])
    host('the militia of Cathair gheal', 'north', {'burg': 476}, 'Raised behind shut gates and sent to neither side.', ['IV-0346'])
    host('the watch of Muileann àrsaidh', 'north', {'burg': 54}, 'Kept on the road against both sides to the end of the war.', ['IV-0347'])
    d['military']['hosts'] = H
    d['military']['hosts_gone'] = [
        {'name_en': 'Merriman\'s and Strake\'s constables and the Company guards', 'note': 'Posts at Muileann shean, Tobar ghorm, Dùn chrom (barracks), Muileann chrom, Baile thais, Ceann fhada and Cnoc chaol; broken, surrendered or gone with Strake.', 'cites': ['IV-0259', 'IV-0260', 'IV-0261', 'IV-0282', 'IV-0283', 'IV-0374']},
        {'name_en': 'the Company\'s gunboat and steamships', 'note': 'Burned the fishermen\'s boats at a cove near Ceann leathan (AE 47); shelled Seann Toll (AE 150); no longer come.', 'cites': ['IV-0109', 'IV-0342', 'IV-0351']},
    ]
    d['military']['campaigns'] = [
        collections.OrderedDict([('name', None), ('name_en', 'the War of the Hills (the Severance war)'), ('date', 'AE 149–151'),
                                 ('sides', ['the council, the crews, the Lamp-Watch, the silver guild, the riflemen of Cnoc leathan, the hawk company', 'Commissioner Strake, the constables, the Company\'s guards and ships']),
                                 ('battles', [{'at': {'burg': 354}, 'cite': 'IV-0325'}, {'at': {'burg': 351}, 'cite': 'IV-0326'}, {'at': {'burg': 44}, 'cite': 'IV-0327'},
                                              {'at': {'burg': 163}, 'cite': 'IV-0335'}, {'at': {'burg': 315}, 'cite': 'IV-0338'}, {'at': {'burg': 313}, 'cite': 'IV-0342'},
                                              {'at': {'burg': 36}, 'cite': 'IV-0344'}, {'at': {'burg': 392}, 'cite': 'IV-0359'}]),
                                 ('outcome', 'the truce of Àth àrsaidh; the Severance'), ('cites', ['IV-0324', 'IV-0369', 'IV-0377', 'App.C The War of the Hills'])]),
        collections.OrderedDict([('name', None), ('name_en', 'the forerunners: strikes, the stoppage and the first bloodshed'), ('date', 'AE 77–148'),
                                 ('battles', [{'at': {'burg': 44}, 'cite': 'IV-0166'}, {'at': {'burg': 415}, 'cite': 'IV-0239'}, {'at': {'burg': 27}, 'cite': 'IV-0263'},
                                              {'at': {'burg': 354}, 'cite': 'IV-0274'}, {'at': {'province': 76}, 'cite': 'IV-0306'}]),
                                 ('cites', ['IV-0165', 'IV-0270', 'IV-0301', 'IV-0308'])]),
        collections.OrderedDict([('name', None), ('name_en', 'the Company and the raiders'), ('date', 'AE 16–47'),
                                 ('battles', [{'at': {'marker': 25}, 'cite': 'IV-0050'}, {'at': {'marker': 26}, 'cite': 'IV-0108'}, {'at': {'burg': 126}, 'cite': 'IV-0109'}]),
                                 ('cites', ['IV-0050', 'IV-0108', 'IV-0109'])]),
    ]
    d['arms'] = [
        collections.OrderedDict([('polity', 'council'), ('blazon', None), ('note', 'The custody\'s seal went out of use under the humans; no arms of the council are recorded. The kingdom cut its arms again from the old seal in SE 4.'), ('cites', ['App.J §I', 'V-0015b'])]),
        collections.OrderedDict([('polity', 'administration'), ('blazon', None), ('shield', 'heater (rounded foot)'), ('note', 'The Residency and the Company sealed with their own devices, not described; the Administration\'s district seals were cut in the humans\' manner, on a shield with a rounded foot.'), ('cites', ['App.J §I'])]),
        collections.OrderedDict([('polity', 'north'), ('blazon', None), ('shield', 'heater'), ('note', 'The human towns\' old seals, later copied into the roll for the Tuathaich towns.'), ('cites', ['V-0080a', 'App.J §V'])]),
        collections.OrderedDict([('polity', 'silver-guild'), ('blazon', None), ('note', 'No arms recorded.'), ('cites', ['App.J §I'])]),
    ]
    d['notes']['polities'] = collections.OrderedDict([
        ('council', 'The custodians gave the strangers leave, signed their treaty in a tongue they could not read, and watched their tally ignored, their Law lapse and their hall locked. The council made in the forest at Cnoc bheag fought the war that ended the age, and now sits in Cathair dhearg with the country from the hills to every coast in its hand. It will stand its companies down in the spring and make itself a kingdom.'),
        ('north', 'The human families left on the island, a few thousand, march north under the council\'s safe-conduct into the country of the old concession. Cathair gheal and Muileann àrsaidh kept out of the war; Baile Mòr ruadh receives the columns. They are about to be called the Tuathaich.'),
        ('silver-guild', 'The refiners of Muileann chiar kept their seam in their own hands through the whole age, by ledger, by compact and at last by rifle. They sold bar silver to the Company at their own price and paid the raiders in it for guns.'),
        ('administration', 'The Commissioners governed from the Residency by districts drawn for the pits, the customs and the Levy, and the Company grew into the office. The last of them locked out the custodians and flew an iron bird over the coal country. He sailed from Cuan shean for an Tìr Thall and was not heard of again.'),
    ])
    d['notes']['burgs'] = collections.OrderedDict([
        ('27', 'Ros dhomhain: the Residency on the rise above it, the Company\'s quays, the chapel of the Mission; its harbour quarter opened its gates to the council in the last autumn of the war.'),
        ('354', 'Muileann chrom: the Company\'s pit-town, the overseers\' staff that went from father to son to daughter, and the store the war began at.'),
        ('44', 'Baile thais: the town of the first strike, the Lamp-Watch and the book of complaints.'),
        ('476', 'Cathair gheal: the humans\' market town of the concession, which kept its gates and asked to be left alone.'),
        ('419', 'Muileann chiar: the silver town, the one place the rising took nothing, because the humans had never held anything there.'),
        ('282', 'Cuan shean: where the humans came ashore in the first winter, and where the last Commissioner took ship.'),
    ])
    return s.finish()
