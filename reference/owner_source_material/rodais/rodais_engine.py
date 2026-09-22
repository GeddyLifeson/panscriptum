"""
Ròdais engine — a small, inspectable rule system for the Rodos dialect,
built in the same spirit as Vulgarlang's phonology tools (phoneme
classes, sound-change notation A > B / _C) but running on real Irish /
Scottish Gaelic phonology instead of randomly generated sound systems.

The naming layer (the first pass) needed three pieces:
  1. A phoneme inventory, classified (broad/slender vowels, consonants).
  2. The Gaelic spelling law "caol le caol, leathan le leathan" --
     slender with slender, broad with broad -- checked by
     check_agreement() and used by attach_suffix() to pick an ending.
  3. A tiny sound-change interpreter in Vulgarlang notation
     (target > replacement / environment), so lenition is a declared
     rule you can read.

The grammar layer (this pass) adds what a sentence needs:
  4. normalize(): the Ròdais spelling rules (grave accents, sc for sg).
  5. article(), possessive(): the article and the possessives, with the
     mutations they cause.
  6. Verb / IRREGULAR / BI: every tense of a regular verb, the ten
     irregular verbs and "bi", independent and dependent forms.
  7. PREP_PRONOUNS: the fused preposition + pronoun forms.
  8. clause(): verb-subject-object clauses with negation and questions.
  9. number(): numerals with the mutations they cause.

GRAMMAR.md is the prose description of all of it. Run this file to
execute the self-test.
"""

VOWELS_BROAD   = set("aoàòuùáóú")
VOWELS_SLENDER = set("eiéèìí")
VOWELS = VOWELS_BROAD | VOWELS_SLENDER


def vowel_class(ch):
    ch = ch.lower()
    if ch in VOWELS_BROAD: return 'broad'
    if ch in VOWELS_SLENDER: return 'slender'
    return None


def is_vowel(ch):
    return bool(ch) and ch.lower() in VOWELS


def last_vowel_class(word):
    """Scan a word right-to-left for its last vowel; report broad/slender."""
    for ch in reversed(word):
        c = vowel_class(ch)
        if c:
            return c
    return None


# ---------------------------------------------------------------
# Spelling: the Ròdais signature
# ---------------------------------------------------------------
_ACUTE_TO_GRAVE = str.maketrans("áéíóúÁÉÍÓÚ", "àèìòùÀÈÌÒÙ")


def normalize(text):
    """
    Turn standard Scottish Gaelic spelling into Ròdais spelling:
      * long vowels take the grave accent, never the acute (the Scottish half);
      * the cluster written sg in Scotland is written sc (the Irish half):
        sgoil -> scoil, uisge -> uisce, Sgeul -> Sceul;
      * curly apostrophes become the plain one used for elision (a' bhean).
    Idempotent: normalizing Ròdais text changes nothing.
    """
    t = text.translate(_ACUTE_TO_GRAVE)
    t = t.replace("’", "'").replace("‘", "'")
    return t.replace("sg", "sc").replace("Sg", "Sc").replace("SG", "SC")


# Real words that break caol le caol. The rule is a spelling law with
# historical exceptions; these are the ones Ròdais inherits from Scottish
# Gaelic. Two whole classes are exempt as well (see check_agreement): the
# past participle in -te (dearbhte, crochte, mùchte) and the adjective
# suffix -mhor (brìghmhor), which are written the same after either class.
# Loanwords (espresso, karaoke) and personal names are not exempt: the
# checker reports them, and the lexicon keeps them as spelled.
AGREEMENT_EXCEPTIONS = {"esan", "seo", "eadar", "ceudna", "iadsan", "airson", "neoni", "rudeigin",
                        "cuideigin", "ògmhios", "t-ògmhios", "còmhstri", "diluain", "dimàirt", "diciadain",
                        "diardaoin", "dihaoine", "disathairne", "didòmhnaich"}
_EXEMPT_ENDINGS = ("te", "mhor")


