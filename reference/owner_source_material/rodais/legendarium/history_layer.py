"""
history_layer.py -- the history carried on the master map itself (the reconcile layer "history").

The master (Rodos_finished.map, Diathir_Atlas/Diathir.map) is the island at the close of DE 27. This layer puts on it
what the annals, the Books and the appendices tell of how it came to be so, each thing on the map where the canon sets
it, with its date and a short note:

  * the Moot, Tional nan Tuathach, as a second state: its eleven shires (Appendix H III), its seat Caol mhòr, the
    kingdom its suzerain (the Moot has no standing in law and speaks for shires of the kingdom), notes on both states;
  * the wars: An Cogadh Fada and its battles as the kingdom's campaigns (the map's calendar is the Dubhan Era, so
    only the wars of this era can be campaigns), every war of Appendix C in the war chronicle (Azgaar's relations
    history), and every named battle, siege and raid of Appendix C's table as a battlefield marker, with the peace
    sites and the regiments' stone;
  * the Making: the mason's fire and slab, the Keeper's grove, the seven lightings of the coals (the second is the
    summit marker Binnean a' Chlachair already on the map), Taigh Dhuinn, Cidhe an Diosail and An Sloc Mòr;
  * the journeys as named routes: An t-Aiseag (the Crossing, north-about), Am Falbh (the Setting-Out), Fenn's line,
    the Leaden Hawk's road and the two pilgrim roads to Allt an Àigh;
  * zones: Ceò Mhanannain on the northern and eastern seas, and the plagues and famines of Appendix C besides the
    five districts already drawn, which get their notes;
  * the seven coals as goods of the vein at An Sloc Mòr, sold in no market (Appendix G);
  * notes on the 123 shires from Appendix H's table.

Names are Dia-thìris, as eras/NAMES.json gives them; notes are short English prose, every date the annals' own.

How it is made. The content is below. `spec` writes it as an era-engine spec (reconcile/history_spec.json); `bake`
builds the map as it stood before this layer (finish_map.py with RODAIS_RECONCILE_EXCLUDE=history), applies the
spec to it in Azgaar itself through the era engine (eras/engine/build_era_map.py: the states' statistics,
neighbours, poles and arms, the routes' paths and saved drawings, the markers' coordinates and the zones' cells are
all Azgaar's own), and writes the difference, record by record, as the edits of reconcile/history.json, which
map_reconcile.py applies like every other layer. The goods of the coals are added by the bake directly (the engine
does not add goods). Nothing here runs when the map is built: finish_map.py only reads history.json, so the build
stays byte for byte.

    python3 history_layer.py spec
    python3 history_layer.py bake        (needs Node, Playwright and Chromium, as the era engine does)
"""
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RECON = os.path.join(HERE, 'reconcile')
SPEC = os.path.join(RECON, 'history_spec.json')
OUT = os.path.join(RECON, 'history.json')
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
import rodais_engine as R  # noqa: E402
import map_reconcile as MR  # noqa: E402

EV = {e['id']: e for e in json.load(open(os.path.join(HERE, 'annals_dated.json'), encoding='utf-8'))}
NAMES = {n['dt'] for n in json.load(open(os.path.join(ROOT, 'eras', 'NAMES.json'), encoding='utf-8'))['names']}


def date(i):
    return EV[i]['date']


def year(i):
    return EV[i]['date'].split(', ')[-1]


def fill(text):
    """{I-0001} -> the event's date; {year:I-0001} -> its era year."""
    text = re.sub(r'\{year:([IVX]+-\d+[a-z]?)\}', lambda m: year(m.group(1)), text)
    return re.sub(r'\{([IVX]+-\d+[a-z]?)\}', lambda m: date(m.group(1)), text)


# ---------------------------------------------------------------- the Moot
MOOT_SHIRES = [7, 14, 23, 28, 36, 75, 86, 88, 105, 107, 122]          # Appendix H III, the Tuathaich shires
KINGDOM_NOTE = (
    "Rìoghachd Dia-thìr, declared at Cathair dhearg on {V-0007} and ruled from there since: the crown, the royal "
    "council of twelve and the Treasury. Niall, first of the restored line, was crowned on {V-0012}; Cathal was "
    "crowned at Lùnastal, {VI-0006}, and reigns in the present year. It holds a hundred and twenty-three shires and "
    "every coast but the windy coast of the far north-west, which no shire holds; it keeps no envoys and makes no "
    "treaties. Its one war, An Cogadh Fada, was fought on its own ground against its own people ({year:VI-0081} to "
    "{year:VI-0118}). The nine regiments and four fleets raised for it stand on their stations, paid from the "
    "wartime tithe laid on {VI-0086} and never lifted ({VI-0131}).")
MOOT_NOTE = (
    "Tional nan Tuathach, the Moot. Tuathaich householders of the northern towns first met at Caol mhòr on "
    "{V-0008} and chose Walter Hale, once a harbour clerk, for their speaker; the minute-books run unbroken from that "
    "day. It has no standing in Dia-thìrich law and has never asked for any: its eleven shires are shires of the "
    "kingdom, with Dia-thìrich maoir, drawn here apart because the Moot speaks for them. It stood apart from An "
    "Cogadh Fada and fed the hungry. Martha Greaves carried its last petition to the council on Christmas Day, "
    "{VI-0077}; after the war the motion for amends was let die ({VI-0138}), and the Moot's minute on it reads "
    "'Allowed to die.' ({VI-0139}). Tuathaich speakers call the tabled request to the Library and the dead motion "
    "together seann-chunntas, an old reckoning that none in power will settle and none has cancelled ({VI-0143}). "
    "Since {VI-0149}, the Tuathaich going south must show a pass at the boundary stones on the northern road. In the "
    "present year it meets under Peter Hale, great-grandson of its first speaker ({VI-0153}).")

