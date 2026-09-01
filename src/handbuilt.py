#!/usr/bin/env python3
"""HAND-BUILT — assays for entities the automated pass cannot reach, and why it cannot.

Each sheet here exists because an entity was ASKED FOR and the library could not answer, and in
every case the reason turned out to be a defect rather than a gap. Recording the defect beside
the assay is the point: the number is worth less than knowing why the machine could not produce
it.

GETTER EMPEROR -- catalogued, mined, and invisible
--------------------------------------------------
It is in the library. `data/records/getter-robo.json` holds it, `feats/getterrobo_fandom_com/`
has its mined page, and its own catalogue entry reads:

    "type":     "Character"
    "category": "Media (in-fiction media: books, songs, broadcasts, works that exist
                 within the story itself)"

The two fields contradict each other in the same record, and it is the ONLY Media entry among
that source's 121 -- a category of one. Its own description says it is "a gigantic being...
Wielding godlike power, it continually absorbs matter on a universal scale". An M7 filed as
though it were a book, and therefore absent from every downstream stage that reads Persons.

Library-wide there are 548 entries typed `Character` and filed elsewhere, 41 of them under
Media. Many are legitimate -- Weyland-Yutani is typed Character and correctly filed under
Factions -- so this is not a blanket repair. It is a class of error worth a pass of its own.

MISTER MXYZPTLK -- mined twice, zero feats, and the gate was right each time
---------------------------------------------------------------------------
He was never catalogued: `data/records/dc.json` holds 377 entries for the whole of DC, and he
is not among them. Mining him directly works immediately -- two pages, 29,676 characters -- and
still yields NOTHING:

    pages 1 (13,651 chars)   feats 0   held-back 2
    pages 1 (16,025 chars)   feats 0   held-back 2

The subject gate is doing exactly what it was built to do. Almost every sentence on his page has
Superman as the actor: Superman tricks him, Superman rewires the typewriter, Superman gets him to
paint his face blue. Mxyzptlk is the PATIENT of his own article, because the character's entire
premise is losing. A gate that requires the entity to be the doer will refuse that page forever,
and it should -- but the entity is not therefore unmeasurable, it is unmeasurable BY THAT GATE.
That is a real limit of the instrument and it is worth writing down next to the sheet.
"""
import argparse
import os
import sys
import textwrap

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import assay as A                                                       # noqa: E402
import silence                                                          # noqa: E402

_BAD_CHARS = (chr(8), chr(11), chr(12), chr(7))
if any(c in open(os.path.abspath(__file__), encoding="utf-8").read() for c in _BAD_CHARS):
    raise SystemExit(__file__ + ": a regex escape was eaten in transit.")

OUT = os.path.join(HERE, "data", "HANDBUILT_ASSAYS.json")

