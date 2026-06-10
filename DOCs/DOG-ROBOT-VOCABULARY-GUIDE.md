# Robot-Dog Voice Vocabulary — Use Guide

A practical guide to driving a **quadruped robot dog** with the DFRobot **DF2301Q** offline
voice module: which of the module's **built-in** command words actually map to a dog's hardware,
which ones you can repurpose, and how to spend your **17 custom (voice-trained) slots** on the
classic dog tricks the firmware doesn't ship.

**Assumed robot:** four legs (locomotion), a **moving head** (servo), **RGB LEDs**, and a **ping
(ultrasonic) distance** sensor. No camera, no line sensors, no dot-matrix display.

**How this fits the other docs:**
- `DOCs/USER-GUIDE.md` — how to *use* the driver object (begin, poll, register custom words).
- `DOCs/COMMAND-CATALOG.md` — the **full** built-in word list (generated, machine-readable).
- This guide — *which* words to wire up for a robot dog, and *why*.

> **Read this before you trust the IDs.** The phrase↔ID mappings below are ported from DFRobot's
> reference vocabulary (see DFRobot's upstream `DFRobot_DF2301Q` project on GitHub). Module firmware
> revisions have **reshuffled** the list before, so **validate every ID against the printed
> command-word card on your actual module** before wiring a behavior to it. The IDs are a starting
> point, not a guarantee.

---

## 1. The short answer

| Bucket | Count | What it covers |
|---|---:|---|
| **Built-ins, directly usable** | ~30 | drive, turn, head angles, RGB color, brightness, obstacle-avoid, wake/reset |
| **Built-ins, repurposable** | ~8 | bark, tail-wag, mood lighting, posture query, speed step |
| **Custom slots (voice-trained)** | **17** | IDs **5–21** — the actual dog tricks (sit, stay, come, …) |
| **Built-ins that don't apply** | the rest | car, fan, A/C, windows/doors, camera & vision, dot-matrix, learn/delete menus |

The module's built-in vocabulary is **fixed in firmware** — you can't add to it. You choose which
built-in **IDs** your dog reacts to, and you train up to **17 custom phrases** by voice for
everything the firmware lacks.

---

## 2. Built-in words that pertain to a robot dog (use these)

These ~30 words name an action the dog can perform as-is. React to the **ID**; call
`cmdName(id)` only if you want to print the phrase.

### Legs / locomotion (7)
| ID | Phrase | Suggested dog action |
|---:|--------|----------------------|
| 22 | Go Forward | walk forward |
| 23 | Retreat | back up |
| 25 | Turn Left 90° | turn left 90° |
| 26 | Turn Left 45° | turn left 45° |
| 27 | Turn Left 30° | turn left 30° |
| 29 | Turn Right 45° | turn right 45° |
| 30 | Turn Right 30° | turn right 30° |

### Moving head — servo angles (5)
| ID | Phrase | Suggested dog action |
|---:|--------|----------------------|
| 83 | Set Servo 10° | head to 10° |
| 84 | Set Servo 30° | head to 30° |
| 85 | Set Servo 45° | head to 45° |
| 86 | Set Servo 60° | head to 60° |
| 87 | Set Servo 90° | head to 90° (look up / center) |

### RGB color (9)
| ID | Phrase | Action |
|---:|--------|--------|
| 115 | Color Mode | enter RGB color mode |
| 116 | Set To Red | LEDs red |
| 117 | Set To Orange | LEDs orange |
| 118 | Set To Yellow | LEDs yellow |
| 119 | Set To Green | LEDs green |
| 120 | Set To Cyan | LEDs cyan |
| 121 | Set To Blue | LEDs blue |
| 122 | Set To Purple | LEDs purple |
| 123 | Set To White | LEDs white |

### LED brightness / on-off (6)
| ID | Phrase | Action |
|---:|--------|--------|
| 103 | Turn On The Light | LEDs on |
| 104 | Turn Off The Light | LEDs off |
| 105 | Brighten The Light | brighter |
| 106 | Dim The Light | dimmer |
| 107 | Brightness To Max | full brightness |
| 108 | Brightness To Min | lowest brightness |

### Ping sensor / behavior (1)
| ID | Phrase | Action |
|---:|--------|--------|
| 35 | Obstacle Avoidance Mode | enable ping-driven obstacle avoidance |

### Wake / system (2)
| ID | Phrase | Action |
|---:|--------|--------|
| 2 | Hello Robot | wake word / greet |
| 82 | Reset | reset behavior to idle |

---

## 3. Repurposable built-ins (the word doesn't say "dog," but the action fits)

Use these only if the trigger phrase is comfortable to say to a dog — otherwise spend a custom slot
on a better word.

| ID | Phrase | Repurpose as |
|---:|--------|--------------|
| 80 | Start Oscillating | tail wag / head sway on |
| 81 | Stop Oscillating | tail wag / head sway off |
| 88 | Turn On The Buzzer | **bark** |
| 89 | Turn Off The Buzzer | stop barking |
| 113 | Daylight Mode | bright LED mood preset |
| 114 | Moonlight Mode | dim LED mood preset |
| 66 | Read Current Posture | "are you sitting or standing?" (IMU report) |
| 31 | Shift Down A Gear | slow down / lower speed step |

---

## 4. Built-ins that do NOT apply

Skip these — they belong to other robots/appliances in the DF2301Q's shared vocabulary and have no
meaning for a ping-sensing, camera-less robot dog:

- **Car:** Park A Car (24), Shift gears as driving (31 — listed above only as a *speed* repurpose).
- **Vision / camera:** Face/Object/Tag/QR/Color Recognition, Object Tracking/Sorting, Take Photos,
  Turn Camera On/Off (36–43, 50, 73, 74). Your dog has *ping*, not a camera.
- **Line/light tracking:** 32, 33, 39 — need floor sensors.
- **Fan:** 75–79. **Air-conditioner / climate:** 124–136. **Home:** windows, curtains, doors (137–142).
- **Dot-matrix display:** numbers and faces (52–65). Your dog shows state on **RGB LEDs**, not a matrix.
- **Module menus:** model load/save/forget (44–49) and the learn/delete word UI (200–208). These
  drive the *module's own* training, not the dog.
- **Color-temperature & sensor reads** (109–112; 67–72): only meaningful with white-balance LEDs or a
  matching sensor suite — mostly N/A for this build.

---

## 5. Two gaps to know about

1. **Turn-Right-90° is missing.** The firmware has Left **90/45/30** but Right only **45/30** (ID 28
   is skipped upstream). Your turns are **asymmetric** out of the box. Fill the gap with a **custom**
   word (Section 6), or approximate with two Right-45° turns.
2. **No actual dog behaviors exist as built-ins.** Sit, stay, come, heel, shake, roll over, fetch,
   speak — **none** are in the firmware. That is exactly what the 17 custom slots are for.

---

## 6. Custom slots — your 17 voice-trained words (IDs 5–21)

You get **17 custom slots total** (`CUSTOM_COUNT = 17`, IDs `CUSTOM_FIRST = 5` … `CUSTOM_LAST = 21`).
This is a **hard ceiling** shared across *all* custom words — movements, tricks, and anything else
combined. The module trains them **by voice** and reports only the slot **ID**; your application is
the only place that knows what each slot *means* (see the User Guide's `registerCustomTable`).

### Suggested 17-word trick set (fills everything the built-ins miss)

> Sit · Stand · Lie Down · Come · Stay · Heel · Shake · Roll Over · Fetch · Speak/Bark · Dance ·
> Jump · Stretch · Spin · Play Dead · Wag Tail · **Turn Right 90°** (fixes the asymmetry gap)

That's exactly 17. Adjust to taste — but every slot you spend on a trick is one you can't spend
elsewhere, so prioritize the commands you'll actually say.

### Drop-in custom table (register once with `registerCustomTable`)

```spin2
DAT ' ---- robot-dog custom voice words (slots 5..21) ----
dogCustomWords
            byte     5, "sit", 0
            byte     6, "stand", 0
            byte     7, "lie down", 0
            byte     8, "come", 0
            byte     9, "stay", 0
            byte    10, "heel", 0
            byte    11, "shake", 0
            byte    12, "roll over", 0
            byte    13, "fetch", 0
            byte    14, "bark", 0
            byte    15, "dance", 0
            byte    16, "jump", 0
            byte    17, "stretch", 0
            byte    18, "spin", 0
            byte    19, "play dead", 0
            byte    20, "wag tail", 0
            byte    21, "turn right 90 degrees", 0
            byte     0                                  ' end of table
```

The phrase strings above are just the **labels your code prints** — the module recognizes whatever
**audio you train** for each slot, in whatever order you train it. Keep the slot→meaning mapping in
this table consistent with how you trained the module.

---

## 7. Spend summary

- **Drive/turn, head, lights, obstacle-avoid, wake/reset:** wire to the ~30 **built-in IDs** (Section 2).
- **Bark, tail-wag, mood lights:** repurpose ~8 **built-ins** if the phrase suits you (Section 3).
- **Sit / stay / come / tricks / Turn-Right-90:** train the **17 custom slots** (Section 6).
- **Safety net:** the demo's unmapped-ID logger prints `** UNMAPPED ... CMDID=n **` whenever the
  module reports an ID you haven't mapped yet — so a missed built-in or an untrained slot shows up
  immediately in the log instead of being silently dropped.

---

*All built-in IDs above are subject to the hardware-validation caveat in the header. Confirm against
your module's command-word card before relying on any specific number.*