# ---------------------------------------------------------------- the wars: the chronicle (Azgaar's relations history)
CHRONICLE = [
    ("Creach an t-Salainn", ['I-0099', 'I-0104'], [
        "{I-0099}: Mòrag Chruaidh, fifth of the Stone Kings, raids the salt-pans on the southern shore at Baile "
        "ghorm and carries off the salt. Seven fall on the hill side. It is the first war in either king-list.",
        "{I-0104}: Iain Dubh, sixth of the Stone Kings, goes down to raid the salt-pans again and is slain on the "
        "shingle at Baile ghorm."]),
    ("Blàr Àth na Fala", ['I-0098a'], [
        "{I-0255b}: Dùn dhearg and the households east of the vein swear to owe nothing to Dùn ìseal nor to its king.",
        "{I-0098a}: Ailean Mòr holds the ford below Dùn dhearg alone three days and three nights against their host, "
        "until the dead dam the river, and falls on the third night. His kin do not come. The ford is called Àth na "
        "Fala after."]),
    ("Aimhreit nan Oighrean", ['II-0001c', 'II-0064c'], [
        "{II-0001c}: first blood among the heirs at Dùn thais, on the line between the great share of the north and "
        "the Red Share; Aonghas Bàn mac Mhurchaidh is killed.",
        "The strife runs some five hundred and fifty years in raids, burnings and killings between kin. Its last and "
        "worst is Cogadh an Dà Mhionn, the War of the Two Oaths.",
        "{II-0064b}: Loscadh Achadh mhòr. Fearghas Dà-Mhionn, sworn to both sides, sees his granary fields burned "
        "to the stubble and dies in his hall; the middle of the island goes hungry that winter.",
        "{II-0064c}: the lords of the shares swear Sìth an Stairsnich on the threshold of Talla na Lasrach, with the "
        "Keeper as witness."]),
    ("Cogadh nan Rathad", ['II-0093', 'II-0099'], [
        "{II-0093}: Iain Garbh of Dùn dhearg burns the toll-house at Muileann òg: the first war fought over a road.",
        "{II-0095}: Blàr Àth fhiadhaich. The men of Caol leathan hold the ford a day; forty dead.",
        "{II-0096}: Lachlann Ciar's men burn Baile ghlas as they fall back. {II-0097}: Baile chiar shuts its gate "
        "on both hosts and feeds the burned-out folk.",
        "{II-0098}: Sèist Caol leathan. The harbour is never closed; the siege ends without an assault.",
        "{II-0099}: the peace under the roof of Am Buabhall Fortanach. Caol leathan keeps half its tolls."]),
    ("Falachd an Airgid", ['II-0150', 'II-0151'], [
        "{II-0150}: Ruairidh Liath demands one ring in five of the silver of Muileann chiar, and the silversmiths "
        "close the workings sooner than pay.",
        "{II-0151}: for three seasons no silver leaves Muileann chiar. A closing of the roads and no war; no one is "
        "killed in it."]),
    ("Cogadh nan Trì Tagraichean", ['III-0104', 'III-0112'], [
        "{III-0104}: Catrìona nic Aonghais, Dùghall Garbh and Raghnall Ruadh claim the crown, and the seven houses "
        "divide among them. Seann Warr declares for none ({III-0105}).",
        "{III-0106}: Blàr Àth shean. Dùghall breaks Raghnall's host; some three hundred dead, most drowned.",
        "{III-0108}: Sèist Cathair dhomhain. Catrìona takes the town after forty days.",
        "{III-0109}: Raghnall, holding the vein-house, refuses the handful to the hearths of the shires against him.",
        "{III-0110}: Blàr Muileann chrom. Raghnall falls on the field.",
        "{III-0112}: Catrìona Bhuadhach crowned at Cathair dhearg, after some ten years of war."]),
    ("Creach Eilean dhubh", ['III-0133'], [
        "{III-0131}: sea-thieves out of the small islands off the north-west coast rob the coasting traders.",
        "{III-0133}: Queen Eilidh Bhàn's force burns their boats on the strand of Eilean dhubh; Uilleam Ruadh is "
        "hanged at Cathair dhearg."]),
    ("Cogadh nam Bràithrean", ['III-0177', 'III-0180'], [
        "{III-0177}: Blàr Cnoc naomh. Alasdair Bàn's men seize the town and Iain Ciar takes it back; the war is "
        "named from it.",
        "{III-0178}: Alasdair's ships burn the waterfront of Ceann mhin.",
        "{III-0179}: Blàr Muileann ghlas. Alasdair Bàn is taken alive.",
        "{III-0180}: the brothers' peace at An Taigh-seinnse Mòr. Iain Ciar is crowned."]),
    ("Cogadh nam Beann", ['IV-0324', 'IV-0377'], [
        "{IV-0324}: the Dia-thìrich of the mining country rise together against the Administration and the Company.",
        "{IV-0325}: the store at Muileann chrom taken at first light. {IV-0327}: Sèist Baile thais; the constables "
        "yield on the twelfth day.",
        "{IV-0335}: Blàr Àth chiar. Ashdown's relief column turned back; forty and nineteen dead.",
        "{IV-0338}: the surrender at Dùn ìseal clears the east of human arms.",
        "{IV-0342}: Loscadh Seann Toll. A Company steamship shells the coal stage; twenty-three townsfolk die.",
        "{IV-0344}: the fishermen of Seann Chwen burn a Company coaster at anchor.",
        "{IV-0359}: Blàr Cnoc ghorm. The Administration's last sally toward the mining country is driven back.",
        "{IV-0369}: Fosadh Àth àrsaidh, the truce. {IV-0377}: the war ends and the crossing is shut: the "
        "Severance."]),
    ("An Cogadh Fada", ['VI-0081', 'VI-0118'], [
        "{VI-0065}: the Board's enforcers posted at Seann Skell in the west to shut the pits of the holdouts.",
        "{VI-0075}: the regiments called up. {VI-0077}: the Moot's last petition, received and filed.",
        "{VI-0081}: Blàr Àth leathan, the first great battle. The open record counts only the kingdom's dead.",
        "{VI-0091}: Sèist Muileann àrsaidh. {VI-0098}: Cnoc thais taken. {VI-0109}: Àth naomh and Tobar dhearg open "
        "their roads without a siege.",
        "{VI-0111}: the column goes south-east from the western hills toward the capital.",
        "{VI-0115}: Blàr Muileann ghlas, the second great battle and the last.",
        "{VI-0118}: the war ends. Nine regiments and four fleets were raised in it; all stand to this day."]),
    ("Tional nan Tuathach", ['V-0008', 'VI-0153'], [
        "{V-0001}: the Tuathaich settled by law in the north and held there. {V-0003}: the boundary stones set on "
        "the north roads.",
        "{V-0008}: the Moot first meets at Caol mhòr, with no standing in Dia-thìrich law.",
        "{VI-0077}: its last petition, carried to the council on Christmas Day, is received and filed.",
        "{VI-0138}: the motion for amends let die. {VI-0143}: seann-chunntas, the old reckoning.",
        "{VI-0149}: passes on the northern road, for a time only, says the council's minute.",
        "{VI-0153}: the Moot of the present year meets under Peter Hale."]),
]

# ---------------------------------------------------------------- campaigns (the Dubhan Era only: the map's calendar)
CAMPAIGNS = [
    {"name": "An Cogadh Fada", "start": 21, "end": 22},
    {"name": "Blàr Àth leathan", "start": 21, "end": 21},
    {"name": "Sèist Muileann àrsaidh", "start": 21, "end": 21},
    {"name": "Blàr Muileann ghlas", "start": 22, "end": 22},
]

