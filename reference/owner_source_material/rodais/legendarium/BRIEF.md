# The Dia-thìr legendarium — writers' brief

Everything written for the legendarium follows this brief. It is the canon's contract.

## What we are making

A record of the island of Dia-thìr in the spirit of *The Silmarillion*, *The Hobbit*, *The Lord of
the Rings* and its Appendices, weighted toward the appendices: annals, genealogies, calendars,
peoples, tongues, faiths, wars, and a gazetteer of every place on the map, with a shorter
prose account of each age. Voice: grave, concrete, archival, the voice of an institution that
kept records (the royal chroniclers, the library at Muileann chaol) and sometimes admits what it
cannot know. No modern slang. No winking. The reader is "the next person": someone handed the
whole record.

## Sources of canon, in order of authority

1. `chronicle_canon.json`: the owner's chronicle, 148 events in five ages. Every event in it
   stays, with its title and meaning unchanged. Its dates stay: the year it gives is kept (a
   "c. 1790 DE" becomes exactly 1790), and a full date (11 April 2020) is kept whole.
2. `world.json`: the map (`../Rodos_finished.map`). 505 burgs, 123 provinces, 157 rivers, 9
   faiths with deities, 48 markers, 5 disaster zones, 13 regiments and fleets, the islands and
   the ocean. Use these names exactly; refer to places by id (below).
3. `../NAMING_LAYER.md`, `../GRAMMAR.md`: the peoples, the language, how names are built.
4. `canon_words_and_faiths.txt`: the chronicle's "Words Born from History" and its faith list.

## The owner's characters: chronicle facts only

These people belong to the owner's own story. They may appear ONLY doing, being or suffering
what the chronicle already says. No new actions, words, thoughts, relatives, relationships,
places, feelings or fates. Refer to them plainly when the record needs them; otherwise leave
them alone.

