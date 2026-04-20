# Curated list of Gen 1-5 Pokemon with animated sprite support
# Format: (pokedex_id, display_name)

POKEMON = [
    (25,  "Pikachu"),
    (133, "Eevee"),
    (4,   "Charmander"),
    (6,   "Charizard"),
    (1,   "Bulbasaur"),
    (7,   "Squirtle"),
    (9,   "Blastoise"),
    (39,  "Jigglypuff"),
    (54,  "Psyduck"),
    (63,  "Abra"),
    (94,  "Gengar"),
    (143, "Snorlax"),
    (150, "Mewtwo"),
    (151, "Mew"),
    (132, "Ditto"),
    (196, "Espeon"),
    (197, "Umbreon"),
    (282, "Gardevoir"),
    (448, "Lucario"),
    (249, "Lugia"),
    (250, "Ho-Oh"),
    (384, "Rayquaza"),
]

POKEMON_BY_ID   = {pid: name for pid, name in POKEMON}
POKEMON_BY_NAME = {name: pid for pid, name in POKEMON}