# ---------------------------------------------------------------- markers
# (key, type, icon, name, cell, note). Cells are the master's pack cells: a battle at its town's cell unless a marker
# stands there (then the nearest free land cell), a lighting where its event puts it, sea things on water.
MARKERS = [
    # the battles, sieges and raids of Appendix C's table, as eras/NAMES.json names them
    ("salt", "battlefields", None, "Creach an t-Salainn", 4166,
     "{I-0099}: Mòrag Chruaidh, fifth of the Stone Kings, raids the salt-pans on the southern shore at Baile ghorm, "
     "which do not yet own the king, and carries off the salt. Seven fall on the hill side, and the number is kept; it "
     "is the first war in either king-list. On {I-0104}, Iain Dubh, sixth of the Stone Kings, came down to raid them "
     "again and was slain on this shingle."),
    ("fala", "battlefields", None, "Blàr Àth na Fala", 3107,
     "{I-0098a}: the host of Dùn dhearg and the eastern households come against Ailean Mòr at the ford below Dùn "
     "dhearg. He holds it alone three days and three nights, until the dead of the host dam the river, and falls on "
     "the third night; no one man overcame him. His kin did not come. The ford has been called Àth na Fala since."),
    ("chiadfhuil", "battlefields", None, "A' Chiad Fhuil", 2017,
     "{II-0001c}: at Dùn thais, on the line between the great share of the north and the Red Share, the men of "
     "Aonghas Bàn mac Mhurchaidh and of Ruairidh Glas come to blows over which share the fort lies in, and Aonghas "
     "Bàn is killed. With it begins Aimhreit nan Oighrean, the strife of the heirs, which ran some five hundred and "
     "fifty years."),
    ("achadhmor", "battlefields", None, "Loscadh Achadh mhòr", 3451,
     "{II-0064b}: Cogadh an Dà Mhionn ends where it began. Fearghas Dà-Mhionn, lord of the granary fields, sworn "
     "both to the line of Ìomhar and to the lords of Cathair mhòr, is called to arms by each against the other; both "
     "come to take his fields, the fields are burned to the stubble, and he dies in his hall. The middle of the island "
     "went hungry that winter."),
    ("fhiadhaich", "battlefields", None, "Blàr Àth fhiadhaich", 3325,
     "{II-0095}, in Cogadh nan Rathad: the men of Caol leathan meet the levies of Iain Garbh at the ford and hold it "
     "for a day before they give way. Forty lie dead of both sides. The carriers call it Àth an Dà Fhichead, the ford "
     "of the forty."),
    ("caolleathan", "battlefields", None, "Sèist Caol leathan", 3485,
     "{II-0098}: Iain Garbh shuts Caol leathan in from the land for a season, but its boats bring in fish from the "
     "sea and the harbour he cannot close. His levies go home for the harvest, and the siege ends without an "
     "assault. The war ended under the roof of Am Buabhall Fortanach ({II-0099})."),
    ("athshean", "battlefields", None, "Blàr Àth shean", 3077,
     "{III-0106}, in Cogadh nan Trì Tagraichean: the host of Dùghall Garbh meets that of Raghnall Ruadh at the ford "
     "and breaks it. The custody-book counts some three hundred dead, most of them drowned in the ford."),
    ("cathairdhomhain", "battlefields", None, "Sèist Cathair dhomhain", 2795,
     "{III-0108}: Catrìona nic Aonghais besieges Cathair dhomhain, which had declared for Dùghall, and takes it after "
     "forty days, when its wells are fouled by the dead of the siege lines. She lets the garrison go free on their "
     "oath."),
    ("muileannchrom", "battlefields", None, "Blàr Muileann chrom", 2907,
     "{III-0110}: the hosts of Catrìona and Dùghall, joined for the purpose, meet Raghnall Ruadh below Muileann "
     "chrom. Raghnall falls on the field, and the next day his own custodians open the vein-house. It decided "
     "Cogadh nan Trì Tagraichean."),
    ("eileandubh", "battlefields", None, "Creach Eilean dhubh", 67,
     "{III-0133}: a force sent by Queen Eilidh Bhàn lands on Eilean dhubh and burns the sea-thieves' boats on the "
     "strand. Their leader, Uilleam Ruadh, is taken to Cathair dhearg and hanged."),
    ("cnocnaomh", "battlefields", None, "Blàr Cnoc naomh", 3338,
     "{III-0177}: Alasdair Bàn's men seize Cnoc naomh and Iain Ciar takes it back. The houses divide four to three, "
     "and Cogadh nam Bràithrean, the Brothers' War, takes its name from this battle."),
    ("muileannghlas", "battlefields", None, "Blàr Muileann ghlas", 3420,
     "{III-0179}: Iain Ciar defeats Alasdair Bàn below Muileann ghlas. Alasdair is taken alive, and his captains "
     "are let go home. The brothers made peace at An Taigh-seinnse Mòr ({III-0180}). The second battle below "
     "Muileann ghlas, in An Cogadh Fada, is marked at Àraich Muileann ghlas."),
    ("bailethais", "battlefields", None, "Sèist Baile thais", 2639,
     "{IV-0327}, in Cogadh nam Beann: the constables hold their walled pithead against the town for eleven days and "
     "yield on the twelfth when their water fails. Eilidh nic Raghnaill sends them under guard to the coast "
     "unharmed."),
    ("athchiar", "battlefields", None, "Blàr Àth chiar", 3169,
     "{IV-0335}: a column of constables and Company guards under Major Peter Ashdown marches up the coal road to "
     "relieve the hills and is met at the ford, where the rebels hold the far bank. Ashdown loses forty men and his "
     "baggage and turns back. The rebels lose nineteen, and the council's roll names them all."),
    ("seanntoll", "battlefields", None, "Loscadh Seann Toll", 2818,
     "{IV-0342}: a Company steamship comes up the Abhainn uaine, shells the coal stage to deny it to the rebels and "
     "sets the fishing town behind it burning. Twenty-three townsfolk die: the first time the humans turned the "
     "island's own coal, burning in their boilers, against a town of the Dia-thìrich."),
    ("cnocghorm", "battlefields", None, "Blàr Cnoc ghorm", 3340,
     "{IV-0359}: Company guards and constables sallying from the capital's harbour to win back the eastern road are "
     "driven back at Cnoc ghorm, in the hills beyond the capital. It was the Administration's last attempt in the "
     "war to reach the mining district."),
    ("muileannarsaidh", "battlefields", None, "Sèist Muileann àrsaidh", 1670,
     "{VI-0091}, in An Cogadh Fada: the regiments lay siege to Muileann àrsaidh. The town holds for weeks on stored "
     "coal and potatoes, and its pit-heads are taken one by one. Sìleas nic Rath's open record gives the day it fell "
     "and nothing else."),
    # the ends of wars, and the stone of the regiments' dead
    ("talla", "custom", "🔥", "Talla na Lasrach", 3104,
     "The hall over the undying flame of Brìde at Dùn ìseal, raised on {II-0004} and rebuilt many times on the same "
     "footings. Here the heirs of Ailean Mòr bound the vein in common, Ceangal na Ciad Lasrach ({II-0001}), and here "
     "the lords of the shares swore Sìth an Stairsnich, the Peace of the Threshold, on its threshold beside the stone "
     "cup, with the Keeper as witness ({II-0064c}). So ended Aimhreit nan Oighrean."),
    ("fosadh", "custom", "🕊️", "Fosadh Àth àrsaidh", 871,
     "{IV-0369}: envoys of the council and of the Administration meet at Àth àrsaidh, on the edge of the northern "
     "concession, and agree a truce: the humans left on Dia-thìr shall withdraw into the north-west under the "
     "council's safe-conduct, and the council shall leave the towns of the concession standing. Cogadh nam Beann "
     "ended in the Severance ({IV-0377})."),
    ("clach", "custom", "🪦", "Clach nan Rèisimeidean", 3437,
     "{VI-0126}: a stone at Cathair mhòr bearing the names of the regiments' dead from Àth leathan and Muileann "
     "ghlas. It stands beside the market cross of the house of Mac Ùisdein."),
    # the Making and the seven lightings of the coals
    ("teine", "custom", "🔥", "Teine a' Chlachair", 2096,
     "The mason's fire, {I-0001}, the first day of Linn na Fèithe: Neachdan, splitting rock for a well, breaks into "
     "a vein of coal that shows every colour at the break; that night lightning strikes the broken vein and it takes "
     "fire, and he carries a burning coal home to lay the first hearth of the Dia-thìrich. Tobar dhìreach, Tobar dhubh "
     "and Tobar òg each tell that the well was theirs; Tobar dhìreach can show a capped shaft with a scorched lip, "
     "and no chronicler has judged between them ({I-0002}). When the fire in the vein burned out, the mason's people "
     "laid a flat stone over it and cut their well again a stone's throw off ({I-0003}). The keepers' house at the "
     "slab became a place of pilgrimage ({I-0246})."),
    ("coimhdeach", "sacred-forests", "🌳", "Coimhdeach na Fine", 482,
     "The oak grove of Doire ghlas. Here on {I-0011a} a figure of grey smoke came to Diarmad of the Mason's line, "
     "who had asked why the coal of the vein has colours, and named itself Coimhdeach na Fine, the Keeper of the Kin. "
     "It told him of the making of the world by Caoran, the Young God, and of the gift hidden in the coal, and gave "
     "the riddle: the sky, the earth and the sea each carry their own spirit; merge the spirits, and they become "
     "almighty. From Diarmad's line the Telling of the Making went to every hearth."),
    ("oir", "custom", "✨", "gual òir", 907,
     "The first lighting, {I-0017a}: Aodh of the Mason's line carries the seven coals of the vein down to the "
     "northern shore, below where Ceann thais now stands, and throws them into the sea one by one. The coal with the "
     "sheen of gold takes fire on the water and burns gold until the waves put it under. The gold coal holds the sea."),
    ("dubh", "custom", "⚫", "gual dubh", 2095,
     "The third lighting, {I-0038a}: Brian of the Mason's line buries the five unlit coals deep in the ground beside "
     "the slab at Tobar dhìreach. When he digs them up the next day the black coal, as black as a wet crow, is warm in "
     "his hand and smoulders as the air comes to it. The black coal holds the earth."),
    ("donnruadh", "custom", "🩸", "gual donn-ruadh", 481,
     "The fourth lighting, {I-0052a}: Cormac of the Mason's line carries the four unlit coals to the grove where the "
     "Keeper first spoke and sets about breaking them. His hammer misses and opens the back of his hand, and where the "
     "blood falls on the red-brown coal it takes fire. The kindred call it the coal of life."),
    ("airgid", "custom", "💧", "gual airgid", 1915,
     "The fifth lighting, {I-0062a}: Eòghann of the Mason's line drinks from the Abhainn ghorm below Tobar dhìreach, "
     "says the water tastes different from the sea's, and throws the three unlit coals into the stream. The coal with "
     "the sheen of silver takes fire in the current and burns silver under the water. The silver coal holds the river "
     "water."),
    ("teinegual", "custom", "🔥", "gual teine", 2097,
     "The sixth lighting, {I-0073a}: Seathan of Clann na Ceiste, who has handled the coal of fire all his days to no "
     "end, snaps his fingers when a thought strikes him, and the coal-dust on his hand takes fire. So the fire coal is "
     "lit by the fire that is in the hand itself."),
    ("bogha", "custom", "🌈", "gual bogha-froise", 607,
     "The seventh lighting, {I-0080a}: Ailean of Clann na Ceiste, having lit each of the six coals again by its own "
     "way, carries them burning to the grove with the last coal, and the Keeper lights the rainbow coal; for the first "
     "time all seven burn together. Ailean keeps watch seven nights, a night for each coal, and on the eighth Caoran "
     "comes into the grove with the Tuath Dè and names him Rìgh Chlann nan Dè ({I-0080b})."),
    # other legend sites of the Books
    ("donn", "custom", "🪨", "Taigh Dhuinn", 4241,
     "Taigh Dhuinn, the house of Donn, lord of the dead: a rock in the sea to the south-west, where the dead gather "
     "on their way over the sea. So the Telling of the Making and the hearths have it."),
    ("diosal", "custom", "⚓", "Cidhe an Diosail", 2410,
     "The departure berth of the west quay at Seann Skell, lengthened on {III-0017}. On the night before the sailing "
     "every house on the waterfront set a lamp on its sill ({III-0022}); on {III-0023} the fleet of the Sundering went "
     "once sunwise round the river pool for luck and down the Abhainn naomh to the sea ({III-0024}). The harbour rolls "
     "entered the berth as Cidhe an Diosail, the quay of the sunwise turn, on {III-0041}."),
    ("sloc", "custom", "⛏️", "An Sloc Mòr", 2542,
     "The great shaft at Achadh dhomhain on the vein, granted to Uisdean mac Ùisdein on {V-0051}. The Mine Board "
     "shut its upper galleries on {VI-0144}. One face is kept open in the Rite's keeping, where the last twelve "
     "hewers of the vein ({VI-0145}) cut the altar-coal: four baskets on {VI-0155}, shared among the houses of the Rite "
     "by lot. The coloured coal is sold in no market."),
]
# notes set anew on markers already on the map
MARKER_NOTES = {
    17: "Blàr Muileann ghlas, the second and last great battle of An Cogadh Fada, was fought here on {VI-0115}: the "
        "first and third regiments, brought down the fair road, against the column of holdouts camped on the fields "
        "by Muileann ghlas, a day's walk from Cathair dhearg. The open record gives no count of the column's dead; the "
        "regiments' own dead are named on the stone at Cathair mhòr ({VI-0116}). The field was sown again on "
        "{VI-0127}, and for years its farmer found weapons in the furrows. It is the second battle fought below "
        "Muileann ghlas; the first was in Cogadh nam Bràithrean ({III-0179}).",
    18: "Blàr Àth leathan, the first great battle of An Cogadh Fada, was fought here on {VI-0081}: the regiments "
        "against the holdouts of the five western towns. The open record counts the kingdom's dead and not the "
        "holdouts'; the Tuathaich tellings put theirs in the hundreds ({VI-0082}). The field has been left "
        "unploughed ({VI-0085}), and on {VI-0130}, Tuathaich families built Càrn nan Tuathach on it without leave; "
        "every time the seventh regiment's patrols pass, it has grown by a stone or two.",
    48: "Binnean a' Chlachair, the Mason's Point: the highest ground of Dia-thìr, a little under three thousand six "
        "hundred feet, on the bare moor above Muileann gheal in the Doire uaine hills. The second lighting, "
        "{I-0027a}: Fearghas of the Mason's line carried the six unlit coals up here and let them fall, and the coal "
        "flecked with white stars took fire in the air as it fell and burned white; the snowflake coal holds the air. "
        "The summit has borne the kindred's name since. Herders of Muileann gheal leave a stone on the top when they "
        "pass, and none will light a fire there.",
}

