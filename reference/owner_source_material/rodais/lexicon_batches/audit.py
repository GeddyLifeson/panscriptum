"""
audit.py -- consistency and archaism audit of the Dia-thìris dictionary, written as a reviewable patch.

    python audit.py            (from this folder)

Reads ../LEXICON.json (the 5,005 original entries, ids not starting "f-") and every out_NN.json here,
applies the fixes below to a working copy, and writes audit_patch.json: the difference between the data
as it stands and the data as it should be. Nothing else is touched; merge_lexicon.py applies the patch
after loading and before writing. Re-running this script rebuilds the patch from scratch.

Patch format (audit_patch.json):

    {"edit": [{"id": ..., "set": {field: new}, "unset": [field], "old": {field: old}, "why": [...]}],
     "add":  [{...a full new entry..., "why": "..."}],
     "drop": [{"id": ..., "why": "..."}],
     "counts": {category: n}}

"old" is only for review (and lets the merge warn if the data changed under the patch). "why" starts
with the fix category:

  1 case      headwords and English in lower case except proper nouns (peoples, languages, faiths,
              days, months, feasts, God); full sentences (phrases ending . ? !) keep sentence case
  2 verbs     every verb: rod = root, vn = verbal noun, English "To x" -> "x"; the original
              lexicon's verbal-noun phrases ("Bhith aig") stay as rod with the verb root in root
  3 peoples   nationality / people / region words the batches skipped become entries
  4 conflict  one gender / plural / genitive / verbal noun per word; one translation per sense
  5a loan     new kennings for things that came in from ~1800 where Scottish Gaelic simply borrows
              the word become plain loans (the original lexicon's kennings are left alone)
  5b old      late loans for things known before 1800 give way to the old native word ("was" keeps
              the old form)
  7 sense     main senses of very common words that the original lexicon lacked (iron the metal)
  6 check     every changed or added form passes normalize() unchanged; caol-le-caol breaches are
              listed (loanwords and names the engine reports as irregular are kept)
"""
import collections
import copy
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import rodais_engine as R  # noqa: E402

ROD_FIELDS = ('rod', 'pl', 'gen', 'root', 'vn', 'comp')
CASE_FIELDS = ('en', 'rod', 'pl', 'gen', 'root', 'vn', 'comp', 'scots')


# ----------------------------------------------------------------------------------------------
# loading

def load():
    base = json.load(open(os.path.join(HERE, 'LEXICON_5005.json'), encoding='utf-8'))  # the original lexicon, before the merge
    orig = [e for e in base['entries'] if not str(e.get('id', '')).startswith('f-')]
    new, skips = [], []
    for f in sorted(glob.glob(os.path.join(HERE, 'out_*.json'))):
        tag = os.path.basename(f)[4:6]
        for e in json.load(open(f, encoding='utf-8')):
            if e.get('skip'):
                skips.append(dict(e, _file=tag))
            else:
                new.append(dict(e, _file=tag))
    return orig, new, skips


# ----------------------------------------------------------------------------------------------
# the working copy and the record of why each thing changed

class Work:
    def __init__(self, orig, new, skips):
        self.before = {e['id']: copy.deepcopy(e) for e in orig + new}
        self.orig_ids = {e['id'] for e in orig}
        self.E = {e['id']: copy.deepcopy(e) for e in orig + new}
        self.order = [e['id'] for e in orig + new]
        self.skips = skips
        self.why = collections.defaultdict(list)
        self.adds = []
        self.drops = {}
        self.counts = collections.Counter()

    def is_orig(self, i):
        return i in self.orig_ids

    def live(self):
        return [self.E[i] for i in self.order if i not in self.drops] + self.adds

    def set(self, i, cat, why, **fields):
        e = self.E[i]
        changed = False
        for k, v in fields.items():
            if v is None:
                if k in e:
                    del e[k]
                    changed = True
            elif e.get(k) != v:
                e[k] = v
                changed = True
        if changed:
            if not any(w.startswith(cat + ':') for w in self.why[i]) or cat not in ('1 case', '2 verbs'):
                self.why[i].append('%s: %s' % (cat, why))
            self.counts[cat] += 1
        return changed

    def drop(self, i, cat, why):
        if i not in self.drops:
            self.drops[i] = '%s: %s' % (cat, why)
            self.counts[cat] += 1

    def add(self, entry, cat, why):
        ids = {x for x in self.E} | {a['id'] for a in self.adds}
        base_id, n = entry['id'], 1
        while entry['id'] in ids:
            n += 1
            entry['id'] = '%s%d' % (base_id, n)
        entry = dict(entry)
        entry['_why'] = '%s: %s' % (cat, why)
        self.adds.append(entry)
        self.counts[cat] += 1
        return entry


def by_id(W, i):
    return W.E.get(i) or next((a for a in W.adds if a['id'] == i), None)


# ----------------------------------------------------------------------------------------------
# 1. case

PROPER_ORIG = {'a1-monday', 'a1-tuesday', 'a1-wednesday', 'a1-thursday', 'a1-friday', 'a1-saturday',
               'a1-sunday', 'a1-january', 'a1-february', 'a1-march', 'a1-april', 'a1-may', 'a1-june',
               'a1-july', 'a1-august', 'a1-september', 'a1-october', 'a1-november', 'a1-december',
               'a2-christmas', 'a2-new-year'}
# Dia-thìris words that are capitalised wherever they stand
PROPER_WORDS = {'Dia', 'Dhia', 'Crìosd', 'Dia-thìr', 'Dia-thìris', 'Dia-thìreach', 'Alba', 'Èirinn', 'Beurla', 'Gàidhlig',
                'Nollaig', 'Càisc', 'Sasainn', 'Sasannach'}
# English of proper-noun batch entries that English writes in lower case all the same
LOWER_EN = {'doomsday', 'mayday', 'wop', 'westerner', 'southerner', 'northerner', 'occidental'}
ARTICLES = re.compile(r"^(An t-|Am |An |A' |Na h-|Na )")


def lc_first(s, english=False):
    """Lower-case the first letter unless the first word is an acronym / has inner capitals / is English 'I'."""
    if not s or not s[0].isupper():
        return s
    first = re.split(r"[\s(]", s, 1)[0]
    if english and first in ('I', "I'm", 'I’m', "I've", 'I’ve', "I'd", 'I’d', "I'll", 'I’ll'):
        return s
    if not english and first.rstrip(',.!?') in PROPER_WORDS:
        return s
    if any(c.isupper() for c in first[1:]):
        return s
    return s[0].lower() + s[1:]


def is_sentence(e):
    return e.get('pos') in ('phrase', 'interj') and any(
        (e.get(k) or '').rstrip().endswith(('.', '?', '!', '…')) and ' ' in (e.get(k) or '') for k in ('en', 'rod'))


def is_proper(W, e):
    if W.is_orig(e['id']):
        return e['id'] in PROPER_ORIG
    if e.get('pos') in ('interj', 'phrase'):
        return False
    words = e['rod'].split()
    if words and words[0] in ('an', 'am', 'air', 'gach', 'na') and len(words) > 1:
        words = words[1:]
    return bool(words) and words[0][:1].isupper()


