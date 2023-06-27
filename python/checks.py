import re

regex_0 = r"[^\.]*?"
# Regex for a word or a word with "-"
una_palabra = r"\w+"
una_palabra_con_rayita = r"\w+-\w+"
regex_1 = f"({una_palabra}|{una_palabra_con_rayita})"
# Land regex
regex_2 = "(land|lands|basic land|basic lands|plains|island|swamp|mountain|forest|plains|islands|swamps|mountains" \
          "|forests|basic plains|basic island|basic swamp|basic mountain|basic forest|basic plains|basic " \
          "islands|basic swamps|basic mountains|basic forests)"
# Target quantity regex
regex_3 = "(a|one|up to one|two|up to two|three|up to three|four|up to four|five|up to five|six|" \
          "up to six|x|up to x|up to ten)"
# Target player regex
regex_4 = r"(player|opponent|any target|target player|target opponent|each player|each opponent|" \
          r"that source's controller)"

regex_5 = "(all|each|another|another target|x|x target|a|target|any number of|one|up to one|up to one target|two|up " \
          "to two|up to two target|three|up to three|up to three target|four|up to four|up to four target)"

regex_6 = "(card|cards|creature|creatures|nonlegendary creature|creature cards?|permanents?|permanent " \
          "cards?|lands?|land cards?|instant or sorcery card|equipment card|aura card|aura or equipment card|artifact " \
          "or enchantment)"


def contains_pattern(text, pattern):
    return bool(re.search(pattern, text.lower()))


def check_all(text, checks):
    for pattern, expected_result in checks:
        if contains_pattern(text, pattern) != expected_result:
            return False
    return True


def check_any(text, checks):
    for pattern, expected_result in checks:
        if contains_pattern(text, pattern) == expected_result:
            return True
    return False


def check_counterspell(row):
    return check_all(row['oracle_text'], [
        (r"counter target", True),
        (r"counter it", True),
        (r"counter all", True),
    ])


def check_mana_rock(row):
    if row['meta.tapping_ability'] == 1 or "tap" in row['oracle_text'].lower():
        if "artifact" in row['all_types']:
            return check_any(row['oracle_text'], [
                (r"{t}: add.*?(mana of any color|mana of that color|{(.*?)})", True),
                (r"{t}, tap an untapped.*?(mana of any color|mana of that color|{(.*?)})", True),
                (r"{t}: choose a color", True),
            ])
    return False


def check_mana_dork(row):
    if row['meta.tapping_ability'] == 1 and row['meta.mana_rock'] is False:
        if "land" not in row['all_types'] and "creature" in row['all_types']:
            return check_any(row['oracle_text'], [
                (r"(^|\b){t}: add", True),
                (r"(^|\b){t}:[^\.]*?add \w+ mana", True),
                (r"(^|\b){t}:[^\.]*?untap\s+target\s+" + regex_2, True),
            ])
    return False


def check_wrath(row):
    wrath_checks = [
        (r"(destroy|exile) (all|all other|each|each other|all attacking) (creature|creatures|(.*?) "
         r"creatures|permanent|permanents|(.*?) permanents|(nonland|multicolored) permanent|(nonland|multicolored) "
         r"permanents)", True),
        (r"each (creature|other creature) gets -(x|[0-9])/-(x|[2-9])", True),
        (r"each creature deals damage to itself equal to", True),
        (r"(destroy|exile) all artifacts, creatures, and enchantments", True),
        (r"sacrifices (all|that many) (creatures|(.*?) creatures|permanents|(.*?) permanents)", True),
        (r"chooses.*?then sacrifices the rest", True),
        (r"creatures.*?get -(x|[0-9])/-(x|[2-9])", True),
        (f"deals ([3-9]|x|[1-9][0-9]) damage to each (creature|{regex_1} creature)", True)
    ]

    return check_any(row['oracle_text'], wrath_checks)


def check_ramp(row):
    ramp_checks = [
        (r"^(?!{[1-9]}: )\w* add (one|two) mana", True),
        (r"{[1]}, {t}: add ({(c|w|u|b|r|g)}{(c|w|u|b|r|g)}|two)", True),
        (r"whenever enchanted land is tapped for mana.*?adds?", True),
        (f"search (your|their) library for {regex_3} {regex_2}.*?put.*?onto the battlefield", True)
    ]

    ramp_negative_checks = [
        (r"{[1-9]}, {t}: add one mana", False),
        (r"enchanted land.*?{t}: add {(c|1|w|u|b|r|g)}", False),
        (r"destroy target (land|nonbasic land)", False),
        (r"spend this mana only to", False),
    ]

    if 'land' not in row['all_types'] and row['meta.mana_rock'] is False and row['meta.mana_dork'] is False:
        return check_any(row['oracle_text'], ramp_checks) and check_all(row['oracle_text'], ramp_negative_checks)

    return False