# ---------------------------------------------------------------- routes (journeys and pilgrim roads)
ROUTES = [
    ("aiseag", "An t-Aiseag", "searoutes", {"stops": [0, 831, 3137]},
     "The Crossing, north-about: the one passage through Ceò Mhanannain. In the winter of {IV-0001a} the mist lifted "
     "from the northern water, and three ships came down out of the thin grey from the north to the water off the "
     "north-west cape, where the fishers of Achadh àrsaidh met them at Coinneachadh nan Long, and followed the fishers "
     "down the coast to anchor off Cuan shean ({IV-0002}). Every port of the Crossing is on the west coast. Since the "
     "Severance ({IV-0377}) the passage is shut; the ship sent north-about on {V-0011} found nothing. The first "
     "tank-hull under Dubhan's charter went out past the north-western capes on this road ({VI-0154b})."),
    ("falbh", "Am Falbh", "searoutes", {"stops": [2683, 0]},
     "The Setting-Out, {III-0023}: the willing of Rolla nan Deònach sail from Cidhe an Diosail at Seann Skell, "
     "down the Abhainn naomh to the open sea and out past the north cape. The chronicles of the island fall silent on "
     "them as the ships clear the harbour; the Dia-thìrich tell that the fleet sailed into Manannan's mist, toward the "
     "Otherworld."),
    ("fenn", "Loidhne Fenn", "trails", {"cells": "fenn"},
     "Fenn's line, {IV-0027a}: on the survey of the beacon headlands the human navigator James Fenn runs a line of "
     "sights across the whole island, from the open sea off the north-west, where ships coming down from the north "
     "first raise the land, to the water off the eastern cape. He made it a hundred and fifty-five miles, some thirty "
     "of them sea at the western end: the first measure of Dia-thìr from side to side, to which every chart the "
     "Company drew was scaled. The ruler on the map is his line; this is its course over the land."),
    ("seabhag", "Slighe an t-Seabhaig Luaidhe", "trails", {"cells": "hawk"},
     "The Leaden Hawk's road, {IV-0342a} to {IV-0342e}: Buidheann an t-Seabhaig Luaidhe, seven hawk-faithful "
     "crewmen with the council's letters to the Hawk coast, go on foot from An Cupa Dàna at Cuan dhearg past the "
     "burned stage at Seann Toll, through Baile thais and over the hills by Achadh dhomhain and Cuan bheag to Inis "
     "mhin, then by carriage across country, off every road, to the grasslands above Tobar dhomhain and down to Inis "
     "thais, six days after they left. The map's journey of the company follows the same road."),
    ("oilithrich", "Slighe nan Oilithreach", "trails", {"stops": [2463, 2559]},
     "The pilgrims' path from the river landing at Caol shean up the valley to Allt an Àigh, worn by {II-0012}. It is "
     "walked by night, so that pilgrims reach the water in the right quarter of the moon; fishermen who walk it are "
     "said to lose fewer boats. Pilgrims of four rites paved it anew in one season ({II-0223})."),
    ("inisuaine", "Rathad nan Oilithreach", "trails", {"stops": [2754, 2559]},
     "The pilgrims' road from Inis uaine to Allt an Àigh. On {IV-0222} pilgrims who keep Na Seann Spioradan came to "
     "the spring from all the east, and they gathered at Inis uaine, where the townsfolk fed them freely as the Old "
     "Spirits require and gave away more water than they kept ({IV-0223})."),
]
JOURNEY_NOTE = (
    "The Leaden Hawk, {IV-0342a} to {IV-0342e}: seven hawk-faithful crewmen of the river towns carry the council's "
    "letters in the first spring of Cogadh nam Beann from An Cupa Dàna at Cuan dhearg to Inis thais, on foot to Inis "
    "mhin and then by carriage off every road; the journey is Azgaar's own reckoning of their eight days.")