def cap_en(s):
    return s[0].upper() + s[1:] if s else s


def fix_case(W):
    for i in list(W.order):
        e = W.E[i]
        if is_sentence(e):
            continue
        if is_proper(W, e):
            upd = {}
            if W.is_orig(i):          # months: the article is lower case (am Faoilleach)
                for k in ('rod', 'pl'):
                    if e.get(k) and ARTICLES.match(e[k]):
                        upd[k] = e[k][0].lower() + e[k][1:]
            elif e['en'].lower() not in LOWER_EN and e['en'][:1].islower():
                upd['en'] = cap_en(e['en'])
            if upd:
                W.set(i, '1 case', 'proper noun: English capitalised, article lower case', **upd)
            continue
        upd = {k: lc_first(e[k], k == 'en') for k in CASE_FIELDS
               if isinstance(e.get(k), str) and lc_first(e[k], k == 'en') != e[k]}
        if upd:
            W.set(i, '1 case', 'lower case except proper nouns', **upd)


# ----------------------------------------------------------------------------------------------
# 2. verbs

VN_OVERRIDE = {       # an original rod that is the root or a wrong verbal noun
    'a2-to-complain': 'gearan',
}


def fix_verbs(W):
    for i in list(W.order):
        if not W.is_orig(i):
            continue
        e = W.E[i]
        if e.get('pos') != 'v':
            continue
        upd = {}
        en = re.sub(r'^[Tt]o ', '', e['en'])
        if en != e['en']:
            upd['en'] = en
        rod, root = e['rod'], e.get('root', '')
        if ' ' not in rod and ' ' not in root and ('-' not in rod or '-' in root):
            # a single verbal noun: rod becomes the root, the verbal noun moves to vn
            upd.update(rod=root, vn=VN_OVERRIDE.get(i, rod))
            why = 'rod = root (%s), vn = verbal noun (%s)' % (root, upd['vn'])
        elif ' ' in root:
            # the root is given as a whole phrase (cuir eòlas air): rod = that phrase, root = its verb
            upd.update(rod=root, root=root.split()[0], vn=rod)
            why = 'rod = root phrase (%s), vn = verbal-noun phrase (%s)' % (root, rod)
        else:
            # a verbal-noun phrase with a one-word root (Bhith aig, Urram a thoirt do, Gairm-sreinge)
            upd.update(vn=rod, sense='verbal-noun phrase; the verb is %s' % root)
            why = 'verbal-noun phrase kept as rod, verb root %s' % root
        W.set(i, '2 verbs', why, **upd)


# ----------------------------------------------------------------------------------------------
# 3. peoples, nationalities, regions the batches skipped

PEOPLES = {
    # en: (rod, plural, noun sense, adjective sense, language, flags)
    'turkish': ('Turcach', 'Turcaich', 'a Turk', 'of Turkey or the Turks', 'Turcais', {}),
    'indians': ('Innseanach', 'Innseanaich', 'people of India (plural: Innseanaich)', None, None, {'plural_en': True}),
    'brazilian': ('Braisileach', 'Braisilich', 'a Brazilian', 'of Brazil', None, {}),
    'egyptian': ('Èipheiteach', 'Èipheitich', 'an Egyptian', 'of Egypt', None, {}),
    'swedish': ('Suaineach', 'Suainich', None, 'of Sweden', 'Suainis', {'n': False}),
    'swiss': ('Eilbheiseach', 'Eilbheisich', 'a Swiss person', 'of Switzerland', None, {}),
    'germans': ('Gearmailteach', 'Gearmailtich', 'people of Germany (plural: Gearmailtich)', None, None, {'plural_en': True}),
    'ukrainian': ('Ucràineach', 'Ucràinich', 'a Ukrainian', 'of Ukraine', None, {}),
    'thai': ('Tàidheach', 'Tàidhich', 'a Thai person', 'of Thailand', None, {}),
    'iranian': ('Ioranach', 'Ioranaich', 'an Iranian', 'of Iran', None, {}),
    'russians': ('Ruiseanach', 'Ruiseanaich', 'people of Russia (plural: Ruiseanaich)', None, None, {'plural_en': True}),
    'welsh': ('Cuimreach', 'Cuimrich', 'a Welsh person', 'of Wales', 'Cuimris', {}),
    'caribbean': ('Caraibeach', None, None, 'of the Caribbean', None, {'n': False}),
    'hindi': (None, None, None, None, 'Hindi', {'n': False, 'adj': False}),
    'philippine': ('Filipineach', None, None, 'of the Philippines', None, {'n': False}),
    'nazi': ('Nàsach', 'Nàsaich', 'a Nazi', 'of the Nazis', None, {}),
    'nazis': ('Nàsach', 'Nàsaich', 'the Nazis (plural: Nàsaich)', None, None, {'plural_en': True}),
    'mormon': ('Mormonach', 'Mormonaich', 'a Mormon', 'of the Mormon church', None, {}),
    'argentine': ('Argantaineach', 'Argantainich', 'an Argentine', 'of Argentina', None, {}),
    'yankee': ('Ameireaganach', 'Ameireaganaich', 'a Yankee, an American (informal)', None, None, {'adj': False}),
    'soviets': ('Sòbhieteach', 'Sòbhietich', 'the Soviets (plural: Sòbhietich)', None, None, {'plural_en': True}),
    'romanian': ('Romàinianach', 'Romàinianaich', 'a Romanian', 'of Romania', None, {}),
    'baltic': ('Baltach', None, None, 'of the Baltic', None, {'n': False}),
    'colombian': ('Coloimbianach', 'Coloimbianaich', 'a Colombian', 'of Colombia', None, {}),
    'jamaican': ('Diameucanach', 'Diameucanaich', 'a Jamaican', 'of Jamaica', None, {}),
    'kenyan': ('Ceinianach', 'Ceinianaich', 'a Kenyan', 'of Kenya', None, {}),
    'antarctic': ('Antartaigeach', None, None, 'of the far south, antarctic', None, {'n': False}),
    'aussie': ('Astràilianach', 'Astràilianaich', 'an Australian (informal)', 'Australian (informal)', None, {}),
    'brits': ('Breatannach', 'Breatannaich', 'Britons (plural: Breatannaich)', None, None, {'plural_en': True}),
    'mexicans': ('Meagsaganach', 'Meagsaganaich', 'people of Mexico (plural: Meagsaganaich)', None, None, {'plural_en': True}),
    'texans': ('Teacsach', 'Teacsaich', 'people of Texas (plural: Teacsaich)', None, None, {'plural_en': True}),
    'arabian': ('Arabach', None, None, 'of Arabia', None, {'n': False}),
    'serbian': ('Sèirbeach', None, None, 'of Serbia', None, {'n': False}),
    'somali': ('Somàilianach', 'Somàilianaich', 'a Somali', 'of Somalia', None, {}),
    'ethiopian': ('Etiòpach', 'Etiòpaich', 'an Ethiopian', 'of Ethiopia', None, {}),
    'tibetan': ('Tibeiteach', 'Tibeitich', 'a Tibetan', 'of Tibet', None, {}),
    'sunni': ('Sunnach', 'Sunnaich', 'a Sunni Muslim', 'of the Sunni branch of Islam', None, {}),
    'israelis': ('Iosaraileach', 'Iosarailich', 'people of Israel (plural: Iosarailich)', None, None, {'plural_en': True}),
    'venezuelan': ('Bheiniseuèileach', 'Bheiniseuèilich', 'a Venezuelan', 'of Venezuela', None, {}),
    'catalan': ('Catalanach', 'Catalanaich', 'a Catalan', 'of Catalonia', 'Catalanais', {}),
    'libyan': ('Libianach', 'Libianaich', 'a Libyan', 'of Libya', None, {}),
    'peruvian': ('Pearùthach', 'Pearùthaich', 'a Peruvian', 'of Peru', None, {}),
    'trojan': ('Tròidheach', 'Tròidhich', 'a Trojan', 'of Troy', None, {}),
    'trojans': ('Tròidheach', 'Tròidhich', 'the Trojans (plural: Tròidhich)', None, None, {'plural_en': True}),
    'zionist': ('Sìonach', 'Sìonaich', 'a Zionist', 'of Zionism', None, {}),
    'hun': ('Hùnach', 'Hùnaich', 'a Hun', None, None, {'adj': False}),
    'latina': ('Laideannach', 'Laideannaich', 'a woman of Latin American descent', None, None, {'adj': False}),
    'latinos': ('Laideannach', 'Laideannaich', 'people of Latin American descent (plural: Laideannaich)', None, None, {'plural_en': True}),
    'kurds': ('Cùrdach', 'Cùrdaich', 'the Kurds (plural: Cùrdaich)', None, None, {'plural_en': True}),
    'spaniards': ('Spàinnteach', 'Spàinntich', 'people of Spain (plural: Spàinntich)', None, None, {'plural_en': True}),
    'haitian': ('Haitianach', 'Haitianaich', 'a Haitian', 'of Haiti', None, {}),
    'hispanics': ('Spàinnteach', 'Spàinntich', 'Spanish-speaking people (plural: Spàinntich)', None, None, {'plural_en': True}),
    'sikh': ('Sìceach', 'Sìcich', 'a Sikh', 'of the Sikh faith', None, {}),
    'taiwanese': ('Taidhbheanach', 'Taidhbheanaich', 'a Taiwanese person', 'of Taiwan', None, {}),
    'croatian': ('Cròthaiseach', 'Cròthaisich', 'a Croatian', 'of Croatia', None, {}),
    'saharan': ('Saharach', None, None, 'of the Sahara', None, {'n': False}),
    'sanskrit': (None, None, None, None, 'Sanscrait', {'n': False, 'adj': False}),
    'siberian': ('Sibèireach', 'Sibèirich', 'a Siberian', 'of Siberia', None, {}),
    'venetian': ('Bheinisianach', 'Bheinisianaich', 'a Venetian', 'of Venice', None, {}),
    'sudanese': ('Sùdanach', 'Sùdanaich', 'a Sudanese person', 'of Sudan', None, {}),
    'parisian': ('Parasach', 'Parasaich', 'a Parisian', 'of Paris', None, {}),
    'amish': ('Aimiseach', 'Aimisich', 'the Amish (plural: Aimisich)', 'of the Amish', None, {}),
    'burmese': ('Burmach', 'Burmaich', 'a Burmese person', 'of Burma', None, {}),
    'algerian': ('Aildireach', 'Aildirich', 'an Algerian', 'of Algeria', None, {}),
    'appalachian': ('Apalàisianach', None, None, 'of the Appalachians', None, {'n': False}),
    'crimean': ('Criomach', None, None, 'of the Crimea', None, {'n': False}),
    'spartans': ('Spartach', 'Spartaich', 'the Spartans (plural: Spartaich)', None, None, {'plural_en': True}),
    'aryan': ('Àirianach', 'Àirianaich', 'an Aryan (the old people; the racist use is 19th-century)', 'of the Aryans', None, {}),
    'himalayan': ('Himealàidheach', None, None, 'of the Himalayas', None, {'n': False}),
    'polish': ('Pòlainneach', 'Pòlainnich', 'a Pole', 'of Poland', 'Pòlainnis', {}),
}