def check_removal(row):
    removal_checks_1 = [
        (f"(destroy|exile) target ({regex_1}|({regex_1}, {regex_1})|({regex_1}, {regex_1}, {regex_1})|({regex_1}, "
         f"{regex_1}, {regex_1}, {regex_1})) "
         f"(creature|permanent)(?! from (a|your) graveyard| card from (a|your) graveyard)", True),
        (r"(destroy|exile) another target (creature|permanent)", True),
        (r"destroy any number of target (creature|creatures|permanent|permanents)", True),
        (r"(destroy|exile) target (attacking|blocking|attacking or blocking) creature", True),
        (r"destroy up to (one|two|three) target (\w+) (creature|permanent|creatures|permanents)", True),
        (r"exile up to (one|two|three) target (creature|permanent|creatures|permanents)", True),
        (r"exile up to (one|two|three) target (nonland|nonartifact) (creature|permanent|creatures|permanents)",
         True),
        (r"exile up to (one|two|three) target (\w+) (\w+) (creature|permanent|creatures|permanents)", True),
        (r"(destroy|exile) target (\w+) or creature", True),
        (
            r"(destroy|exile) a (creature|permanent) with the (greatest|highest|lowest) (power|toughness|converted mana "
            r"cost|mana value)", True),
        (r"(destroy|exile) target (creature|permanent)(?! from a graveyard| card from a graveyard)", True),
        (r"(destroy|exile) up to (\w+) target (attacking or blocking|attacking|blocking) (creature|creatures)",
         True),
        (r"target (player|opponent) sacrifices a (creature|permanent)", True),
        (r"each (player|opponent) sacrifices (a|one|two|three|four) (creature|creatures|permanent|permanents)",
         True),
        (r"enchanted (creature|permanent) is a treasure", True),
        (r"enchanted creature doesn't untap", True),
        (r"(annihilator)", True),
        (r"deals damage equal to its power to target creature", True),
        (r"(fights|fight) target creature", True),
        (r"(those creatures|the chosen creatures) fight each other", True),
        (r"(fights|fight) up to (\w+) target (creature|creatures)", True),
        (r"(fights|fight) another target creature", True),
        (r"choose target creature you don't control.*?each creature.*?deals damage equal.*?to that creature", True),
        (r"you may have (cardname|it) fight (that creature|target creature|another target creature)", True),
        (r"target creature deals damage to itself equal to (its power)", True),
        (r"target creature gets -[0-9]/-[2-9]", True),
        (r"target creature gets \+[0-9]/-[2-9]", True),
        (r"target creature an opponent controls gets \-[0-9]/\-[2-9]", True),
        (r"enchanted creature (gets|has).*?loses (all|all other) abilities", True),
        (r"enchanted creature gets \-[0-9]/\-[2-9]", True),
        (r"enchanted creature gets \-[0-9]/\-[2-9]", True),
        (r"enchanted creature gets \+[0-9]/\-[2-9]", True),
        (r"(enchanted|target) creature gets \-[0-9][0-9]/\-[0-9][0-9]", True),
        (r"target creature gets \-x/\-x", True),
        (r"target creature gets \+x/\-x", True),
        (r"target creature an opponent controls gets \-x/\-x", True),
        (r"enchanted creature gets \-x/\-x", True),
        (r"enchanted (creature|permanent) can't attack or block", True),
        ("enchanted creature has defender", True),
        ("enchanted creature can't block.*?its activated abilities can't be activated", True),
        (r"enchanted creature.*?loses all abilities", True),
        (r"enchanted (creature|permanent) can't attack.*?block.*?and its activated abilities can't be activated",
         True),
        (r"deals ([2-9|x]) damage.*?(creature|any target|divided as you choose|to each of them)", True),
        (r"deals ([2-9|x]) damage.*?to each of up to (one|two|three|four) (target|targets)", True),
        (r"deals damage equal to.*?to (any target|target creature|target attacking creature|target blocking "
         r"creature|target attacking or blocking creature)", True),
        (r"target creature deals (.*?) damage to itself", True),
        (r"deals damage to (any target|target creature|target attacking creature|target blocking creature|target "
         r"attacking or blocking creature).*?equal to", True),
    ]
    removal_checks_2 = [
        (r"(cardname|it) deals [a-zA-Z0-9] damage to that player.", False),
        (r"(cardname|it) deals [a-zA-Z0-9] damage to target (player|opponent) or planeswalker", False),
        (r"(cardname|it) deals [a-zA-Z0-9] damage to that creature's controller", False),
        ("that was dealt damage this turn", False),
        (r"^(?!damage|creature)\w* random", False),
        (r"search.*?(creature|artifact|enchantment) card", False),
        (r"(destroy|exile) target land", False),
        ("return it to the battlefield", False),
        (r"return that (card|creature|permanent) to the battlefield", False),
        (r"if you control a.*?^(?!liliana)\w* planeswalker", False),
        (r"^(?!additional cost|additional cost)\w* exile (target|a|one|two|three|all).*?from (your|a|target "
         r"opponent's) graveyard", False),
    ]
    return check_any(row['oracle_text'], removal_checks_1) and check_all(row['oracle_text'], removal_checks_2)