def check_agreement(word):
    """
    Enforce caol le caol, leathan le leathan WITHIN a single fused word:
    for every internal consonant cluster with a vowel on each side, the
    flanking vowels must share broad/slender class. Returns a list of
    violations (empty = clean). Two-word compounds ("Cathair mhòr") are
    exempt -- the rule only binds inside one orthographic word. Hyphenated
    compounds are checked part by part, for the same reason.
    """
    if '-' in word or ' ' in word:
        out = []
        for part in word.replace('-', ' ').split():
            out.extend(check_agreement(part))
        return out
    if word.lower() in AGREEMENT_EXCEPTIONS:
        return []
    out = []
    for w, seg, left, right, j in _violations(word):
        # the -te participle and the -mhor suffix: forgive the clash on the ending itself
        if any(word.lower().endswith(e) and j >= len(word) - len(e) for e in _EXEMPT_ENDINGS):
            continue
        out.append((w, seg, left, right))
    return out


def _violations(word):
    violations = []
    i = 0
    n = len(word)
    while i < n:
        if vowel_class(word[i]):
            j = i + 1
            while j < n and not vowel_class(word[j]):
                j += 1
            # word[i] = a vowel, word[i+1:j] = consonant cluster, word[j] = next vowel (if any).
            # Adjacent vowels with nothing between them are a diphthong (ai, ao, ia, ua...),
            # which Gaelic orthography allows freely and is not what the rule governs.
            if j > i + 1 and j < n and vowel_class(word[j]):
                left = vowel_class(word[i])
                right = vowel_class(word[j])
                if left != right:
                    violations.append((word, word[i:j+1], left, right, j))
            i = j
        else:
            i += 1
    return violations


# ---------------------------------------------------------------
# Sound-change rule engine: Vulgarlang notation, minimal subset.
#   "m > mh"                 -- context-free
#   "m > mh / #_"             -- only word-initially (# = word boundary)
# ---------------------------------------------------------------
class SoundRule:
    def __init__(self, notation):
        self.notation = notation
        body, _, env = notation.partition('/')
        target, _, repl = body.partition('>')
        self.target = target.strip()
        self.repl = repl.strip()
        self.word_initial_only = env.strip() == '#_'

    def apply(self, word):
        if not word:
            return word
        if self.word_initial_only:
            if word.lower().startswith(self.target.lower()):
                kept_case = word[0]
                rest = word[len(self.target):]
                new_start = self.repl if kept_case.islower() else self.repl.capitalize()
                return new_start + rest
            return word
        return word.replace(self.target, self.repl)


# Lenition declared as sound-change rules instead of a lookup table.
LENITION_RULES = [SoundRule(f"{a} > {b} / #_") for a, b in [
    ("m", "mh"), ("b", "bh"), ("c", "ch"), ("p", "ph"),
    ("t", "th"), ("d", "dh"), ("g", "gh"), ("s", "sh"), ("f", "fh"),
]]
# s does not lenite before a stop or m: sc-, sp-, st-, sm-. The naming
# layer also writes substrate roots with k (Skell) and Scottish text may
# still carry sg-, so k and g block too. (The first pass left out k,
# which is how "Seann Shkell" got onto the map.)
S_BLOCKERS = {'c', 'p', 't', 'm', 'k', 'g'}
# The "dental block": after a word ending in n (the article, seann, aon),
# d, t and s stay unlenited: seann duine, an taigh, aon sagart.
DENTALS = {'d', 't', 's'}


def lenite(word, block_dentals=False):
    """
    Lenite the first sound of a word.
      block_dentals=True  -- d, t, s stay plain (after seann, aon, the article)
      block_dentals='dt'  -- only d, t stay plain (after cha)
    Already-lenited words, vowels, l, n, r and sc/sp/st/sm are unchanged.
    """
    if not word:
        return word
    c0 = word[0].lower()
    if len(word) > 1 and word[1].lower() == 'h':
        return word                              # already lenited
    if block_dentals:
        blocked = DENTALS if block_dentals is True else set(block_dentals)
        if c0 in blocked:
            return word
    if c0 == 's' and len(word) > 1 and not (is_vowel(word[1]) or word[1].lower() in 'lnr'):
        return word                              # sc, sp, st, sm (and sk, sg)
    for rule in LENITION_RULES:
        if word.lower().startswith(rule.target):
            out = rule.apply(word)
            if out != word:
                return out
    return word


def attach_suffix(root, broad_form, slender_form):
    """Pick the broad or slender allomorph of a suffix by the root's last vowel."""
    cls = last_vowel_class(root)
    suffix = broad_form if cls == 'broad' else slender_form
    return root + suffix


