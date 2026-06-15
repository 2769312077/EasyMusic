# General MIDI Instrument Reference

## 1. Core Rule

- `program` uses 0-127 (mido format). GM numbering is 1-128.
- `program = GM_number - 1`
- Channel 9 only for drums. No program_change on drum channel.

## 2. GM Instrument Families (program ranges)

| Family | Range | Key Instruments |
|--------|-------|-----------------|
| Piano | 0-7 | 0=Grand Piano, 4=ElecPiano1(lo-fi), 5=ElecPiano2(dreamy) |
| Chromatic Perc | 8-15 | 8=Celesta, 11=Vibraphone(lo-fi lead), 14=TubularBells |
| Organ | 16-23 | 16=Drawbar(jazz), 18=Rock, 19=Church |
| Guitar | 24-31 | 24=Nylon, 25=Steel, 27=Clean(city pop), 28=Muted(funk), 30=Distortion(metal) |
| Bass | 32-39 | 33=Finger(all-purpose), 34=Pick(rock), 38/39=Synth(electronic/cyberpunk) |
| Strings | 40-47 | 40=Violin, 42=Cello, 44=Tremolo(horror), 45=Pizzicato, 46=Harp |
| Ensemble | 48-55 | 48=Strings1, 49=Strings2, 52=Choir, 55=OrchHit |
| Brass | 56-63 | 56=Trumpet, 57=Trombone, 60=FrenchHorn, 61=BrassSection, 62/63=SynthBrass |
| Reed | 64-71 | 64=SopranoSax, 65=AltoSax, 66=TenorSax, 68=Oboe, 71=Clarinet |
| Pipe | 72-79 | 73=Flute(fantasy lead), 75=PanFlute, 77=Shakuhachi(east-asian) |
| Synth Lead | 80-87 | 80=Square(8-bit), 81=Sawtooth(cyberpunk) |
| Synth Pad | 88-95 | 88=NewAge, 89=Warm(lo-fi), 90=Polysynth, 95=Sweep |
| Synth FX | 96-103 | 96=Rain, 98=Crystal, 99=Atmosphere, 103=Sci-fi |
| Ethnic | 104-111 | 104=Sitar, 106=Shamisen, 107=Koto(east-asian), 108=Kalimba |
| Percussive | 112-119 | 116=Taiko, 118=SynthDrum, 119=ReverseCymbal |
| Sound FX | 120-127 | 120-127 = SFX (not recommended for core tracks) |

## 3. Style-to-Instrument Recommendations

```
8-bit/Retro:       lead=80, bass=38, chords=80, pad=90
Cyberpunk:         lead=81, bass=38, chords=90, pad=95, fx=103
Fantasy/RPG:       lead=73, bass=42, chords=48, pad=88, accent=46
Horror/Suspense:   lead=77, bass=43, chords=44, pad=93, fx=101
Lo-fi/Chill:       lead=4, bass=33, chords=4, pad=89, melody=11
East-Asian:        lead=77, chords=107, accent=15, pad=88, drums=116
Rock/Metal:        lead=30, rhythm=29, bass=34, brass=61
Epic/Orchestral:   strings=48, brass=61, horn=60, choir=52, timpani=47, taiko=116
```

Note: GM does not contain Erhu, Pipa, Dizi, Guzheng. Use Shakuhachi(77), Koto(107), Dulcimer(15), Flute(73), Shamisen(106), Taiko(116) as approximations.

## 4. LLM Decision Rules

1. Use zero-based program numbers (0-127)
2. Channel 9 only for drums
3. No program_change on drum channel 9
4. Set program_change at start of non-drum tracks
5. Validate program: 0-127, channel: 0-15