def check_tutor(row):
    tutor_checks = [
        (r"search your [^\.]* (put|reveal)", True)
    ]
    neg_tutor_checks = [
        (f"search your library for a {regex_2}", False),
        (r"put [^\.,]* into your graveyard", False),
        (r"search your [^\.,]* for a card named", False),
    ]
    if row['meta.ramp'] is not True and 'land' not in row['all_types']:
        return check_all(row['oracle_text'], tutor_checks) and check_all(row['oracle_text'], neg_tutor_checks)
    return False


def check_card_draw(row):
    draw_checks = [
        (r"(?<!whenever you |if you would )draw [^\.,]*? cards?", True),
        (r"draw (cards equal to|that many cards)", True),
        (r"draw a card for each", True),
        (r"target player draws (.*?) (card|cards)", True),
        (r"draw cards equal to", True),
        (r"(look at|reveal) the.*?put.*?(into|in) your hand", True),
    ]

    neg_draw_checks = [
        (r"cards?, then discard", False),
        (r"discard [^\.,]* cards?, then draw", False),
    ]
    return check_any(row['oracle_text'], draw_checks) and check_all(row['oracle_text'], neg_draw_checks)


def check_burn(row):
    burn_checks = [
        (f"deals {regex_0}damage (to )?{regex_4}", True),
        (f"deals {regex_0} times (damage|x damage) {regex_0} {regex_4}", True),
        (f"deals damage equal to {regex_0} to {regex_4}", True),
        (f"deals damage to {regex_4} equal to", True),
        (f"deals that much damage to {regex_4}", True),
        (f"deals {regex_0}damage (to each of up to|to them|to each of them|equal to {regex_0} to that)", True),
    ]
    return check_any(row['oracle_text'], burn_checks)


def check_discard(row):
    discard_checks = [
        (r"(that|target|each) (player|opponent) discards [^\.,]+? cards?", True),
        (r"unless that player.*?discards a card", True),
        (r"target (player|opponent) reveals their hand.*?you choose.*?exile (that|it)", True),
    ]
    return check_any(row['oracle_text'], discard_checks)


def check_etb_trigger(row):
    etb_checks = [
        (r"enters? the battlefield", True),
    ]
    neg_etb_checks = [
        (r"enters? the battlefield tapped", False),
        (r"whenever a [^\.,]* (you control|your opponents control) enters the battlefield", False),
        (r"land (enter|enters) the battlefield", False),
        (r"it becomes (day|night)", False),
    ]
    return "creature" in row['all_types'] \
        and check_any(row['oracle_text'], etb_checks) \
        and check_all(row['oracle_text'], neg_etb_checks)


def check_etb_tapped(row):
    etb_tapped_checks = [
        (r"enters? the battlefield tapped", True),
    ]
    return check_any(row['oracle_text'], etb_tapped_checks)


def check_die_trigger(row):
    die_trigger_checks = [
        (f"when {regex_0} dies", True),
        (f"whenever {regex_0} dies", True),
        # (r"leaves the battlefield", True),
    ]

    return check_any(row['oracle_text'], die_trigger_checks)


def check_attacks_trigger(row):
    if 'battalion' in row['keywords'] or 'exert' in row['keywords'] or 'raid' in row['keywords']:
        return True

    attacks_trigger_checks = [
        (r"(when|whenever) (cardname|equipped creature|it) attacks", True),
        (r"(when|whenever) (cardname|equipped creature|it) and.*?(other|another) (creature|creatures) "
         r"attack", True),
        (r"(when|whenever) (cardname|equipped creature|it) enters the battlefield or attacks", True),
    ]

    return check_any(row['oracle_text'], attacks_trigger_checks)


def check_psudo_ramp(row):
    psudo_ramp_checks = [
        (r"you may put a (land|basic land).*?onto the battlefield", True),
        (r"(you|each player) may (play|put) an additional land", True),
        (r"if it's a land card, you may put it onto the battlefield", True),
        (r"sacrifice.*?add.*?({(.*?)}|to your mana pool|mana of (any|any one) color)", True),
    ]
    return check_any(row['oracle_text'], psudo_ramp_checks)


def check_static_ramp(row):
    if 'enchantment' in row['all_types'] or 'artifact' in row['all_types'] or 'creature' in row['all_types']:
        if 'land' not in row['all_types']:
            return check_all(row['oracle_text'], [
                (r"at the beginning of.*?add.*?(mana|{(.*?)})", True)
            ])
    return False


def check_creature_tokens(row):
    creature_token_keywords = [
        "living weapon", "amass", "fabricate", "afterlife", "populate", "incubate", "embalm", "eternalize",
    ]

    for kw in creature_token_keywords:
        if kw in row['keywords']:
            return True

    creature_token_checks = [
        (f"(create|put) {regex_0} creature (token|tokens)", True),
        (r"(creature tokens|creature tokens with.*?) are created instead", True),
    ]

    return check_any(row['oracle_text'], creature_token_checks)


