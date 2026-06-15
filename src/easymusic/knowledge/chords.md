# Chord Progression Selection Knowledge

## 1. Degree-to-Chord Mapping

In C major:

| Degree | Chord | Quality |
|--------|-------|---------|
| I | C | major — tonic, stable center |
| ii | Dm | minor — transition, gentle motion |
| iii | Em | minor — soft color |
| IV | F | major — subdominant, expansion |
| V | G | major — dominant, returns to I |
| vi | Am | minor — lyrical, pop, slightly sad |
| vii° | Bdim | diminished — unstable, avoid in simple BGM |

In A minor:

| Degree | Chord | Quality |
|--------|-------|---------|
| i | Am | minor — dark tonic |
| ii° | Bdim | diminished — avoid |
| III | C | major — bright, epic, cinematic |
| iv | Dm | minor — gloomy subdominant |
| v | Em | minor — weak dominant |
| V | E | major — strong dominant (harmonic minor) |
| VI | F | major — broad, emotional |
| VII | G | major — drive, loop feeling |

## 2. Core Selection Rules

1. Decide major or minor first based on mood:
   - Bright/relaxed/healing/playful → major
   - Dark/tense/battle/suspense/epic/dungeon → minor
   - Sad/lyrical → minor or vi-start in major
   - Traditional/East-Asian → minor or pentatonic major, simple harmony
   - Lo-fi/Chill → either, seventh-chord color, smooth motion

2. Use 4-bar loops by default. One chord per bar in 4/4.

3. Chord movement direction:
   - Stable → push → tension → return
   - I/i: tonic, stable, return point
   - IV/iv/VI: expansion, color
   - V/VII: drive, tension, guide back to tonic
   - vi/III: emotional, pop, cinematic

## 3. Progression Templates

### Major
```
bright_pop:      I - V - vi - IV
warm_everyday:   I - vi - IV - V
simple_clear:    I - IV - V - I
open_folk:       I - V - IV - I
emotional_pop:   vi - IV - I - V
lofi_soft:       I - vi - ii - V
lofi_smooth:     ii - V - I - I
```

### Minor
```
dark_loop:       i - VI - VII - i
epic_adventure:  i - VI - III - VII
dark_descending: i - VII - VI - VII
boss_battle:     i - VI - VII - V
classical_dark:  i - iv - V - i
tragic_dramatic: i - V - VI - iv
horror_drone:    i (single chord, long hold)
horror_phrygian: i - bII
eastern_dark:    i - VII - VI - VII
eastern_fantasy: i - III - VII - i
```

## 4. Quick Selection by Mood

```
Bright/happy/positive:      I - V - vi - IV  |  I - IV - V - I
Warm/healing/everyday:      I - vi - IV - V  |  vi - IV - I - V
Sad/memory/lyrical:         vi - IV - I - V  |  i - VI - III - VII
Dark/dungeon/mysterious:    i - VI - VII - i  |  i - VII - VI - VII
Tense/battle/boss:          i - VI - VII - V  |  i - V - VI - iv
Epic/adventure/grand:       i - VI - III - VII  |  i - VI - VII - V
Horror/suspense/unease:     i  |  i - bII  |  i - VII - VI - VII
Cyberpunk/electronic:       i - VI - VII - V  |  i - VII - VI - VII
8-bit/retro major:          I - V - vi - IV  |  I - IV - V - I
8-bit/retro minor:          i - VI - VII - i  |  i - VII - VI - VII
Fantasy/RPG major:          I - V - vi - IV  |  I - IV - V - I
Fantasy/RPG minor:          i - VI - III - VII  |  i - iv - VII - III
Lo-fi/Chill:                I - vi - ii - V  |  ii - V - I - I
Rock/Metal:                 i - VII - VI - VII  |  i - VI - VII - V
Traditional/East-Asian:     i - VII - VI - VII  |  i - III - VII - i
```

## 5. Section-Specific Rules

- Intro: use only I/i or first 2 chords of progression; slower harmonic rhythm
- Main A: full 4-bar loop; one chord per bar; bass follows root
- Main B/Climax: same progression, increased arrangement density; V or VII return
- Ending/Loop: final chord must naturally return to opening chord
  - Major: V→I preferred, IV→I works, vi→I is weaker
  - Minor: V→i preferred, VII→i works, VI→i is weaker

## 6. Compatibility Rules (STRICT)

- Output root-position major/minor triads ONLY
- Allowed: C, Dm, Bb, F#m
- Forbidden: slash chords (Eb/G), extensions (maj7, m7, sus4, add9, dim7), diminished symbols
- If template uses vii° or ii°, replace with nearby triad
- Root notes must be from: C, C#, Db, D, D#, Eb, E, F, F#, Gb, G, G#, Ab, A, A#, Bb, B