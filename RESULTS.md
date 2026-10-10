# Results log

Every hardware test, in the order it was run. Times are London time on Sat 10 Oct 2026. Newest last.

## About 10:32. Hardware check on the MacBook Air: GO

`python probe_live.py --check`, MacBook Air speakers and microphone at 48 kHz, output volume 50%, tone level 0.3.

| Tone | Above noise | Needed |
|---|---|---|
| 18.5 kHz | 61.2 dB | 20 dB |
| 19.1 kHz | 65.1 dB | 20 dB |
| 19.7 kHz | 69.5 dB | 20 dB |

No clipping (mic peak 0.194). All three tones are usable on the laptop.

## 10:39. Book over the laptop, 10 passes: 10 of 10 detected after one fix

`python probe_live.py --record recordings/book.wav --seconds 40`, same volume. A book was held about 30 cm above the keyboard, lowered to about 10 cm and raised again, 10 times.

| Counter | Passes found | Counted at the 15 cm line | Flagged too shallow |
|---|---|---|---|
| As first written (`return_frac` 0.35) | 7 | 6 | 1 |
| After the fix (`return_frac` 0.6) | 10 | 8 | 2 (13.1 and 14.8 cm) |
| After the fix, 10 cm line | 10 | 10 | 0 |

What happened:

- The tracker saw all 10 passes from the start. The plot shows 10 clean peaks.
- The counter merged passes whenever the book did not come most of the way back up, so four passes became one "rep" of 37.6 cm. A rep had to return 65% of its depth before it closed.
- Fix: a rep now closes after returning 40% of its depth. Each down and up is then judged on its own depth, so a partial return shows up as a shallow rep, not a merged one.
- Two passes read just under the 15 cm push-up line. That is about how far the book really moved, so the stored take uses a 10 cm line.

Signal quality over the 40 s take: carriers 70.4, 67.5 and 78.4 dB above the noise floor, no clipping. While the book moves, each tone's velocity matches the combined trace with a correlation of 0.89 to 0.96.

Known limits from this take:

- A single tone on its own drifts by tens of centimetres over 40 s. The median over three tones is what keeps the trace steady, so all three tones are needed.
- Depth is good to a few centimetres, not millimetres, at this volume. The band-limited copy of the same take reads up to 4 cm different on one pass.
- There was no ruler, so depth accuracy is unchecked. Pass 9 reads 34.6 cm, more than the intended 20 cm.

Stored as `takes/book_10.flac` (sonar band only, no room speech) with the plot in `takes/book_10.png`. `python simulate.py` replays it as a regression test.

## 10:59. First push-ups over the iPhone: 13 of 13 found, after reworking the tracker

iPhone 16 Pro Max face-up on the floor under the chest, volume about 75%, tone level 0.3 (0.1 per tone). The app saved the take and it was pulled off the phone over the cable.

| Tracker | Cycles found | Counted | Flagged too shallow |
|---|---|---|---|
| As tuned on the laptop, 15 cm line | 14 fragments | 1 | 13 |
| Reworked, 8 cm line | 13 | 13 | 0 |

The trace shows 13 clean, evenly spaced cycles, about 2.3 s apart. The true count still has to be confirmed by Addy.

Why the laptop tracker failed on the phone:

- On the phone the speaker and microphone share one body, so the direct sound is about 200 times stronger than the chest echo (carrier amplitude 0.005, Doppler lines 45 to 50 dB below it).
- The neighbouring tones, 600 Hz away, leaked through the low-pass at a level above the echo. The two outer tones read a steady 277 and 254 cm/s of motion that was not there, and the trace ran off by 460 cm in 35 s.
- The circle fit could not find an echo circle that small, so its estimate of the static sound stayed wrong.

What changed:

- Each tone is averaged over one beat of the tone spacing (80 samples), which puts exact nulls on the other tones. Fake motion fell to under 1 cm/s.
- The static part is removed with a 2 Hz high-pass.
- The phase step comes from the lag-1 products of all three tones together (pulse-pair, as in Doppler radar), not from a median of three separate phase tracks.

Known limits from this take:

- Depth reads low on the phone: 9.8 to 16.3 cm for full push-ups, roughly half the real travel. The rep line for the phone is therefore 8 cm for now and needs half reps to calibrate.
- The way up reads shorter than the way down (about 13 cm down, 7 cm up), so the raw trace climbs about 6 cm per rep. The counter copes because it judges each rep on the way down and takes a new top at every rest.

Stored as `takes/phone_pushups_1.flac`.

The book take from 10:39 now reads 11, with depths of 28.6 to 37.0 cm. The extra one is a real movement at 1 to 2 s, before the 10 passes, most likely the book being brought into place.

## 11:10. Second push-ups, louder tones at full volume: unusable