def check_extra_turn(row):
    extra_turn_checks = [
        (r"(take|takes) (an|one|two) extra (turn|turns)", True),
    ]

    return check_any(row['oracle_text'], extra_turn_checks)


def check_plus1_counters(row):
    plus1_keyword_checks = [
        "evolve", "mentor", "adapt", "bolster", "bloodthirst", "devour", "monstrosity", "reinforce", "training",
        "modular", "outlast", "riot", "scavenge", "undying", "unleash", "fabricate",
    ]
    for kw in plus1_keyword_checks:
        if kw in row['keywords']:
            return True

    plus1_counter_checks = [
        (r"\+1/\+1 counters?", True),
    ]

    return check_any(row['oracle_text'], plus1_counter_checks)


def check_minus1_counters(row):
    minus1_keyword_checks = [
        "wither", "undying",
    ]
    for kw in minus1_keyword_checks:
        if kw in row['keywords']:
            return True
    minus1_counter_checks = [
        (r"-1/-1 counters?", True),
    ]

    return check_any(row['oracle_text'], minus1_counter_checks)


def check_graveyard_hate(row):
    graveyard_hate_checks = [
        (f"exile {regex_0} from {regex_0} graveyard", True),
        (r"remove all graveyards from the game", True),
        (r"exile each opponent's graveyard", True),
        (r"if a.*?(card|creature|permanent) would (be put into.*?graveyard|die).*?(instead exile|exile it instead)",
         True),
        (r"choose target card in (target opponent's|a) graveyard.*?exile (it|them)", True),
        (r"(target|each) player puts all the cards from their graveyard", True),
        (r"in graveyards( and libraries)? can't", True),
    ]

    neg_graveyard_hate_checks = [
        ("your graveyard", False),
    ]
    return check_any(row['oracle_text'], graveyard_hate_checks) \
        and check_all(row['oracle_text'], neg_graveyard_hate_checks)


def check_free_spells(row):
    if 'cascade' in row['keywords']:
        return True

    free_spell_checks = [
        (r"(rather than pay|without paying) (its|it's|their|this spell's|the) mana cost", True),
        (r"you may pay {", False),
    ]

    return check_all(row['oracle_text'], free_spell_checks)


def check_bounce_spell(row):
    bounce_spell_checks = [
        (r"return [^\.,]*to (it's|its|their) (owner's|owners') (hand|hands)", True),
        (r"owner [^\.,]*puts it.*?(top|bottom).*?library", True),
    ]

    neg_bounce_spell_checks = [
        (r"^(?!islands)\w* you control", False),
        (r"(when|whenever).*?dies.*?return.*?to its owner's hand", False),
        (r"return (cardname|the exiled card) to its owner's hand", False),
        (r"whenever cardname.*?return it to its owner's hand", False),
    ]

    return check_any(row['oracle_text'], bounce_spell_checks) \
        and check_all(row['oracle_text'], neg_bounce_spell_checks)


def check_sac_outlet(row):
    sac_keyword_checks = [
        "exploit", "casualty",
    ]
    for kw in sac_keyword_checks:
        if kw in row['keywords']:
            return True

    sac_outlet_checks = [
        (r"sacrifice (a|another) (creature|permanent)", True),
    ]

    return check_any(row['oracle_text'], sac_outlet_checks)


def check_sac_payoff(row):
    sac_payoff_checks = [
        (r"whenever (you|a player) (sacrifice|sacrifices) a (creature|permanent)", True),
    ]

    return check_any(row['oracle_text'], sac_payoff_checks)


def check_cant_counter(row):
    cant_counter_checks = [
        (r"can't be countered", True),
    ]

    return check_all(row['oracle_text'], cant_counter_checks)


def check_cost_x_more(row):
    if "ward" in row['keywords']:
        return True

    cost_x_more_checks = [
        (r"costs? [^\.,]* more to cast", True),
    ]

    return check_all(row['oracle_text'], cost_x_more_checks)


def check_cost_x_less(row):
    cost_x_less_checks = [
        (r"costs? [^\.,]* less to cast", True),
    ]

    return check_all(row['oracle_text'], cost_x_less_checks)


def check_cost_x_more_activate(row):
    cost_x_more_activate_checks = [
        (r"costs? [^\.,]* more to activate", True),
    ]

    return check_all(row['oracle_text'], cost_x_more_activate_checks)


def check_cost_x_less_activate(row):
    cost_x_less_activate_checks = [
        (r"costs? [^\.,]* less to activate", True),
    ]

    return check_all(row['oracle_text'], cost_x_less_activate_checks)


def check_whenever_opp(row):
    whenever_opp_checks = [
        (r"whenever (an opponent|a player)", True),
    ]

    return check_all(row['oracle_text'], whenever_opp_checks)