# ---------------------------------------------------------------- zones
MIST_BOXES = [[0, 0, 1536, 106.1], [1183.47, 0, 1536, 702]]        # the northern and eastern seas (as eras/specs IV, V)
ZONES = [
    ("ceo", "Ceò Mhanannain", "Custom", {"water_box": MIST_BOXES}, "url(#hatch4)",
     "Manannan's mist on the northern and eastern seas. On the first morning the lord of the sea walked round the "
     "island's coasts and drew up his mist about it, so that no ship from beyond should find it. The fleet of the "
     "Sundering sailed into it ({III-0023}); it thinned in the last years of that age ({III-0239a}) and lifted from "
     "the northern water in the winter of the Crossing ({IV-0001a}), when the one passage ran north-about and down to "
     "the north-west coast. Since the Severance it lies shut again ({V-0011}). The priests of Manannan at Seann Skell "
     "pray at every tide, A Mhanannain, cùm a' mhuir dùinte; they said it on the day the first tank-hull under "
     "Dubhan's charter went out past the north-western capes ({VI-0154b})."),
    ("casadcaol", "Casad Caol fhiadhaich", "Disease", {"around": {"cells": [3887], "steps": 2}}, None,
     "{III-0054}: a coughing sickness runs through Caol fhiadhaich on the south-west coast and kills some ten before "
     "it burns out. The shared meal was kept throughout, and the reeve held that it saved the rest."),
    ("inischrom", "Fiabhras Inis chrom", "Disease", {"around": {"cells": [3729], "steps": 2}}, None,
     "{III-0118}: a spotted fever kills some forty at Inis chrom. The Fianna of the Stone nursed the sick, and many of "
     "them died of it; thereafter the town is the Stone's."),
    ("casadmd", "Casad Muileann dhomhain", "Disease", {"around": {"cells": [3868], "steps": 3}}, None,
     "{III-0158}: the swallowing cough, a sickness that closes the throat, breaks out at Muileann dhomhain and moves "
     "along the coast road. The town loses near a third of its people."),
    ("coigreach", "Fiabhras nan Coigreach", "Disease", {"around": {"cells": [3048], "steps": 3}}, None,
     "{IV-0034}: the strangers' fever comes ashore at Cuan shean with a crowded ship and runs down the west coast. "
     "Ninety-one Dia-thìrich die, and eleven humans; the custodians shut the town to ships for a season."),
    ("breac", "Breac Ros dhomhain", "Disease", {"around": {"cells": [2975], "steps": 3}}, None,
     "{IV-0096}: a spotted pox comes ashore at Ros dhomhain on a Company ship and climbs the coal road into the camps. "
     "The Mission counts four hundred and six dead; the custodians count more, and write the difference in the margin "
     "of the Mission's list."),
    ("glas", "Fiabhras glas", "Disease", {"around": {"cells": [981, 1560, 1859], "steps": 2}}, None,
     "The grey fever, a fever of the chest, came in on the ships on {IV-0276} and ran over the whole island, killing "
     "the young and strong more readily than the old. It returned and settled in the north-west, about Baile chrom and "
     "the towns of the concession ({IV-0287}), where it killed humans as readily as Dia-thìrich, and the Mission's "
     "hospital at Cathair gheal laid Dia-thìrich and human sick in the same wards for the first time."),
    ("gortadoire", "Gorta Doire ghlas", "Disaster", {"shires": MOOT_SHIRES}, None,
     "{V-0004}: in the Tuathaich north's first year alone the stores that came over the water from an Tìr Thall come "
     "no more, and the northern settlements go short of grain. Tuathaich memory puts the dead at Doire ghlas above two "
     "hundred; the Dia-thìrich made no count."),
    ("gortaachadh", "Gorta Achadh mhòr", "Disaster", {"shires": [12]}, None,
     "The winter after the burning of Achadh mhòr ({II-0064b}), at the end of Cogadh an Dà Mhionn, when the granary "
     "fields were burned to the stubble: the middle of the island went hungry, and the Hall counted its dead with the "
     "dead of the war."),
]
ZONE_NOTES = {
    0: "From {IV-0152} the Green Death went through the mining camps: a greenish pallor, then a cough that brings up "
       "dark dust, then weakness. It was first marked at Achadh dhomhain, where the camp buried forty in the first "
       "month in the field still called An Acair Uaine ({IV-0153}), and it spread along the coal roads to twenty-six "
       "settlements ({IV-0154}). The coal dust was blamed; no inquiry was ever finished, and no reckoning of all the "
       "dead survives.",
    1: "The Great Hunger, from {IV-0194}: the harvest failed in thirty-four settlements along the north-west shore "
       "and the hills behind it ({IV-0195a}), the worse because the Levy had taken so many to the pits that too few "
       "were left to till the land. It was worst at Baile chrom, whose people could see the new beacon from their "
       "empty fields ({IV-0195}). The Levy was set aside too late for the harvest and never repealed ({IV-0200}).",
    2: "The Long Drought lay on the island's dry season three years from {IV-0217}. The custodians counted ten "
       "districts of the east as drought country, worst at Achadh shean, Àth uaine, Achadh àrsaidh and Muileann chiar "
       "({IV-0219}); fewer than half of Achadh shean's cattle reached water ({IV-0218}), and the fever of foul water "
       "that followed killed seventeen at Baile Mòr ruadh ({IV-0224}).",
    3: "The Rending, {IV-0269}: in the hills east of the capital, about Cill ghlas, the earth tore open along a "
       "fault beneath a common working, and dozens were killed. The Company shut and fenced the whole district "
       "({IV-0272}) for a generation. On {V-0141} a gallery under Muileann dhearg gave way along a line the surveyors "
       "had called sound, and thirty-one hewers died: the same fault.",
    4: "The Great Wave, {V-0017}: it fell without warning on the southern coast and laid waste Cnoc chaol, Cuan "
       "dhearg and Achadh mhin in one night, and ran on up the gulf to break the quays of Ros gharbh. The relief parties "
       "counted a little over forty dead ({V-0018}). It was the first calamity the new kingdom met by its own means.",
}

