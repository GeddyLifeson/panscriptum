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
     irregular verbs and "bi", independent and dependent forms, the
     synthetic 1 sg./1 pl., every person of the imperative, the relative
     future, the impersonal forms (person=IMPERSONAL) and syncope (SYNCOPE).
  7. PREP_PRONOUNS: the fused preposition + pronoun forms.
  8. clause(): verb-subject-object clauses with negation and questions.
  9. number(): numerals with the mutations they cause.

The sound layer adds:
 10. pronounce(): Ròdais spelling to broad phonemic IPA, following
     PHONOLOGY.md (broad/slender, fortis/lenis with pre-aspiration, tense
     and lax sonorants, lenition, the helping vowel, eclipsis).

GRAMMAR.md and PHONOLOGY.md are the prose description of all of it. Run this file to
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
                        "diardaoin", "dihaoine", "disathairne", "didòmhnaich",
                        # traditional emphatic prepositional pronouns (GRAMMAR_MORPHOLOGY.md §5)
                        "aigesan", "airsan", "leathase", "bhuaithesan", "dhaibhsan", "thuigesan", "uimesan"}
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
# The person code for the impersonal (autonomous) forms: "one lifts / it is lifted".
IMPERSONAL = 'imp'

# Syncopating verbs (GRAMMAR_MORPHOLOGY.md §6.3): a root of two syllables whose second vowel is
# short and unstressed loses it before a vowel-initial ending (-aidh, -adh, -ainn, -amaid, -aibh,
# -as, -ar, -am), and the cluster takes the class of the first vowel: caidil -> cadlaidh. The
# past, the 2 sg. imperative and the consonant-initial endings (-tadh, -tar) keep the full root.
SYNCOPE = {
    'caidil': 'cadl', 'foscail': 'foscl', 'innis': 'inns', 'bruidhinn': 'bruidhn',
    'freagair': 'freagr', 'tachair': 'tachr', 'labhair': 'labhr', 'iomair': 'iomr',
    'ceangail': 'ceangl', 'fuascail': 'fuascl', 'seachain': 'seachn', 'coisinn': 'cosn',
    'cagainn': 'cagn', 'caomhain': 'caomhn', 'tadhail': 'tadhl', 'siubhail': 'siubhl',
    'fògair': 'fògr', 'tagair': 'tagr', 'agair': 'agr', 'amail': 'aml', 'tiomain': 'tiomn',
}

# Person codes for the imperative: 3rd persons share -adh/-eadh.
_IMP_KEY = {None: '2s', '1s': '1s', '2s': '2s', '3sm': '3', '3sf': '3', '3p': '3', '1p': '1p', '2p': '2p'}


def _lenited_with_dh(word):
    """
    The lenition of the past, the conditional and the relative future: lenite; dh' before a
    vowel (dh'òl) and before f + vowel (dh'fhàg); before f + consonant the lenited form stands
    alone (fhreagair, fhliuch), as in the tales.
    """
    if is_vowel(word[:1]):
        return "dh'" + word
    l = lenite(word)
    if l[:2].lower() == 'fh' and is_vowel(l[2:3]):
        return "dh'" + l
    return l


class Verb:
    """
    A regular verb, from its root and its (lexical) verbal noun. `stem` is the syncopated
    stem for vowel-initial endings (caidil -> cadl); it defaults to SYNCOPE, then the root.
    """

    def __init__(self, root, vn, stem=None):
        self.root = root
        self.vn = vn
        self.stem = stem or SYNCOPE.get(root, root)

    def _v(self, broad, slender):
        """A vowel-initial ending, on the (syncopated) stem."""
        return attach_suffix(self.stem, broad, slender)

    def _lenited_with_dh(self, word):
        return _lenited_with_dh(word)

    def form(self, tense, dependent=False, person=None):
        """
        tense: past | future | conditional | imperative | relative.
        person: '1s' and '1p' give the synthetic forms of the conditional and imperative;
        '3sm'/'3sf'/'3p' the 3rd-person imperative; IMPERSONAL ('imp') the impersonal forms.
        """
        r = self.root
        imp = person == IMPERSONAL
        if tense == 'past':
            p = _lenited_with_dh(self._v('adh', 'eadh') if imp else r)
            return 'do ' + p if dependent else p
        if tense == 'future':
            if imp:
                return self._v('ar', 'ear')                    # togar, brisear: indep. = dep.
            return r if dependent else self._v('aidh', 'idh')
        if tense == 'conditional':
            if imp:
                stem = attach_suffix(r, 'tadh', 'teadh')      # thogtadh, bhristeadh
            elif person == '1s':
                stem = self._v('ainn', 'inn')
            elif person == '1p':
                stem = self._v('amaid', 'eamaid')
            else:
                stem = self._v('adh', 'eadh')
            return stem if dependent else _lenited_with_dh(stem)
        if tense == 'imperative':
            if imp:
                return attach_suffix(r, 'tar', 'tear')        # togtar, bristear
            key = _IMP_KEY[person]
            return {'1s': lambda: self._v('am', 'eam'), '2s': lambda: r,
                    '3': lambda: self._v('adh', 'eadh'), '1p': lambda: self._v('amaid', 'eamaid'),
                    '2p': lambda: self._v('aibh', 'ibh')}[key]()
        if tense == 'relative':
            return _lenited_with_dh(self._v('as', 'eas'))
        raise ValueError('a regular verb has no simple %s' % tense)


class IrregularVerb(Verb):
    """One of the ten irregular verbs (or bi): every form is listed."""

    def __init__(self, root, vn, forms):
        super().__init__(root, vn)
        self.forms = forms   # tense -> (independent, dependent); 'imperative' -> {person: form}

    def form(self, tense, dependent=False, person=None):
        if person == IMPERSONAL:
            if tense not in self.forms['impersonal']:
                raise ValueError('%s has no impersonal %s' % (self.root, tense))
            ind, dep = self.forms['impersonal'][tense]
        elif tense == 'imperative':
            return self.forms['imperative'][_IMP_KEY[person]]
        elif tense == 'conditional' and person in ('1s', '1p'):
            ind, dep = self.forms['conditional' + person]
        else:
            ind, dep = self.forms[tense]
        return dep if dependent else ind


def _irr(root, vn, past, future, cond, cond1, cond1p, rel, imp, impersonal):
    """imp: (1s, 2s, 3rd, 1p, 2p); impersonal: tense -> (independent, dependent)."""
    return IrregularVerb(root, vn, {'past': past, 'future': future, 'conditional': cond,
                                    'conditional1s': cond1, 'conditional1p': cond1p,
                                    'relative': (rel, rel),
                                    'imperative': dict(zip(('1s', '2s', '3', '1p', '2p'), imp)),
                                    'impersonal': impersonal})