def check_gy_to_hand(row):
    return_from_gy_checks = [
        (fr"(return|put) {regex_0} from (your|any|all|their) graveyards? "
         "(to your hand|on top of your library)", True),
        # (fr"choose.*?graveyard.*?return{regex_0}to your hand", True),
        (r"search your (library and/or )?graveyard [^\.]* put it into your hand", True),
    ]

    # neg_return_from_gy_checks = [
    #     (r"exile a creature card from your graveyard", False),
    # ]

    return contains_pattern(row['oracle_text'], r"from (your|any|all) graveyard") \
        and check_any(row['oracle_text'], return_from_gy_checks)


def check_reanimation(row):
    reanimation_keywords = [
        "embalm", "eternalize", "undying", "persist", "unearth", "disturb"
    ]

    if any(kw in row['keywords'] for kw in reanimation_keywords):
        return True

    reanimation_card_names = [
        "Back from the Brink",
        "Command the Dreadhorde",
        "Dollhouse of Horrors",
        "God-Pharaoh's Gift",
    ]

    if row['name'] in reanimation_card_names:
        return True

    reanimation_checks = [
        (fr"(return|put) {regex_0} from (your|any|all|their) graveyards? (to|onto) the battlefield", True),
        (r"choose.*?graveyard.*?return.*?to the battlefield", True),
        (r"return from your graveyard to the battlefield", True),
        (r"put all creature cards from all graveyards onto the battlefield", True),

        (fr"(return|put) {regex_5} {regex_6}.*?from (your|a) graveyard (to|onto) the battlefield", True),

        (r"(return|put) (target|another target).*?card from your graveyard to the battlefield", True),
    ]

    neg_return_from_gy_checks = [
        (r"exile a creature card from your graveyard", False),
    ]

    return contains_pattern(row['oracle_text'], r"from (your|any|all) graveyard") \
        and check_any(row['oracle_text'], reanimation_checks) \
        and check_all(row['oracle_text'], neg_return_from_gy_checks)


def check_cast_from_gy(row):
    cast_from_gy_keywords = [
        "flashback", "jump-start", "escape", "retrace", "aftermath", "embalm", "eternalize",
        "unearth", "disturb",
    ]

    if any(kw in row['keywords'] for kw in cast_from_gy_keywords):
        return True

    cast_from_gy_checks = [
        (r"cast .*? from (your|any|all|their) graveyards?", True),
        (r"exile[^.]+from your graveyard.[^.]+copy[^.]+.[^.]+cast[^.]+.", True),
    ]

    return check_any(row['oracle_text'], cast_from_gy_checks)


def check_lord(row):
    types = [
        "creature",
        "artifact",
        "enchantment",
    ]

    if not any(t in row['all_types'] for t in types):
        return False

    lord_checks = [
        (r"other.*?creatures? you control gets? \+\d+/\+\d+", True),
        (r"each (creature|other creature).*?gets? \+\d+/\+\d+", True),
    ]
    neg_lord_checks = [
        (r"until end of turn", False),
    ]

    return check_any(row['oracle_text'], lord_checks) and check_all(row['oracle_text'], neg_lord_checks)


def check_upkeep_trigger(row):
    upkeep_trigger_checks = [
        (r"beginning of (your|enchanted player's|each|each player's) upkeep", True),
    ]

    return check_any(row['oracle_text'], upkeep_trigger_checks)


def check_end_step_trigger(row):
    end_step_trigger_checks = [
        (r"beginning of (your|enchanted player's|each|each player's) end step", True),
    ]

    return check_any(row['oracle_text'], end_step_trigger_checks)


def check_combat_trigger(row):
    combat_trigger_checks = [
        (r"beginning of (combat|each combat)", True),
        (r"deals combat damage", True),
    ]

    return check_any(row['oracle_text'], combat_trigger_checks)


def check_life_gain(row):
    keywords = [
        "lifelink", "extort",
    ]

    if any(kw in row['keywords'] for kw in keywords):
        return True

    life_gain_checks = [
        (r"gain (.*?) life", True),
        (r"gains (.*?) x life", True),
        (r"gain life equal", True),
    ]

    return check_any(row['oracle_text'], life_gain_checks)


def check_treasure_tokens(row):
    treasure_checks = [
        (r"treasure token", True),
    ]

    return check_any(row['oracle_text'], treasure_checks)


def check_elusive(row):
    if 'creature' in row['all_types']:
        elusive_keywords = [
            "shadow", "skulk", "fear", "intimidate", "menace", "horsemanship", "flying",
            "landwalk", "islandwalk", "plainswalk", "swampwalk", "mountainwalk", "forestwalk",
            "deathtouch", "double strike", "first strike", "vigilance", "reach", "trample",
        ]

        if any(kw in row['keywords'] for kw in elusive_keywords):
            return True

        elusive_checks = [
            (r"can't be blocked", True),
        ]

        return check_any(row['oracle_text'], elusive_checks)
    return False