# ---------------------------------------------------------------- the seven coals, goods of the vein
# (name, colour) in the order of their lighting; they lie together in the one vein, cut only at the Sloc Mòr's last
# face, sold in no market (Appendix G I): chance 0, no distribution, placed on the vein's cells next to the shaft
COALS = [("gual òir", "#d4af37", "the sea", "I-0017a"), ("gual sneachda", "#e8edf2", "the air", "I-0027a"),
         ("gual dubh", "#1b1b1b", "the earth", "I-0038a"), ("gual donn-ruadh", "#6f2f1f", "life", "I-0052a"),
         ("gual airgid", "#c0c0c0", "the river water", "I-0062a"), ("gual teine", "#e25822", "fire", "I-0073a"),
         ("gual bogha-froise", "#9b5de5", "the spirit", "I-0080a")]
COAL_CELLS = [2543, 2446, 2447, 2732, 2355, 2540, 2731]            # the nearest land cells to An Sloc Mòr with no good


# ---------------------------------------------------------------- the shires' notes (Appendix H VII)
def resolver(lines):
    burgs = {b['i']: b['name'] for b in json.loads(lines[MR.L_BURGS]) if isinstance(b, dict) and b.get('i')}
    provs = {p['i']: p['name'] for p in json.loads(lines[MR.L_PROVINCES]) if isinstance(p, dict) and p.get('i')}

    def place(kind, i):
        return {'burg': burgs, 'province': provs}[kind][int(i)]

    def res(text):
        text = re.sub(r'\{\{date:([^}]+)\}\}', lambda m: date(m.group(1)), text)
        text = re.sub(r'\{\{year:([^}]+)\}\}', lambda m: year(m.group(1)), text)
        return re.sub(r'\{\{place:(burg|province):(\d+)\}\}', lambda m: place(m.group(1), m.group(2)), text)
    return res