def fix_peoples(W):
    skip_by_en = {s['en']: s for s in W.skips}
    for en, (rod, pl, sn, sa, lang, fl) in PEOPLES.items():
        s = skip_by_en.get(en)
        rank = s['rank'] if s else next((e['rank'] for e in W.E.values() if e['en'] == en and 'rank' in e), 16000)
        rows = []
        if rod and fl.get('adj', True) and not fl.get('plural_en') and sa:
            rows.append(('adj', rod, {}, sa))
        if rod and fl.get('n', True) and sn:
            rows.append(('n', rod, {'g': 'm', 'pl': pl, 'gen': pl}, sn))
        if lang:
            rows.append(('n', lang, {'g': 'f', 'gen': lang}, 'the %s language' % cap_en(en)))
        k = collections.Counter()
        for pos, r, extra, sense in rows:
            k[pos] += 1
            entry = {'id': 'f-%s-%s%s' % (en, pos, '' if k[pos] == 1 else k[pos]), 'en': cap_en(en), 'rank': rank,
                     'sense': sense, 'pos': pos, 'rod': r}
            entry.update(extra)
            why = ('skipped in out_%s as "%s"; nationalities and peoples are entries' % (s['_file'], s['skip'])
                   if s else 'the nationality sense was left out')
            W.add(entry, '3 peoples', why)


# ----------------------------------------------------------------------------------------------
# 5a. new kennings -> plain loans (things from ~1800 on, where Scottish Gaelic just borrows the word)

MASS = {'jazz', 'funk', 'bluegrass', 'bebop', 'vaudeville', 'napalm', 'progesterone', 'chloroform', 'propane',
        'mitochondria', 'octane', 'margarine', 'marge', 'testosterone', 'aerospace', 'pepperoni', 'penicillin',
        'chiropractic', 'telepathy', 'sabotage', 'chemotherapy', 'chemo', 'shrapnel', 'flak', 'polyester', 'toner',
        'tomography', 'peroxide', 'polystyrene', 'polyethylene', 'hypnosis', 'rayon', 'crochet', 'tarmac', 'epoxy',
        'kerosene', 'ethernet', 'manicure', 'cabaret'}