def check_resilient(row):
    resilient_keywords = [
        "indestructible", "hexproof", "shroud", "protection", "ward",
    ]

    if any(kw in row['keywords'] for kw in resilient_keywords):
        return True

    resilient_checks = [
        (f"protection from", True),
        (r"can't (be|become) (the|target)", True),
        (f"becomes the target of a spell", True),
    ]
    neg_resilient_checks = [
        (r"becomes the target of.*?sacrifice (it|cardname)", False),
        (r"becomes the target of.*?shuffle.*?into its owner's library", False),
        (r"becomes.*?with hexproof.*?until end of turn", False),
    ]

    return check_any(row['oracle_text'], resilient_checks) and check_all(row['oracle_text'], neg_resilient_checks)


def check_cost_reduction(row):
    keywords = [
        "convoke", "foretell", "surge", "delve", "improvise", "spectacle", "assist",
        "affinity", "madness", "miracle", "evoke",
    ]

    if any(kw in row['keywords'] for kw in keywords):
        return True

    cost_reduction_checks = [
        (r"you may pay.*?to cast this spell", True),
        (r"you may pay (.*?) rather than pay", True),
    ]

    return check_all(row['oracle_text'], cost_reduction_checks)


def check_mana_multipliers(row):
    mana_multiplier_checks = [
        (
            r"(whenever|if).*?tap (a|an) (land|permanent|nonland permanent|plains|island|swamp|mountain|forest|creature) for mana.*?add (one mana|an additional|{(.*?)})",
            True),
        (
            r"(whenever|if).*?tap (a|an) (land|permanent|nonland permanent|plains|island|swamp|mountain|forest|creature) for mana.*?it produces.*?instead",
            True),
    ]

    return check_any(row['oracle_text'], mana_multiplier_checks)


def check_card_selection(row):
    card_selection_keywords = [
        "scry", "surveil", "explore", "hideaway"
    ]

    if any(kw in row['keywords'] for kw in card_selection_keywords):
        return True

    card_selection_checks = [
        (r"look at the top.*?bottom of your library.*?on top", True),
        (r"look at the top.*?on top.*?bottom of your library", True),
        (r"look at the top.*?graveyard.*?on top", True),
        (r"look at the top.*?on top.*?graveyard", True),
        (r"look at the top (.*?) of target opponent's library", True),
        (r"look at the top.*?you may put.*?into your graveyard", True),
    ]
    neg_card_selection_checks = [
        (r"whenever a creature you control explores", False),
    ]

    return check_any(row['oracle_text'], card_selection_checks) \
        and check_all(row['oracle_text'], neg_card_selection_checks)


def check_when_cast(row):
    keywords = [
        "prowess",
    ]

    if any(kw in row['keywords'] for kw in keywords):
        return True

    checks = [
        (r"whenever (you|a player|another player|an opponent) cast", True),
    ]

    return check_any(row['oracle_text'], checks)


def check_gain_control(row):
    gain_control_checks = [
        (r"gain control of", True),
    ]

    return check_any(row['oracle_text'], gain_control_checks)


def check_copy(row):
    keywords = [
        "storm", "casualty",
    ]

    if any(kw in row['keywords'] for kw in keywords):
        return True

    copy_checks = [
        (r"copy", True),
    ]

    return check_any(row['oracle_text'], copy_checks)


def check_milling(row):
    milling_keywords = [
        "mill",
    ]

    if any(kw in row['keywords'] for kw in milling_keywords):
        return True

    milling_checks = [
        (r"puts the top.*?of (their|his or her|your) library into (their|his or her|your) graveyard", True),
    ]

    return check_any(row['oracle_text'], milling_checks)


def check_trigger_multiplier(row):
    checks = [
        (r"triggers (one more|an additional) time", True),
    ]

    return check_any(row['oracle_text'], checks)


def check_untapper(row):
    checks = [
        (r"untap (target|that|another|the chosen|them|all)", True),
    ]
    neg_checks = [
        (r"gain control", False),
        (r"untapped", False),
    ]
    return check_any(row['oracle_text'], checks) and check_all(row['oracle_text'], neg_checks)


def check_static_effects(row):
    checks = [
        (r"(artifacts and creatures|creatures|permanents) (your opponents|enchanted player|you) "
         "(control|controls) (enter|lose|have|with|can't)", True),
        (r"activated abilities of (artifacts|creatures).*?can't be activated", True),
        (r"can't cause their controller to search their library", True),
        (r"don't cause abilities to trigger", True),
        (r"can't draw more than", True),
        (r"only any time they could cast a sorcery", True),
        (r"enchanted player", True),
        (r"at the beginning of (your|each).*?(you|that player)", True),
        (r"(players|counters) can't", True),
        (r"if (you|target opponent|a player|another player) would.*?instead", True),
        (r"each (card|(.*?) card) in your (hand|graveyard).*?has", True),
        (r"(each player|players|your opponents) can't cast (spells|more than)", True),
        (r"is determined by their (power|toughness) rather than their (power|toughness)", True),
        (r"each creature.*?assigns combat damage.*?toughness rather than its power", True),
        (r"they put half that many", True),
    ]
    return check_any(row['oracle_text'], checks)