# Forms as in GRAMMAR_MORPHOLOGY.md §6.9, impersonals included.
IRREGULAR = {
    'abair':  _irr('abair', 'ràdh', ('thuirt', 'tuirt'), ('their', 'abair'), ('theireadh', 'abradh'), ('theirinn', 'abrainn'),
                   ('theireamaid', 'abramaid'), 'their', ('abram', 'abair', 'abradh', 'abramaid', 'abraibh'),
                   {'past': ('thuirteadh', 'tuirteadh'), 'future': ('theirear', 'abrar'), 'conditional': ('theirteadh', 'abairteadh')}),
    'beir':   _irr('beir', 'breith', ('rug', 'do rug'), ('beiridh', 'beir'), ('bheireadh', 'beireadh'), ('bheirinn', 'beirinn'),
                   ('bheireamaid', 'beireamaid'), 'bheireas', ('beiream', 'beir', 'beireadh', 'beireamaid', 'beiribh'),
                   {'past': ('rugadh', 'do rugadh'), 'future': ('beirear', 'beirear'), 'conditional': ('bheirteadh', 'beirteadh')}),
    'cluinn': _irr('cluinn', 'cluinntinn', ('chuala', 'cuala'), ('cluinnidh', 'cluinn'), ('chluinneadh', 'cluinneadh'), ('chluinninn', 'cluinninn'),
                   ('chluinneamaid', 'cluinneamaid'), 'chluinneas', ('cluinneam', 'cluinn', 'cluinneadh', 'cluinneamaid', 'cluinnibh'),
                   {'past': ('chualas', 'cualas'), 'future': ('cluinnear', 'cluinnear'), 'conditional': ('chluinnteadh', 'cluinnteadh')}),
    'dèan':   _irr('dèan', 'dèanamh', ('rinn', 'do rinn'), ('nì', 'dèan'), ('dhèanadh', 'dèanadh'), ('dhèanainn', 'dèanainn'),
                   ('dhèanamaid', 'dèanamaid'), 'nì', ('dèanam', 'dèan', 'dèanadh', 'dèanamaid', 'dèanaibh'),
                   {'past': ('rinneadh', 'do rinneadh'), 'future': ('nithear', 'dèanar'), 'conditional': ('dhèantadh', 'dèantadh')}),
    'faic':   _irr('faic', 'faicinn', ('chunnaic', 'faca'), ('chì', 'faic'), ('chitheadh', 'faiceadh'), ('chithinn', 'faicinn'),
                   ('chitheamaid', 'faiceamaid'), 'chì', ('faiceam', 'faic', 'faiceadh', 'faiceamaid', 'faicibh'),
                   # dep. conditional also short "faicte" (gum faicte ròn mòr glas, tale of the seal wife)
                   {'past': ('chunnacas', 'facas'), 'future': ('chithear', 'faicear'), 'conditional': ('chiteadh', 'faicteadh')}),
    'faigh':  _irr('faigh', 'faighinn', ('fhuair', "d' fhuair"), ('gheibh', 'faigh'), ('gheibheadh', 'faigheadh'), ('gheibhinn', 'faighinn'),
                   ('gheibheamaid', 'faigheamaid'), 'gheibh', ('faigheam', 'faigh', 'faigheadh', 'faigheamaid', 'faighibh'),
                   {'past': ('fhuaireadh', "d' fhuaireadh"), 'future': ('gheibhear', 'faighear'), 'conditional': ('gheibhteadh', 'faighteadh')}),
    'rach':   _irr('rach', 'dol', ('chaidh', 'deach'), ('thèid', 'tèid'), ('rachadh', 'rachadh'), ('rachainn', 'rachainn'),
                   ('rachamaid', 'rachamaid'), 'thèid', ('racham', 'rach', 'rachadh', 'rachamaid', 'rachaibh'),
                   {'past': ('chaidheas', 'deachas'), 'future': ('thèidear', 'tèidear'), 'conditional': ('rachtadh', 'rachtadh')}),
    'ruig':   _irr('ruig', 'ruigsinn', ('ràinig', 'do ràinig'), ('ruigidh', 'ruig'), ('ruigeadh', 'ruigeadh'), ('ruiginn', 'ruiginn'),
                   ('ruigeamaid', 'ruigeamaid'), 'ruigeas', ('ruigeam', 'ruig', 'ruigeadh', 'ruigeamaid', 'ruigibh'),
                   {'past': ('ràinigeadh', 'do ràinigeadh'), 'future': ('ruigear', 'ruigear'), 'conditional': ('ruigteadh', 'ruigteadh')}),
    'thig':   _irr('thig', 'tighinn', ('thàinig', 'tàinig'), ('thig', 'tig'), ('thigeadh', 'tigeadh'), ('thiginn', 'tiginn'),
                   ('thigeamaid', 'tigeamaid'), 'thig', ('thigeam', 'thig', 'thigeadh', 'thigeamaid', 'thigibh'),
                   {'past': ('thàinigeadh', 'tàinigeadh'), 'future': ('thigear', 'tigear'), 'conditional': ('thigteadh', 'tigteadh')}),
    'thoir':  _irr('thoir', 'toirt', ('thug', 'tug'), ('bheir', 'toir'), ('bheireadh', 'toireadh'), ('bheirinn', 'toirinn'),
                   ('bheireamaid', 'toireamaid'), 'bheir', ('thoiream', 'thoir', 'thoireadh', 'thoireamaid', 'thoiribh'),
                   {'past': ('thugadh', 'tugadh'), 'future': ('bheirear', 'toirear'), 'conditional': ('bheirteadh', 'toirteadh')}),
    'bi':     _irr('bi', 'bhith', ('bha', 'robh'), ('bidh', 'bi'), ('bhiodh', 'biodh'), ('bhithinn', 'bithinn'),
                   ('bhitheamaid', 'bitheamaid'), 'bhios', ('bitheam', 'bi', 'bitheadh', 'bitheamaid', 'bithibh'),
                   {'present': ('thathar', 'eilear'), 'past': ('bhathar', 'robhar'), 'future': ('bithear', 'bithear'),
                    'conditional': ('bhite', 'bite')}),
}
IRREGULAR['bi'].forms['present'] = ('tha', 'eil')
BI = IRREGULAR['bi']


def verb(root, vn=None):
    """Look up an irregular verb, or build a regular one (syncopating from SYNCOPE)."""
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
        if form.startswith('eil'):
            return 'a bh' + form                    # a bheil, a bheilear
        return ('am ' if _labial(form) else 'an ') + form
    if particle == 'nach':
        return 'nach ' + form
    raise ValueError(particle)