def _labial(word):
    return word[:1].lower() in ('b', 'f', 'm', 'p')


def _vowelish(word):
    """Starts with a vowel, or with silent fh + vowel."""
    return is_vowel(word[:1]) or (word[:2].lower() == 'fh' and is_vowel(word[2:3]))


# ---------------------------------------------------------------
# The article
# ---------------------------------------------------------------
def article(noun, gender='m', number='sg', case='nom'):
    """
    "the" + noun, with the mutation the article causes.
      case: 'nom' (subject/object), 'gen' (of the ...), 'dat' (after a preposition).
    The caller supplies the right case form of the noun itself (genitives and
    plurals are lexical); this function only adds the article and mutates.
    """
    w = noun
    c0 = w[:1].lower()
    vowel = is_vowel(c0)
    s_plus = c0 == 's' and len(w) > 1 and (is_vowel(w[1]) or w[1].lower() in 'lnr')

    if number == 'pl':
        if case == 'gen':
            return ('nam ' if _labial(w) else 'nan ') + w
        return ('na h-' if vowel else 'na ') + w
    if gender == 'f' and case == 'gen':
        return ('na h-' if vowel else 'na ') + w
    if gender == 'f' or case in ('gen', 'dat'):
        # feminine nominative/dative, masculine genitive/dative: the lenited pattern
        if vowel:
            return 'an ' + w
        if c0 == 'f':
            return 'an ' + lenite(w)
        if s_plus:
            return 'an t-' + w
        if c0 in 'bcgmp':
            return "a' " + lenite(w)
        return 'an ' + w
    # masculine nominative
    if vowel:
        return 'an t-' + w
    return ('am ' if _labial(w) else 'an ') + w


# ---------------------------------------------------------------
# Possessives
# ---------------------------------------------------------------
def possessive(person, noun):
    """mo / do / a / a / ar / ur / an + noun. person: 1s 2s 3sm 3sf 1p 2p 3p."""
    w = noun
    if person in ('1s', '2s'):
        l = lenite(w)
        if _vowelish(l):
            return ("m' " if person == '1s' else "d' ") + l
        return ('mo ' if person == '1s' else 'do ') + l
    if person == '3sm':
        return 'a ' + lenite(w)
    if person == '3sf':
        return ('a h-' if is_vowel(w[:1]) else 'a ') + w
    if person in ('1p', '2p'):
        p = 'ar ' if person == '1p' else 'ur '
        return p + ('n-' + w if is_vowel(w[:1]) else w)
    if person == '3p':
        return ('am ' if _labial(w) else 'an ') + w
    raise ValueError(person)


PRONOUNS = {'1s': 'mi', '2s': 'thu', '3sm': 'e', '3sf': 'i', '1p': 'sinn', '2p': 'sibh', '3p': 'iad'}
EMPHATIC = {'1s': 'mise', '2s': 'thusa', '3sm': 'esan', '3sf': 'ise', '1p': 'sinne', '2p': 'sibhse', '3p': 'iadsan'}
PERSONS = ['1s', '2s', '3sm', '3sf', '1p', '2p', '3p']

# Fused preposition + pronoun, in PERSONS order.
PREP_PRONOUNS = {
    'aig': ['agam', 'agad', 'aige', 'aice', 'againn', 'agaibh', 'aca'],
    'air': ['orm', 'ort', 'air', 'oirre', 'oirnn', 'oirbh', 'orra'],
    'do':  ['dhomh', 'dhut', 'dha', 'dhi', 'dhuinn', 'dhuibh', 'dhaibh'],
    'le':  ['leam', 'leat', 'leis', 'leatha', 'leinn', 'leibh', 'leotha'],
    'ann': ['annam', 'annad', 'ann', 'innte', 'annainn', 'annaibh', 'annta'],
    'bho': ['bhuam', 'bhuat', 'bhuaithe', 'bhuaipe', 'bhuainn', 'bhuaibh', 'bhuapa'],
    'ri':  ['rium', 'riut', 'ris', 'rithe', 'rinn', 'ribh', 'riutha'],
    'de':  ['dhìom', 'dhìot', 'dheth', 'dhith', 'dhinn', 'dhibh', 'dhiubh'],
    'à':   ['asam', 'asad', 'às', 'aisde', 'asainn', 'asaibh', 'asta'],
    'fo':  ['fodham', 'fodhad', 'fodha', 'foidhpe', 'fodhainn', 'fodhaibh', 'fodhpa'],
    'mu':  ['umam', 'umad', 'uime', 'uimpe', 'umainn', 'umaibh', 'umpa'],
}