def check_damage_multipliers(row):
    checks = [
        (r"it deals that much damage plus", True),
        (r"it deals (double|triple) that damage", True),
    ]
    return check_any(row['oracle_text'], checks)


def check_variable_pt(row):
    if 'creature' in row['all_types']:
        return contains_pattern(row['power'], r"\*") or contains_pattern(row['toughness'], r"\*")
    return False


def check_agressive(row):
    if 'creature' in row['all_types']:
        keywords = [
            "haste", "riot", "dash",
        ]

        if any(kw in row['keywords'] for kw in keywords):
            return True
    return False


def check_doublers(row):
    checks = [
        (r"(put|it creates|it puts|create) twice that many", True),
    ]
    return check_any(row['oracle_text'], checks)


def check_blinker(row):
    checks = [
        (r"exile (up to (one|two) target|up to (one|two) other target|target|another target|any number of target) ("
         r"creature|creatures|(.*?) creature|permanent|permanents|(.*?) permanent|(.*?) or creature).*?return.*?to "
         r"the battlefield", True),
        (r"exile (target|another target) (permanent|creature).*?return (that card|that permanent|it) to the "
         r"battlefield under its owner's control", True),
        (r"exile (two|three|four|five|all|each).*?you (control|own).*?then return (them|those).*?to the battlefield",
         True),
    ]
    return check_any(row['oracle_text'], checks)


def check_graveyard_tutor(row):
    if 'land' in row['all_types']:
        return False

    if row['meta.ramp'] is True or row['meta.tutor'] is True:
        return False

    checks = [
        (r"search your library for.*?put.*?into your graveyard", True),
    ]

    return check_any(row['oracle_text'], checks)


def check_play_toplibrary(row):
    checks = [
        (r"play with the top of your library", True),
        (r"you may (play|cast).*?(from the|the) top of your library", True),
    ]

    return check_any(row['oracle_text'], checks)


def check_life_loss(row):
    keywords = [
        "afflict", "extort",
    ]

    if any(kw in row['keywords'] for kw in keywords):
        return True

    checks = [
        (fr"{regex_4}.*?loses (.*?) life", True),
    ]

    return check_any(row['oracle_text'], checks)


def check_play_from_graveyard(row):
    checks = [
        (rf"you may (play|cast).*?{regex_6}.*?from your graveyard", True),
    ]

    return check_any(row['oracle_text'], checks)


def check_venture(row):
    keywords = [
        "initiative",
    ]

    if any(kw in row['keywords'] for kw in keywords):
        return True

    checks = [
        (r"venture into the dungeon", True),
    ]

    return check_any(row['oracle_text'], checks)


def check_animator(row):
    checks = [
        (r"(target|another target).*?becomes a.*?creature", True),
    ]
    neg_checks = [
        (r"copy", False),
        (r"class", False),
    ]

    return check_any(row['oracle_text'], checks) and check_any(row['oracle_text'], neg_checks)


def check_wish(row):
    if 'learn' in row['keywords']:
        return True

    checks = [
        (r"from outside the game", True),
    ]

    return check_any(row['oracle_text'], checks)


def check_gy_synergies(row):
    keywords = [
        "dredge",
    ]

    if any(kw in row['keywords'] for kw in keywords):
        return True

    checks = [
        (r"for each.*?in your graveyard", True),
    ]
    return check_any(row['oracle_text'], checks)


def check_looting_similar(row):
    keywords = [
        "cycling",
    ]

    if any(kw in row['keywords'] for kw in keywords):
        return True

    checks = [
        (r"draw (a|one|two|three|four) (card|cards), then discard (a|one|two|three|four) (card|cards)", True),
        (
            r"discard (a|one|two|three|four) (card|cards)(,|:) (draw|then draw) (a|one|two|three|four) (card|cards)",
            True),
        (r"create (.*?) (blood|clue) token", True),
    ]
    return check_any(row['oracle_text'], checks)


def check_cheatinto_play(row):
    checks = [
        (r"creature.*?put (it|them) onto the battlefield", True),
        (r"look at the.*?put.*?creature.*?onto the battlefield", True),
        (r"you may put.*?(creature|permanent).*?onto the battlefield", True),
    ]
    return check_any(row['oracle_text'], checks)


def check_pumped_foreach(row):
    checks = [
        (r"gets \+[0-9]/\+[0-9] for each", True),
    ]
    return check_any(row['oracle_text'], checks)


def check_ritual(row):
    if 'instant' in row['all_types'] or 'sorcery' in row['all_types']:
        checks = [
            (r"add {(.*?)}", True),
            (r"add (.*?) {(.*?)}", True),
        ]
        return check_any(row['oracle_text'], checks)
    return False


def check_no_maximum(row):
    checks = [
        (r"no maximum hand size", True),
    ]

    return check_any(row['oracle_text'], checks)


def check_wheel(row):
    checks = [
        (r"each player.*?(discards|shuffles (his or her|their) hand and graveyard into (his or her|their) "
         r"library).*?then draws seven cards", True),
    ]

    return check_any(row['oracle_text'], checks)


