#!/usr/bin/env python3
# Nerd Fonts Version: 3.1.0
# Script Version: 1.0.1
# Generates original-source.otf from individual glyphs
#
# Idea & original code taken from
# https://github.com/lukas-w/font-logos/blob/v1.0.1/scripts/generate-font.py

import os
import re
import fontforge
import psMat

# Double-quotes required here, for version-bump.sh:
version = "3.1.0"

start_codepoint = 0xE4FA # with shift this is 0xE5FA
end_codepoint = 0xE5FF # Next set starts at 0xE700 - 0x0100 shift = 0xE600
codepoint_shift = 0x0100 # shift introduced by font-patcher

vector_datafile = 'icons.tsv'
vectorsdir = '../../src/svgs'
fontfile = 'original-source.otf'
fontdir = '../../src/glyphs'
glyphsetfile = 'i_seti.sh'
glyphsetsdir = 'lib'

def hasGaps(data, start_codepoint):
    """ Takes a list of integers and checks that it contains no gaps """
    for i in range(min(data) + 1, max(data)):
        if not i in data:
            print('Gap at offset {}'.format(i - start_codepoint))
            return True
    return False

def iconFileLineOk(parts):
    """ Check one line for course errors, decide if it shall be skipped """
    if parts[0].startswith('#'):
        # Comment lines start with '#'
        return False
    if len(parts) != 2 and len(parts) != 3:
        print('Unexpected data on the line "{}"'.format(line.strip()))
        return False
    if int(parts[0]) < 0:
        print('Offset must be positive on line "{}", ignoring'.format(line.strip()))
        return False
    return True

def addLineToData(data, parts, codepoint):
    """ Add one line to the data. Return (success, is_alias) """
    ali = False
    if codepoint in data:
        data[codepoint][0] += [ parts[1] ]
        if len(parts) > 2 and data[codepoint][1] != parts[2]:
            print('Conflicting filename for {}, ignoring {}'.format(codepoint, parts[2]))
            return False, False
        ali = True
    else:
        data[codepoint] = [[parts[1]], parts[2]]
    return True, ali

def readIconFile(filename, start_codepoint):
    """ Read the database with codepoints, names and files """
    # First line of the file is the header, it is ignored
    # All other lines are one line for one glyph
    # Elements in each line are tab separated (any amount consecutive of tabs)
    # First element is the offset, 2nd is name, 3rd is filename
    # For aliases the 3rd can be ommited on an additional line
    data = {}
    num = 0
    ali = 0
    with open(filename, 'r') as f:
        for line in f.readlines():
            parts = re.split('\t+', line.strip())
            if not iconFileLineOk(parts):
                continue
            offset = int(parts[0])
            codepoint = start_codepoint + offset
            if re.search('[^a-zA-Z0-9_]', parts[1]):
                print('Invalid characters in name: "{}" replaced by "_"'.format(parts[1]))
                parts[1] = re.sub('[^a-zA-Z0-9_]', '_', parts[1])
            added = addLineToData(data, parts, codepoint)
            if not added[0]:
                continue
            num += 1
            if added[1]:
                ali += 1
    print('Read glyph data successfully with {} entries ({} aliases)'.format(num, ali))
    return (data, num, ali)

def widthFromBB(bb):
    """ Calculate glyph width from BoundingBox data """
    return bb[2] - bb[0]

def heightFromBB(bb):
    """ Calculate glyph height from BoundingBox data """
    return bb[3] - bb[1]

def calcShift(left1, width1, left2, width2):
    """ Calculate shift needed to center '2' in '1' """
    return width1 / 2 + left1 - width2 / 2 - left2

def addIcon(codepoint, name, filename):
    """ Add one outline file and rescale/move """
    dBB = [53, 0, 1000 - 53, 900] # just some nice sizes
    filename = os.path.join(vectorsdir, filename)
    glyph = font.createChar(codepoint, name)
    glyph.importOutlines(filename)
    gBB = glyph.boundingBox()
    scale_x = widthFromBB(dBB) / widthFromBB(gBB)
    scale_y = heightFromBB(dBB) / heightFromBB(gBB)
    scale = scale_y if scale_y < scale_x else scale_x
    glyph.transform(psMat.scale(scale, scale))
    gBB = glyph.boundingBox() # re-get after scaling (rounding errors)
    glyph.transform(psMat.translate(
        calcShift(dBB[0], widthFromBB(dBB), gBB[0], widthFromBB(gBB)),
        calcShift(dBB[1], heightFromBB(dBB), gBB[1], heightFromBB(gBB))))
    glyph.width = int(dBB[2] + dBB[0])
    glyph.manualHints = True

def createGlyphInfo(icon_datasets, filepathname, into):
    """ Write the glyphinfo file """
    with open(filepathname, 'w', encoding = 'utf8') as f:
        f.write(u'#!/usr/bin/env bash\n')
        f.write(intro)
        f.write(u'# Script Version: (autogenerated)\n')
        f.write(u'test -n "$__i_seti_loaded" && return || __i_seti_loaded=1\n')
        for codepoint, data in icon_datasets.items():
            f.write(u"i='{}' {}=$i\n".format(chr(codepoint),data[0][0]))
            for alias in data[0][1:]:
                f.write(u"      {}=${}\n".format(alias, data[0][0]))
        f.write(u'unset i\n')


### Lets go

print('\n[Nerd Fonts]  Glyph collection font generator {}\n'.format(version))

font = fontforge.font()
font.fontname = 'NerdFontFileTypes-Regular'
font.fullname = 'Nerd Font File Types Regular'
font.familyname = 'Nerd Font File Types'
font.em = 1024
font.encoding = 'UnicodeFull'

# Add valid space glyph to avoid "unknown character" box on IE11
glyph = font.createChar(32)
glyph.width = 200

font.sfntRevision = None # Auto-set (refreshed) by fontforge
font.version = version
font.copyright = 'Nerd Fonts'
font.appendSFNTName('English (US)', 'Version', version)
font.appendSFNTName('English (US)', 'Vendor URL', 'https://github.com/ryanoasis/nerd-fonts')
font.appendSFNTName('English (US)', 'Copyright', 'Nerd Fonts')

icon_datasets, _, num_aliases = readIconFile(os.path.join(vectorsdir, vector_datafile), start_codepoint)
gaps = ' (with gaps)' if hasGaps(icon_datasets.keys(), start_codepoint) else ''

for codepoint, data in icon_datasets.items():
    if codepoint not in range(start_codepoint, end_codepoint + 1):
        print('FATAL: We are leaving the allocated codepoint range with "{}", bailing out'.format(data[0][0]))
        exit(1)
    addIcon(codepoint, data[0][0], data[1])
num_icons = len(icon_datasets)

print('Generating {} with {} glyphs'.format(fontfile, num_icons))
font.generate(os.path.join(fontdir, fontfile), flags=("no-FFTM-table",))

# We create the font, but ... patch it in on other codepoints :-}
icon_datasets = { code + codepoint_shift : data for (code, data) in icon_datasets.items() }

intro  = u'# Seti-UI + Custom ({} icons, {} aliases)\n'.format(num_icons, num_aliases)
intro += u'# Codepoints: {:X}-{:X}{}\n'.format(min(icon_datasets.keys()), max(icon_datasets.keys()), gaps)
intro += u'# Nerd Fonts Version: {}\n'.format(version)

print('Generating GlyphInfo {}'.format(glyphsetfile))
createGlyphInfo(icon_datasets, os.path.join(glyphsetsdir, glyphsetfile), intro)
print('Finished')