def verb_phrase(v, tense, negative=False, question=False, person=None, impersonal=False):
    """
    The inflected verb with its particle, e.g. 'cha do sheas', 'am faic', 'chan eil'.
    impersonal=True (or person=IMPERSONAL) gives the impersonal: 'chan fhacas', 'cha togar'.
    """
    if impersonal:
        person = IMPERSONAL
    if tense == 'imperative':
        f = v.form('imperative', person=person)
        if not negative:
            return f
        return ('na h-' if is_vowel(f[:1]) else 'na ') + f     # na seas, na h-òl
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


def clause(v, tense, subject, obj=None, negative=False, question=False, extra=None, impersonal=False):
    """
    Build a verb-subject-object clause.
      tense: past | future | conditional | present | perfect | imperative
      present and perfect are periphrastic: bi + subject + ag/air + verbal noun (+ object).
      subject: a person code ('1s' ... '3p') or any noun phrase string. The synthetic forms
      (conditional and imperative 1 sg. and 1 pl.) take no pronoun; a 3rd-person subject of the
      imperative follows it (togadh e, "let him lift").
      impersonal=True: the impersonal form, with no subject (pass None); obj follows the verb
      (chan fhacas iad).
    Returns the clause with a capital and final punctuation, in Ròdais spelling.
    """
    person = subject if subject in PRONOUNS else None
    subj = PRONOUNS.get(subject, subject)
    if impersonal:
        if tense in ('present', 'perfect') and v is not BI:
            raise ValueError('the periphrastic %s has no impersonal form' % tense)
        t = 'present' if tense == 'perfect' else tense
        words = [verb_phrase(v, t, negative, question, impersonal=True)] + ([obj] if obj else [])
    elif tense in ('present', 'perfect'):
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
        if person is None and subj:
            person = '3sm'                               # a noun subject: togadh Cian
        vp = verb_phrase(v, 'imperative', negative, person=person)
        third = _IMP_KEY[person] == '3'
        words = [vp] + ([subj] if third else []) + ([obj] if obj else [])
    else:
        vp = verb_phrase(v, tense, negative, question, person=person)
        synthetic = tense == 'conditional' and person in ('1s', '1p')
        words = [vp] + ([] if synthetic else [_subject(subj, vp)]) + ([obj] if obj else [])
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
    predicate: the pronoun that stands for it (e / i / iad), or an emphatic pronoun (mise…);
    subject: the rest. The past/conditional bu lenites (not d, t: bu tusa, bu dòcha) and is
    elided to b' before a vowel and fh + vowel (GRAMMAR_MORPHOLOGY.md §7.1-7.2):
    B' e Cian a rinn e; cha b' e; bu mhise.
    """
    if tense == 'present':
        head = {(False, False): 'is', (True, False): 'chan', (False, True): 'an', (True, True): 'nach'}[(negative, question)]
    else:
        head = {(False, False): 'bu', (True, False): 'cha bu', (False, True): 'am bu', (True, True): 'nach bu'}[(negative, question)]
        predicate = lenite(predicate, block_dentals='dt')
        if _vowelish(predicate):
            head = head[:-2] + "b'"
    s = ('%s %s %s' % (head, predicate, subject)).rstrip()
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
    aon and dà lenite a singular noun (aon chù, dà chù; aon keeps d, t, s plain;
    pass the dative for a feminine dual: dà làimh); 3-10 take the plural when one
    is given (trì coin); 11-19 add deug (dheug after dà), and 13-19 put the plural
    between unit and deug, the conservative norm (trì bàtaichean deug); 20 and up
    take the singular. Covers 1-99 and the round hundreds and thousand in COUNTING.
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
        body = _ATTRIB[u] + ' ' + (lenite(noun, block_dentals=(u == 1)) if u in (1, 2) else (plural or noun))
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
# Pronunciation (PHONOLOGY.md, implemented)
# ---------------------------------------------------------------
# pronounce() turns Ròdais spelling into a broad phonemic IPA transcription.
# It follows the rules of PHONOLOGY.md for regular spellings: broad and
# slender consonants, the fortis/lenis stops with light pre-aspiration,
# the tense and lax sonorants (four nasals, three laterals, three rhotics),
# lenited consonants, the helping vowel, hiatus, the lengthening and
# diphthongisation before tense sonorants, unstressed reduction, the
# prefixed t-/h-/n-, and eclipsis after the nasal-final article.
# Where Gaelic dialects differ Ròdais takes the conservative realisation
# (cn [kn], four-way nasals, [əɣ] for final -adh, no r-glide before t/d).
# Words the rules get wrong are listed in PRON_EXCEPTIONS.

_PV = set("aeiouàèìòù")
_DIGRAPHS = ('bh', 'ch', 'dh', 'fh', 'gh', 'mh', 'ph', 'sh', 'th', 'll', 'nn', 'rr', 'ng')

# stressed vowel groups: spelling -> phonemes (glide letters absorbed)
_STRESSED = {
    'a': 'a', 'à': 'aː', 'ai': 'a', 'ài': 'aː', 'ao': 'ɯː', 'aoi': 'ɯː',
    'e': 'e', 'è': 'eː', 'ea': 'ɛ', 'eà': 'aː', 'èa': 'iə', 'eai': 'ɛ', 'ei': 'e', 'èi': 'eː',
    'eo': 'ɔ', 'eò': 'ɔː', 'eòi': 'ɔː', 'eoi': 'ɔ', 'eu': 'iə', 'eui': 'iə',
    'i': 'i', 'ì': 'iː', 'ia': 'iə', 'iai': 'iə', 'io': 'i', 'ìo': 'iə', 'ìoi': 'iə',
    'iu': 'u', 'iù': 'uː', 'iùi': 'uː', 'iui': 'u',
    'o': 'ɔ', 'ò': 'ɔː', 'oi': 'ɔ', 'òi': 'ɔː',
    'u': 'u', 'ù': 'uː', 'ua': 'uə', 'uai': 'uə', 'ui': 'u', 'ùi': 'uː',
}
# a short stressed vowel before a tense sonorant (ll, nn, ng, final m) that
# closes the syllable: ceann [kʲʰaun̪ˠ], sinn [ʃiːɲ], fionn [fʲuːn̪ˠ], long [l̪ˠɔuŋk]
_TENSE = {'a': 'au', 'ea': 'au', 'o': 'ɔu', 'i': 'iː', 'io': 'uː', 'u': 'uː', 'ui': 'uːi',
          'ai': 'ai', 'oi': 'ɔi', 'ei': 'ei', 'eo': 'ɔu'}
_BEFORE_RR = {'a': 'aː', 'ea': 'aː', 'o': 'ɔː', 'i': 'iː', 'u': 'uː', 'io': 'iː'}
# a vowel group ending in i + dh/gh: chaidh [xaj], taigh [t̪ʰɤj], oidhche [ɤiçə], Gàidhlig [kaːlʲɪkʲ]
_IDH = {'ai': ('aj', 'ɤj'), 'ài': ('aːj', 'aːj'), 'oi': ('ɤi', 'ɤi'), 'òi': ('ɔːj', 'ɔːj'),
        'ui': ('ɯj', 'ɯj'), 'ùi': ('uːj', 'uːj'), 'ei': ('ej', 'ej'), 'èi': ('eːj', 'eːj'),
        'i': ('iː', 'iː'), 'ì': ('iː', 'iː'), 'uai': ('uəj', 'uəj'), 'aoi': ('ɯːj', 'ɯːj'),
        'eai': ('ɛj', 'ɛj'), 'iui': ('uj', 'uj')}
_BACK = set('aɔoɯuɤ')

# Unstressed proclitics: written without a stress mark.
PRON_CLITICS = {
    'an': 'ən̪ˠ', 'am': 'əm', "a'": 'ə', 'a': 'ə', 'na': 'nə', 'nan': 'nən̪ˠ', 'nam': 'nəm',
    'mo': 'mə', 'do': 't̪ə', 'ar': 'əɾ', 'ur': 'əɾ', 'gu': 'kə', 'gun': 'kən̪ˠ', 'gum': 'kəm',
    'cha': 'xa', 'chan': 'xan', 'is': 'ɪs', "'s": 's', 'ag': 'ək', 'ma': 'mə', 'nach': 'nəx',
    'mura': 'muɾə', 'ri': 'ɾʲə', 'le': 'lʲə', 'de': 'tʃə', 'fo': 'fə', 'mu': 'mə', 'ro': 'ɾə',
    'bu': 'pə', 'don': 't̪ən̪ˠ', 'den': 'tʃən̪ˠ', 'dhan': 'ɣən̪ˠ', 'sa': 'sə', 'san': 'sən̪ˠ', 'o': 'ə', 'mus': 'məs',
}
# Frequent words whose sound the spelling does not predict (without stress mark;
# an internal ˈ marks non-initial stress).
PRON_EXCEPTIONS = {
    'math': 'ma', 'mhath': 'va', 'fhuair': 'huəɾʲ', 'fhèin': 'heːnʲ', 'fèin': 'feːnʲ',
    'mòr': 'moːɾ', 'mhòr': 'voːɾ', 'mòra': 'moːɾə', 'mòran': 'moːɾan', 'mòine': 'moːnʲə',
    'mòir': 'moːɾʲ', 'mhòir': 'voːɾʲ', 'còig': 'kʰoːkʲ', 'dòigh': 'toːj', 'thu': 'u', 'e': 'ɛ',
    'seo': 'ʃɔ', 'robh': 'r̪ˠɔ', 'abhainn': 'a.ɪɲ', 'leabhar': 'ʎɔ.əɾ', 'dòmhnall': 't̪ɔːl̪ˠ',
    'dhomh': 'ɣɔ̃ː', 'dhuibh': 'ɣuj', 'aig': 'ekʲ', 'fhathast': 'hã.əst̪', 'ciamar': 'kʲʰimɛɾ',
    'diluain': 'tʃiˈl̪ˠuənʲ', 'dimàirt': 'tʃiˈmaːɾʲtʃ', 'diciadain': 'tʃiˈkʲʰiət̪ɪnʲ',
    'diardaoin': 'tʃiəɾˈt̪ɯːnʲ', 'dihaoine': 'tʃiˈhɯːnʲə', 'disathairne': 'tʃiˈsahəɾnʲə',
    'didòmhnaich': 'tʃiˈt̪ɔ̃ːnɪç', 'ars': 'aɾs', 'air': 'ɛɾʲ',
    'samhradh': 'sãũɾəɣ', 'geamhradh': 'kʲãũɾəɣ', 'dhachaigh': 'ɣaxɪ',
}
_NASAL_TRIGGERS = {'an', 'am', 'nan', 'nam'}
_LENITING = {'mo', 'do', 'glè', 'ro'}
_ECLIPSE = [('pʲʰ', 'bʲ'), ('pʰ', 'b'), ('t̪ʰ', 'd̪'), ('tʃʰ', 'dʒ'), ('kʲʰ', 'ɡʲ'), ('kʰ', 'ɡ')]
_ECLIPSE_LENIS = [('pʲ', 'mʲ'), ('p', 'm'), ('t̪', 'n̪ˠ'), ('tʃ', 'ɲ'), ('kʲ', 'ɲ'), ('k', 'ŋ')]


def _units(cluster):
    out, i = [], 0
    while i < len(cluster):
        if cluster[i:i + 2] in _DIGRAPHS:
            out.append(cluster[i:i + 2]); i += 2
        else:
            out.append(cluster[i]); i += 1
    return out


def _segment(word):
    """Split a word into alternating ('C', units) and ('V', group) pieces."""
    segs, i = [], 0
    while i < len(word):
        j = i
        isv = word[i] in _PV
        while j < len(word) and (word[j] in _PV) == isv:
            j += 1
        segs.append(('V', word[i:j]) if isv else ('C', _units(word[i:j])))
        i = j
    return segs


def _q(group, first):
    """Consonant quality from a vowel group: its first letter if the group follows, else its last."""
    ch = group[0] if first else group[-1]
    return 's' if ch in 'eièì' else 'b'


def _nasalise(ph):
    return ph[0] + '̃' + ph[1:] if ph else ph


def _word_ipa(word, lenis_initial=False, after_prefix_t=False):
    w = word.lower()
    if w in PRON_EXCEPTIONS:
        return PRON_EXCEPTIONS[w]
    segs = _segment(w)
    vidx = [k for k, s in enumerate(segs) if s[0] == 'V']
    stressed_k = vidx[0] if vidx else None
    out = []
    skip_units = {}          # seg index -> number of leading units consumed by the vowel before
    vowel_phone = {}         # seg index -> phones chosen for a vowel group
    for k, (kind, val) in enumerate(segs):
        if kind == 'V':
            g = val
            nxt = segs[k + 1][1] if k + 1 < len(segs) else []
            final_cluster = k + 2 >= len(segs)
            u0 = nxt[0] if nxt else None
            if k == stressed_k:
                if u0 in ('dh', 'gh') and g in _IDH and (len(nxt) > 1 or final_cluster):
                    ph = _IDH[g][0 if u0 == 'dh' else 1]
                    if g == 'ài' and not final_cluster:
                        ph = 'aː'
                    skip_units[k + 1] = 1
                elif u0 in ('ll', 'nn', 'ng') and (len(nxt) > 1 or final_cluster) and g in _TENSE:
                    ph = _TENSE[g]
                elif u0 == 'm' and len(nxt) == 1 and final_cluster and g in _TENSE:
                    ph = _TENSE[g]
                elif u0 == 'rr' and g in _BEFORE_RR:
                    ph = _BEFORE_RR[g]
                elif g == 'ui':
                    ph = 'ɯ' if u0 in ('n', 'nn', 's', 'g', 'c') else 'u'
                elif g == 'ea':
                    ph = 'e' if u0 in ('g', 'c') else 'a' if u0 == 'l' else 'ɛ'
                elif g == 'aoi' and not nxt:
                    ph = 'ɯi'                                  # naoi [n̪ˠɯi]
                elif g in _STRESSED:
                    ph = _STRESSED[g]
                else:
                    ph = _STRESSED.get(g[-1], g)
                if g[0] in 'ie' and ph[0] in 'uɔa' and (k == 0 or segs[k - 1][1] == ['fh']):
                    ph = 'j' + ph                              # Iuchar [juxəɾ], fheàrr [jaːr̪ˠ]
            else:
                if any(c in 'àèìòù' for c in g) or g in ('ia', 'ua', 'uai', 'iai', 'eu'):
                    ph = _STRESSED.get(g, 'ə')
                elif u0 in ('dh', 'gh') and final_cluster and g[-1] == 'i':
                    ph = 'i'; skip_units[k + 1] = 1          # -aidh, -idh [i]
                elif g[-1] == 'i':
                    ph = 'ɪ'
                elif g in ('a', 'ea') and u0 == 'n':
                    ph = 'a'                                  # -an, -ean
                elif g in ('a', 'ea') and u0 == 'g' and final_cluster:
                    ph = 'a'                                  # -ag, -eag
                else:
                    ph = 'ə'
            vowel_phone[k] = ph
            out.append(ph)
            continue
        # consonant cluster
        units = val[skip_units.get(k, 0):]
        if not units:
            continue
        initial = k == 0
        final = k == len(segs) - 1
        prevg = segs[k - 1][1] if k > 0 else None
        nextg = segs[k + 1][1] if k + 1 < len(segs) else None
        q = _q(nextg, True) if nextg else _q(prevg, False)
        after_stressed = k - 1 == stressed_k
        prev_ph = vowel_phone.get(k - 1, '')
        short_mono = after_stressed and len(prev_ph) == 1
        cl = []
        epenthesis = (short_mono and len(units) >= 2 and units[0] in ('l', 'n', 'r')
                      and units[1] in ('b', 'bh', 'g', 'ch', 'm', 'mh'))
        for i, u in enumerate(units):
            s = q == 's'
            if initial and i + 1 < len(units) and units[i + 1] == 'r':
                s = False                                      # trì [t̪ʰɾʲiː]: C before r is broad
            onset0 = initial and i == 0
            after_v = i == 0 and not initial
            prev = units[i - 1] if i else None
            nx = units[i + 1] if i + 1 < len(units) else None
            last = final and i == len(units) - 1
            if u == 'b':
                p = 'p'
            elif u == 'p':
                p = 'pʰ' if onset0 else 'ʰp' if after_v else 'p'
            elif u == 't':
                if after_prefix_t and onset0:
                    p = 'tʃʰ' if s else 't̪ʰ'
                else:
                    p = ('tʃʰ' if s else 't̪ʰ') if onset0 else ('ʰtʃ' if s else 'ʰt̪') if after_v else ('tʃ' if s else 't̪')
            elif u in ('c', 'k', 'q'):
                p = ('kʲʰ' if s else 'kʰ') if onset0 else ('ʰkʲ' if s else 'ʰk') if after_v else ('kʲ' if s else 'k')
            elif u == 'd':
                p = 'k' if prev == 'ch' else ('tʃ' if s else 't̪')
            elif u == 'g':
                p = 'kʲ' if s else 'k'
            elif u == 'ng':
                p = ('ɲkʲ' if s else 'ŋk') if last else ('ɲ' if s else 'ŋ')
            elif u in ('f', 'ph'):
                p = 'f'
            elif u == 'fh':
                p = ''
            elif u == 'm':
                p = 'm'
            elif u == 'mh':
                if onset0 or last or nx is None:
                    p = 'v'
                else:                                          # vocalised: samhradh-type
                    p = 'ũ' if out and out[-1][-1:] in ('a', 'ɛ') else ''
                    if out:
                        out[-1] = _nasalise(out[-1])
            elif u == 'bh':
                p = '' if (last and prev_ph.endswith('u') and i == 0) else 'v'
            elif u == 'ch':
                p = 'ç' if s else 'x'
            elif u in ('dh', 'gh'):
                if onset0:
                    p = 'j' if s else 'ɣ'
                elif last and not s and (u == 'dh' or not after_stressed):
                    p = 'ɣ'                                    # ruadh [r̪ˠuəɣ], -adh [əɣ]; but diugh [tʃu]
                else:
                    p = ''
            elif u == 'th':
                if onset0:
                    p = 'h'
                elif last:
                    p = 'h' if short_mono else ''
                elif nx is None and nextg and (nextg[-1] == 'i' or (
                        k + 2 < len(segs) and segs[k + 2][1][:1] == ['n'])):
                    p = 'h'                                    # athair, màthair, bothan
                else:
                    p = ''                                     # latha, rathad: hiatus
            elif u == 'sh':
                p = 'h'
            elif u == 's':
                if onset0 and nx == 'r':
                    p = 'st̪'                                  # sràid [st̪ɾaːtʃ]
                elif onset0 and nx in ('c', 'p', 'm', 'k'):
                    p = 's'                                    # scian [skʲiən]: sc is always [sk]
                else:
                    p = 'ʃ' if s else 's'
            elif u in ('l', 'll'):
                if u == 'll' or (onset0 and not lenis_initial):
                    p = 'ʎ' if s else 'l̪ˠ'
                else:
                    p = 'lʲ' if s else 'l̪ˠ'
            elif u in ('n', 'nn'):
                if u == 'nn' or (onset0 and not lenis_initial):
                    p = 'ɲ' if s else 'n̪ˠ'
                elif nx in ('t', 'd', 'c', 'g') and not initial:
                    p = 'ɲ' if s else 'n̪ˠ'                    # slàinte [sl̪ˠaːɲtʃə]: tense before a stop
                elif initial and prev in ('c', 'g', 'm', 't'):
                    p = 'ɲ' if s else 'n̪ˠ'                    # cnoc [kʰn̪ˠɔʰk]: the old [kn]
                else:
                    p = 'nʲ' if s else 'n'
            elif u in ('r', 'rr'):
                if u == 'rr' or (onset0 and not lenis_initial):
                    p = 'r̪ˠ'
                else:
                    p = 'ɾʲ' if s else 'ɾ'
            elif u == 'h':
                p = 'h'
            elif u == 'w':
                p = 'w'
            elif u == 'v':
                p = 'v'
            elif u == 'y':
                p = 'j'
            else:
                p = u
            cl.append(p)
            if epenthesis and i == 0:
                cl.append(prev_ph)
        joined = ''.join(cl)
        if not joined and 0 < k < len(segs) - 1:
            joined = '.'                                       # hiatus
        out.append(joined)
    # slender labial + back vowel after the vowel was computed (fionn [fʲuːn̪ˠ])
    res = ''.join(out)
    if segs and segs[0][0] == 'C' and len(segs) > 1 and _q(segs[1][1], True) == 's':
        first = segs[0][1]
        if len(first) == 1 and first[0] in ('b', 'p', 'f', 'm', 'bh', 'mh', 'ph'):
            head = out[0]
            if 'ʲ' not in head and out[1][:1] in _BACK:
                res = head[0] + 'ʲ' + head[1:] + ''.join(out[1:])
    return res


def _split_token(tok):
    """Strip punctuation around a token; keep elision apostrophes."""
    lead = ''
    while tok and tok[0] in '"“”(«[':
        tok = tok[1:]
    trail = ''
    while tok and tok[-1] in '.,;:!?"“”)»]…':
        trail = tok[-1] + trail
        tok = tok[:-1]
    return tok, trail


_ELIDED = {"dh'": ('ɣ', 'j'), "m'": ('m', 'm'), "d'": ('t̪', 'tʃ'), "th'": ('h', 'h'),
           "b'": ('p', 'p'), "t'": ('t̪ʰ', 'tʃʰ'), "bh'": ('v', 'v'), "'n": ('n̪ˠ', 'ɲ')}


def _first_vowel_slender(word):
    for ch in word.lower():
        if ch in _PV:
            return ch in 'eièì'
    return False


def pronounce(text):
    """
    Ròdais spelling -> broad phonemic IPA (PHONOLOGY.md).
    Each stressed word carries ˈ on its first syllable (unstressed proclitics
    like an, a', mo, gu carry none); a comma or colon gives |, a sentence end ‖.
    pronounce("uisce") -> 'ˈɯʃkʲə';  pronounce("an cù") -> 'əŋ ˈɡuː'
    """
    text = normalize(text).replace('’', "'")
    raw = text.split()
    # pass 1: tokens -> (key, clitic_prefix, word, trail)
    toks = []
    pending = None
    for r in raw:
        t, trail = _split_token(r)
        low = t.lower()
        if not t:
            continue
        if low in _ELIDED and low not in ("a'",):
            pending = low
            continue
        m = None
        for el in sorted(_ELIDED, key=len, reverse=True):
            if low.startswith(el) and len(low) > len(el) and el != "'n":
                m = el
                break
        pre = pending
        if m and pre is None:
            pre, low = m, low[len(m):]
        pending = None
        toks.append((pre, low, trail))
    out = []
    prev_word = None
    for pre, low, trail in toks:
        lenis = prev_word in _LENITING
        if low in PRON_CLITICS and pre is None:
            ipa = PRON_CLITICS[low]
        elif low == "'s" or low == 's':
            ipa = 's'
        else:
            parts = low.split('-')
            pieces = []
            for pi, part in enumerate(parts):
                if not part:
                    continue
                nextp = parts[pi + 1] if pi + 1 < len(parts) else ''
                if part in ('t', 'h', 'n') and nextp:
                    continue                               # handled with the next part
                prefix = parts[pi - 1] if pi and parts[pi - 1] in ('t', 'h', 'n') else None
                body = part
                if prefix == 't' and body[:1] == 's':
                    body = body[1:]                        # an t-sràid: the s is silent
                if prefix == 't':
                    p = _word_ipa('t' + body, after_prefix_t=True)
                    if part[:1] == 's':
                        p = p.replace('t̪ʰ', 't̪', 1).replace('tʃʰ', 'tʃ', 1)
                elif prefix == 'h':
                    p = 'h' + _word_ipa(body)
                elif prefix == 'n':
                    p = ('ɲ' if _first_vowel_slender(body) else 'n̪ˠ') + _word_ipa(body)
                else:
                    p = _word_ipa(body, lenis_initial=(lenis and pi == 0))
                proclitic = pi == 0 and len(parts) > 1 and part in ('a', 'an', 'am', 'ma', 'mu', 'co')
                if proclitic:
                    p = PRON_CLITICS.get(part, p)
                elif 'ˈ' not in p:
                    p = 'ˈ' + p
                pieces.append(p)
            ipa = ''.join(pieces)
            if pre:
                c = _ELIDED[pre][1 if _first_vowel_slender(low) else 0]
                if low.startswith('fh') and ipa.lstrip('ˈ').startswith('h'):
                    ipa = ipa.replace('h', '', 1)          # d' fhuair [t̪uəɾʲ]
                ipa = 'ˈ' + c + ipa.lstrip('ˈ')
        # eclipsis after the nasal-final article and its kin (PHONOLOGY.md §9)
        if (prev_word in _NASAL_TRIGGERS and out and low[:1] in 'bcdgpt'
                and not low.startswith(('bh', 'ch', 'dh', 'gh', 'ph', 'th', 't-', 'h-', 'n-'))):
            body = ipa.lstrip('ˈ')
            done = False
            for a, b in _ECLIPSE:
                if body.startswith(a):
                    body = b + body[len(a):]; done = True
                    velar = b[0] == 'ɡ'
                    if velar:
                        out[-1] = out[-1].replace('n̪ˠ', 'ŋ')
                    break
            if not done and body[:1] == 'k':
                out[-1] = out[-1].replace('n̪ˠ', 'ŋ')             # an gille [əŋ ˈkʲiʎə]
            if not done and prev_word in ('nan', 'nam'):
                for a, b in _ECLIPSE_LENIS:
                    if body.startswith(a):
                        body = b + body[len(a):]
                        out[-1] = 'nə'                               # nam bàta [nə ˈmaːʰt̪ə]
                        break
            ipa = ('ˈ' if ipa.startswith('ˈ') else '') + body
        elif prev_word in ('nan', 'nam') and low.startswith('f') and not low.startswith('fh'):
            ipa = ipa.replace('f', 'v', 1)
            out[-1] = 'nə'
        out.append(ipa)
        if trail:
            if any(c in trail for c in '.!?'):
                out.append('‖')
            elif any(c in trail for c in ',;:'):
                out.append('|')
        prev_word = low if pre is None else None
    while out and out[-1] in ('‖', '|'):
        out.pop()
    return ' '.join(out)


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
    # dh' before a vowel and fh + vowel only; fh + consonant stands alone (TEXTS: "fhreagair Fionn")
    freagair, fliuch = Verb('freagair', 'freagairt'), Verb('fliuch', 'fliuchadh')
    eq(freagair.form('past'), "fhreagair"); eq(fliuch.form('past'), "fhliuch")
    eq(Verb('faighnich', 'faighneachd').form('past'), "dh'fhaighnich"); eq(Verb('fàs', 'fàs').form('past'), "dh'fhàs")
    eq(freagair.form('conditional'), "fhreagradh"); eq(verb_phrase(freagair, 'past', negative=True), "cha do fhreagair")
    # the relative future: lenited, dh' like the past (a dh'òlas, ma dh'èisteas, nuair a dh'fhaighnicheas)
    eq(ol.form('relative'), "dh'òlas"); eq(fag.form('relative'), "dh'fhàgas")
    eq(Verb('èist', 'èisteachd').form('relative'), "dh'èisteas")
    eq(Verb('faighnich', 'faighneachd').form('relative'), "dh'fhaighnicheas")
    eq(Verb('bris', 'briseadh').form('relative'), "bhriseas"); eq(freagair.form('relative'), "fhreagras")
    # syncopating verbs (GRAMMAR_MORPHOLOGY.md §6.3)
    caidil, foscail, innis, bruidhinn = (verb('caidil', 'cadal'), verb('foscail', 'foscladh'),
                                         verb('innis', 'innse'), verb('bruidhinn', 'bruidhinn'))
    tachair, labhair, iomair = verb('tachair', 'tachairt'), verb('labhair', 'labhairt'), verb('iomair', 'iomradh')
    eq(caidil.form('future'), "cadlaidh"); eq(caidil.form('conditional'), "chadladh")
    eq(caidil.form('conditional', person='1s'), "chadlainn"); eq(caidil.form('imperative', person='2p'), "cadlaibh")
    eq(caidil.form('past'), "chaidil"); eq(caidil.form('imperative'), "caidil"); eq(caidil.form('future', dependent=True), "caidil")
    eq(foscail.form('future'), "fosclaidh"); eq(foscail.form('conditional'), "dh'fhoscladh")
    eq(foscail.form('imperative', person='2p'), "fosclaibh")
    eq(innis.form('future'), "innsidh"); eq(innis.form('conditional'), "dh'innseadh")   # a dh'innseadh dhaibh (TEXTS)
    eq(bruidhinn.form('future'), "bruidhnidh"); eq(bruidhinn.form('conditional'), "bhruidhneadh")
    eq(bruidhinn.form('past'), "bhruidhinn")                                       # Bhruidhinn guth (TEXTS)
    eq(freagair.form('future'), "freagraidh"); eq(freagair.form('imperative', person='2p'), "freagraibh")
    eq(tachair.form('future'), "tachraidh"); eq(tachair.form('conditional'), "thachradh")
    eq(labhair.form('future'), "labhraidh"); eq(iomair.form('conditional'), "dh'iomradh")
    eq(caidil.form('relative'), "chadlas"); eq(Verb('ceangail', 'ceangal', stem='ceangl').form('future'), "ceanglaidh")
    # the synthetic 1 pl. (-amaid) and the full imperative
    tog, bris = Verb('tog', 'togail'), Verb('bris', 'briseadh')
    eq(tog.form('conditional', person='1p'), "thogamaid"); eq(bris.form('conditional', person='1p'), "bhriseamaid")
    eq(ol.form('conditional', person='1p'), "dh'òlamaid"); eq(fag.form('conditional', person='1p'), "dh'fhàgamaid")
    eq(tog.form('conditional', dependent=True, person='1p'), "togamaid")
    eq(tog.form('imperative', person='1p'), "togamaid"); eq(bris.form('imperative', person='1p'), "briseamaid")
    eq(tog.form('imperative', person='1s'), "togam"); eq(bris.form('imperative', person='1s'), "briseam")
    eq(tog.form('imperative', person='3sm'), "togadh"); eq(bris.form('imperative', person='3p'), "briseadh")
    eq(verb_phrase(tog, 'imperative', negative=True, person='1p'), "na togamaid")
    eq(verb_phrase(ol, 'imperative', negative=True), "na h-òl")
    eq(clause(tog, 'conditional', '1p'), "Thogamaid."); eq(clause(tog, 'imperative', '1p'), "Togamaid.")
    eq(clause(tog, 'imperative', '3sm'), "Togadh e."); eq(clause(tog, 'imperative', 'Cian', 'an long'), "Togadh Cian an long.")
    eq(IRREGULAR['bi'].form('conditional', person='1p'), "bhitheamaid"); eq(IRREGULAR['faic'].form('conditional', True, '1p'), "faiceamaid")
    eq(IRREGULAR['dèan'].form('imperative', person='1p'), "dèanamaid"); eq(IRREGULAR['rach'].form('imperative', person='1s'), "racham")
    eq(IRREGULAR['thig'].form('imperative', person='3sf'), "thigeadh"); eq(IRREGULAR['bi'].form('imperative', person='2p'), "bithibh")
    eq(verb_phrase(IRREGULAR['dèan'], 'conditional', negative=True, person='1p'), "cha dèanamaid")
    # impersonal forms (GRAMMAR_MORPHOLOGY.md §6.4, §6.9)
    I, faic = IMPERSONAL, IRREGULAR['faic']
    eq(tog.form('past', person=I), "thogadh"); eq(bris.form('past', person=I), "bhriseadh")
    eq(ol.form('past', person=I), "dh'òladh"); eq(fag.form('past', True, I), "do dh'fhàgadh")
    eq(tog.form('future', person=I), "togar"); eq(bris.form('future', person=I), "brisear"); eq(ol.form('future', person=I), "òlar")
    eq(tog.form('conditional', person=I), "thogtadh"); eq(bris.form('conditional', person=I), "bhristeadh")
    eq(ol.form('conditional', person=I), "dh'òltadh"); eq(fag.form('conditional', True, I), "fàgtadh")
    eq(ceannaich.form('conditional', person=I), "cheannaichteadh"); eq(ceannaich.form('future', person=I), "ceannaichear")
    eq(tog.form('imperative', person=I), "togtar"); eq(bris.form('imperative', person=I), "bristear")
    eq(caidil.form('future', person=I), "cadlar"); eq(foscail.form('past', person=I), "dh'fhoscladh")
    eq(verb_phrase(tog, 'future', negative=True, impersonal=True), "cha togar")
    eq(verb_phrase(bris, 'past', negative=True, impersonal=True), "cha do bhriseadh")
    eq(verb_phrase(faic, 'past', negative=True, impersonal=True), "chan fhacas")
    eq(verb_phrase(IRREGULAR['faigh'], 'past', negative=True, impersonal=True), "cha d' fhuaireadh")
    eq(IRREGULAR['beir'].form('past', person=I), "rugadh"); eq(IRREGULAR['dèan'].form('future', person=I), "nithear")
    eq(IRREGULAR['faic'].form('conditional', True, I), "faicteadh"); eq(IRREGULAR['rach'].form('past', True, I), "deachas")
    eq(IRREGULAR['cluinn'].form('past', person=I), "chualas"); eq(IRREGULAR['thoir'].form('future', True, I), "toirear")
    eq(BI.form('present', person=I), "thathar"); eq(verb_phrase(BI, 'present', question=True, impersonal=True), "a bheilear")
    eq(BI.form('conditional', person=I), "bhite"); eq(BI.form('past', True, I), "robhar")
    eq(clause(faic, 'past', None, 'iad', negative=True, impersonal=True, extra='a-riamh tuilleadh'),
       "Chan fhacas iad a-riamh tuilleadh.")                                              # tale of the Old Ones
    eq(clause(IRREGULAR['faigh'], 'past', None, 'sgeul orra', negative=True, impersonal=True, extra='tuilleadh'),
       "Cha d' fhuaireadh sceul orra tuilleadh.")                                         # tale of the water horse
    eq(clause(IRREGULAR['beir'], 'past', None, 'mi', impersonal=True, extra='ann an Seann Dunn'),
       "Rugadh mi ann an Seann Dunn.")
    eq(clause(BI, 'present', None, impersonal=True, extra="ag ràdh"), "Thathar ag ràdh.")
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
    eq(copula('e', 'Cian a rinn e', tense='past'), "B' e Cian a rinn e.")   # bu elides before a vowel
    eq(copula('e', 'ainm a thagh iad', tense='past', negative=True), "Cha b' e ainm a thagh iad.")
    eq(copula('e', 'Fionn', tense='past', question=True), "Am b' e Fionn?")
    eq(copula('mise', 'Eilidh', tense='past'), "Bu mhise Eilidh."); eq(copula('tusa', 'an t-oide', tense='past'), "Bu tusa an t-oide.")
    # prepositional pronouns, object particles
    eq(prep_pronoun('aig', '1s'), "agam"); eq(prep_pronoun('le', '3sf'), "leatha")
    eq(object_particle('3sm', 'faicinn'), "ga fhaicinn"); eq(object_particle('1s', 'faicinn'), "gam fhaicinn")
    eq(object_particle('3sf', 'ithe'), "ga h-ithe")
    # numbers
    eq(number(2, 'cù'), "dà chù"); eq(number(3, 'cù', 'coin'), "trì coin"); eq(number(1, 'taigh'), "aon taigh")
    eq(number(1, 'bàta'), "aon bhàta")
    eq(number(12), "a dhà dheug"); eq(number(12, 'cù'), "dà chù dheug"); eq(number(20, 'cù'), "fichead cù")
    eq(number(45), "ceathrad còig")
    # 13-19: the plural between unit and deug, the conservative norm (GRAMMAR_MORPHOLOGY.md §8.1)
    eq(number(13, 'bàta', 'bàtaichean'), "trì bàtaichean deug"); eq(number(15, 'cù', 'coin'), "còig coin deug")
    eq(number(11, 'bàta', 'bàtaichean'), "aon bhàta deug"); eq(number(11, 'taigh'), "aon taigh deug")
    eq(number(12, 'bàta', 'bàtaichean'), "dà bhàta dheug"); eq(number(2, 'làimh'), "dà làimh")
    eq(number(19, 'latha'), "naoi latha deug")         # no plural given: bliadhna, latha stay singular
    # place names
    eq(place_name('Cathair', 'mòr'), "Cathair mhòr"); eq(place_name('Abhainn', 'sgìth'), "Abhainn scìth")
    # pronunciation (PHONOLOGY.md): well-known Scottish Gaelic values in Ròdais spelling
    P = pronounce
    for word, ipa in [
        ("bàta", "ˈpaːʰt̪ə"), ("uisce", "ˈɯʃkʲə"), ("athair", "ˈahɪɾʲ"), ("beag", "ˈpek"),
        ("dubh", "ˈt̪u"), ("oidhche", "ˈɤiçə"), ("Gàidhlig", "ˈkaːlʲɪkʲ"), ("taigh", "ˈt̪ʰɤj"),
        ("math", "ˈma"), ("loch", "ˈl̪ˠɔx"), ("cnoc", "ˈkʰn̪ˠɔʰk"), ("fhuair", "ˈhuəɾʲ"),
        ("mhàthair", "ˈvaːhɪɾʲ"), ("ceann", "ˈkʲʰaun̪ˠ"), ("sinn", "ˈʃiːɲ"), ("dearg", "ˈtʃɛɾɛk"),
        ("gorm", "ˈkɔɾɔm"), ("Alba", "ˈal̪ˠapə"), ("marbh", "ˈmaɾav"), ("duine", "ˈt̪ɯnʲə"),
        ("caileag", "ˈkʰalʲak"), ("latha", "ˈl̪ˠa.ə"), ("piuthar", "ˈpʲʰu.əɾ"), ("iasc", "ˈiəsk"),
        ("scoil", "ˈskɔlʲ"), ("sràid", "ˈst̪ɾaːtʃ"), ("ceud", "ˈkʲʰiət̪"), ("gille", "ˈkʲiʎə"),
        ("ruadh", "ˈr̪ˠuəɣ"), ("craobh", "ˈkʰɾɯːv"), ("dèan", "ˈtʃiən"), ("seachd", "ˈʃɛxk"),
        ("chaidh", "ˈxaj"), ("tighinn", "ˈtʃʰi.ɪɲ"), ("mac", "ˈmaʰk"), ("Ròdais", "ˈr̪ˠɔːt̪ɪʃ"),
        ("ceòl", "ˈkʲʰɔːl̪ˠ"), ("slàinte", "ˈsl̪ˠaːɲtʃə"), ("samhradh", "ˈsãũɾəɣ"),
    ]:
        eq(P(word), ipa)
    eq(P("an t-uisce"), "ən̪ˠ ˈt̪ʰɯʃkʲə"); eq(P("an t-sràid"), "ən̪ˠ ˈt̪ɾaːtʃ")
    eq(P("an cù"), "əŋ ˈɡuː"); eq(P("nam bàtaichean"), "nə ˈmaːʰt̪ɪçan")
    eq(P("na h-eileanan"), "nə ˈhelʲanan"); eq(P("cha d' fhuair"), "xa ˈt̪uəɾʲ")
    eq(P("a-màireach"), "əˈmaːɾʲəx"); eq(P("mo mhàthair"), "mə ˈvaːhɪɾʲ")
    eq(P("Tha gu math, gu robh math agaibh."), "ˈha kə ˈma | kə ˈr̪ˠɔ ˈma ˈakɪv")

    bad = [(g, w) for ok, g, w in checks if not ok]
    for g, w in bad:
        print('FAIL  got %r  want %r' % (g, w))
    print('%d/%d checks passed' % (len(checks) - len(bad), len(checks)))
    return not bad


if __name__ == "__main__":
    import sys
    sys.exit(0 if _selftest() else 1)