LOANS = {  # id: rod override (None = the scots form)
    'f-jazz-n': None, 'f-jet-n2': None, 'f-inning-n': None, 'f-quarterback-n': None, 'f-marina-n1': None,
    'f-funk-n2': None, 'f-bikini-n': None, 'f-ufo-n': 'UFO', 'f-glitch-n': None, 'f-emoji-n': None,
    'f-paparazzi-n': None, 'f-cabaret-n': None, 'f-bluegrass-n': None, 'f-taser-n': None, 'f-mohawk-n': None,
    'f-ombudsman-n': None, 'f-perm-n': None, 'f-hologram-n': None, 'f-slalom-n': None, 'f-pinball-n': None,
    'f-lumen-n': None, 'f-magneto-n': None, 'f-shortstop-n': None, 'f-tarmac-n': None, 'f-aerosol-n': None,
    'f-tutu-n': None, 'f-resistor-n': None, 'f-tampon-n': None, 'f-epidural-n': None, 'f-vaudeville-n': None,
    'f-bungee-n': None, 'f-napalm-n': None, 'f-neutrino-n': None, 'f-bebop-n': None, 'f-matinee-n': None,
    'f-stent-n': None, 'f-progesterone-n': None, 'f-crematorium-n': None, 'f-chloroform-n': None,
    'f-android-n': None, 'f-hipster-n': None, 'f-propane-n': None, 'f-glider-n': None, 'f-mitochondria-n': None,
    'f-crisp-n': None, 'f-octane-n': None, 'f-trampoline-n': None, 'f-youtubers-n': 'iùtiùbar',
    'f-youtuber-n': None, 'f-capacitor-n': None, 'f-anode-n': None, 'f-cathode-n': None, 'f-electrode-n': None,
    'f-margarine-n': None, 'f-marge-n': None, 'f-antigen-n': None, 'f-testosterone-n': None,
    'f-milligram-n': None, 'f-millimeter-n': None, 'f-periscope-n': None, 'f-aerospace-n': None,
    'f-lollipop-n': None, 'f-lolly-n': None, 'f-pepperoni-n': None, 'f-penicillin-n': None, 'f-ohm-n': None,
    'f-manicure-n': None, 'f-chiropractic-n': None, 'f-telepathy-n': None, 'f-polytechnic-n': None,
    'f-cinematographer-n': None, 'f-doughnut-n': None, 'f-dynamo-n': None, 'f-cursor-n': None,
    'f-ticker-n2': None, 'f-locomotive-n': None, 'f-transistor-n': None, 'f-sabotage-n': None,
    'f-chemotherapy-n': None, 'f-chemo-n': None, 'f-shrapnel-n': None, 'f-flak-n1': None,
    'f-polyester-n': None, 'f-bureaucrat-n': None, 'f-toner-n': None, 'f-tomography-n': None,
    'f-blogger-n1': None, 'f-rickshaw-n': None, 'f-commuter-n': None, 'f-peroxide-n': None, 'f-disk-n': None,
    'f-gyro-n': None, 'f-tux-n': None, 'f-polystyrene-n': None, 'f-polyethylene-n': None, 'f-hypnosis-n': None,
    'f-hypnotize-v': None, 'f-cyborg-n': None, 'f-gamers-n': None, 'f-carburetor-n': None, 'f-gasket-n': None,
    'f-ethernet-n': None, 'f-inverter-n': None, 'f-psychedelic-adj': None, 'f-browser-n1': None,
    'f-ukulele-n': None, 'f-rayon-n': None, 'f-hack-v2': 'hac', 'f-crochet-n': None, 'f-smoothie-n': None,
    'f-triathlon-n': 'triathlon', 'f-quark-n': None, 'f-epoxy-n': None, 'f-kamikaze-n': None, 'f-vape-n': None,
    'f-kerosene-n': None, 'f-synthesizer-n': None,
}
VOWELS = set('aeiouàèìòù')


def loan_plural(rod):
    w = rod.lower()
    if w.endswith('idh'):
        return rod + 'ean'
    if w[-1] == 'a':
        return rod + 'ichean'
    if w[-1] in VOWELS:
        return rod + 'than'
    last = [c for c in w if c in VOWELS][-1]
    return rod + ('ean' if last in 'eièì' else 'an')


def loan_vn(root):
    if root.endswith('aich'):
        return root[:-4] + 'achadh'
    if root.endswith('ich'):
        return root[:-3] + 'eachadh'
    return root + ('eadh' if [c for c in root if c in VOWELS][-1] in 'eièì' else 'adh')


def fix_loans(W):
    for i, override in LOANS.items():
        e = W.E[i]
        assert e.get('kenning'), i
        rod = override or R.normalize(e['scots'])
        if rod != 'UFO':
            rod = rod[0].lower() + rod[1:]
        upd = {'rod': rod, 'kenning': None, 'lit': None, 'scots': None, 'was': e['rod']}
        if e['pos'] == 'n':
            upd['g'] = 'm'
            upd['gen'] = rod
            upd['pl'] = None if e['en'] in MASS else loan_plural(rod)
        elif e['pos'] == 'v':
            upd.update(root=rod, vn=('hacadh' if rod == 'hac' else loan_vn(rod)))
        W.set(i, '5a loan', 'Scottish Gaelic borrows %s for this post-1800 thing; kenning %s dropped'
              % (e['scots'], e['rod']), **upd)


# ----------------------------------------------------------------------------------------------
# 5b. late loans for things known before 1800 -> the old native word

OLD = [  # (id, fields, why)
    ('a2-doctor', {'rod': 'lighiche', 'pl': 'lighichean'}, 'dotair is a late loan; lighiche is the old word (batches: doc, medic)'),
    ('a2-i-need-a-doctor', {'rod': 'tha feum agam air lighiche'}, 'doctor = lighiche'),
    ('c1-over-the-counter', {'rod': 'gun òrdugh-lighiche'}, 'doctor = lighiche'),
    ('c2-court-clerk', {'rod': 'clèireach cùirte', 'pl': 'clèirich cùirte'}, 'clàrc is a late loan; clèireach (as out_06 clerk)'),
    ('b1-character-story', {'rod': 'pearsa', 'pl': 'pearsachan'}, 'caractar is a late loan; pearsa, a person in a tale or play'),
    ('f-character-n2', {'rod': 'pearsa', 'pl': 'pearsachan', 'gen': 'pearsa'}, 'caractar is a late loan; pearsa (as out_09 persona)'),
    ('a2-teacher', {'rod': 'oide', 'pl': 'oidean'}, 'tidsear is a late loan; oide, the teacher/tutor of Classical Gaelic (as Tutor)'),
    ('a2-baker', {'rod': 'fuineadair', 'pl': 'fuineadairean'}, 'bèicear is a late loan; fuineadair'),
    ('a1-bag', {'rod': 'poca', 'pl': 'pocannan'}, 'baga is a late loan; poca (cha sheas poca falamh)'),
    ('a2-luggage', {'rod': 'treallaich', 'g': 'f'}, 'bagaist is a late loan; treallaich (as out_08 baggage)'),
    ('a1-breakfast', {'rod': 'biadh-maidne', 'pl': None}, 'bracaist is a late loan; biadh-maidne'),
    ('a2-to-have-breakfast', {'rod': 'gabh biadh-maidne', 'vn': 'gabhail biadh-maidne'}, 'breakfast = biadh-maidne'),
    ('a2-game', {'rod': 'cluiche', 'pl': 'cluichean'}, 'geama is a late loan; cluiche'),
    ('a2-board-game', {'rod': 'cluiche-bùird', 'pl': 'cluichean-bùird'}, 'game = cluiche'),
    ('a2-party', {'rod': 'cuirm', 'pl': 'cuirmean', 'g': 'f'}, 'pàrtaidh (a celebration) is a late loan; cuirm (as out_03 celebration)'),
    ('a1-uncle', {'rod': 'bràthair-athar', 'pl': 'bràithrean-athar', 'sense': "uncle: father's brother (mother's brother: bràthair-màthar)"}, 'uncail is a late loan'),
    ('a1-aunt', {'rod': 'piuthar-athar', 'pl': 'peathraichean-athar', 'sense': "aunt: father's sister (mother's sister: piuthar-màthar)"}, 'antaidh is a late loan'),
    ('a1-dress', {'rod': 'gùn', 'pl': 'gùintean', 'g': 'm'}, 'dreasa is a late loan; gùn, the old borrowing (as out_08 gown)'),
    ('a1-lamp', {'rod': 'lòchran', 'pl': 'lòchrain'}, 'lampa is a late loan; lòchran (as out_08 torch, out_10 lantern)'),
    ('a1-orange-color', {'rod': 'dearg-bhuidhe'}, 'the colour has the native dearg-bhuidhe (as out_02 orange adj.); orains stays for the fruit'),
]
OLD_ADD = [
    {'id': 'f-uncle-n2', 'en': 'uncle', 'rank': 1893, 'sense': "uncle: mother's brother", 'pos': 'n',
     'rod': 'bràthair-màthar', 'g': 'm', 'pl': 'bràithrean-màthar', 'gen': 'bràthar-màthar'},
    {'id': 'f-aunt-n2', 'en': 'aunt', 'rank': 2575, 'sense': "aunt: mother's sister", 'pos': 'n',
     'rod': 'piuthar-màthar', 'g': 'f', 'pl': 'peathraichean-màthar', 'gen': 'peathar-màthar'},
]