ROSTER = {
 # The epoch line does real work on this one. His page distinguishes the performer, Mark
 # Calaway, from the character, and says so in as many words: two contrasting personas, one of
 # them "The Deadman, an undead, occult-like figure". The Deadman is what is assayed here.
 # Calaway is a man from Houston with knee surgeries and would assay at M0.
 "The Undertaker": dict(
  anchor="M1", host="prowrestling.fandom.com", epoch="The Deadman, 1990-2020",
  why_missed="his SOURCE is catalogued and its 158 entries are COUNTRIES -- Afghanistan, "
             "Albania, Argentina, Armenia, Australia. The category resolver took a "
             "by-nationality listing and catalogued the nations. There are no wrestlers in "
             "professional wrestling.",
  presence="A promotion, wholly -- but the first version of this sheet read the summary "
           "paragraph and scored a wrestler. The storyline canon is not a wrestler. He founds a "
           "religious order, prophesies 'a plague of evil would be unleashed on the WWF' and "
           "then delivers it, fuses that order with the company's own power structure into the "
           "CORPORATE MINISTRY, and takes orders from a concealed 'higher power' that 'owned the "
           "key to McMahon's heart and soul'. His extent is still one institution. What changed "
           "is that within it he is not a competitor but a claimant on the souls of the people "
           "running it.",
  axes=dict(
   ruin=(4.5, "'Throughout the PPV, the Undertaker appeared to have Austin EMBALMED ALIVE, have "
              "Kane committed to a mental asylum, and CRUCIFY Austin.' He does not break "
              "structures; he does things to people that have no counterpart on any other sheet "
              "here", "wiki"),
   continuity=(9.9, "CEILING, AND EARNED TWICE OVER. He is not merely hard to kill -- he DIES ON "
                    "SCREEN AND RETURNS. Entombed in a casket at the 1994 Royal Rumble, where he "
                    "'died and ascended to the heavens'; buried alive by The Executioner in "
                    "1996, and 're-born a month later, descending to the ring from the rafters "
                    "in black leather attire with bat-like wings'. Death is an episode in his "
                    "record rather than an end to it", "wiki"),
   celerity=(4.0, "Deliberately, famously slow. The menace is that he does not hurry", "canon"),
   reach=(6.5, "The Ministry acts at his word across the whole company -- a burning crucifix "
               "left in McMahon's yard, the owner 'reduced to tears at the sight of a burning "
               "teddy bear' that had belonged to his daughter. He reaches into people's homes "
               "and childhoods", "wiki"),
   transgression=(9.0, "Prophecy that comes true; a black wedding; an urn carried as the vessel "
                       "of his power and 'stolen and used to attack Kane'; Paul Bearer 'returned "
                       "after being brought out in a casket'; teleportation, lightning and fire. "
                       "He does not break the rules of his world -- he installs new ones and "
                       "everyone obeys them", "wiki"),
   sustain=(9.0, "'From 1990 to 2020', across five distinct incarnations, plus a 15-year "
                 "contract signed in 2019", "wiki"),
   vector=(5.5, "Descends from the rafters, rises from graves, appears and vanishes at will "
                "inside his own domain", "wiki"),
   volition=(9.0, "'An undefeated streak at WrestleMania of 21-0' -- twenty-one consecutive "
                  "years of refusing -- and a submission to the Higher Power that is his own "
                  "choice rather than a compulsion", "wiki"),
   acumen=(7.5, "Ran a months-long conspiracy with a CONCEALED PRINCIPAL, revealing the higher "
                "power only when it suited him, and ended it holding the company. That is a "
                "plot, not a gimmick", "wiki"),
   discernment=(7.5, "He prophesies what is coming and is right; he knows what object in a "
                     "billionaire's house will hurt him most", "wiki"),
   suasion=(9.9, "CEILING, AND THE HIGHEST-EARNED SCORE IN THIS LIBRARY. Not the crowd pop -- "
                 "the ORDER. Mideon, Viscera, Gangrel, Edge, Christian, Bradshaw and Farooq "
                 "serve him as a faith, the company's owner is broken down to tears by symbols "
                 "left where his daughter can see them, and the promotion's actual power "
                 "structure merges into his ministry. Naruto turned three enemies with speeches. "
                 "This is a congregation", "wiki"))),

 # Not a joke, and not a fiction either. Charter Part Three: "A treasure, an institution, an
 # event and a law of nature all have a scale of presence; most of them have no threat at all."
 # An institution is assayable BY CONSTRUCTION under the presence thesis, and would not have
 # been under the threat one -- which is the clearest demonstration available of what changed
 # when the anchor moved. Provenance is marked [record] throughout: this is the public record,
 # not a mined wiki, and the sheet says so rather than borrowing the authority of a citation
 # format it has not earned.
 "The Internal Revenue Service": dict(
  anchor="M1", host="(the public record)", epoch="post-FATCA, 2010 onward",
  why_missed="not a fiction, and the Acquisitions Roll is a roll of fictions. The instrument "
             "has no objection to it; the collection policy does.",
  presence="A nation, pervaded rather than merely occupied. Almost every adult and every "
           "business in the United States appears in its records annually, and the reach does "
           "not stop at the border: the US is one of a bare handful of countries that taxes its "
           "citizens on worldwide income regardless of where they live, and FATCA obliges "
           "FOREIGN financial institutions to report on American account holders. Its presence "
           "is a nation's population, wherever on Earth that population happens to stand.",
  axes=dict(
   ruin=(5.0, "Can levy wages and seize bank accounts administratively, without first suing "
              "anyone. Total against an individual, negligible against a structure", "record"),
   continuity=(9.0, "The office dates to 1862 and has outlasted every administration, party and "
                    "constitutional argument raised against it since", "record"),
   celerity=(1.5, "Correspondence measured in months and appeals in years. The slowest thing on "
                  "any sheet in this library", "record"),
   reach=(9.0, "Worldwide taxation of citizens by residence-independent rule, plus FATCA "
               "compelling banks in other sovereign states to report on its behalf", "record"),
   transgression=(7.0, "In a deficiency case the Commissioner's determination is presumed "
                       "correct and the taxpayer carries the burden -- the ordinary direction of "
                       "proof runs backwards inside its own forum", "record"),
   sustain=(9.5, "Funded by the activity it exists to perform. It cannot run out of the thing "
                 "it collects", "record"),
   vector=(2.0, "It does not travel anywhere. It summons, and things come to it", "record"),
   volition=(2.0, "It wants nothing. It executes statute written elsewhere, and changes course "
                  "only when Congress says so", "record"),
   acumen=(6.5, "Selects audits from returns algorithmically, at a scale no human review could "
                "reach", "record"),
   discernment=(8.5, "Third-party information returns mean it is told about most income "
                     "independently of the person earning it. It largely knows the answer "
                     "before it asks the question", "record"),
   suasion=(9.0, "THE HIGHEST SCORE ON THIS SHEET, AND THE LEAST EXPECTED. The overwhelming "
                 "majority of what it collects arrives voluntarily, filed on time, by people "
                 "against whom no enforcement action is ever taken. An entire nation performs "
                 "an elaborate annual ritual on its word alone", "record"))),

 # The one sheet here that REFUSES most of its own axes. Zalama never acts on-page: his entire
 # record is 2,310 characters, and everything known about him is known through the thing he
 # built. Charter Part Three's answer to that is a STATUS, not a guess -- an axis with no
 # evidence takes `unestimable` and the interval widens to say so. Every other entity in this
 # file scores all eleven axes and publishes ± 0.15; this one scores five (the other six are
 # `unestimable`) and publishes ± 0.19 -- about a quarter wider, not the four-times-wider figure
 # once claimed here (measured by calling `compute()` directly: every other sheet's interval is
 # 0.15, Zalama's is 0.19, a ratio of ~1.27, not 4). That is the instrument being honest about a
 # thin record rather than manufacturing a number to fill the row.
 "Zalama": dict(
  anchor="M8", host="dragonball.fandom.com", epoch="the Dragon God, before recorded history",
  why_missed="not catalogued; his own page is 2,310 chars with a single feat. The scale "
             "evidence lives on the pages of the THINGS HE MADE, and nothing joins an artificer "
             "to his artifacts.",
  presence="Known entirely by his works, and his works are the highest-leverage objects in that "
           "cosmology. He made 'a set of seven PLANET-SIZED Dragon Balls... the first known set "
           "of Dragon Balls to be created, predating the creation of the Namekian Dragon Balls', "
           "one of which is disguised as the Nameless Planet that gods hold tournaments on. What "
           "they summon can restore SEVEN ERASED UNIVERSES and 'over trillions of beings' -- it "
           "undoes the Omni-King's own erasures. An instrument that operates on universes as "
           "objects places its maker above the scale of one.",
  axes=dict(
   ruin=("unestimable", "He is never shown destroying anything. His instrument could -- 'Beerus "
                        "noted that he could have wished the dragon to destroy the universe if "
                        "he wanted to' -- but that is Beerus's wish, not Zalama's act", "wiki"),
   continuity=("unestimable", "No death, no injury, no threat is on record. There is nothing to "
                              "measure and inventing a 9 would be a fabrication", "wiki"),
   celerity=("unestimable", "Never depicted acting at all", "wiki"),
   reach=(9.5, "Seven planet-sized bodies, 37,196 km across each, scattered so widely that one "
               "of them passes for a planet; and the wish they carry 'brought back over "
               "trillions of beings from seven erased universes'", "wiki"),
   transgression=(9.5, "His engine reverses erasure by the Omni-King -- the one act in that "
                       "cosmology stated to be final. The Grand Minister must address it 'in "
                       "the language of the gods'", "wiki"),
   sustain=(9.0, "The balls predate the Namekian set and are still working; they turn to stone "
                 "and recharge rather than expiring", "wiki"),
   vector=("unestimable", "Never shown travelling, or anywhere", "wiki"),
   volition=("unestimable", "He built the thing and left. No want of his is recorded", "wiki"),
   acumen=(8.5, "'He shaped the balls to be the size of planets, about 37,196 kilometres in "
                "circumference' -- and hid the seventh as a planet. The design outlived every "
                "civilisation that uses it", "wiki"),
   discernment=("unestimable", "No perception attributed to him anywhere", "wiki"),
   suasion=(8.0, "Two Gods of Destruction and two angels go looking for his handiwork; the "
                 "Tournament of Power's prize is a wish on it. Gods organise expeditions around "
                 "objects he left behind", "wiki"))),

 "Molecule Man": dict(
  anchor="M9", host="marvel.fandom.com", epoch="Secret Wars (2015), post-Beyonder absorption",
  why_missed="not catalogued under either name, and 'Molecule Man' is a 3,688-byte "
             "disambiguation. The real page is 'Owen Reece (Earth-616)', 61,587 chars.",
  presence="He is not present IN the multiverse. He is present AS a term of it, in every "
           "reality at once: 'They created the Molecule Man as A SINGULARITY, BEING THE SAME IN "
           "EVERY REALITY, to have the function of a bomb, which would destroy his universe if "
           "he died.' Both the death and the rebirth of a multiverse ran through him -- his "
           "selves' deaths 'caused the Multiverse to contract, resulting in the incursions', and "
           "afterwards he 'was crucial in the restoration of the Multiverse as the Eighth "
           "Cosmos'. A being who remakes multiverses is not measured at the scale of one.",
  axes=dict(
   ruin=(9.5, "'They planned to kill all of the Molecule Men at the same time in 25 years to "
              "destroy the entire Multiverse' -- he IS the ordnance, and the partial detonation "
              "collapsed the Seventh Cosmos", "wiki"),
   continuity=(9.0, "Survived the end of one multiverse and walked into the next; 'split himself "
                    "in the process' rather than dying", "wiki"),
   celerity=(5.0, "Never contests tempo. He alters the terms of the fight instead", "canon"),
   reach=(9.5, "'As the Molecule Man powered up Reed's new Multiverse, he placed a sliver of The "
               "Maker in every reality' -- one act, every universe", "wiki"),
   transgression=(9.5, "'He rewrote some of Earth-616's history to fit Miles Morales in it.' "
                       "Editing which history a universe HAD, as a courtesy", "wiki"),
   sustain=(9.0, "'Nigh-Omnipotence... so powerful that Galactus has ever' -- no clock, no cost, "
                 "no state to hold", "wiki"),
   vector=(8.0, "Moves between realities and pocket dimensions at will; travelled back in time "
                "with Doom to reach his other selves", "wiki"),
   volition=(6.0, "Made as a weapon by others and spent his history being acted upon -- by the "
                  "Beyonders, by the Beyonder, by Doom. Enormous power, borrowed purpose", "wiki"),
   acumen=(6.5, "Worked out the Beyonders' design and conspired with Doom to sabotage it, then "
                "misjudged the sabotage badly enough to collapse a multiverse", "wiki"),
   discernment=(6.0, "Saw the plan; did not see what killing his other selves would do", "wiki"),
   suasion=(7.0, "Doom's indispensable partner in building and running Battleworld, and the one "
                 "being Doom could not simply overrule", "wiki"))),

 "Rune King Thor": dict(
  anchor="M7", host="marvel.fandom.com", epoch="Rune King, Ragnarok (Thor Vol 2 80-85)",
  why_missed="the strongest Thor has no page of his own -- he is a passage inside a "
             "171,750-character article filed under the base character, so the miner surfaced "
             "Silver Age material and this arc never separated out.",
  presence="Yggdrasil and everything hanging from it, including the things that were feeding on "
           "it from outside. Having hung on the World Tree and taken the runes, he sought out "
           "Those Who Sit Above in Shadow -- the gods ABOVE the Asgardian gods, who 'had "
           "manipulated Asgard into the repeating cycle of Ragnarok, feeding on the energies "
           "released by the deaths and rebirths of the gods' -- 'and gave his life to destroy "
           "them.' He did not win a war; he ended a cosmological cycle that had always run.",
  axes=dict(
   ruin=(8.5, "Destroyed Those Who Sit Above in Shadow outright, an order of beings above his "
              "own pantheon", "wiki"),
   continuity=(8.0, "Gave his life to do it and returned; and 'overpowered M.Y.T.H.O.S, who had "
                    "assimilated the full power of Yggdrasill, even after the Odin-Force had "
                    "been stripped from Thor'", "wiki"),
   celerity=(7.5, "God-tier tempo, never his distinguishing axis", "canon"),
   reach=(8.5, "'His cries as a newborn created storms that shook the world tree AND EVERY REALM "
               "IN ITS BRANCHES'; the Odin-Force operates 'across all the infinite planes of "
               "reality'", "wiki"),
   transgression=(9.0, "The runes are the writing the cosmos is made of. He broke an eternal "
                       "cycle -- Ragnarok stopped being a law and became an event that had "
                       "happened", "canon"),
   sustain=(7.0, "The Odin-Force is his to spend and is spent; the state is bought with an eye, "
                 "a hanging and a life", "canon"),
   vector=(7.5, "Bifrost and the branches of Yggdrasil; moves between realms as a matter of "
                "course", "wiki"),
   volition=(9.5, "He hangs himself on the World Tree and gives up an eye for knowledge, then "
                  "spends the resulting life to kill the authors of his people's suffering. The "
                  "highest volition in the library, and it is not close", "canon"),
   acumen=(8.5, "Odin's wisdom plus the runes: he identifies WHO has been farming Asgard's "
                "deaths across all of history, which nobody had managed in any prior cycle",
           "wiki"),
   discernment=(9.0, "Runic omniscience -- he sees the whole loop, from outside it", "canon"),
   suasion=(7.0, "Accepted the throne and the Odinpower, and became 'more distant and less "
                 "empathetic' for it. His authority is total and his warmth is the cost", "wiki"))),

 "The Sentry": dict(
  anchor="M4", host="marvel.fandom.com", epoch="Post-reveal, New Avengers through Siege",
  why_missed="NOTHING missed it -- catalogued, mined, 94,809 chars, 10 clean feats. The only "
             "one of these nine the machine could have assayed on its own, and it never got a "
             "turn because 21,614 entities are queued ahead of nothing.",
  presence="A planet and its moon. The reputation says otherwise -- 'the hero with the power of "
           "a million exploding suns' -- but reputation is not extent, and his cited acts stop "
           "at his own system: he shatters the moon, he erases himself from the mind of every "
           "being on Earth, he trades blows with Galactus and Terrax without deciding anything "
           "above his own sky. The Void's stated goal is 'destroying the entire universe and "
           "more', and a goal is not a feat.",
  axes=dict(
   ruin=(7.5, "'Shattering the entire moon to reveal the Void's whereabouts and then kill him "
              "easily by ripping him apart'; 'levelling whole city blocks'", "wiki"),
   continuity=(8.5, "'When the Scarlet Witch rewrote the history of reality, the Sentry was able "
                    "to resist and retain some memories of his life in the original reality' -- "
                    "he persists through a rewrite of reality itself", "wiki"),
   celerity=(5.0, "The wiki's own conservative figure, and it is modest: 'fast enough to move at "
                  "orbital velocity (5 miles a second)'", "wiki"),
   reach=(6.5, "'Able to erase himself from the memories of every being on the planet' -- "
               "planetary reach, applied to every mind at once", "wiki"),
   transgression=(8.5, "Memory erasure across a whole world including his own mind, memory "
                       "implantation into another man's head, and resistance to a reality "
                       "rewrite. He edits the record of what happened", "wiki"),
   sustain=(6.0, "No clock on the power, but it is hostage to his psychiatric state and has "
                 "failed him at every decisive moment on record", "canon"),
   vector=(4.5, "Flight to orbit; no passage above his own system", "wiki"),
   volition=(2.5, "THE AXIS THAT DEFINES HIM, AND IT IS NEAR THE FLOOR. His will is the thing "
                  "that fails. He had his own existence erased from every mind INCLUDING HIS "
                  "OWN to keep himself in check, and the Void is nothing but his own volition "
                  "turned against him", "wiki"),
   acumen=(3.5, "'This virus created delusions that if the Sentry used his powers, a devil would "
                "appear' -- and he believed it. Agoraphobic and deceived through most of his "
                "record", "wiki"),
   discernment=(3.0, "He cannot tell what is real. That is not a weakness of the character, it "
                     "IS the character, and it sits two points below a man who catches bullets",
                "canon"),
   suasion=(5.5, "The world's most beloved hero in a timeline nobody remembers; 'the Sentry's "
                 "former friends assembled to defend him and the city'", "wiki"))),

 "The Black Winter": dict(
  anchor="M8", host="marvel.fandom.com", epoch="Thor Vol 6, the Herald of Thunder",
  why_missed="never catalogued, and its page title carries a DOUBLE parenthetical -- "
             "'Black Winter (Sixth Cosmos) (Multiverse)'. Every sane guess at the title returns "
             "zero chars, and 'Black Winter' itself is a 492-character disambiguation stub that "
             "mines to nothing. The library had no way to find it by name.",
  presence="It eats universes for a living and it is not the only one of its kind. 'This Black "
           "Winter was one of the ENDERS, A RACE THAT CONSUMES ENTIRE UNIVERSES.' Its own power "
           "listing reads 'Universal Consumption: The Black Winter devours entire universes AND "
           "TIMELINES, reducing them to nothingness.' A being whose diet is universes is not "
           "present at universal scale -- universes are objects to it, and the scale it moves "
           "through is the one that contains them.",
  axes=dict(
   ruin=(9.5, "'Devours entire universes and timelines, reducing them to nothingness' -- and it "
              "'consumed the universe that existed in the Sixth Cosmos before the current "
              "Multiverse, leaving Galan as the sole survivor'", "wiki"),
   continuity=(9.0, "It predates the current multiverse and survived the turn from one cosmos to "
                    "the next. Nothing in the record defeats it; Thor ESCAPES", "wiki"),
   celerity=(4.5, "Never contests tempo with anything. It is inevitability rather than speed",
             "canon"),
   reach=(9.0, "'The Black Winter attacked an alternate universe' -- it reaches across the "
               "multiverse to feed", "wiki"),
   transgression=(8.5, "It consumes TIMELINES, not merely matter: histories are erased rather "
                       "than destroyed. And it wears other beings' futures as a face", "wiki"),
   sustain=(9.5, "Formless and perpetually feeding, across cosmic iterations. 'Life-Force "
                 "Absorption: feeds upon the life forces of universes and cosmic entities it "
                 "consumes, INCLUDING GALACTUS HIMSELF'", "wiki"),
   vector=(8.5, "Moves between universes and between cosmoses under its own power", "wiki"),
   volition=(8.0, "'Assuring him it had no intention of destroying his universe' -- it declines "
                  "a meal by choice, which is the clearest possible evidence of a will", "wiki"),
   acumen=(7.0, "Chose Galan of Taa as its Herald from an entire dead cosmos, and works on Thor "
                "by showing him his own death rather than by fighting him", "wiki"),
   discernment=(7.5, "Perceives across timelines well enough to show a god a true vision of his "
                     "own end", "wiki"),
   suasion=(7.5, "IT MADE GALACTUS. The Devourer of Worlds is its herald and its leavings, and "
                 "'the Silver Surfer compares it to Galactus but on a far larger scale, "
                 "consuming universes instead of planets'", "wiki"))),

 "Getter Emperor": dict(
  anchor="M7", host="getterrobo.fandom.com", epoch="Shin Getter Robo, final evolution",
  why_missed="catalogued as Media, not as a Person -- invisible to every assay stage",
  presence="A universe, and taking more of it continuously. Its own catalogue entry: 'a "
           "gigantic being described as the final evolution of the Getter. Wielding godlike "
           "power, IT CONTINUALLY ABSORBS MATTER ON A UNIVERSAL SCALE.' It is not a being that "
           "acts at universal scale occasionally -- it is one whose ordinary metabolism is "
           "universal, and which grows monotonically toward occupying everything.",
  axes=dict(
   ruin=(8.5, "'Each Getter Machine is armed with a Getter Beam capable of destroying an entire "
              "planet' -- and the Emperor is the final evolution of the whole line", "wiki"),
   continuity=(9.0, "The terminal form of an open-ended evolution. Nothing in the record ends "
                    "it; it is what everything else is on the way to becoming", "wiki"),
   celerity=(5.5, "Enormous and unhurried. Its threat is not tempo and the record never gives "
                  "it one", "canon"),
   reach=(9.0, "'The complete machine's Getter Beam capable of travelling over 400 million "
               "light-years' -- a firing range spanning thousands of galaxies", "wiki"),
   transgression=(8.0, "Getter Rays are the evolutionary principle of that cosmos rather than an "
                       "energy source; the Emperor is that principle wearing a body", "canon"),
   sustain=(9.5, "'Continually absorbs matter' -- it has no clock, no lapse and no upper bound. "
                 "The highest sustain in the library", "wiki"),
   vector=(7.5, "Moves through space at a scale where galaxies are waypoints", "canon"),
   volition=(4.0, "'Depicted as neither a malevolent or benevolent force' -- it wants nothing "
                  "the record can name, which is a low score and not a criticism", "wiki"),
   acumen=(3.0, "No reasoning is ever depicted. It does not plan; it arrives", "canon"),
   discernment=(4.0, "No perception is attributed to it beyond its own advance", "canon"),
   suasion=(6.5, "'A major plot point throughout Shin Getter Robo and the entire Getter Robo "
                 "universe', and 'humanity spread across space and conquered countless worlds' "
                 "under the power it represents. An entire species' future organises around it",
            "wiki"))),

 "Mister Mxyzptlk": dict(
  anchor="M8", host="dc.fandom.com", epoch="Post-Crisis through Prime Earth",
  why_missed="never catalogued (DC's roster is 377 entries); mines to zero feats because he is "
             "the patient of every sentence on his own page",
  presence="A fifth-dimensional being, and the fifth dimension is not inside the multiverse the "
           "way a universe is -- it looks down on it. His own page lists him harangueing "
           "Supermen on Earth-One, Earth-Two, Earth 12, 16, 21, 22, 29, 38, 49, 55, 66, 162, 898 "
           "and 1956. He is a recurring feature OF the multiverse rather than a resident of any "
           "universe in it, and Zrfff is his address.",
  axes=dict(
   ruin=(6.0, "'This changed history so that Earth was destroyed' -- a world lost as the "
              "SIDE EFFECT of him briefly deciding to be a serious student", "wiki"),
   continuity=(9.5, "He cannot be killed, only sent home, and only by being tricked into saying "
                    "his own name backwards. The rules for doing it change every visit, by his "
                    "choice", "wiki"),
   celerity=(4.5, "Never depicted contesting tempo with anything. He does not need to", "canon"),
   reach=(8.5, "Present across fourteen named Earths on his own page, plus counterparts, "
               "offspring and rivals seeded through the multiverse", "wiki"),
   transgression=(9.5, "'A reality-manipulating imp from the 5th Dimension.' He brings a giant "
                       "typewriter into existence out of a billboard advertisement because the "
                       "scene needs one. Near-ceiling, and the axis's clearest case", "wiki"),
   sustain=(9.0, "No state to hold and no cost; the ninety-day exile is imposed from outside "
                 "and is the only limit on record", "wiki"),
   vector=(8.5, "Moves between the fifth dimension and any universe he pleases, at will", "wiki"),
   volition=(7.0, "Does exactly as he likes and nothing compels him -- except a naming rule he "
                  "invented and agreed to himself", "wiki"),
   acumen=(6.5, "Chooses 'Mxyzptlk' deliberately 'as he figures it will be nearly impossible for "
                "Superman to accomplish'. He games the rules he writes", "wiki"),
   discernment=(4.0, "THE DEFECT AT THE HEART OF HIM. A near-omnipotent being who loses, every "
                     "single time, to a newspaperman with a trick -- a rewired typewriter, a "
                     "dare, a bucket of blue paint. Reality obeys him and he cannot read a room",
                "wiki"),
   suasion=(6.0, "Poses as Ben Deroy and 'convinces Lois Lane to marry him'", "wiki"))),
}


