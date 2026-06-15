# Note and Duration Generation Knowledge

## 1. Core Principles

### 1.1 Chord progression is the foundation
- Bass: prefer current chord root at each chord start; add fifth, octave, passing tones
- Chord track: current chord tones (root, third, fifth)
- Pad: current chord tones, longer durations
- Lead: chord tones on strong beats, in-key passing tones on weak beats
- Arpeggio: break current chord tones into sequential notes
- Drums: no chord pitches; rhythm follows chord/section changes
- Strings/Brass: chord tones, sustained tones, accents, counter-lines

### 1.2 Strong beats prefer chord tones
In 4/4: beat 1,3 = strong; beat 2,4 = secondary; offbeats = weak
- Strong beats: root, third, fifth
- Weak beats: in-key passing tones, neighbor tones, ornaments
- Endings: current chord tones, especially root or third

### 1.3 Register and duration by role

| Role | Register | Duration (beats) |
|------|----------|-------------------|
| Bass | C1-C3 | 0.25-4 (slow:2-4, pop:0.5-1, electronic:0.25-0.5) |
| Chords | C3-C5 | 0.5-4 (block:1-4, rhythmic:0.25-1, stabs:0.25-0.75) |
| Pad | C3-C5/C4-C6 | 2-8, sustained across bars |
| Lead | C4-C6 | 0.25-2, form motifs |
| Arpeggio | C3-C6 | 0.25-0.5 (fast), 0.5-1 (slow) |
| Strings long | C3-C5 | 2-8 |
| Strings short | C3-C5 | 0.25-0.75 |
| Brass accent | C3-C5 | 0.5-2 |
| Piano LH | C2-C4 | 0.5-4 |
| Piano RH | C3-C6 | 0.25-2 |
| Guitar strum | C3-C5 | 0.25-1 |

### 1.4 Section energy → density
- Intro: few notes, long durations, low density
- Main: complete patterns, stable density
- Climax: higher register, stronger velocity, denser rhythm
- Ending: reduce notes or strong cadence

## 2. Instrument-Specific Rules

### Bass
- Priority: root → fifth → octave → passing tone → chromatic (special styles only)
- Patterns: Root Only (intro/ambient), Root Pulse (pop/BGM), Root-Octave (electronic/8-bit), Root-Fifth (rock/fantasy), Syncopated (cyberpunk/boss)
- First note of each new chord MUST be current chord root

### Chords
- Use root, third, fifth of current chord
- Avoid register conflict with bass and lead
- Retain common tones between neighboring chords
- Style: pop=stable rhythmic, electronic=syncopated stabs, lo-fi=soft long chords, epic=strings+brass accents

### Lead
- Strong beats: chord tones; weak beats: scale tones
- Form motifs: short-short-long (0.5+0.5+1.0), syncopated (0.5+1.0+0.5), etc.
- First note of new chord: root, third, or fifth
- Avoid: continuous large leaps, same density throughout, random every bar
- Style: 8-bit=clear short motifs+leaps, cyberpunk=repeated motifs+syncopation, fantasy=singable+stepwise, east-asian=space+pentatonic

### Drums (no pitch, use GM drum map)
- Kick: low-frequency center, beats 1,3 or sync with bass
- Snare: backbeat, beats 2,4
- Closed hat: subdivision rhythm, groove density
- Open hat: weak beats, pre-transition
- Crash: section starts, climax starts, loop returns
- Tom: fills, transitions
- Durations: kick 0.05-0.15, snare 0.05-0.2, hat 0.05-0.15, crash 0.25-1, tom 0.1-0.25
- Style: electronic=kick on 1,3+syncopation, snare 2,4, 1/8-1/16 hats; lo-fi=sparse kick, laid-back snare, lower velocity; rock=kick sync with bass, strong snare, continuous hats; east-asian=taiko accents, sparse, more space

### Arpeggio
- Notes: root, third, fifth, octave, optional seventh
- Directions: ascending (root→3rd→5th→octave), descending, up-down, leaping
- Style: 8-bit=fast 1/8-1/16, electronic=repeating for tension, fantasy=harp not too fast

### Strings
- Long: chord tones, 2-8 beats, epic/fantasy/ambient
- Staccato: root/fifth, 0.25-0.75, battle/chase/tension
- Pizzicato: chord tones, 0.25-0.5, stealth/medieval/fantasy
- Tremolo: chord tones, 1-4 beats, suspense/horror

### Brass
- Notes: root, fifth, third, octave. Avoid excessive passing tones.
- Short accents: 0.5-1 beat; theme: 0.5-2; long support: 2-4
- Epic: reinforce chords with root/fifth; Battle: short stabs on chord changes

### Piano
- LH: root long notes, root+fifth, broken-chord bass, C2-C4, 0.5-4 beats
- RH: chords, melody, broken chords, ornaments, C3-C6, 0.25-2 beats
- Patterns: block chords (pop/warm), broken chords (lyrical/fantasy), offbeat (lo-fi)

### Ethnic/East-Asian
- Koto/guzheng-like: broken chords, high accents, pentatonic, 0.25-0.5 arp
- Shakuhachi/flute: lead melody, more space, avoid dense Western writing, 0.5-2 beats
- GM approximations: Shakuhachi(77), Koto(107), Dulcimer(15), Taiko(116)

## 3. Multi-Track Generation Flow

For each chord:
1. Drums: rhythmic center, no chord pitches
2. Bass: state root at chord start
3. Chords: play chord tones
4. Pad: sustain chord
5. Lead: chord tones on strong beats, in-key on weak beats
6. Arp: break chord tones

Default 4/4 one-chord-per-bar:
- Beat 1: bass root, kick, chord/pad starts, lead may land on chord tone
- Beat 2: snare, lead develops motif
- Beat 3: bass root/fifth/octave, kick, chord repeats/sustains
- Beat 4: snare, transition note or fill

## 4. Common Mistakes to Avoid

- All instruments playing full chords → divide roles: bass=roots, chords=harmony, pad=sustain, lead=melody
- Bass not following chord roots at chord changes
- Lead strong beats using non-chord tones
- Pad too short (should use 2-8 beat long tones)
- Drums ignoring section changes (add crash at starts, fill at loop end)
- All tracks same rhythmic density → vary: bass stable, chords medium, lead breathes, arp moves, pad sustains

## 5. Core Generation Logic

```
current chord → determine instrument role → choose register
→ choose note source (root/chord tone/in-key/passing)
→ choose duration (long/rhythmic/staccato/arp)
→ adjust density, velocity, register by section energy
```

Goal: bass, harmony, melody, rhythm unfold around same chord progression, producing structurally clear, stylistically coherent, loopable MIDI.