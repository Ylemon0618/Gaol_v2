scale_sharp = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
scale_flat = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']

chord_names = {'': ['', 'maj', 'Maj', 'M'],  # maj
               '5': ['5'],  # 5
               '6': ['6'],  # 6
               '7': ['7'],  # 7
               '7sus4': ['7sus4'],  # 7sus4
               '9': ['9'],  # 9
               '11': ['11'],  # 11
               '13': ['13'],  # 13
               'add9': ['add9', 'add2', '2'],  # add9
               'aug': ['aug', '+'],  # aug
               'aug7': ['aug7', '+7'],  # aug7
               'dim': ['dim', 'o'],  # dim
               'dim7': ['dim7', 'o7'],  # dim7
               'm': ['min', 'Min', 'm'],  # min
               'm6': ['min6', 'Min6', 'm6'],  # min6
               'm7': ['min7', 'Min7', 'm7'],  # min7
               'm9': ['min9', 'Min9', 'm9'],  # min9
               'm11': ['min11', 'Min11', 'm11'],  # min11
               'm13': ['min13', 'Min13', 'm13'],  # min13
               'M7': ['maj7', 'Maj7', 'M7'],  # maj7
               'M9': ['maj9', 'Maj9', 'M9'],  # maj9
               'M11': ['maj11', 'Maj11', 'M11'],  # maj11
               'M13': ['maj13', 'Maj13', 'M13'],  # maj13
               'mMaj7': ['mMaj7', 'mM7'],  # mMaj7
               'sus2': ['sus2'],  # sus2
               'sus4': ['sus4'],  # sus4
               }

chord_pattern = {'': [[0, 4, 7], [1, 3, 5]],
                 '5': [[0, 4, 7], [1, 3, 5]],
                 '6': [[0, 4, 7, 9], [1, 3, 5, 6]],
                 '7': [[0, 4, 7, 10], [1, 3, 5, 7]],
                 '7sus4': [[0, 5, 7, 10], [1, 4, 5, 7]],
                 '9': [[0, 4, 7, 10, 14], [1, 3, 5, 7, 9]],
                 '11': [[0, 4, 7, 10, 14, 17], [1, 3, 5, 7, 9, 11]],
                 '13': [[0, 4, 7, 10, 14, 17, 21], [1, 3, 5, 7, 9, 11, 13]],
                 'add9': [[0, 2, 4, 7], [1, 2, 3, 5]],
                 'aug': [[0, 4, 8], [1, 3, 5]],
                 'aug7': [[0, 4, 8, 10], [1, 3, 5, 7]],
                 'dim': [[0, 3, 6], [1, 3, 5]],
                 'dim7': [[0, 3, 6, 9], [1, 3, 5, 7]],
                 'm': [[0, 3, 7], [1, 3, 5]],
                 'm6': [[0, 3, 7, 9], [1, 3, 5, 6]],
                 'm7': [[0, 3, 7, 10], [1, 3, 5, 7]],
                 'm9': [[0, 3, 7, 10, 14], [1, 3, 5, 7, 9]],
                 'm11': [[0, 3, 7, 10, 14, 17], [1, 3, 5, 7, 9, 11]],
                 'm13': [[0, 3, 7, 10, 14, 17, 21], [1, 3, 5, 7, 9, 11, 13]],
                 'M7': [[0, 4, 7, 11], [1, 3, 5, 7]],
                 'M9': [[0, 4, 7, 11, 14], [1, 3, 5, 7, 9]],
                 'M11': [[0, 4, 7, 11, 14, 17], [1, 3, 5, 7, 9, 11]],
                 'M13': [[0, 4, 7, 11, 14, 17, 21], [1, 3, 5, 7, 9, 11, 13]],
                 'mMaj7': [[0, 3, 7, 11], [1, 3, 5, 7]],
                 'sus2': [[0, 2, 7], [1, 2, 5]],
                 'sus4': [[0, 6, 7], [1, 4, 5]],
                 }


def get_chord(chord: str):
    chord = chord.replace(' ', '')

    chord_name = ""
    if 'b' in chord:
        scale = scale_flat
    else:
        scale = scale_sharp

    try:
        if len(chord) > 1 and chord[1] in ['b', '#']:
            root_str = chord[:2]
            root = scale.index(root_str)
        else:
            root_str = chord[0]
            root = scale.index(root_str)

        chord_name += root_str
    except ValueError:
        return

    if '(' in chord:
        name = chord.split('(')[0].removeprefix(root_str)
        other = chord.split('(')[1][:-1].replace(' ', '').split(',')
    else:
        name = chord.removeprefix(root_str)
        other = None

    pattern = None
    notes_num = None
    for key, possible_names in chord_names.items():
        if name in possible_names:
            name = key
            pattern, notes_num = chord_pattern[name]
            break

    chord_name += name

    if not pattern:
        return

    if other:
        chord_name += " ("

        for cur in other:
            try:
                if cur.startswith("omit"):
                    note = int(cur.removeprefix("omit"))
                    num = notes_num.index(note)

                    pattern.pop(num)
                elif cur.startswith("b"):
                    note = int(cur.removeprefix("b"))
                    num = notes_num.index(note)

                    pattern[num] = 11 if pattern[num] == 0 else pattern[num] - 1
                elif cur.startswith("#"):
                    note = int(cur.removeprefix("#"))
                    num = notes_num.index(note)

                    pattern[num] = 0 if pattern[num] == 11 else pattern[num] + 1
                else:
                    continue

                chord_name += cur + ","
            except ValueError:
                continue

        chord_name = chord_name[:-1] + ")"

    notes = []
    notes_str = []
    for i in pattern:
        now = root + i
        if now > 11:
            now -= 12

        notes.append(now)
        notes_str.append(scale[now])

    return chord_name, notes_str