def prep_pronoun(prep, person):
    return normalize(PREP_PRONOUNS[prep][PERSONS.index(person)])


# Pronoun object of a verbal noun: "Tha e gam fhaicinn" (he is seeing me).
OBJECT_PARTICLES = {'1s': 'gam', '2s': 'gad', '3sm': 'ga', '3sf': 'ga', '1p': 'gar', '2p': 'gur', '3p': 'gan'}


def object_particle(person, verbal_noun):
    p = OBJECT_PARTICLES[person]
    if person in ('1s', '2s', '3sm'):
        return p + ' ' + lenite(verbal_noun)
    if person == '3sf' and is_vowel(verbal_noun[:1]):
        return p + ' h-' + verbal_noun
    if person == '3p' and _labial(verbal_noun):
        return 'gam ' + verbal_noun
    return p + ' ' + verbal_noun


# ---------------------------------------------------------------
# Verbs
# ---------------------------------------------------------------
class Verb:
    """A regular verb, from its root and its (lexical) verbal noun."""

    def __init__(self, root, vn):
        self.root = root
        self.vn = vn

    def _lenited_with_dh(self, stem):
        # past and conditional: lenite; dh' before a vowel and before f (dh'fhàg)
        if is_vowel(stem[:1]):
            return "dh'" + stem
        if stem[:1].lower() == 'f':
            return "dh'" + lenite(stem)
        return lenite(stem)

    def form(self, tense, dependent=False, person=None):
        r = self.root
        if tense == 'past':
            p = self._lenited_with_dh(r)
            return 'do ' + p if dependent else p
        if tense == 'future':
            return r if dependent else attach_suffix(r, 'aidh', 'idh')
        if tense == 'conditional':
            end = ('ainn', 'inn') if person == '1s' else ('adh', 'eadh')
            stem = attach_suffix(r, *end)
            return stem if dependent else self._lenited_with_dh(stem)
        if tense == 'imperative':
            return attach_suffix(r, 'aibh', 'ibh') if person == '2p' else r
        if tense == 'relative':
            return lenite(attach_suffix(r, 'as', 'eas'))
        raise ValueError(tense)


class IrregularVerb(Verb):
    """One of the ten irregular verbs (or bi): every form is listed."""

    def __init__(self, root, vn, forms):
        super().__init__(root, vn)
        self.forms = forms   # tense -> (independent, dependent)

    def form(self, tense, dependent=False, person=None):
        if tense == 'imperative':
            return self.forms['imperative'][1 if person == '2p' else 0]
        if tense == 'conditional' and person == '1s':
            ind, dep = self.forms['conditional1s']
        else:
            ind, dep = self.forms[tense]
        return dep if dependent else ind


def _irr(root, vn, past, future, cond, cond1, rel, imp):
    return IrregularVerb(root, vn, {'past': past, 'future': future, 'conditional': cond,
                                    'conditional1s': cond1, 'relative': (rel, rel), 'imperative': imp})