def fix_old(W):
    for i, fields, why in OLD:
        e = W.E[i]
        fields = dict(fields)
        fields['was'] = e['rod']
        W.set(i, '5b old', why, **fields)
    for a in OLD_ADD:
        W.add(dict(a), '5b old', 'the other side of the family, now that uncle/aunt are the native kin terms')


# ----------------------------------------------------------------------------------------------
# 4. conflicts

GENDER = {  # rod: gender for the whole word, or {english of the homonym: gender}
    'dealbh': 'm', 'sreath': 'f', 'roghainn': 'f', 'meur': 'm', 'carragh': 'f', 'cruinne': 'f', 'buidheann': 'f',
    'cumhachd': 'f', 'daingneach': 'f', 'boinne': 'f', 'eas-aonta': 'm', 'caitheamh': 'm', 'ribe': 'f',
    'steall': 'f', 'co-bhann': 'f', 'laoidh': 'm', 'pairilis': 'f', 'fleasc': 'f', 'mì-earbsa': 'f',
    'cuibhrig': 'f', 'snèap': 'f', 'breisleach': 'f', 'sùith': 'm', 'tairbeart': 'm',
    'bile': {'flange': 'f', 'bezel': 'f'},   # the lip/rim word is feminine; bill (the loan) stays masculine
    'gas': {'stalk': 'f'},                   # the stalk word is feminine; gas (the loan) stays masculine
}
HOMONYMS = {  # rod: groups of English headwords that are different words spelled alike
    'tì': [{'tee'}], 'bile': [{'bill (utility)', 'bill (proposed law)', 'bill'}], 'giall': [{'hostage'}],
    'coire': [{'fault', 'foul'}], 'gas': [{'gas'}], 'àth': [{'kiln'}], 'breac': [{'smallpox', 'pox'}],
    'meas': [{'fruit'}], 'lòn': [{'pond'}], 'ball': [{'ball'}], 'clò': [{'press'}], 'preas': [{'bush', 'scrub', 'shrub'}],
    'arm': [{'weapon'}], 'bus': [{'pout'}],
}
PL_OVERRIDE = {'atharrachadh': 'atharrachaidhean', 'dìsne': 'dìsnean', 'fabhra': 'fabhraidhean', 'cionta': 'ciontan',
               'cùl': 'cùlan', 'gùn': 'gùintean', 'snaidheadh': 'snaidhidhean',
               'duine-uasal': 'daoine-uaisle'}
GEN_OVERRIDE = {'gùn': 'gùin', 'cur às': None, 'togail': 'togail'}
VN = {  # root: the one verbal noun (entries whose English is listed keep their own)
    'ruig': 'ruigsinn', 'brùth': 'brùthadh', 'malairtich': 'malairteachadh', 'lorg': 'lorg', 'tilg': 'tilgeil',
    'cuir iongnadh air': 'cur iongnadh air', 'scrios': 'scrios', 'iomair': 'iomradh',
    'gabh leisceul': 'gabhail leisceul', 'clisc': 'clisceadh', 'leòn': 'leòn', 'claoidh': 'claoidh',
    'èalaidh': 'èaladh', 'gin': 'gineadh', 'beuc': 'beucail', 'drùidh': 'drùdhadh', 'tuislich': 'tuisleadh',
    'caisc': 'cascadh', 'crith': 'crith', 'tiomnaich': 'tiomnadh', 'itealaich': 'itealaich',
    'fàisnich': 'fàisneachadh', 'plosc': 'ploscadh',
}
RENAME = [  # (id, fields, why) -- one translation per sense
    ('f-yank-n', {'rod': 'Ameireaganach', 'pl': 'Ameireaganaich', 'gen': 'Ameireaganaich'}, 'spelled Ameireaganach everywhere else'),
    ('f-britons-n', {'rod': 'Breatannach', 'pl': 'Breatannaich', 'gen': 'Breatannaich'}, 'spelled Breatannach everywhere else (out_01 british)'),
    ('f-palestinians-n', {'rod': 'Palastaineach', 'pl': 'Palastainich', 'gen': 'Palastainich'}, 'spelled Palastaineach in out_05 palestinian'),
    ('f-olympian-n', {'rod': 'Oilimpeach', 'pl': 'Oilimpich', 'gen': 'Oilimpich'}, 'spelled Oilimpeach in out_03 olympic'),
    ('f-carton-n', {'rod': 'bogsa-cairt', 'pl': 'bogsaichean-cairt', 'gen': 'bogsa-cairt'}, 'box is bogsa in LEXICON.json'),
    ('f-caddy-n1', {'rod': 'bogsa-tì', 'pl': 'bogsaichean-tì', 'gen': 'bogsa-tì'}, 'box is bogsa in LEXICON.json'),
    ('f-headquarter-n', {'rod': 'prìomh oifis', 'pl': 'prìomh oifisean', 'gen': 'prìomh oifis'}, 'as LEXICON.json Headquarters'),
    ('f-blind-n', {'rod': 'scàil-uinneig', 'pl': 'scàilean-uinneig', 'gen': 'scàil-uinneig'}, 'as LEXICON.json Blinds (gen. uinneig)'),
    ('f-tattoos-n1', {'rod': 'dealbh-craicinn', 'lit': 'skin-picture'}, 'as out_05 tattoo'),
    ('f-telecom-n', {'rod': 'fios-cèine', 'lit': 'far-tidings'}, 'as out_07 telecommunications (same sense)'),
    ('f-lab-n', {'rod': 'ceàrdach-dheuchainn', 'kenning': True, 'lit': 'trial-smithy', 'scots': 'obair-lann',
                 'pl': 'ceàrdaichean-dheuchainn', 'gen': 'ceàrdaich-dheuchainn', 'g': 'f'},
     'obair-lann is a Scottish Gaelic coinage; the Dia-thìris kenning is out_07 ceàrdach-dheuchainn (labs)'),
    ('f-euros-n', {'rod': 'iùro'}, 'as out_05 euro'),
    ('f-smartphones-n', {'rod': 'scàthan-pòca', 'lit': 'pocket-mirror'}, 'as out_05 smartphone'),
    ('f-processors-n', {'rod': 'cridhe-iarainn', 'kenning': True, 'lit': 'iron-heart', 'scots': 'pròiseasar'},
     'as out_07 processor (the kenning LEXICON.json uses)'),
    ('f-pubs-n', {'rod': 'taigh-seinnse', 'gen': 'taigh-seinnse'}, 'as out_04 pub'),
    ('f-filmmakers-n', {'rod': 'dèanadair-scàile', 'lit': 'shadow-maker'}, 'as out_10 filmmaker'),
    ('f-detectors-n', {'rod': 'faire-iarainn', 'lit': 'iron-watch'}, 'as out_09 detector'),
    ('f-bots-n', {'rod': 'gille-lìn', 'kenning': True, 'lit': 'net-lad', 'scots': 'bot'}, 'as out_07 bot (the kenning LEXICON.json uses)'),
    ('f-superheroes-n', {'rod': 'sàr-laoch'}, 'as out_07 superhero'),
    ('f-wingers-n', {'rod': 'neach-sciathain'}, 'as out_11 winger'),
    ('f-regents-n', {'rod': 'leas-rìgh'}, 'as out_13 regent'),
    ('f-geeks-n', {'rod': 'nèard'}, 'as out_10 geek'),
    ('f-playlists-n', {'rod': 'rolla-òran'}, 'as out_10 playlist'),
    ('f-timelines-n', {'rod': 'sreath-ama'}, 'as out_04 timeline'),
    ('f-ads-n', {'rod': 'sanas-reic'}, 'as out_02 ad'),
    ('f-survivors-n', {'rod': 'marthanaiche'}, 'as out_06 survivor'),
    ('f-afterwards-adv', {'rod': 'às dèidh sin'}, 'as LEXICON.json After (às dèidh sin)'),
    ('f-meet-v2', {'rod': 'cuir eòlas air', 'root': 'cuir', 'vn': 'cur eòlas air'}, 'as LEXICON.json meet (someone new): cuir eòlas air'),
]
DROP = [
    ('f-orange-n', 'the fruit is orains in LEXICON.json (no attested native word; ubhal-òir is not one)'),
]