- **Aisling**, born 1848 DE in the mining camps (at Achadh dhomhain): the first of the immortal generation. Owner's
  canon since: she is distantly of the first king's line, and her father is named (the one exception to the rule
  below): **Donnchadh mac Thormoid**, a Dia-thìreach hewer of the deep galleries. The Keeper of the Kin met him in a
  gallery (AE 68) and gave him, in his breath, the secret gift (*Tìodhlac a' Choimhdich*) it had laid in the dust of
  the deep places for the kin, so that they could stand against the occupiers; the Mission's surgeon took it for the
  miners' lung-rot; his cough stopped the night she was born, and it woke in her. The camps called her *nighean an
  rìgh*, the king's daughter, half in jest; in AE 126 the copyist Cailean mac Eachainn and the reciter Ealasaid of
  Clann na Ceiste traced her line and found it true (IV-0251a). The full line is Appendix A, *The Line of Aisling*.
  She is a deliverer figure of the camps, always "a daughter of the king's line"; never name or allude to any
  real-world parallel.
- **Fionnan**, born 1900 DE: the second case.
- **Lorccan**, born 1913 DE in a mining town: the third.
- **Cian**, born 1914 DE: the fourth. Cian and Lorccan grew up in the wake of the Severance.
- **Dubhan**, born 1958 DE, mortal, Tuathach. From c. 1990 he experimented with a synthetic
  fuel, and the first working *dubhan* came c. 2000. His name became the fuel's name.
- **Splatter and Dodge's generation**, born 1953 in the shunting families: Dubhan's closest
  allies, **Seachran** and **Brean** among them.
- **The rulers of the restored kingdom**: Niall, crowned c. 1932, died 1951; his daughter
  Brìghde, crowned 1951, whose reign ended young in 1957 with no cause made public; her cousin
  Eòghan, crowned 1957; Mairead, crowned c. 1987; Cathal, crowned c. 2002, reigning in 2026.

Everyone else is yours to invent: custodians, chroniclers, shipwrights, smiths, priests,
captains, clerks, poets, rebels, administrators, lesser nobles, earlier kings and queens of the
Holy Age, the leaders of the Sundering. Give them Dia-thìris names (Scottish Gaelic personal names:
Ailean, Beathag, Catrìona, Dòmhnall, Eilidh, Fearchar, Gormshuil, Iain, Mòrag, Raghnall,
Sìleas, Tormod…), with patronymics (*mac*/*nic*) and bynames (*Ailean Gobha*, "Ailean the
smith"). Humans get names from their own tongue (plain, English-like, not Gaelic). No invented
person may be a parent, child, spouse, lover, rival or teacher of the owner's characters (the owner has since
named Aisling's father and her line himself; see above).

## The six ages and the reckoning of years

Each age is an era with its own count of years. Year 1 of an era is the year of the age's opening
event; there is no year 0, and the era changes on the day the next age opens. A date is written
"12 am Màrt, AE 67"; a bare year "AE 67". (The old count by the Diosal, from the year the ships of
the Sundering set out, was used for many centuries and then given up; Appendix D tells it.)

| Age | Dia-thìris name | Era | Opens with (year 1) |
|---|---|---|---|
| I | An Aois Àrsaidh, the Ancient Age | Linn na Fèithe, the Vein Era (VE) | the crack in the stone |
| II | An Aois Naomh, the Holy Age | Linn an Teine, the Flame Era (FE) | the Binding of the First Flame |
| III | An Aois Scaraidh, the Age of Sundering | Linn na Tìre, the Landfall Era (LE) | land found across the water |
| IV | An Aois Choigreach, the Age of Strangers | Linn an Acair, the Anchor Era (AE) | the Crossing |
| V | An Aois Rìoghachd, the Age of the Kingdom | Linn an Dealachaidh, the Severance Era (SE) | the Tuathaich homeland, after the Severance |
| VI | An Aois Dhubhain, the Age of Dubhan | Linn an Dubhain, the Dubhan Era (DE) | the first working dubhan |

Windows and chronicle years below are given in the tooling's continuous count (negative before
its year 1, no year 0; 1780 is AE 1, 1930 SE 1, 2000 DE 1, the present year 2026 is DE 27).

Every event gets an exact day, month and year. **Writers do not choose dates.** A separate
reckoning assigns every date from the order you put events in, holding the chronicle's years
fixed. So what you control is ORDER: list events in the order they happened. When an event must
fall in a particular stretch of years, say so with `"between": [from, to]` in the continuous count
(negative numbers before its year 1), for example `"between": [1850, 1860]` (AE 71 to AE 81).

Months are the Gaelic months, one to one with the Gregorian: am Faoilleach, an Gearran, am Màrt,
an Giblean, an Cèitean, an t-Ògmhios, an t-Iuchar, an Lùnastal, an t-Sultain, an Dàmhair, an
t-Samhain, an Dùbhlachd. Feasts: Là Fhèill Brìghde (1 Gearran), Bealltainn (1 Cèitean),
Lùnastal (1 Lùnastal), Samhain (1 t-Samhain). Don't write dates in the text of events; the
reckoning supplies them.

## The world in brief (see the chronicle for the full arc)

- **The making.** Caoran, the Young God (*an Dia Òg*), youngest son of an Dagda and Danu, chose coal for his world,
  made all that is, then the island and its first people, the godfolk (*an Dia-shluagh*), whose children are the
  godkin (*Clann nan Dè*). In the island's coal he hid the elements, one to each colour: *na Seachd Guail*, the Seven
  Coals (black/earth, fire/fire, snowflake/air, gold sheen/sea, silver sheen/river water, mahogany/life,
  rainbow/spirit). The island was born of drops of fire from his last coal; the godfolk grew out of it like grass
  (*feur uaine an eilein*). The spirit Coimhdeach na Fine, the Keeper of the Kin, a figure of grey smoke that stands
  still in a wind, watches the kin for him.
- **The first king and the long years.** Ailean Mòr (crowned VE 5,324) alone received the coals' power. He gave the
  hill to his daughter Gormshuil and lived on by the slab at Tobar dhìreach, keeping his secret, until VE 5,995
  (I-0098a), aged 695 (crowned at 24). His children had only a portion, their long years; Somhairle, his youngest, died VE 6,050 (I-0104a) aged 540, and
  the years thinned each generation (408, 296, 221, 173, then Ceallach 140) until the sixth after Somhairle lived as others do. That fading is why it all
  became myth: from the Holy Age on, the first king and his long years are the reciters' tale, and the Library keeps
  them in its book of tellings. At the vigil the Keeper promised that when strangers hold the island the fire will wake
  again in his line: in Aisling it is a new waking, not a survival. See legendarium/book/creation.md. The word for the stuff is always **coal**, never any kind of glass.
- **The vein.** Under the island's central mountains runs the coloured coal, *an gual dathach*, a hard coal that takes a
  polish and shows its colours when broken; VE 1 is the mason's breaking of the vein and the lightning fire. Only the
  godkin see the colours. The Dia-thìrich call it sacred; the humans saw only black coal. Bonding with it, first in Aisling
  (1848), makes the *fuil-ghuail*, "coal-blood" (in the humans' tongue, "coal-touched"):
  those who do not age as others do. By 2026 the vein is nearly spent and the island runs on
  *dubhan*.
- **Age I**: before record. The doctrine *Cha do thàinig sinn; bha sinn ann*, "we did not come;
  we were here." The **Seann-Dhaoine**, the Old Ones, a people before the Dia-thìrich, built the
  ruins (Làrach an Dùin-fhaire, Làrach an Dùin, Làrach an Teampaill) and the standing stones, and
  left only their place names: Seann Dunn, Seann Chwen, Seann Skell, Seann Bhral, Seann Tarr,
  Seann Vell, Seann Morn, Seann Brenn, Seann Toll, Seann Warr (the roots are not Gaelic). How they
  ended is not known; don't resolve it.
- **Age II**: the Dia-thìrich, custodians of the vein. The Small-Burning Law. The first king-list.
  Faiths splitting from one folk practice. The last age of even population.
- **Age III**: a land is found across the water; volunteers choose to go; the fleet sets out (1
  DE); two landfalls; the thinning of the departed; the long quiet centuries on Dia-thìr after.
  Keep the chronicle's hint unresolved: the humans who came back in 1780 crossed "the water the
  Dia-thìrians once crossed". Nobody on Dia-thìr knows whether they descend from the departed.
- **Age IV**: the humans' Crossing (c. 1780); trade that became extraction; the humans'
  treaties, coinage and tithe; the mining camps; plagues, famines, droughts; the immortal
  generation; the Long War's forerunners; war declared 1928; the Severance c. 1930, which
  closed the crossing and sent the remaining humans north.
- **Age V**: the restored kingdom, Rìoghachd Dia-thìr; the same extraction under new owners; the
  Tuathaich in the north; the Depletion; dubhan; the Tuathaich coal-holdouts; **An Cogadh Fada**,
  the Long War (2020–2021), with its battles at Àth leathan (11 April 2020) and Muileann ghlas
  (10 December 2021); 2026, the present.
- **The humans' homeland** is *an Tìr Thall*, "the land beyond", in Dia-thìris; its own name is not
  recorded on Dia-thìr. Human administrators, traders and clerics have human names.
- **Peoples**: the **Dia-thìrich** (the majority, holders of the capital and the sea); the
  **Tuathaich** (descendants of the humans left on Dia-thìr, in the north-west since the
  Severance: 64 burgs); the **Seann-Dhaoine** (gone).
- **Faiths on the map** and their place in the chronicle:
  Seann Spioradan nan Dia-thìreach (the oldest folk tradition, ancestors, the vein, the weather);
  Creideamh nan Dia-thìreach (the Coal Rite in its orthodox form, formalized 1935);
  Creideamh an t-Seabhaig (the Rite's older form; deity Mòd, the Hungry Hawk);
  Feallsanachd an Fhèidh (the philosophical school asking why the vein answers some hands and
  not others; the most widespread); Creideamh nan Tuathach (Tuathaich folk tradition, keeper of
  the First Canoe fragment); Creideamh na Scairpe Buidhe (monotheist; Cnut, the Yellow Scorpion);
  Creideamh an Aon-adharcaich Dhuibh (dualist, the capital's faith; Uallach, the Dark Unicorn);
  Creideamh a' Mhadaidh-allaidh (monotheist; Clach, the Resplendent Direwolf); Rùn-dìomhair na
  h-Oidhche Glaise (a heterodox cult; Sìne, the Peaceful Goose).

## Places: refer by id

Every event that happened somewhere names its place as a reference string:
`burg:19` (Cathair dhearg), `province:1`, `river:5`, `marker:12`, `zone:3`, `feature:2`. Take ids
from `world.json`. Names repeat between burgs (there are two Baile chrom): the id decides. Spread
events across the whole island; a legendarium touches every province. Tuathaich burgs are in the
north-west. Towns, lighthouses, taverns, bridges, markers and routes can all have histories.

## Spelling

Dia-thìris words in Dia-thìris spelling: grave accents only, *sc* not *sg* (*Scàineadh*, *uisce*). Use
`world.json` names exactly as written.