IRREGULAR = {
    'abair':  _irr('abair', 'ràdh', ('thuirt', 'tuirt'), ('their', 'abair'), ('theireadh', 'abradh'), ('theirinn', 'abrainn'), 'their', ('abair', 'abraibh')),
    'beir':   _irr('beir', 'breith', ('rug', 'do rug'), ('beiridh', 'beir'), ('bheireadh', 'beireadh'), ('bheirinn', 'beirinn'), 'bheireas', ('beir', 'beiribh')),
    'cluinn': _irr('cluinn', 'cluinntinn', ('chuala', 'cuala'), ('cluinnidh', 'cluinn'), ('chluinneadh', 'cluinneadh'), ('chluinninn', 'cluinninn'), 'chluinneas', ('cluinn', 'cluinnibh')),
    'dèan':   _irr('dèan', 'dèanamh', ('rinn', 'do rinn'), ('nì', 'dèan'), ('dhèanadh', 'dèanadh'), ('dhèanainn', 'dèanainn'), 'nì', ('dèan', 'dèanaibh')),
    'faic':   _irr('faic', 'faicinn', ('chunnaic', 'faca'), ('chì', 'faic'), ('chitheadh', 'faiceadh'), ('chithinn', 'faicinn'), 'chì', ('faic', 'faicibh')),
    'faigh':  _irr('faigh', 'faighinn', ('fhuair', "d' fhuair"), ('gheibh', 'faigh'), ('gheibheadh', 'faigheadh'), ('gheibhinn', 'faighinn'), 'gheibh', ('faigh', 'faighibh')),
    'rach':   _irr('rach', 'dol', ('chaidh', 'deach'), ('thèid', 'tèid'), ('rachadh', 'rachadh'), ('rachainn', 'rachainn'), 'thèid', ('rach', 'rachaibh')),
    'ruig':   _irr('ruig', 'ruigsinn', ('ràinig', 'do ràinig'), ('ruigidh', 'ruig'), ('ruigeadh', 'ruigeadh'), ('ruiginn', 'ruiginn'), 'ruigeas', ('ruig', 'ruigibh')),
    'thig':   _irr('thig', 'tighinn', ('thàinig', 'tàinig'), ('thig', 'tig'), ('thigeadh', 'tigeadh'), ('thiginn', 'tiginn'), 'thig', ('thig', 'thigibh')),
    'thoir':  _irr('thoir', 'toirt', ('thug', 'tug'), ('bheir', 'toir'), ('bheireadh', 'toireadh'), ('bheirinn', 'toirinn'), 'bheir', ('thoir', 'thoiribh')),
    'bi':     _irr('bi', 'bhith', ('bha', 'robh'), ('bidh', 'bi'), ('bhiodh', 'biodh'), ('bhithinn', 'bithinn'), 'bhios', ('bi', 'bithibh')),
}
IRREGULAR['bi'].forms['present'] = ('tha', 'eil')
BI = IRREGULAR['bi']


def verb(root, vn=None):
    """Look up an irregular verb, or build a regular one."""
    if root in IRREGULAR:
        return IRREGULAR[root]
    if vn is None:
        raise ValueError('a regular verb needs its verbal noun: %s' % root)
    return Verb(root, vn)


def _with_particle(particle, form):
    """Join a preverbal particle to a dependent verb form, with its mutation."""
    if particle == 'cha':
        if form.startswith('do ') or form.startswith("d' "):
            return 'cha ' + form
        l = lenite(form, block_dentals='dt')     # cha lenites, but not d or t: cha dèan, cha tèid
        return ('chan ' if _vowelish(l) else 'cha ') + l
    if particle == 'an':
        if form == 'eil':
            return 'a bheil'
        return ('am ' if _labial(form) else 'an ') + form
    if particle == 'nach':
        return 'nach ' + form
    raise ValueError(particle)


def verb_phrase(v, tense, negative=False, question=False, person=None):
    """The inflected verb with its particle, e.g. 'cha do sheas', 'am faic', 'chan eil'."""
    if tense == 'imperative':
        f = v.form('imperative', person=person)
        return 'na ' + f if negative else f
    if not negative and not question:
        return v.form(tense, dependent=False, person=person)
    dep = v.form(tense, dependent=True, person=person)
    if negative and question:
        return _with_particle('nach', dep)
    return _with_particle('cha' if negative else 'an', dep)


def _subject(subject, verb_form):
    # "tu" rather than "thu" after verb forms ending in -dh or -s (bidh tu, cuiridh tu, sheasadh tu)
    if subject == 'thu' and (verb_form.endswith('dh') or verb_form.endswith('s')):
        return 'tu'
    return subject