def fix_conflicts(W):
    for i, fields, why in RENAME:
        e = W.E.get(i)
        if e is None:
            raise SystemExit('RENAME: no entry %s' % i)
        # carry the plural/genitive along when the rod changes and they are not given
        if 'rod' in fields and e.get('pos') == 'n':
            other = next((x for x in W.live() if x is not e and x.get('pos') == 'n' and x['rod'] == fields['rod']), None)
            if other:
                for k in ('g', 'pl', 'gen'):
                    if k not in fields and other.get(k) and e.get(k):
                        fields[k] = other[k]
        W.set(i, '4 conflict', why, **fields)
    for i, why in DROP:
        W.drop(i, '4 conflict', why)
    for e in W.live():   # cum is "shape" (vn cumadh); "keep" is cùm (vn cumail)
        if e.get('pos') == 'v' and e.get('root') == 'cum' and (e.get('vn') or '').startswith('cumail'):
            extra = {'rod': 'cùm'} if e['rod'] == 'cum' else {}
            if 'the verb is cum' in (e.get('sense') or ''):
                extra['sense'] = e['sense'].replace('the verb is cum', 'the verb is cùm')
            W.set(e['id'], '4 conflict', 'the verb of cumail is cùm (cum is "shape")', root='cùm', **extra)

    live = [e for e in W.live()]
    # genders, plurals, genitives: one per word (homonyms apart)
    groups = collections.defaultdict(list)
    for e in live:
        if e.get('pos') != 'n':
            continue
        r = e['rod'].lower()
        en = e['en'].lower()
        sub = 0
        for n, s in enumerate(HOMONYMS.get(r, []), 1):
            if en in s:
                sub = n
        groups[(r, sub)].append(e)
    for (r, sub), L in groups.items():
        if len(L) < 2:
            continue
        L.sort(key=lambda e: (0 if W.is_orig(e['id']) else 1, e.get('_file', ''), e['id']))
        # gender
        g = GENDER.get(r)
        if isinstance(g, dict):
            for e in L:
                if e['en'].lower() in g and e.get('g') != g[e['en'].lower()]:
                    W.set(e['id'], '4 conflict', 'gender of %s is %s' % (r, g[e['en'].lower()]), g=g[e['en'].lower()])
        elif g is None and len({e.get('g') for e in L}) > 1:
            g = L[0].get('g')   # LEXICON.json first, then the oldest batch
        if isinstance(g, str):
            for e in L:
                if e.get('g') != g:
                    W.set(e['id'], '4 conflict', '%s is %s (one gender per word)' % (r, g), g=g)
        # plural: LEXICON.json's, else the commonest (ties: the oldest batch); only where an entry has one
        pls = [e['pl'] for e in L if e.get('pl')]
        if len({p.lower() for p in pls}) > 1:
            pl = PL_OVERRIDE.get(r)
            if not pl:
                op = [e['pl'] for e in L if W.is_orig(e['id']) and e.get('pl') and not R.check_agreement(e['pl'])]
                if op:
                    pl = op[0]
                else:
                    c = collections.Counter(p for p in pls if p.lower() != r)
                    best = max(c.values())
                    pl = next(p for p in pls if c.get(p) == best)
            for e in L:
                if e.get('pl') and e['pl'] != pl:
                    W.set(e['id'], '4 conflict', 'plural of %s is %s' % (r, pl), pl=pl)
        gens = [e['gen'] for e in L if e.get('gen')]
        if len({x.lower() for x in gens}) > 1:
            if r in GEN_OVERRIDE and GEN_OVERRIDE[r]:
                gen = GEN_OVERRIDE[r]
            else:
                c = collections.Counter(gens)
                best = max(c.values())
                gen = next(x for x in gens if c[x] == best)
            for e in L:
                if e.get('gen') and e['gen'] != gen:
                    W.set(e['id'], '4 conflict', 'genitive of %s is %s' % (r, gen), gen=gen)

    # one verbal noun per verb
    for e in live:
        if e.get('pos') != 'v':
            continue
        key = e['rod'] if e['rod'] in VN else (e.get('root') if e['rod'] == e.get('root') else None)
        want = VN.get(key)
        if want and e.get('vn') != want:
            W.set(e['id'], '4 conflict', 'verbal noun of %s is %s' % (e['rod'], want), vn=want)

    # near duplicates: a batch entry repeating an original one ("spend" caith = "spend (money)" caith)
    def base(en):
        return re.sub(r'\s*\(.*?\)', '', re.sub(r'^to ', '', en.lower())).strip()
    orig_keys = {}
    for e in W.live():
        if W.is_orig(e['id']):
            orig_keys.setdefault((base(e['en']), e['rod'].lower(), e.get('pos')), e['id'])
    for e in W.live():
        if not W.is_orig(e['id']) and e['id'] in W.E:
            k = (base(e['en']), e['rod'].lower(), e.get('pos'))
            if k in orig_keys:
                W.drop(e['id'], '4 conflict', 'repeats LEXICON.json %s (same English word, Dia-thìris and part of speech)'
                       % orig_keys[k])

    # exact duplicates: same English, same Dia-thìris, same part of speech
    seen = {}
    for e in W.live():
        k = (e['en'].lower(), e['rod'].lower(), e.get('pos'))
        if k in seen:
            if e['id'] in W.E:
                keep = by_id(W, seen[k])
                if e.get('sense') and e['sense'] not in (keep.get('sense') or '') and keep['id'] in W.E:
                    W.set(keep['id'], '4 conflict', 'took in the sense of its duplicate %s' % e['id'],
                          sense='%s; %s' % (keep['sense'], e['sense']) if keep.get('sense') else e['sense'])
                W.drop(e['id'], '4 conflict', 'duplicate of %s (same English, Dia-thìris and part of speech)' % seen[k])
        else:
            seen[k] = e['id']


