# Sonar Reps: pitch and AI plan

Working notes for the 3 minute video. Every number here is from `RESULTS.md`. Anything not yet built or measured is marked **planned**. Do not say a planned thing is done.

## One line

Put your phone on the floor and train. It counts your push-ups and refuses half reps, using sound you cannot hear. No camera, no wearable, nothing to look at.

## The problem

- Camera rep counters need you to film yourself: framing, lighting, and a video of you in your bedroom or a changing room.
- Motion counters (phone in hand, watch on wrist) count a shake as a rep.
- Both make you manage a screen while you are trying to train.

## What it does today (measured)

- The phone plays three tones at 18.5, 19.1 and 19.7 kHz and tracks the phase of the echo off the chest.
- Labelled sets on an iPhone 16 Pro Max: **38 of 40 full push-ups counted, 15 of 15 half reps refused.** Normal pace 10 of 10, fast 10 of 10, deep 5 of 5.
- Picking up, sliding and shaking the phone: nothing counted. The phone's motion sensor blocks counting while the phone moves.
- Live from phone to laptop screen over a hotspot. The laptop sends its verdict back to the phone as well (the phone's own count is not yet confirmed on the device).
- It worked in a loud room: audible noise up to half of full scale did not change the count.
- The whole pipeline runs 57 times faster than real time in plain Python on one laptop core.

What it does not do, also measured:

- **A hand moved up and down over the phone counts as a rep** (10 of 10).
- **Kneeling push-ups count** (9 of 10). The sonar sees one surface moving, not the knees.
- An empty floor gave one false rep in 30 s, in the first 5 s.
- Two full reps in a mixed set read too shallow and were refused.
- With the volume turned down it fails outright, so it now refuses to count and says why.

One person, one phone, one afternoon. The full table is in the README.

## Where the AI is

Say this plainly, because a judge will ask.

**The tracking is physics, not AI.** Echo phase to chest movement is signal processing, and it should stay that way, because it is exact and explainable.

**We trained a model to judge each movement, tested it properly, and it lost.** So it is not in the product. Every figure is for a take the model had not seen:

| | Right |
|---|---|
| One depth line, fitted on the other takes | 53 of 55 full and half reps |
| Trained model, full against half | 51 of 55 |
| Trained model, full, half or not a push-up | 21 of 72 movements |

**What is learned from data in the product is the rep line.** It was not picked by hand: half reps read 4.7 to 11.2 cm, full reps 13.6 cm and up, and any line from 11.5 to 13.5 cm sorts the same 53 of 55. The product runs 12 cm.

This replaces what these notes said before the labelled sets existed, that no fixed line could work. Within one session it does. The earlier spread (full reps at 9 to 17 cm in two morning sets) is still unexplained, and those sets would lose reps at 12 cm.

**What the data says a model would need.** Not more parameters, better measurements:

- A hand wave matches a push-up on all 7 features we gave the model (depth, timing, speed, echo strength, phase steadiness). Telling a chest from a hand needs the distance to the moving surface and its size. Steady tones give movement only. Short chirps would give distance.
- The two full reps we refused read 8.6 and 7.7 cm on the way down but 17 and 14.5 cm on the way back up. Using both strokes is the next feature to try.
- Kneeling cannot be seen from the chest alone at all.

How to say it: "Sound gives us the movement. We trained a model to judge it and tested it on sets it had never seen. One line fitted to the same data beat it, 53 to 51 out of 55, so we shipped the line. Here is the table, and here is what fooled both."

### After today (planned, roadmap only)

- **On the phone.** The tracker moves into the app, so the phone works alone. Today the phone is the speaker and microphone and a laptop on the same hotspot does the processing. Nothing goes to the internet.
- **Distance, not just movement.** Chirps in the same band, to tell a chest at 30 cm from a hand at 10 cm. This is what a learned judge needs before it can beat the line.
- **More data.** More people, floors and phones. Every labelled take is already both a training example and a regression test.
- **More movements.** Squats, sit-ups, breathing rate: same tones, same tracker.
- **A coach line.** After the set, one sentence from the per-rep numbers, for example a fade over the last three reps.

## Why this is "Invisible AI"

Three ways, each one true of the build:

1. **Invisible sensing.** The tones sit above what most adults hear. There is no camera and nothing to wear.
2. **Invisible interface.** No prompt, no chat, no buttons during a set. You press start once and put the phone down. All you see is a count and the words NO REP.
3. **Invisible footprint.** No image of you ever exists. Stored recordings keep only the band above 17.5 kHz, so they hold no speech.

## How it is used

1. Phone face-up on the floor under your chest, volume at about three quarters.
2. Press Start. Hands off the phone.
3. Do push-ups. Each full rep counts. A half rep flashes NO REP. Moving the phone shows "PHONE MOVED, NOT COUNTING".
4. Press Stop. The set is saved on the phone.

## How it scales

- **Hardware that already exists.** It needs a speaker and a microphone that work near 19 kHz. Tested on two devices so far: a MacBook Air (tones 61 to 70 dB above the noise floor) and an iPhone 16 Pro Max. A two second self-test (`probe_live.py --check`) says go or no-go for a device and can fall back to fewer tones.
- **No cost per user.** No server is needed: 57 times real time in unoptimised Python leaves plenty of room on a phone.
- **Data that compounds.** Every labelled recording is stored once and used twice, to fit the rep line and as a regression test (`takes.py`). Today that is 13 takes.
- **One front end, many movements.** A new exercise is a new labelled set and a new line or small model, not a new sensor.

What limits scale, said honestly: speakers differ between phones; two phones playing the same tones in one room would interfere (planned fix: each picks its own tones); some young people and most pets can hear these tones, so volume stays moderate; full volume makes the iPhone speaker sag and breaks the count.

## Use cases

- **Training alone at home.** A count you can trust without filming yourself.
- **Challenges between friends.** Reps that cannot be faked by shaking a phone or doing half reps. A hand waved over the phone still can fake one today.
- **Fitness tests.** School PE, club and service entry tests, where depth matters and counting is argued over.
- **Where cameras are not welcome.** Gyms, changing rooms, shared flats, schools.
- **Physio and remote coaching.** Did the sets happen, and through what range, with no video of someone's home. Not a medical device.
- **Low vision.** Nothing on screen is needed during a set (spoken count is planned, not built).

## The video, 3 minutes

| Time | Shot | Line |
|---|---|---|
| 0:00 | Phone on the floor, push-ups, count rising | "There is no camera on. This phone is counting with sound you cannot hear." |
| 0:20 | The problem, three quick cuts | Film yourself, or get fooled by a shake. |
| 0:45 | Live: 5 full reps | Count goes 1 to 5. |
| 1:10 | Live: one half rep | NO REP flash. |
| 1:20 | Live: pick the phone up and shake it | "Phone moved, not counting." |
| 1:35 | The trace on the laptop, the pipeline in one picture | Sound gives the movement, a line fitted on labelled sets gives the verdict. |
| 2:00 | The evaluation table | 38 of 40 full, 15 of 15 half refused, shaking blocked. Then the model we trained and why we did not ship it. |
| 2:20 | Scale and use cases | Hardware everyone has, no cloud, no camera. |
| 2:40 | Limits and next | A hand and kneeling get through. Chirps for distance are next. |

## Questions a judge will ask

- **"Where is the AI?"** We trained a classifier on 72 labelled movements and tested it on takes it had not seen. It lost to one fitted depth line, so the line ships. The learned part of the product is that line. We would rather show a model that lost in a fair test than claim one that works.
- **"Is this just signal processing?"** The tracking is, on purpose. The verdict is a threshold fitted on labelled data and checked on held-out takes.
- **"Can I cheat it?"** Shaking the phone and half reps: no. Waving a hand over it: yes, today. Kneeling: yes.
- **"Is the technique new?"** No. Tracking movement from the phase of phone tones is published work (LLAP), and Doppler exercise recognition on a stock phone is too (Fu et al. 2018, linked in the README). What we add is counting and judging push-up reps on an iPhone, with an evaluation that includes the failures.
- **"How accurate is the depth?"** Good enough to sort full from half reps, not good enough to quote. A deep rep of roughly 30 cm read 17 to 24 cm.
- **"Does it work on any phone?"** Tested on one iPhone and one MacBook. The self-test is how a new device would be checked.
- **"Is the processing on the phone?"** Not today. The laptop does it over a local hotspot. It is light enough to move onto the phone, and that is the next step.

## Prior work, disclosed

Ideas, not code, from Addy's earlier PressPass project (a camera push-up counter): the rep state machine design and the replay evaluation approach.