Tone level 0.9 (0.3 per tone) and the phone at full volume, to lift the echo.

| Tone | Level at the start | Lowest | At the end |
|---|---|---|---|
| 18.5 kHz | 0.067 | 0.037 | 0.037 |
| 19.1 kHz | 0.072 | 0.025 | 0.025 |
| 19.7 kHz | 0.058 | 0.028 | 0.057 |

The carriers came in 9 times stronger, but the speaker output sagged by up to two thirds within 27 s, most likely its heat protection. That drift is far larger than the echo: 0 reps counted, with the 10 push-ups just visible as bumps on a ramp. The tone level is back at 0.3. Do not run the phone at full volume.

## 11:22. Third push-ups over the iPhone, 10 confirmed reps: 10 of 10

Tone level back at 0.3, phone plugged in and face-up on the floor, carriers steady at 0.003 for the whole take. Addy counted 10 reps.

| True reps | Counted | Flagged too shallow | Depths |
|---|---|---|---|
| 10 | 10 | 1 | 20.6 to 24.9 cm |

The one NO REP is a 6 cm movement at 1.4 s, Addy getting into position, so rejecting it is correct. The count is the same at the 8 cm line and at the 15 cm line.

These reps were slower (about 4 s apart) and read about twice as deep as the 13 quick ones at 10:59. Whether those were really shallower or the reading depends on speed or placement is not known yet.

Stored as `takes/phone_pushups_3.flac`.

## 11:25. Fourth set, streamed live to the Mac: stream works, 10 cycles found

Same setup, phone a little quieter (carriers at 0.002). The Mac joined the iPhone hotspot and the app streamed to it while it also saved its own copy.

| Copy | Length | Cycles found | Counted at 8 cm | Counted at 15 cm | Depths |
|---|---|---|---|---|---|
| Saved on the phone | 33.1 s | 10 | 10 | 7 | 9.3 to 17.5 cm |
| Received on the Mac over UDP | 33.5 s | 10 | 10 | 7 | 9.3 to 17.5 cm |

The Mac's copy gives the same 10 reps with the same depths to 0.1 cm, and it holds no filled-in gaps, so no packets were lost. This is the first time the live stream is seen working end to end.

The true count is not yet confirmed by Addy.

What this take shows:

- Depths fade at the end: 17.3, 15.8, 13.2, then 9.3 cm. The last rep clears the 8 cm line by only 1.3 cm.
- Full push-ups have now read 9.8 to 16.3 cm (10:59), 20.6 to 24.9 cm (11:22) and 9.3 to 17.5 cm (this set). No single depth line can separate a full rep in one set from a half rep in another. Half reps have still not been recorded.
- The room was loud (audible peaks up to 0.46 of full scale, one click at 2.4 s over full scale) and the count was not affected.
- The trace sinks about 3 cm per rep here. At 10:59 it climbed. The counter copes either way.

Stored as `takes/phone_live_4.flac`. The band-limited copy reads rep 9 as 15.7 cm against 13.2 cm in the raw file.

## 11:34. A 5 second clip: not a set

Two quick movements, 0.5 s and 0.9 s long, read as reps of 15.1 and 19.0 cm. Too short to be a push-up set, and what was done is not known, so it is not stored as a take. If this was a hand waved over the phone, it shows that a hand can pass as a rep today.

## 11:49. Live session of 146.6 s: not labelled

`recordings/live2.wav`, streamed to the Mac with the 8 cm line: 22 counted, 7 refused, 9 packets lost (48 ms of sound), 361 blocks ignored while the phone was moved. What was done in it was not written down, so it is not stored as a take. Tone level at the microphone was normal (0.0017 to 0.0021).

## 13:04. 10 normal push-ups with the phone volume turned down: 0 of 10 counted

`recordings/sonar-2026-10-10T12-04-30Z.wav`, 31.2 s, saved on the phone. The Mac had dropped off the hotspot onto the university Wi-Fi, so nothing was streamed and the phone showed no count.

**Failed, and the cause is measured.** The tones reach the microphone 10 times weaker than in every good set:

| Take | 18.5 kHz | 19.1 kHz | 19.7 kHz | Result |
|---|---|---|---|---|
| 11:22 (10 of 10) | 0.0028 | 0.0031 | 0.0027 | clean cycles, 20.6 to 24.9 cm |
| 11:25 (10 of 10) | 0.0020 | 0.0023 | 0.0019 | clean cycles, 9.3 to 17.5 cm |
| 11:49 session | 0.0020 | 0.0021 | 0.0017 | counted |
| 13:04 (this one) | 0.0002 | 0.0002 | 0.0002 | no cycles, 4 movements of 3.7 to 5.9 cm, 0 counted |