def clause(v, tense, subject, obj=None, negative=False, question=False, extra=None):
    """
    Build a verb-subject-object clause.
      tense: past | future | conditional | present | perfect | imperative
      present and perfect are periphrastic: bi + subject + ag/air + verbal noun (+ object).
      subject: a person code ('1s' ... '3p') or any noun phrase string.
    Returns the clause with a capital and final punctuation, in Ròdais spelling.
    """
    person = subject if subject in PRONOUNS else None
    subj = PRONOUNS.get(subject, subject)
    if tense in ('present', 'perfect'):
        if v is BI:
            words = [verb_phrase(BI, 'present', negative, question), subj]
        else:
            vp = verb_phrase(BI, 'present', negative, question)
            if tense == 'present':
                aspect = ('ag ' if is_vowel(v.vn[:1]) else "a' ") + v.vn
            else:
                aspect = 'air ' + v.vn
            words = [vp, subj, aspect]
        words += [obj] if obj else []
    elif tense == 'imperative':
        words = [verb_phrase(v, 'imperative', negative, person=person)] + ([obj] if obj else [])
    else:
        vp = verb_phrase(v, tense, negative, question, person=person)
        synthetic_1s = tense == 'conditional' and person == '1s'
        words = [vp] + ([] if synthetic_1s else [_subject(subj, vp)]) + ([obj] if obj else [])
    if extra:
        words.append(extra)
    s = ' '.join(words)
    s = s[0].upper() + s[1:]
    return normalize(s + ('?' if question else '.'))


# ---------------------------------------------------------------
# The copula
# ---------------------------------------------------------------
def copula(predicate, subject, tense='present', negative=False, question=False):
    """
    Identity with a definite noun: copula('i', 'Aisling an ceannard') -> "Is i Aisling an ceannard."
    predicate: the pronoun that stands for it (e / i / iad); subject: the rest.
    """
    if tense == 'present':
        head = {(False, False): 'is', (True, False): 'chan', (False, True): 'an', (True, True): 'nach'}[(negative, question)]
    else:
        head = {(False, False): 'bu', (True, False): 'cha bu', (False, True): 'am bu', (True, True): 'nach bu'}[(negative, question)]
    s = '%s %s %s' % (head, predicate, subject)
    s = s[0].upper() + s[1:]
    return normalize(s + ('?' if question else '.'))


# ---------------------------------------------------------------
# Numbers
# ---------------------------------------------------------------
COUNTING = {1: 'a h-aon', 2: 'a dhà', 3: 'a trì', 4: 'a ceithir', 5: 'a còig', 6: 'a sia', 7: 'a seachd',
            8: 'a h-ochd', 9: 'a naoi', 10: 'a deich', 20: 'fichead', 30: 'trithead', 40: 'ceathrad',
            50: 'caogad', 60: 'seasgad', 70: 'seachdad', 80: 'ochdad', 90: 'naochad', 100: 'ceud', 1000: 'mìle'}
_ATTRIB = {1: 'aon', 2: 'dà', 3: 'trì', 4: 'ceithir', 5: 'còig', 6: 'sia', 7: 'seachd', 8: 'ochd', 9: 'naoi', 10: 'deich'}


def number(n, noun=None, plural=None):
    """
    A numeral, counting (number(3) -> 'a trì') or with a noun:
    aon and dà lenite a singular noun (aon chù, dà chù; aon keeps d, t, s plain);
    3-10 take the plural when one is given (trì coin); 11-19 add deug (dheug
    after dà); 20 and up take the singular. Covers 1-99 and the round hundreds
    and thousand in COUNTING.
    """
    if noun is None:
        if n in COUNTING:
            return normalize(COUNTING[n])
        if 10 < n < 20:
            return normalize(COUNTING[n - 10] + (' dheug' if n == 12 else ' deug'))
        tens, unit = divmod(n, 10)
        return normalize(COUNTING[tens * 10] + ' ' + _ATTRIB[unit])
    if n in (1, 2):
        return normalize(_ATTRIB[n] + ' ' + lenite(noun, block_dentals=(n == 1)))
    if 3 <= n <= 10:
        return normalize(_ATTRIB[n] + ' ' + (plural or noun))
    if 10 < n < 20:
        u = n - 10
        body = _ATTRIB[u] + ' ' + (lenite(noun, block_dentals=(u == 1)) if u in (1, 2) else noun)
        return normalize(body + (' dheug' if u == 2 else ' deug'))
    return normalize(number(n) + ' ' + noun)


# ---------------------------------------------------------------
# Place names (the naming layer, as functions)
# ---------------------------------------------------------------
def place_name(generic, qualifier):
    """
    Generic + qualifier, as on the map: the qualifier is lenited whatever the
    generic's gender (Baile ghorm, Cathair mhòr). This is a Ròdais naming
    convention, not everyday grammar; in speech an adjective after a
    masculine noun stays plain (baile gorm).
    """
    return normalize(generic + ' ' + lenite(qualifier))