# ----------------------------------------------------------------------------------------------
# 7. main senses of very common words that only had a minor sense

def n_(en, rank, sense, rod, g, pl=None, gen=None, **kw):
    e = {'id': 'f-%s-n' % en, 'en': en, 'rank': rank, 'sense': sense, 'pos': 'n', 'rod': rod, 'g': g}
    if pl:
        e['pl'] = pl
    e['gen'] = gen or rod
    e.update(kw)
    return e


def v_(en, rank, sense, rod, vn, root=None):
    return {'id': 'f-%s-v' % en, 'en': en, 'rank': rank, 'sense': sense, 'pos': 'v', 'rod': rod,
            'root': root or rod.split()[0], 'vn': vn}


def a_(en, rank, sense, rod, pos='adj'):
    return {'id': 'f-%s-%s' % (en, pos), 'en': en, 'rank': rank, 'sense': sense, 'pos': pos, 'rod': rod}


# rank = position in wordfreq's top-n English list (not lemmatised, so close to, not identical with, the batches' rank)
SENSES = [
    n_('right', 115, 'a right, what one is entitled to', 'còir', 'f', 'còraichean', 'còrach'),
    a_('right', 115, 'correct, just (the other side is deas)', 'ceart'),
    n_('work', 116, 'work, labour; a job', 'obair', 'f', 'obraichean', 'obrach'),
    n_('need', 112, 'need, want, use', 'feum', 'm', 'feuman', 'feuma'),
    n_('state', 163, 'state, condition', 'staid', 'f', 'staidean', 'staide'),
    a_('own', 178, "own: after the noun with aig and fhèin (an taigh agam fhèin 'my own house')", 'fhèin'),
    v_('please', 208, 'give pleasure to, satisfy', 'toilich', 'toileachadh'),
    n_('point', 265, 'point, dot; the point of an argument', 'puing', 'f', 'puingean', 'puinge'),
    n_('support', 276, 'support, backing', 'taic', 'f', 'taicean', 'taice'),
    n_('kind', 337, 'kind, sort', 'seòrsa', 'm', 'seòrsaichean', 'seòrsa'),
    n_('hope', 346, 'hope', 'dòchas', 'm', 'dòchasan', 'dòchais'),
    n_('type', 546, 'type, kind, sort', 'seòrsa', 'm', 'seòrsaichean', 'seòrsa'),
    n_('march', 550, 'a march (of soldiers); a marching tune', 'caismeachd', 'f', 'caismeachdan', 'caismeachd'),
    v_('march', 550, 'march in step', 'dèan caismeachd', 'dèanamh caismeachd'),
    n_('cost', 568, 'cost, expense', 'coscais', 'f', 'coscaisean', 'coscais'),
    n_('rest', 594, 'rest, repose', 'fois', 'f', None, 'foise'),
    {'id': 'f-rest-n2', 'en': 'rest', 'rank': 594, 'sense': 'the rest, the remainder', 'pos': 'n', 'rod': 'còrr', 'g': 'm', 'gen': 'còrra'},
    n_('share', 642, 'share, portion', 'cuid', 'f', 'codaichean', 'codach'),
    n_('return', 663, 'return, coming back', 'tilleadh', 'm', 'tillidhean', 'tillidh'),
    a_('total', 627, 'total, whole', 'iomlan'),
    v_('race', 882, 'run a race, compete in speed', 'dèan rèis', 'dèanamh rèis'),
    n_('increase', 877, 'increase, growth', 'meudachadh', 'm', None, 'meudachaidh'),
    a_('daily', 899, 'daily, every day', 'gach latha', 'adv'),
    n_('practice', 931, 'practice, habit; exercise of a skill', 'cleachdadh', 'm', 'cleachdaidhean', 'cleachdaidh'),
    n_('sleep', 957, 'sleep', 'cadal', 'm', None, 'cadail'),
    n_('sign', 885, 'sign, mark, token', 'comharra', 'm', 'comharran', 'comharra'),
    n_('network', 1023, 'network, web of links', 'lìon', 'm', 'lìontan', 'lìn'),
    v_('double', 1049, 'double, make twice as much', 'dùblaich', 'dùblachadh'),
    n_('focus', 1077, 'focus, attention', 'aire', 'f', None, 'aire'),
    n_('claim', 1181, 'claim, plea', 'tagradh', 'm', 'tagraidhean', 'tagraidh'),
    v_('judge', 1193, 'give judgement, judge', 'thoir breith air', 'toirt breith air'),
    v_('approach', 1241, 'come near to', 'dlùthaich', 'dlùthachadh'),
    n_('dance', 1246, 'dance', 'dannsa', 'm', 'dannsaichean', 'dannsa'),
    n_('master', 1250, 'master, one in charge; master of a craft', 'maighstir', 'm', 'maighstirean', 'maighstir'),
    a_('secret', 1284, 'secret, hidden', 'dìomhair'),
    n_('comment', 1392, 'remark, comment', 'beachd', 'm', 'beachdan', 'beachd'),
    v_('interview', 1458, 'question someone in an interview', 'dèan agallamh le', 'dèanamh agallamh le'),
    n_('attempt', 1476, 'attempt, effort', 'oidhirp', 'f', 'oidhirpean', 'oidhirpe'),
    n_('influence', 1725, 'influence, effect', 'buaidh', 'f', 'buaidhean', 'buaidhe'),
    n_('patient', 1769, 'a sick person under care', 'euslainteach', 'm', 'euslaintich', 'euslaintich'),
    v_('dress', 1789, 'put clothes on, clothe', 'sceadaich', 'sceadachadh'),
    v_('guide', 1829, 'lead the way, guide', 'treòraich', 'treòrachadh'),
    v_('dry', 1857, 'make or become dry', 'tiormaich', 'tiormachadh'),
    n_('iron', 1866, 'iron, the metal', 'iarann', 'm', None, 'iarainn'),
    n_('taste', 1924, 'taste, flavour', 'blas', 'm', 'blasan', 'blais'),
    n_('exercise', 2109, 'exercise, physical training', 'eacarsaich', 'f', 'eacarsaichean', 'eacarsaich'),
    v_('grant', 2157, 'bestow, grant', 'builich', 'buileachadh'),
    v_('strike', 2234, 'hit, strike', 'buail', 'bualadh'),
    n_('struggle', 2408, 'struggle, strife', 'strì', 'f', None, 'strì'),
    n_('smile', 2316, 'smile', 'fiamh-ghàire', 'm', None, 'fiamh-ghàire'),
    n_('medium', 2454, 'medium, means', 'meadhan', 'm', 'meadhanan', 'meadhain'),
    v_('upset', 2470, 'upset, put into disorder', 'cuir troimh-a-chèile', 'cur troimh-a-chèile'),
    v_('switch', 2504, 'change over, switch', 'atharraich', 'atharrachadh'),
    n_('cry', 2525, 'cry, shout', 'glaodh', 'm', 'glaodhan', 'glaoidh'),
    n_('kiss', 2586, 'kiss', 'pòg', 'f', 'pògan', 'pòige'),
    v_('rent', 2592, 'hire, take on rent', 'gabh air màl', 'gabhail air màl'),
    v_('shift', 2644, 'move, shift', 'gluais', 'gluasad'),
    n_('object', 2689, 'object, thing', 'nì', 'm', 'nithean', 'nì'),
    v_('witness', 2925, 'see with one\'s own eyes, witness', 'faic', 'faicinn'),
    v_('suspect', 2967, 'suspect, hold under suspicion', 'cuir an amharas', 'cur an amharas'),
    v_('tie', 2970, 'tie, bind', 'ceangail', 'ceangal'),
    n_('lock', 2954, 'lock', 'glas', 'f', 'glasan', 'glaise'),
    n_('smell', 3086, 'smell, scent', 'fàileadh', 'm', 'fàilidhean', 'fàilidh'),
    v_('protest', 3327, 'complain, protest', 'gearain', 'gearan'),
    v_('assault', 3349, 'attack, assault', 'thoir ionnsaigh air', 'toirt ionnsaigh air'),
    n_('comfort', 3548, 'comfort, solace', 'comhfhurtachd', 'f', None, 'comhfhurtachd'),
    n_('repair', 3582, 'repair, mending', 'càradh', 'm', 'càraidhean', 'càraidh'),
    v_('bid', 3601, 'offer a price, bid', 'tairg', 'tairgsinn'),
    v_('delay', 3618, 'delay, put off', 'cuir dàil air', 'cur dàil air'),
    v_('desert', 3620, 'forsake, desert', 'trèig', 'trèigsinn'),
    n_('regret', 3838, 'regret, remorse', 'aithreachas', 'm', None, 'aithreachais'),
    n_('spell', 3849, 'magic spell, charm', 'geas', 'f', 'geasan', 'geasa'),
    n_('promise', 2009, 'promise', 'gealladh', 'm', 'geallaidhean', 'geallaidh'),
    n_('praise', 4259, 'praise', 'moladh', 'm', 'molaidhean', 'molaidh'),
    v_('sacrifice', 4409, 'offer up, sacrifice', 'ìobair', 'ìobradh'),
    v_('warrant', 4812, 'guarantee, warrant', 'barantaich', 'barantachadh'),
    v_('cruise', 4933, 'sail at leisure', 'seòl', 'seòladh'),
    v_('permit', 4970, 'allow, permit', 'ceadaich', 'ceadachadh'),
    v_('calm', 2777, 'calm, soothe', 'ciùinich', 'ciùineachadh'),
    a_('close', 431, 'near, close', 'faisc'),
    a_('in', 6, "in, inside (at rest); a-steach 'inwards' (motion)", 'a-staigh', 'adv'),
    a_('on', 13, 'on, onward', 'air adhart', 'adv'),
]


