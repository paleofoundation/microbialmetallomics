#!/usr/bin/env python3
"""Generate social covers for the current published collection and reviews.

Requires Pillow. The covers use editorial typography and conceptual motifs,
not chemical structures or claims of treatment efficacy. No network access.
On macOS, the installed Georgia and Avenir fonts are used; Linux has explicit
DejaVu fallbacks. Fonts are rendered to pixels and are not redistributed.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
import argparse
import math
import json
from check_host_series import release_scope

from PIL import Image, ImageDraw, ImageFont, PngImagePlugin


ROOT = Path(__file__).resolve().parents[1]
WIDTH, HEIGHT, SCALE = 1200, 630, 2
PAPER = "#F6F3EB"
FOREST = "#193F35"
INK = "#213D35"
MUTED = "#576B5C"
COPPER = "#AE653F"
RULE = "#D8D6C8"
LEAF = "#90AB8A"
PANEL_RULE = "#476A55"


@dataclass(frozen=True)
class Cover:
    slug: str
    series: str
    lines: tuple[str, ...]
    subline: str
    motif: str
    action: tuple[str, ...]
    number: str


COVERS = (
    Cover("host-metal-defense", "A RESEARCH COLLECTION", ("Host metal", "defenses"),
          "The host strategies that shape microbial access.", "Fe", ("WITHHOLD", "REDISTRIBUTE", "DEFEND"), "01 / 02"),
    Cover("unexpected-metal-biology", "A RESEARCH COLLECTION", ("Unexpected", "metal biology"),
          "What familiar compounds might be doing with metals.", "Zn", ("FOLLOW", "THE METAL", "INTERACTION"), "02 / 02"),
    Cover("lactoferrin-iron-withholding-microbial-countermeasures", "HOST METAL DEFENSES", ("Lactoferrin:", "the battle for iron"),
          "Iron withholding and microbial counterstrategies.", "Fe", ("BINDING", "ACCESS", "IMMUNITY"), "01 / 08"),
    Cover("hepcidin-ferroportin-iron-redistribution", "HOST METAL DEFENSES", ("Hepcidin &", "ferroportin:", "rerouting iron"),
          "Hormones, transporters and the tradeoffs of restriction.", "Fe", ("SIGNAL", "TRANSPORT", "DISTRIBUTE"), "02 / 08"),
    Cover("transferrin-ferritin-heme-recycling", "HOST METAL DEFENSES", ("Transferrin, ferritin", "& the recycling", "of heme"),
          "Storage, trafficking and the iron microbes pursue.", "Fe", ("CARRY", "STORE", "RECYCLE"), "03 / 08"),
    Cover("calprotectin-multimetal-nutritional-immunity", "HOST METAL DEFENSES", ("Calprotectin:", "many metals,", "one immune weapon"),
          "Nutritional immunity beyond zinc alone.", "Zn", ("WITHHOLD", "COMPETE", "RESPOND"), "04 / 08"),
    Cover("phagosomal-copper-zinc-intoxication", "HOST METAL DEFENSES", ("Copper & zinc", "inside the", "phagosome"),
          "When host defenses use metal excess.", "Cu", ("DELIVER", "CONCENTRATE", "DEFEND"), "05 / 08"),
    Cover("metallothionein-metal-buffering-microbial-conflict", "HOST METAL DEFENSES", ("Metallothionein:", "the cell’s metal", "buffer"),
          "Binding, release and the tradeoffs of protection.", "Zn", ("BUFFER", "RELEASE", "SIGNAL"), "06 / 08"),
    Cover("glutathione-metals-mitochondria-drug-metabolism", "HOST METAL DEFENSES", ("Glutathione,", "metals &", "mitochondria"),
          "Redox reserves, drug metabolism and metal handling.", "GSH", ("REDOX", "LIGANDING", "RESILIENCE"), "07 / 08"),
    Cover("bile-acids-biliary-metal-excretion", "HOST METAL DEFENSES", ("Bile, metals", "& the route out"),
          "Binding a metal is only the beginning.", "Cu", ("TRANSPORT", "EXCRETION", "RETURN"), "08 / 08"),
    Cover("vancomycin-zinc-binding-antimicrobial-mechanisms", "UNEXPECTED METAL BIOLOGY", ("Vancomycin", "meets zinc"),
          "An antibiotic’s unexpected metal interaction.", "Zn", ("ANTIBIOTIC", "BINDING", "MECHANISM"), "01 / 03"),
    Cover("silymarin-metal-binding-liver-evidence", "UNEXPECTED METAL BIOLOGY", ("Silymarin:", "metal binding &", "liver evidence"),
          "From ligand chemistry to claims about human benefit.", "Fe", ("LIGANDS", "MODELS", "EVIDENCE"), "02 / 03"),
    Cover("saccharomyces-boulardii-metal-biosorption", "UNEXPECTED METAL BIOLOGY", ("Can probiotic yeast", "capture metals?"),
          "S. boulardii, biosorption and the path to excretion.", "Pb", ("ADSORPTION", "TRANSIT", "RELEASE"), "03 / 03"),
)


def font_path(kind: str) -> Path:
    paths = {
        "serif": (
            "/System/Library/Fonts/Supplemental/Georgia.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        ),
        "sans": (
            "/System/Library/Fonts/Avenir Next.ttc",
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ),
        "mono": (
            "/System/Library/Fonts/Menlo.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        ),
    }[kind]
    for path in paths:
        if Path(path).exists():
            return Path(path)
    raise FileNotFoundError(f"No installed {kind} font; install Georgia/Avenir or DejaVu.")


FONT_PATHS = {}


def font(kind: str, size: int):
    if kind not in FONT_PATHS:
        FONT_PATHS[kind] = font_path(kind)
    return ImageFont.truetype(str(FONT_PATHS[kind]), size * SCALE)


def box(coords):
    return tuple(round(c * SCALE) for c in coords)


def checked_text(draw, xy, text, face, color, bounds):
    """All editorial text must fit its declared safe area."""
    xy = box(xy)
    bounds = box(bounds)
    actual = draw.textbbox(xy, text, font=face, anchor="lt")
    if not (actual[0] >= bounds[0] and actual[1] >= bounds[1] and actual[2] <= bounds[2] and actual[3] <= bounds[3]):
        raise ValueError(f"Text outside safe area: {text!r}: {actual} vs {bounds}")
    draw.text(xy, text, font=face, fill=color, anchor="lt")
    return actual


def text_width(draw, text, face):
    return draw.textlength(text, font=face) / SCALE


def tracked(draw, xy, text, size, tracking, color, bounds):
    face = font("sans", size)
    x, y = xy
    for char in text:
        checked_text(draw, (x, y), char, face, color, bounds)
        x += text_width(draw, char, face) + tracking
    return x


def choose_title_font(draw, lines):
    """Keep headlines large, using explicit line breaks rather than truncation."""
    for size in range(94 if len(lines) == 2 else 75, 56, -1):
        face = font("serif", size)
        line_height = size * 1.10
        last_height = draw.textbbox((0, 0), lines[-1], font=face, anchor="lt")[3] / SCALE
        if all(text_width(draw, line, face) <= 744 for line in lines) and (len(lines) - 1) * line_height + last_height <= 232:
            return face, size, line_height
    raise ValueError(f"Title does not fit legibly: {lines}")


def wrap_line(draw, text, face, width):
    lines, current = [], ""
    for word in text.split():
        proposed = f"{current} {word}".strip()
        if text_width(draw, proposed, face) <= width:
            current = proposed
        else:
            if not current:
                raise ValueError(f"Subline word does not fit: {word}")
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def draw_panel(draw, cover):
    draw.rectangle(box((898, 0, WIDTH, HEIGHT)), fill=FOREST)
    # This orbit-like motif identifies the editorial topic. It is not a
    # molecular model, coordination geometry, or representation of a reaction.
    cx, cy = 1049, 299
    for radius in (86, 118):
        draw.ellipse(box((cx - radius, cy - radius, cx + radius, cy + radius)), outline=PANEL_RULE, width=SCALE)
    draw.arc(box((cx - 102, cy - 102, cx + 102, cy + 102)), 218, 332, fill=LEAF, width=2 * SCALE)
    draw.arc(box((cx - 102, cy - 102, cx + 102, cy + 102)), 35, 113, fill=COPPER, width=3 * SCALE)
    for angle, color, radius in ((235, PAPER, 6), (28, LEAF, 5), (124, COPPER, 7)):
        x, y = cx + 118 * math.cos(math.radians(angle)), cy + 118 * math.sin(math.radians(angle))
        draw.ellipse(box((x - radius, y - radius, x + radius, y + radius)), fill=color)
    motif_face = font("serif", 64 if len(cover.motif) == 2 else 46)
    motif_width = text_width(draw, cover.motif, motif_face)
    checked_text(draw, (cx - motif_width / 2, cy - 32), cover.motif, motif_face, PAPER, (941, 230, 1158, 350))
    center_face = font("sans", 11)
    center_label = "METAL BIOLOGY"
    checked_text(draw, (cx - text_width(draw, center_label, center_face) / 2, cy + 42), center_label, center_face, LEAF, (947, 333, 1160, 357))
    tracked(draw, (946, 65), cover.number, 15, 1.5, LEAF, (943, 60, 1160, 87))
    for index, line in enumerate(cover.action):
        face = font("sans", 14)
        width = text_width(draw, line, face)
        checked_text(draw, (cx - width / 2, 452 + index * 25), line, face, PAPER if index == 0 else LEAF, (922, 440, 1180, 528))
    draw.line(box((964, 561, 1134, 561)), fill=PANEL_RULE, width=SCALE)
    tiny = font("sans", 11)
    signature = "RESEARCH SERIES"
    checked_text(draw, (cx - text_width(draw, signature, tiny) / 2, 578), signature, tiny, LEAF, (941, 570, 1160, 603))


def render(cover: Cover, target: Path):
    image = Image.new("RGB", (WIDTH * SCALE, HEIGHT * SCALE), PAPER)
    draw = ImageDraw.Draw(image)
    draw_panel(draw, cover)
    # A small typographic seal, consistent with the guide's restrained palette.
    draw.ellipse(box((72, 54, 103, 85)), outline=FOREST, width=SCALE)
    draw.ellipse(box((97, 54, 105, 62)), fill=COPPER)
    checked_text(draw, (78, 61), "M", font("serif", 18), FOREST, (74, 58, 101, 82))
    tracked(draw, (119, 62), "MICROBIAL METALLOMICS", 18, 1.3, FOREST, (116, 58, 823, 88))
    draw.line(box((74, 116, 824, 116)), fill=RULE, width=SCALE)
    draw.line(box((74, 162, 103, 162)), fill=COPPER, width=3 * SCALE)
    tracked(draw, (117, 153), cover.series, 14, 1.6, COPPER, (115, 148, 826, 176))
    face, size, line_height = choose_title_font(draw, cover.lines)
    for index, line in enumerate(cover.lines):
        checked_text(draw, (72, 211 + index * line_height), line, face, INK, (68, 203, 829, 447))
    sub_face = font("sans", 22)
    sublines = wrap_line(draw, cover.subline, sub_face, 744)
    assert len(sublines) <= 2, f"Subline too long: {cover.slug}"
    for index, line in enumerate(sublines):
        checked_text(draw, (75, 475 + index * 28), line, sub_face, MUTED, (72, 470, 826, 535))
    draw.line(box((74, 561, 824, 561)), fill=RULE, width=SCALE)
    checked_text(draw, (75, 579), "microbialmetallomics.com", font("sans", 15), FOREST, (73, 573, 563, 605))
    footer = "FOLLOW THE METAL"
    footer_face = font("mono", 11)
    checked_text(draw, (824 - text_width(draw, footer, footer_face), 582), footer, footer_face, MUTED, (601, 575, 826, 605))
    image = image.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
    meta = PngImagePlugin.PngInfo()
    meta.add_text("Title", " ".join(cover.lines))
    meta.add_text("Description", f"{' '.join(cover.lines)} — {cover.series.title()}. {cover.subline} Microbial Metallomics.")
    meta.add_text("Software", "Microbial Metallomics editorial cover generator")
    image.save(target, format="PNG", pnginfo=meta, optimize=True)
    with Image.open(target) as check:
        assert check.size == (WIDTH, HEIGHT), f"Incorrect cover size: {target}"
        assert check.mode == "RGB", f"Incorrect cover mode: {target}"
        check.verify()
    return size


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "assets/series-covers")
    parser.add_argument("--release", type=Path, default=ROOT / "assets/data/host-defense/release.json")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    assert len({c.slug for c in COVERS}) == 13
    selected, _ = release_scope(json.loads(args.release.read_text()))
    covers = [c for c in COVERS if c.slug in selected or c.slug in ['host-metal-defense', 'unexpected-metal-biology']]
    for cover in covers:
        if cover.slug in selected:
            peers = [c.slug for c in covers if c.series == cover.series]
            cover = replace(cover, number=f'{peers.index(cover.slug) + 1:02d} / {len(peers):02d}')
        target = args.output / f"{cover.slug}.png"
        size = render(cover, target)
        print(f"{target.name}: {WIDTH}×{HEIGHT}; headline {size}px; {target.stat().st_size:,} bytes")
    print(f"Built {len(covers)} editorial covers. Every text block fits its declared safe area.")


if __name__ == "__main__":
    main()
