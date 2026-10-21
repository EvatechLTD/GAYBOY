"""Reapply the emulator's four shade indices to its pixel-exact site captures."""
from pathlib import Path
from PIL import Image
from sameboy_palette import website_palette

ROOT = Path(__file__).resolve().parents[1]


def main():
    colors = website_palette()
    shades = [(c & 255, (c >> 8) & 255, (c >> 16) & 255) for c in colors]
    for source in (ROOT / 'website/images').glob('*.png'):
        image = Image.open(source).convert('RGB')
        used = sorted(set(image.getdata()), key=lambda c: sum(v * w for v, w in zip(c, (299, 587, 114))), reverse=True)
        if len(used) > 4:
            raise ValueError(f'{source.name} is not a four-shade Game Boy capture')
        # Two-shade captures use the endpoints; four-shade captures retain indices.
        indices = (0, 3) if len(used) == 2 else range(len(used))
        lookup = dict(zip(used, (shades[i] for i in indices)))
        image.putdata([lookup[pixel] for pixel in image.getdata()])
        image.save(source)
        (ROOT / 'network/apps/gayboy/images' / source.name).write_bytes(source.read_bytes())
        assert set(image.getdata()).issubset(set(shades))
        print(source.name, 'neutral white; original pixel positions preserved')


if __name__ == '__main__':
    main()