def shire_notes(lines):
    res = resolver(lines)
    text = open(os.path.join(HERE, 'appendices', 'H_shires.md'), encoding='utf-8').read()
    table = text[text.index('### VII. The Table of Shires'):]
    out = {}
    for row in table.split('\n'):
        cols = [c.strip() for c in row.strip().strip('|').split('|')]
        if len(cols) != 7 or not cols[0].isdigit():
            continue
        no, shire, seat, towns, people, founded, notes = cols
        shire, seat, notes = res(shire), res(seat), res(notes)
        if seat.startswith('—'):
            out[int(no)] = '%s. Its people: %s.' % (notes.rstrip('.'), people.split(' (')[0])
        else:
            out[int(no)] = 'Seat %s, founded in the %s. %s town%s; people of its towns: %s. %s.' % (
                seat, founded, towns, '' if towns == '1' else 's', people, notes.rstrip('.'))
    assert sorted(out) == list(range(1, 124)), 'Appendix H VII: %d rows' % len(out)
    return out


# ---------------------------------------------------------------- the spec
def chronicle_head(name, a, b):
    return '%s · %s' % (name, year(a) if year(a) == year(b) else '%s – %s' % (year(a), year(b)))


def build_spec(lines):
    provs = [p for p in json.loads(lines[MR.L_PROVINCES]) if isinstance(p, dict) and p.get('i') and not p.get('removed')]
    kingdom_shires = [p['i'] for p in provs if p['i'] not in MOOT_SHIRES]
    extra = json.load(open(os.path.join(RECON, 'history_cells.json'), encoding='utf-8'))
    notes = {'state:@kingdom': fill(KINGDOM_NOTE), 'state:@moot': fill(MOOT_NOTE), 'journey:0': fill(JOURNEY_NOTE)}
    for i, t in MARKER_NOTES.items():
        notes['marker:%d' % i] = fill(t)
    for i, t in ZONE_NOTES.items():
        notes['zone:%d' % i] = fill(t)
    for i, t in shire_notes(lines).items():
        notes['province:%d' % i] = t
    spec = {
        "name": "Dia-thìr: the history on the master map",
        "seed": "history",
        "comment": "Made by legendarium/history_layer.py; baked into legendarium/reconcile/history.json.",
        "states": {"list": [
            {"key": "kingdom", "base": 1, "keep_label": True, "military": "keep", "shires": kingdom_shires,
             "campaigns": [dict(c, attacker="@kingdom", defender=0) for c in CAMPAIGNS]},
            {"key": "moot", "name": "Tional nan Tuathach", "fullName": "Tional nan Tuathach", "form": "Republic",
             "formName": "Moot", "capital": 95, "culture": 1, "color": "#dababf", "coa": "generate",
             "salesTax": 0, "pollTax": 0, "treasury": 0,
             "shires": MOOT_SHIRES},
        ], "chronicle": [[chronicle_head(n, sp[0], sp[-1])] + [fill(x) for x in rows] for n, sp, rows in CHRONICLE],
            "neutral_name": "Neutrals"},
        "diplomacy": [["@kingdom", "@moot", "Suzerain"]],
        "diplomacy_default": "x",                  # towards the neutrals, as Azgaar keeps it
        "markers": {"edit": {}, "add": [dict({"key": k, "type": t, "name": n, "cell": c, "note": fill(note)},
                                             **({"icon": icon} if icon else {}))
                                        for k, t, icon, n, c, note in MARKERS]},
        "routes": {"add": [dict({"key": k, "name": n, "group": g, "note": fill(note)},
                                **({"cells": extra[w["cells"]]} if "cells" in w else {"stops": w["stops"]}))
                           for k, n, g, w, note in ROUTES]},
        "zones": {"add": [dict({"key": k, "name": n, "type": t, "note": fill(note)}, **sel, **({"color": col} if col else {}))
                          for k, n, t, sel, col, note in ZONES]},
        "notes": notes,
    }
    names = [m[3] for m in MARKERS] + [r[1] for r in ROUTES] + [z[1] for z in ZONES] + [c['name'] for c in CAMPAIGNS] + \
        [c[0] for c in CHRONICLE] + [c[0] for c in COALS] + ['Tional nan Tuathach']
    bad = [x for x in names if R.normalize(x) != x or any(R.check_agreement(w) for w in re.split(r"[\s']+", x) if w)]
    assert not bad, 'names not in Dia-thìris spelling or against caol le caol: %s' % bad
    unreg = sorted({x for x in names if x not in NAMES})
    return spec, unreg


# ---------------------------------------------------------------- the bake: the engine's map, as edits
def load(path):
    lines = open(path, encoding='utf-8', newline='').read().split('\r\n')
    assert len(lines) == MR.RECORDS
    return lines


def svg_path(svg, i):
    m = re.search(r'<path id="route%d" d="([^"]*)"/>' % i, svg)
    assert m, 'no saved path for route %d' % i
    return m.group(1)


def diff_fields(record, old_list, new_list, ids, skip=()):
    edits = []
    for i in ids:
        a, b = old_list[i], new_list[i]
        for k in sorted(set(a) | set(b)):
            if k in skip or a.get(k) == b.get(k):          # == : 3.0 and 3 are the same number
                continue
            assert k in b, 'record %d [%d]: the engine dropped %s' % (record, i, k)
            e = {"record": record, "path": "[%d].%s" % (i, k), "value": b[k]}
            if k in a:
                e["old"] = a[k]
            edits.append(e)
    return edits