def fix_senses(W):
    have = {(re.sub(r'^to ', '', e['en'].lower()), e['rod'].lower(), e.get('pos')) for e in W.live()}
    for e in SENSES:
        if (e['en'], e['rod'].lower(), e['pos']) in have:
            continue
        W.add(dict(e), '7 sense', 'main sense of a top-5,000 word missing from LEXICON.json')


# ----------------------------------------------------------------------------------------------
# 6. checks

def check(W):
    bad_norm, breaches = [], []
    touched = [W.E[i] for i in W.why] + W.adds
    for e in touched:
        for k in ROD_FIELDS + ('was',):
            v = e.get(k)
            if not isinstance(v, str) or not v:
                continue
            if R.normalize(v) != v:
                bad_norm.append((e['id'], k, v))
            if k == 'was':
                continue
            for w in re.findall(r"[^\s\-'’,.!?;:()]+", v):
                if R.check_agreement(w):
                    breaches.append((e['id'], k, w))
    return bad_norm, breaches


# ----------------------------------------------------------------------------------------------

def main():
    orig, new, skips = load()
    W = Work(orig, new, skips)
    fix_case(W)
    fix_verbs(W)
    fix_peoples(W)
    fix_loans(W)
    fix_old(W)
    fix_conflicts(W)
    fix_senses(W)
    bad_norm, breaches = check(W)
    if bad_norm:
        for b in bad_norm:
            print('NOT RÒDAIS SPELLING', *b)
        raise SystemExit(1)

    edits = []
    for i in W.order:
        if i in W.drops or not W.why[i]:
            continue
        a, b = W.before[i], W.E[i]
        st = {k: v for k, v in b.items() if k != '_file' and a.get(k) != v}
        un = sorted(k for k in a if k not in b)
        if not st and not un:
            continue
        ed = {'id': i, 'set': st}
        if un:
            ed['unset'] = un
        ed['old'] = {k: a[k] for k in list(st) + un if k in a}
        ed['why'] = W.why[i]
        edits.append(ed)
    adds = []
    for e in W.adds:
        e = {k: v for k, v in e.items() if k != '_file'}
        e['why'] = e.pop('_why')
        adds.append(e)
    drops = [{'id': i, 'why': w} for i, w in W.drops.items()]
    counts = collections.Counter()
    for ed in edits:
        for w in ed['why']:
            counts[w.split(':')[0]] += 1
    for a in adds:
        counts[a['why'].split(':')[0] + ' (added)'] += 1
    for d in drops:
        counts[d['why'].split(':')[0] + ' (dropped)'] += 1
    patch = {'about': 'written by audit.py; applied by merge_lexicon.py after loading and before writing',
             'counts': dict(sorted(counts.items())),
             'caol_le_caol': ['%s %s %s' % b for b in breaches],
             'edit': edits, 'add': adds, 'drop': drops}
    json.dump(patch, open(os.path.join(HERE, 'audit_patch.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('audit_patch.json: %d edits, %d additions, %d drops' % (len(edits), len(adds), len(drops)))
    for k, v in sorted(counts.items()):
        print('  %-22s %d' % (k, v))
    print('caol le caol breaches in changed/added forms: %d' % len(breaches))
    for b in breaches:
        print('  ', *b)


if __name__ == '__main__':
    main()