def check_extra_combat(row):
    checks = [
        (r"additional combat phase", True),
    ]
    return check_any(row['oracle_text'], checks)


def check_ghostly_prison(row):
    checks = [
        (r"creatures can't attack (you|you or planeswalkers you control) unless", True),
        (r"whenever an opponent attacks (you|with creatures)", True),
    ]
    return check_any(row['oracle_text'], checks)


def check_land_destruction(row):
    checks = [
        (r"destroy target (land|nonbasic land)", True),
        (r"destroy all (land|nonbasic land)", True),
    ]
    return check_any(row['oracle_text'], checks)


def check_win_game(row):
    checks = [
        (r"you win the game", True),
    ]
    return check_any(row['oracle_text'], checks)


def check_lose_game(row):
    checks = [
        (r"you lose the game", True),
    ]
    return check_any(row['oracle_text'], checks)


def check_cant_lose(row):
    checks = [
        (r"you can't lose the game", True),
        (r"your opponents can't win the game", True),
    ]
    return check_any(row['oracle_text'], checks)


check_list = {
    'meta.counterspell': check_counterspell,
    'meta.mana_rock': check_mana_rock,
    'meta.mana_dork': check_mana_dork,
    'meta.wrath': check_wrath,
    'meta.ramp': check_ramp,
    'meta.removal': check_removal,
    'meta.tutor': check_tutor,
    'meta.card_draw': check_card_draw,
    'meta.burn': check_burn,
    'meta.discard': check_discard,
    'meta.etb': check_etb_trigger,
    'meta.etb_tapped': check_etb_tapped,
    'meta.die_trigger': check_die_trigger,
    'meta.attacks_trigger': check_attacks_trigger,
    'meta.psudo_ramp': check_psudo_ramp,
    'meta.static_ramp': check_static_ramp,
    'meta.creature_tokens': check_creature_tokens,
    'meta.extra_turn': check_extra_turn,
    'meta.plus1_counters': check_plus1_counters,
    'meta.minus1_counters': check_minus1_counters,
    'meta.graveyard_hate': check_graveyard_hate,
    'meta.free_spell': check_free_spells,
    'meta.bounce_spell': check_bounce_spell,
    'meta.sac_outlet': check_sac_outlet,
    'meta.sac_payoff': check_sac_payoff,
    'meta.cant_counter': check_cant_counter,
    'meta.cost_x_more': check_cost_x_more,
    'meta.cost_x_less': check_cost_x_less,
    'meta.cost_x_more_activate': check_cost_x_more_activate,
    'meta.cost_x_less_activate': check_cost_x_less_activate,
    'meta.whenever_opp': check_whenever_opp,
    'meta.gy_to_hand': check_gy_to_hand,
    'meta.reanimation': check_reanimation,
    'meta.cast_from_gy': check_cast_from_gy,
    'meta.lord': check_lord,
    'meta.upkeep_trigger': check_upkeep_trigger,
    'meta.end_step_trigger': check_end_step_trigger,
    'meta.combat_trigger': check_combat_trigger,
    'meta.life_gain': check_life_gain,
    'meta.treasure_tokens': check_treasure_tokens,
    'meta.elusive': check_elusive,
    'meta.resilient': check_resilient,
    'meta.cost_reduction': check_cost_reduction,
    'meta.mana_multiplier': check_mana_multipliers,
    'meta.card_selection': check_card_selection,
    'meta.when_cast': check_when_cast,
    'meta.gain_control': check_gain_control,
    'meta.copy': check_copy,
    'meta.milling': check_milling,
    'meta.trigger_multiplier': check_trigger_multiplier,
    'meta.untapper': check_untapper,
    'meta.static_effects': check_static_effects,
    'meta.damage_multipliers': check_damage_multipliers,
    'meta.variable_pt': check_variable_pt,
    'meta.agressive': check_agressive,
    'meta.doublers': check_doublers,
    'meta.blinker': check_doublers,
    'meta.graveyard_tutor': check_graveyard_tutor,
    'meta.play_toplibrary': check_play_toplibrary,
    'meta.life_lose': check_life_loss,
    'meta.play_from_graveyard': check_play_from_graveyard,
    'meta.venture': check_venture,
    'meta.animator': check_animator,
    'meta.wish': check_wish,
    'meta.gy_synergies': check_gy_synergies,
    'meta.looting_similar': check_looting_similar,
    'meta.cheatinto_play': check_cheatinto_play,
    'meta.pumped_foreach': check_pumped_foreach,
    'meta.ritual': check_ritual,
    'meta.no_maximum': check_no_maximum,
    'meta.wheel': check_wheel,
    'meta.extra_combat': check_extra_combat,
    'meta.ghostly_prison': check_ghostly_prison,
    'meta.land_destruction': check_land_destruction,
    'meta.win_game': check_win_game,
    'meta.lose_game': check_lose_game,
    'meta.cant_lose': check_cant_lose,
}
