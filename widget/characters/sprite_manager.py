"""
Downloads and caches Pokemon HOME HD sprites from PokeAPI's GitHub sprite repo.
All sprites are saved to the local sprites/ folder.
"""
import os
import sys
import requests as _requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from logger import log

_SPRITES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "sprites"
)

_BASE = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon"

# Pokemon HOME HD renders — clean transparent PNG, ~475x475
_URLS = {
    "front":        "{base}/other/home/{id}.png",
    "front_shiny":  "{base}/other/home/shiny/{id}.png",
    # Fallback to official artwork if HOME not available
    "fallback":     "{base}/other/official-artwork/{id}.png",
    "fallback_shiny": "{base}/other/official-artwork/shiny/{id}.png",
}


def sprite_path(pokemon_id: int, variant: str = "front") -> str:
    return os.path.join(_SPRITES_DIR, f"{pokemon_id}_{variant}.png")


def is_cached(pokemon_id: int, variant: str = "front") -> bool:
    return os.path.exists(sprite_path(pokemon_id, variant))


def download(pokemon_id: int, variant: str = "front") -> str | None:
    path = sprite_path(pokemon_id, variant)
    if os.path.exists(path):
        return path

    urls_to_try = []
    if variant in _URLS:
        urls_to_try.append(_URLS[variant].format(base=_BASE, id=pokemon_id))
    # Always try fallback artwork as backup
    fallback_key = "fallback_shiny" if "shiny" in variant else "fallback"
    fallback_url = _URLS[fallback_key].format(base=_BASE, id=pokemon_id)
    if fallback_url not in urls_to_try:
        urls_to_try.append(fallback_url)

    os.makedirs(_SPRITES_DIR, exist_ok=True)
    for url in urls_to_try:
        log.info(f"Downloading sprite | pokemon={pokemon_id} variant={variant} | {url}")
        try:
            resp = _requests.get(url, timeout=15)
            if resp.status_code == 200 and len(resp.content) > 500:
                with open(path, "wb") as f:
                    f.write(resp.content)
                log.info(f"Sprite saved ({len(resp.content)//1024}KB): {path}")
                return path
            else:
                log.warning(f"Sprite not found ({resp.status_code}): {url}")
        except Exception as e:
            log.error(f"Download error: {e}")

    return None


def ensure_pokemon(pokemon_id: int, shiny: bool = False) -> dict[str, str | None]:
    """Download front and shiny variants. Returns dict of variant -> local path."""
    variants = ["front_shiny"] if shiny else ["front"]
    result = {}
    for v in variants:
        result[v] = download(pokemon_id, v)
    log.info(f"Sprites ready for Pokemon #{pokemon_id} | shiny={shiny}")
    return result