Levels are the tone amplitude in the recording, full scale 1.0. The app's audio code is the same as at 11:25, so the phone volume was almost certainly well below the usual 75 percent. With the echo 20 dB down the trace is noise: no push-up can be picked out of it by eye either.

Not stored as a take: the 10 reps are not recoverable from it.

Fix made straight away: the tracker now reports the weakest tone level (`SonarTracker.level`), and `phone_receiver.py` refuses to count and shows "TONE TOO QUIET, TURN THE PHONE VOLUME UP" on the demo screen while it is under 0.0008. Checked by replay: this take is blocked from its first second (level 0.0001 to 0.0002), and the 11:22 take still counts 10 of 10 with no warning. The warning needs the stream to reach the Mac; a set recorded on the phone alone is not checked.

## 13:19 to 13:27. The nine labelled sets

Recorded by Addy one after another, volume back at about 75 percent, phone streaming to the Mac. Tone level at the microphone 0.0021 to 0.0022 in all nine, so the sets can be compared. Labels are his, given in order. Stored in `takes/` as `set_*.flac`.

Read live with the 8 cm line that was running at the time:

| Set | Done | Counted | Refused | Depths read |
|---|---|---|---|---|
| Full, normal pace | 10 | 10 | 0 | 17.5 to 22.1 cm |
| Full, fast | 10 | 10 | 0 | 13.6 to 19.3 cm, about 0.9 s a rep |
| Half reps | 10 | 4 | 6 | 4.7 to 11.1 cm |
| Kneeling | 10 | 10 | 0 | 8.7 to 19.5 cm |
| Empty floor, people walking | 0 | 1 | 0 | one movement of 19.5 cm at 2 to 5 s, most likely Addy getting up after pressing Start; nothing in the 27 s after |
| Hand waved 10 times | 0 | 10 | 0 | 12.8 to 21.1 cm |
| Phone picked up, slid, shaken | 0 | 0 | 0 | the motion sensor blocked everything. From the sound alone, with no motion flag: 1 counted, 4 refused |
| 5 full and 5 half, alternating | 5 | 7 | 3 | full 8.6 to 18.1 cm, half 4.7 to 11.0 cm |
| Deep, chest touching down | 5 | 3 | 0 | 17.3 to 24.5 cm |

What went wrong at 8 cm, and what was changed:

- **Half reps counted** (4 of 10, and 5 of 5 in the mixed set). Half reps read 4.7 to 11.2 cm and full reps 13.6 cm and up, apart from two. The line is now 12 cm. Any line from 11.5 to 13.5 cm sorts the same 53 of 55 full and half reps.
- **Two deep reps never counted.** Each deep rep pauses at the bottom, and after the pause the way up reads only 8 to 10 cm against 21 to 24 cm on the way down, so the rep never came back far enough to close. `return_frac` is now 0.7 (a rep closes once it has come back 30 percent of its depth). All 5 count, and no other stored take changes.
- **Two full reps in the mixed set read 8.6 and 7.7 cm** on the way down and 17 and 14.5 cm on the way back up. Still refused. The way up is not used for depth yet.

With the 12 cm line and the new closing rule (replay of the stored takes): full 10 of 10, fast 10 of 10, deep 5 of 5, mixed 3 of 5 full with all 5 half refused, half 0 of 10 counted, phone handled 0 counted, empty floor 1 counted, hand 10 of 10 counted, kneeling 9 of 10 counted. The two older unconfirmed sets lose reps at 12 cm: 9 of 13 and 9 of 10.

**Not blocked: a hand, and kneeling.** A hand moved up and down over the phone reads 12.7 to 21.1 cm at a push-up's pace with a steady echo of 10.5 to 14.8 dB, inside the range of real push-ups on every feature. Kneeling push-ups move the chest the same distance, and the sonar does not see knees.

**Depth check.** Addy puts his chest about one A4 sheet (29.7 cm) above the floor with arms locked. The deep reps read 17.3, 21.2, 22.1, 22.2 and 24.2 cm. In the right range, probably short. His figure is an estimate, so this is not a calibration.

## 13:36. The rep judge, trained and tested: it loses to the line

`python judge.py`, 72 movements from 9 labelled takes (40 full, 15 half, 17 not a push-up). Every figure is for a take the model was not trained on.

| | Right |
|---|---|
| One depth line, fitted on the other takes (11.5 cm every time) | 53 of 55 full and half reps |
| Model, full against half | 51 of 55 |
| Model, full, half or not a push-up | 21 of 72 |

The three-way model calls 30 of 40 full reps "not a push-up" and 11 of 17 other movements "full": hand waves and push-ups cannot be told apart from these 7 features, so training on hand waves damages the full class. The two-way model makes the same two mistakes as the line in the mixed set and two more in the fast set.

Decision, as written in `PITCH.md` before the test: the model does not beat the fixed line, so the fixed line ships. No `judge.json` is committed.