def compute():
    out = {}
    for name, rec in ROSTER.items():
        scores = {ax: v[0] for ax, v in rec["axes"].items()}
        sheet = {ax: "[" + v[2] + "] " + v[1] for ax, v in rec["axes"].items()}
        res = A.assay(rec["anchor"], scores, attestation="Transcribed",
                      epoch=rec["epoch"], worksheet=sheet)
        out[name] = {"assay": res, "anchor": rec["anchor"], "host": rec["host"],
                     "epoch": rec["epoch"], "presence": rec["presence"],
                     "why_the_machine_missed_it": rec["why_missed"],
                     "axes": {k: {"score": v[0], "cited": v[1], "provenance": v[2]}
                              for k, v in rec["axes"].items()}}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true")
    a = ap.parse_args()
    out = compute()

    # THE ARTIFACT LANDS BEFORE ANYTHING IS PRINTED.
    #
    # This write used to sit after the report loop, and the report loop prints `moth_number`,
    # which opens with U+1D504 (FRAKTUR CAPITAL A). On this machine's default console that is
    # cp1252, so `python src/handbuilt.py` died with UnicodeEncodeError partway through the
    # first sheet -- BEFORE the write -- and HANDBUILT_ASSAYS.json silently stopped being
    # regenerated while every stale copy on disk went on looking current. A display encoding
    # must never be able to cost the file. Writing first makes the console strictly cosmetic;
    # the reconfigure below then keeps the console working too.
    # THROUGH `silence.write_json`, NOT A HAND-ROLLED FIXED TEMP NAME (order f9c7a2c55536).
    # The five lines this replaces staged to `OUT + ".tmp"`, which costs two things silence.py
    # documents against itself: (1) the temp name carried no pid/thread, so two writers of this
    # path collide on the TEMP FILE and the loser can replace the target with a partial one
    # (silence.py:511, and the same repair already made at standards.py:1534 and
    # retry_synthesis.py:47-49); (2) a denied replace leaked `HANDBUILT_ASSAYS.json.tmp` beside
    # the target permanently, with no cleaner anywhere in the tree (silence.py:519-530) -- and a
    # denied replace is the ORDINARY case on Windows, which is why replace_retry exists at all.
    # This module's three twins -- halo.py, wh40k.py, zfighters.py -- already route this way.
    # The ORDERING is unchanged and must stay so: see the note above on the console encoding.
    if not silence.write_json(OUT, out, indent=1, ensure_ascii=False):
        silence.note("handbuilt.py:write-did-not-land")
        print("WRITE DID NOT LAND: " + OUT)
        return 1
    print("-> " + OUT)

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        _ = "silence-exempt: an un-reconfigurable stdout still prints, just with replacements"

    for n, rec in sorted(out.items(),
                         key=lambda kv: -(A.LADDER.index(kv[1]["assay"]["magnitude"])
                                          + kv[1]["assay"]["decimal"])):
        print("=" * 88)
        print("%-24s %s   (%s)" % (n, rec["assay"]["moth_number"], rec["epoch"]))
        print("=" * 88)
        print("  ANCHOR %s -- %s" % (rec["anchor"], rec["presence"]))
        print("")
        print("  MISSED BECAUSE: " + rec["why_the_machine_missed_it"])
        if a.full:
            print("")
            for ax in A.WEIGHTS:
                d = rec["axes"][ax]
                score = d["score"]
                # A SCORE CAN BE A SENTINEL, NOT A NUMBER. Zalama's ruin, continuity, celerity,
                # vector, volition and discernment are all the string "unestimable" (:184-203),
                # and `%5.1f` on a string raises TypeError -- which killed `--full` on the one
                # sheet the module documents as its most instructive, because the JSON write
                # above already landed and nothing downstream of it was checked again.
                score_str = ("%5.1f" % score if isinstance(score, (int, float))
                             and not isinstance(score, bool) else "%5s" % score)
                # THE WHOLE CITATION, WRAPPED -- NOT `d["cited"][:58]` (order 9c6a23625865).
                # This is the one view whose entire purpose is to show the evidence a score
                # rests on: compute()'s provenance work above exists so a reader checking
                # whether a high score rests on a citation or on the assayer's judgment can do
                # so, and the citations run to 250+ characters. At 58 the reader got as far as
                # the first clause of the argument for a 9.9. catalogue_models.py:227-228
                # already ruled on the console half of this exact shape -- "the persisted copy
                # being complete does not help someone looking at the terminal". Wrapped rather
                # than widened: the fix this tree applies to a truncated field is removal.
                head = "   %-15s%s  [%s] " % (ax, score_str, d["provenance"])
                lines = textwrap.wrap(str(d["cited"]), max(30, 88 - len(head))) or [""]
                print(head + lines[0])
                for extra in lines[1:]:
                    print(" " * len(head) + extra)
        print("")
    return 0


if __name__ == "__main__":
    sys.exit(main())