def substrate_name(root):
    """'Seann' + an Old Ones root. Seann lenites, but not d, t or s (seann duine)."""
    return normalize('Seann ' + lenite(root, block_dentals=True))


# ---------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------
def _selftest():
    checks = []

    def eq(got, want):
        checks.append((got == want, got, want))

    # naming layer, unchanged behaviour
    eq(lenite("mòr"), "mhòr"); eq(lenite("beag"), "bheag"); eq(lenite("Dunn"), "Dhunn")
    eq(lenite("fiadhaich"), "fhiadhaich"); eq(lenite("Tarr"), "Tharr")
    eq(attach_suffix("Dubh", "as", "eas"), "Dubhas"); eq(attach_suffix("Ciar", "as", "eas"), "Ciaras")
    eq(check_agreement("Dubheas") != [], True); eq(check_agreement("Dubhas"), [])
    eq(check_agreement("Àrsaidh"), []); eq(check_agreement("esan"), [])
    eq(check_agreement("an-diugh"), []); eq(check_agreement("dearbhte"), []); eq(check_agreement("brìghmhor"), [])
    eq(check_agreement("Diluain"), []); eq(check_agreement("airson"), []); eq(check_agreement("espresso") != [], True)
    # the fixes
    eq(lenite("Skell"), "Skell")                      # s + k does not lenite (was Shkell)
    eq(substrate_name("Skell"), "Seann Skell"); eq(substrate_name("Dunn"), "Seann Dunn")
    eq(substrate_name("Cwen"), "Seann Chwen"); eq(substrate_name("Bral"), "Seann Bhral")
    eq(lenite("Chwen"), "Chwen")                      # never lenite twice
    # spelling
    eq(normalize("sgoil"), "scoil"); eq(normalize("uisge"), "uisce"); eq(normalize("mór"), "mòr")
    eq(normalize(normalize("Sgeulachd")), "Sceulachd")
    # article
    eq(article("cù"), "an cù"); eq(article("bàta"), "am bàta"); eq(article("uisce"), "an t-uisce")
    eq(article("bean", "f"), "a' bhean"); eq(article("fìrinn", "f"), "an fhìrinn")
    eq(article("sràid", "f"), "an t-sràid"); eq(article("oidhche", "f"), "an oidhche")
    eq(article("deoch", "f"), "an deoch"); eq(article("eileanan", number='pl'), "na h-eileanan")
    eq(article("bàird", "m", case='gen'), "a' bhàird"); eq(article("eaglaise", "f", case='gen'), "na h-eaglaise")
    eq(article("sagairt", "m", case='gen'), "an t-sagairt")
    eq(article("bòrd", "m", case='dat'), "a' bhòrd"); eq(article("fear", "m", case='dat'), "an fhear")
    eq(article("baile", "m"), "am baile"); eq(article("sagart", "m"), "an sagart")
    eq(article("coin", number='pl', case='gen'), "nan coin"); eq(article("bàtaichean", number='pl', case='gen'), "nam bàtaichean")
    # possessives
    eq(possessive('1s', 'màthair'), "mo mhàthair"); eq(possessive('1s', 'athair'), "m' athair")
    eq(possessive('2s', 'fàrdach'), "d' fhàrdach")
    eq(possessive('3sf', 'athair'), "a h-athair"); eq(possessive('1p', 'athair'), "ar n-athair")
    eq(possessive('3p', 'bàta'), "am bàta"); eq(possessive('3sm', 'cù'), "a chù")
    # regular verbs
    seas, cuir, ol, fag, ceannaich = (Verb('seas', 'seasamh'), Verb('cuir', 'cur'), Verb('òl', 'òl'),
                                      Verb('fàg', 'fàgail'), Verb('ceannaich', 'ceannach'))
    eq(seas.form('past'), "sheas"); eq(ol.form('past'), "dh'òl"); eq(fag.form('past'), "dh'fhàg")
    eq(seas.form('future'), "seasaidh"); eq(cuir.form('future'), "cuiridh"); eq(ceannaich.form('future'), "ceannaichidh")
    eq(seas.form('conditional'), "sheasadh"); eq(cuir.form('conditional', person='1s'), "chuirinn")
    eq(ol.form('conditional'), "dh'òladh"); eq(fag.form('conditional'), "dh'fhàgadh")
    eq(seas.form('relative'), "sheasas"); eq(seas.form('imperative', person='2p'), "seasaibh")
    # particles
    eq(verb_phrase(seas, 'past', negative=True), "cha do sheas")
    eq(verb_phrase(seas, 'future', negative=True), "cha sheas")      # Cha sheas poca falamh.
    eq(verb_phrase(ol, 'future', negative=True), "chan òl")
    eq(verb_phrase(fag, 'future', negative=True), "chan fhàg")
    eq(verb_phrase(IRREGULAR['dèan'], 'future', negative=True), "cha dèan")
    eq(verb_phrase(IRREGULAR['rach'], 'future', negative=True), "cha tèid")
    eq(verb_phrase(IRREGULAR['faic'], 'future', question=True), "am faic")
    eq(verb_phrase(IRREGULAR['faic'], 'past', negative=True), "chan fhaca")
    eq(verb_phrase(IRREGULAR['faigh'], 'past', negative=True), "cha d' fhuair")
    eq(verb_phrase(IRREGULAR['cluinn'], 'past', negative=True), "cha chuala")
    eq(verb_phrase(IRREGULAR['rach'], 'past', question=True), "an deach")
    eq(verb_phrase(BI, 'present', question=True), "a bheil")
    eq(verb_phrase(BI, 'present', negative=True), "chan eil")
    eq(verb_phrase(BI, 'present', negative=True, question=True), "nach eil")
    eq(verb_phrase(BI, 'future', negative=True), "cha bhi")
    eq(verb_phrase(BI, 'past', negative=True), "cha robh")
    eq(verb_phrase(seas, 'imperative', negative=True), "na seas")
    # clauses
    faic = IRREGULAR['faic']
    eq(clause(faic, 'past', 'Cian', 'an long'), "Chunnaic Cian an long.")
    eq(clause(faic, 'past', 'Cian', 'an long', negative=True), "Chan fhaca Cian an long.")
    eq(clause(faic, 'past', 'Cian', 'an long', question=True), "Am faca Cian an long?")
    eq(clause(Verb('coisich', 'coiseachd'), 'present', 'Aisling', extra='dhan bhaile'), "Tha Aisling a' coiseachd dhan bhaile.")
    eq(clause(ol, 'present', '3sf', 'cofaidh'), "Tha i ag òl cofaidh.")
    eq(clause(BI, 'present', '1s', negative=True, extra='sgìth'), "Chan eil mi scìth.")
    eq(clause(BI, 'future', '2s', extra='ann'), "Bidh tu ann.")
    eq(clause(seas, 'conditional', '1s'), "Sheasainn.")
    eq(clause(Verb('ith', 'ithe'), 'perfect', '1p'), "Tha sinn air ithe.")
    eq(clause(seas, 'imperative', '2s', negative=True), "Na seas.")
    # copula
    eq(copula('i', 'Aisling an ceannard'), "Is i Aisling an ceannard.")
    eq(copula('e', 'Cian a rinn e', tense='past'), "Bu e Cian a rinn e.")
    # prepositional pronouns, object particles
    eq(prep_pronoun('aig', '1s'), "agam"); eq(prep_pronoun('le', '3sf'), "leatha")
    eq(object_particle('3sm', 'faicinn'), "ga fhaicinn"); eq(object_particle('1s', 'faicinn'), "gam fhaicinn")
    eq(object_particle('3sf', 'ithe'), "ga h-ithe")
    # numbers
    eq(number(2, 'cù'), "dà chù"); eq(number(3, 'cù', 'coin'), "trì coin"); eq(number(1, 'taigh'), "aon taigh")
    eq(number(1, 'bàta'), "aon bhàta")
    eq(number(12), "a dhà dheug"); eq(number(12, 'cù'), "dà chù dheug"); eq(number(20, 'cù'), "fichead cù")
    eq(number(45), "ceathrad còig")
    # place names
    eq(place_name('Cathair', 'mòr'), "Cathair mhòr"); eq(place_name('Abhainn', 'sgìth'), "Abhainn scìth")

    bad = [(g, w) for ok, g, w in checks if not ok]
    for g, w in bad:
        print('FAIL  got %r  want %r' % (g, w))
    print('%d/%d checks passed' % (len(checks) - len(bad), len(checks)))
    return not bad


if __name__ == "__main__":
    import sys
    sys.exit(0 if _selftest() else 1)
