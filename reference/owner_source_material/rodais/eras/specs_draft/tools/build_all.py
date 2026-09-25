"""Build, validate and write every era spec draft: python3 build_all.py [I II ...]"""
import importlib
import json
import sys
import collections
import common

ages = sys.argv[1:] or common.AGES
summary = collections.OrderedDict()
for age in ages:
    mod = importlib.import_module('age_%s' % age)
    spec = mod.build()
    errs, warns = common.validate(spec, age)
    names = common.name_report()
    bad = [n for n in names if n['problems'] and n['kind'] != 'person']
    persons = [n for n in names if n['problems'] and n['kind'] == 'person']
    spec['validation'] = collections.OrderedDict([
        ('errors', errs), ('warnings', warns),
        ('dia_thiris_names_checked', len(names)),
        ('dia_thiris_name_problems', bad),
        ('canon_personal_names_reported', [dict(n, note='a canon personal name, kept as spelled; rodais_engine reports personal names and does not exempt them') for n in persons]),
        ('checks', 'every burg, province, route and marker id is in Rodos_finished.map; every annals id is in '
                   'legendarium/annals_dated.json; every province 1-123 has a polity; every master route and marker is '
                   'classified present or absent; every Dia-thìris name registered is unchanged by rodais_engine.normalize() '
                   'and clean under check_agreement() (Old Ones\' roots are checked for normalize only).'),
    ])
    path = common.write(spec, age)
    summary[age] = dict(burgs=len(spec['burgs']), new_burgs=len(spec['new_burgs']), polities=[p['name_en'] for p in spec['polities']],
                        markers=len(spec['markers']['master']) + len(spec['markers']['new']),
                        routes=len(spec['routes']['master']) + len(spec['routes']['new']),
                        errors=len(errs), warnings=len(warns), name_problems=len(bad))
    print(age, json.dumps(summary[age], ensure_ascii=False))
    for e in errs[:40]:
        print('  ERR', e)
    for w in warns[:10]:
        print('  warn', w)
    for b in bad:
        print('  NAME', b)