def bake():
    with tempfile.TemporaryDirectory() as tmp:
        base = os.path.join(tmp, 'base.map')
        env = dict(os.environ, RODAIS_RECONCILE_EXCLUDE='history', RODAIS_FINISH_OUT=base)
        subprocess.run([sys.executable, os.path.join(ROOT, 'finish_map.py')], env=env, check=True, capture_output=True)
        A = load(base)
        spec, unreg = build_spec(A)
        json.dump(spec, open(SPEC, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        # the engine's map must be served from the RODAIS folder
        work = os.path.join(ROOT, 'eras', 'engine', '.work')
        os.makedirs(work, exist_ok=True)
        eng = os.path.join(work, 'history_engine.map')
        subprocess.run([sys.executable, os.path.join(ROOT, 'eras', 'engine', 'build_era_map.py'), SPEC, eng,
                        '--master', base, '--report', os.path.join(tmp, 'report.json')], check=True)
        B = load(eng)
        rep = json.load(open(os.path.join(tmp, 'report.json'), encoding='utf-8'))
    J = {n: (json.loads(A[n]), json.loads(B[n])) for n in (14, 15, 30, 35, 36, 37, 38, 52)}
    edits = []
    # states: the kingdom and the neutrals set field by field, the Moot appended; rural totals are derived
    sa, sb = J[14]
    assert len(sa) == 2 and len(sb) == 3
    edits += diff_fields(14, sa, sb, [0, 1], skip=('rural',))
    moot = dict(sb[2], rural=0)
    edits.append({"record": 14, "path": "", "op": "append", "value": moot})
    # burgs: the state of each burg in the Moot's shires, and Caol mhòr its capital
    ba, bb = J[15]
    ids = [i for i in range(1, len(ba)) if isinstance(ba[i], dict) and ba[i].get('i')]
    be = diff_fields(15, ba, bb, ids)
    assert {e['path'].split('.')[1] for e in be} <= {'state', 'capital', 'group'}, sorted({e['path'] for e in be})[:20]
    edits += be
    # the cells' states
    ca, cb = A[25].split(','), B[25].split(',')
    edits += [{"record": 25, "path": "[%d]" % c, "old": int(x), "value": int(y)} for c, (x, y) in enumerate(zip(ca, cb)) if x != y]
    # the shires: their state and their notes
    pa, pb = J[30]
    pe = diff_fields(30, pa, pb, [i for i in range(1, len(pa)) if isinstance(pa[i], dict)], skip=('pole',))
    assert {e['path'].split('.')[1] for e in pe} <= {'state', 'note'}, sorted({e['path'] for e in pe})[:20]
    edits += pe
    # markers: notes of the old, and the new appended
    ma, mb = J[35]
    old_ids = {m['i'] for m in ma}
    edits += diff_fields(35, {m['i']: m for m in ma}, {m['i']: m for m in mb}, sorted(old_ids))
    edits += [{"record": 35, "path": "", "op": "append", "value": m} for m in mb if m['i'] not in old_ids]
    # routes: the new ones, with their links and saved paths; the old unchanged
    ra, rb = J[37]
    old_r = {r['i']: r for r in ra}
    assert all(old_r[r['i']] == r for r in rb if r['i'] in old_r) and len(rb) == len(ra) + len(ROUTES)
    la, lb = J[36]
    for r in rb:
        if r['i'] in old_r:
            continue
        # the links of its stretch where no route ran before (a stretch shared with an older route stays that
        # route's link, as the older route's own path needs it)
        links = sorted({tuple(sorted((int(c), int(n)))) for c, v in lb.items() for n, rid in v.items()
                        if rid == r['i'] and la.get(c, {}).get(n) is None})
        links = [list(x) for x in links]
        edits.append({"record": 37, "action": "add_route", "route": r, "links": links, "d": svg_path(B[5], r['i'])})
    new_ids = {r['i'] for r in rb if r['i'] not in old_r}
    assert all(v[n] in new_ids for c, v in lb.items() for n in v if la.get(c, {}).get(n) != v[n]), \
        'record 36 changed beyond the new routes'
    # zones: notes of the old five, and the new
    za, zb = J[38]
    old_z = {z['i'] for z in za}
    edits += diff_fields(38, {z['i']: z for z in za}, {z['i']: z for z in zb}, sorted(old_z))
    edits += [{"record": 38, "path": "", "op": "append", "value": z} for z in zb if z['i'] not in old_z]
    # the journey's note
    ja, jb = J[52]
    edits += diff_fields(52, ja, jb, [0])
    # the seven coals: goods of the vein, on the cells beside An Sloc Mòr
    goods = json.loads(A[MR.L_GOODS])
    cellgood = A[MR.L_CELL_GOOD].split(',')
    nxt = max(g['i'] for g in goods) + 1
    for k, ((name, color, holds, ev), cell) in enumerate(zip(COALS, COAL_CELLS)):
        assert cellgood[cell] == '0', 'cell %d already holds good %s' % (cell, cellgood[cell])
        g = {"i": nxt + k, "name": name, "tags": ["ritual"], "icon": "good-coal", "color": color, "value": 0,
             "chance": 0, "unit": "basket",
             "note": fill("One of na Seachd Guail, the Seven Coals of the vein: it holds %s, and was first lit by its "
                          "own spirit on {%s}. The coloured coal lies in the one vein under the mountains, and only the "
                          "eyes of the godkin see its colours. It is cut only at the last face of An Sloc Mòr, in the "
                          "Rite's keeping, as altar-coal, and is sold in no market." % (holds, ev))}
        edits.append({"record": MR.L_GOODS, "path": "", "op": "append", "value": g})
        edits.append({"record": MR.L_CELL_GOOD, "path": "[%d]" % cell, "old": 0, "value": nxt + k})
    doc = {
        "layer": "history",
        "summary": (
            "The history carried on the master map (history_layer.py; the spec is history_spec.json, applied in "
            "Azgaar through the era engine and baked here as edits). The Moot, Tional nan Tuathach, a second state "
            "of eleven shires with Caol mhòr its seat and the kingdom its suzerain; An Cogadh Fada and its three "
            "battles as the kingdom's campaigns (DE 21-22); every war of Appendix C in the war chronicle; %d markers "
            "(the named battles, sieges and raids of Appendix C's table, two peace sites, the regiments' stone, the "
            "mason's fire, the Keeper's grove, six of the seven lightings, Taigh Dhuinn, Cidhe an Diosail, An Sloc "
            "Mòr) and new notes on the two battlefields and the summit; %d routes (An t-Aiseag, Am Falbh, Loidhne "
            "Fenn, the Leaden Hawk's road, the two pilgrim roads); %d zones (Ceò Mhanannain and the plagues and "
            "famines) and notes on the five districts; the seven coals as goods of the vein at An Sloc Mòr; notes on "
            "the two states, the 123 shires and the Leaden Hawk's journey." % (len(MARKERS), len(ROUTES), len(ZONES))),
        "engine": {"ids": rep.get('ids'), "warnings": rep.get('warnings'), "counts": rep.get('counts')},
        "names_not_in_NAMES_json": unreg,
        "map_edits": edits,
    }
    with open(OUT, 'w', encoding='utf-8') as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)
        fh.write('\n')
    os.remove(eng)
    print('history.json: %d edits; engine warnings: %d; names coined here: %s' % (len(edits), len(rep.get('warnings') or []), unreg))


if __name__ == '__main__':
    if sys.argv[1:] == ['spec']:
        spec, unreg = build_spec(load(os.path.join(ROOT, 'Rodos_finished.map')))
        json.dump(spec, open(SPEC, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('history_spec.json written; names coined here (not in eras/NAMES.json):', unreg)
    elif sys.argv[1:] == ['bake']:
        bake()
    else:
        sys.exit(__doc__)
