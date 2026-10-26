"""Location titles shown over the battle map (story files 648-700, section 6: 16-colour
grey clut + 4bpp 256x24, index 6..15 = brightness, 0 = transparent). Needs Pillow.
Usage: <python with Pillow> scripts/gen_loctitles.py <VBE_work dir> -> assets/loctitles.bin
(per file: 2-byte file number + 3072 bytes of pixels)."""
import sys, struct
from PIL import Image, ImageDraw, ImageFont
W = sys.argv[1]
RU = {
 'Fruah Village': 'Деревня Фруа', 'Egas Canyon': 'Каньон Эгас', 'Maqui Bridge': 'Мост Маки',
 'Araba Castle': 'Замок Араба', 'Muilama Plateau': 'Плато Муилама', 'Vukryou Desert': 'Пустыня Вукрю',
 'Echial Field': 'Поле Экиал', 'Regio Castle': 'Замок Регио', 'Melania Delta': 'Дельта Мелании',
 'Aylin': 'Айлин', 'Darafa Field': 'Поле Дарафа', 'Eiza Township': 'Посёлок Эйза',
 'Norze Castle': 'Замок Норзе', 'Royal Capital': 'Королевская столица', 'Taliu Tundra': 'Тундра Талиу',
 'Okisa Trail': 'Тропа Окиса', 'Xenia Forest': 'Лес Ксения', 'Vanilin Fort': 'Форт Ванилин',
 'Imperial Capitol': 'Имперская столица', 'Imperial Palace': 'Имперский дворец',
 'Mogron Trail': 'Тропа Могрон', 'Rakton Plaza': 'Площадь Рактон', 'Altaiga Forest': 'Лес Алтайга',
 'Tokoma Valley': 'Долина Токома', 'Estel Mountain': 'Гора Эстель', 'Flavin Trail': 'Тропа Флавин',
 'Lake Sokuen': 'Озеро Сокуэн', 'Algini Field': 'Поле Алджини', 'Gultar Trail': 'Тропа Гултар',
 'Tolefas Village': 'Деревня Толефас',
}
FILES = {  # story file -> English title (read from the original images)
 648: 'Fruah Village', 649: 'Egas Canyon', 650: 'Maqui Bridge', 651: 'Araba Castle',
 652: 'Muilama Plateau', 653: 'Vukryou Desert', 654: 'Echial Field', 655: 'Regio Castle',
 656: 'Vukryou Desert', 657: 'Echial Field', 658: 'Echial Field', 659: 'Melania Delta',
 660: 'Aylin', 661: 'Darafa Field', 662: 'Eiza Township', 663: 'Norze Castle',
 664: 'Royal Capital', 665: 'Taliu Tundra', 666: 'Okisa Trail', 667: 'Xenia Forest',
 668: 'Vanilin Fort', 669: 'Imperial Capitol', 670: 'Imperial Palace', 671: 'Mogron Trail',
 672: 'Muilama Plateau', 673: 'Rakton Plaza', 674: 'Araba Castle', 675: 'Araba Castle',
 676: 'Altaiga Forest', 677: 'Taliu Tundra', 678: 'Tokoma Valley', 679: 'Echial Field',
 680: 'Regio Castle', 681: 'Vukryou Desert', 682: 'Melania Delta', 683: 'Estel Mountain',
 684: 'Flavin Trail', 685: 'Xenia Forest', 686: 'Vanilin Fort', 687: 'Imperial Palace',
 688: 'Vanilin Fort', 689: 'Imperial Palace', 690: 'Estel Mountain', 691: 'Araba Castle',
 692: 'Taliu Tundra', 693: 'Lake Sokuen', 694: 'Algini Field', 695: 'Eiza Township',
 696: 'Gultar Trail', 697: 'Rakton Plaza', 698: 'Xenia Forest', 699: 'Tolefas Village',
 700: 'Imperial Palace',
}
SS = 4
CX, MAXW = 71.5, 142          # the game shows only the left 144 px, centred on x=71
SIZES = {}
font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Luminari.ttf', 17 * SS)
cache = {}
def render(text):
    if text in cache: return cache[text]
    big = Image.new('L', (256 * SS, 24 * SS), 0); dr = ImageDraw.Draw(big)
    tw = dr.textlength(text, font=font)
    size = 17
    while tw > MAXW * SS:                             # shrink long names
        size -= 1; f2 = ImageFont.truetype('/System/Library/Fonts/Supplemental/Luminari.ttf', size * SS)
        tw = dr.textlength(text, font=f2)
    f = ImageFont.truetype('/System/Library/Fonts/Supplemental/Luminari.ttf', size * SS)
    dr.text((CX * SS - tw / 2, 0), text, font=f, fill=255); SIZES[text] = size
    m = big.resize((256, 24), Image.LANCZOS)
    vals = []
    for y in range(24):
        for x in range(256):
            a = m.getpixel((x, y)) / 255
            vals.append(0 if a < 0.3 else min(15, max(6, round(5 + a * 10))))
    px = bytes(vals[i] | (vals[i+1] << 4) for i in range(0, len(vals), 2))
    cache[text] = px
    return px
out = bytearray()
for k, en in sorted(FILES.items()):
    out += struct.pack('<H', k) + render(RU[en])
open(f'{W}/assets/loctitles.bin', 'wb').write(out)
sheet = Image.new('L', (256, 24 * len(RU)))
for i, ru in enumerate(sorted(set(RU.values()))):
    px = render(ru)
    sheet.paste(Image.frombytes('L', (256, 24), bytes(((px[j//2] >> (4*(j & 1))) & 15) * 17 for j in range(256*24))), (0, 24*i))
sheet.save(f'{W}/assets/loctitles_preview.png')
print(len(FILES), 'titles'); print(sorted(SIZES.items(), key=lambda t: t[1])[:8])
