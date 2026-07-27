# Raven Codex Desktop Pet

Raven is a black pixel-style Codex desktop pet package. It includes idle, blink, autonomous walking, hover eye-loop, task status, approval, and output states.

Current version: `1.1`

![Raven idle](assets/idle.gif)

## Download

Download this repository, then copy the `raven` folder into your Codex pets directory.

```sh
mkdir -p ~/.codex/pets
cp -R raven ~/.codex/pets/raven
```

After copying, restart Codex or reload the pet list.

The installed files should look like this:

```text
~/.codex/pets/raven/pet.json
~/.codex/pets/raven/spritesheet.webp
```

## Optional Completion Feedback Patch

The Raven spritesheet includes a task-complete `waving` row, but some ChatGPT/Codex desktop builds return the active conversation from `running` directly to `idle` without emitting a normal `review` notification. In that case the pet package alone cannot keep the completion animation visible.

For local desktop installs, `scripts/patch_chatgpt_avatar_completion_hold.py` can patch ChatGPT's `app.asar` so the renderer holds `waving` for about 3 seconds when the mascot state transitions from `running` or `review` back to `idle`.

The patch gives completion feedback priority over Raven's movement/drag transient state, so autonomous walking does not hide the task-complete animation. It also limits cursor/look-direction frames to `idle`, preventing look frames from visually masking `waving` feedback.

```sh
python3 scripts/patch_chatgpt_avatar_completion_hold.py \
  /Applications/ChatGPT.app/Contents/Resources/app.asar \
  /tmp/chatgpt-app-raven-completion-hold.asar

cp /Applications/ChatGPT.app/Contents/Resources/app.asar \
  /Applications/ChatGPT.app/Contents/Resources/app.asar.raven-completion-hold.bak

cp /tmp/chatgpt-app-raven-completion-hold.asar \
  /Applications/ChatGPT.app/Contents/Resources/app.asar
```

Restart ChatGPT/Codex after applying the patch. App updates may replace `app.asar`, so the patch may need to be reapplied.

## Preview

Idle:

![Idle](assets/idle.gif)

Walking:

![Walking](assets/walk-right.gif)

Task complete:

![Task complete](assets/task-complete.gif)

Task failed or disconnected:

![Task failed or disconnected](assets/task-failed-disconnected.gif)

Hover eye loop:

![Hover eye loop](assets/hover-eye-loop.gif)

Approval needed:

![Approval needed](assets/approval-needed.gif)

Thinking/running task:

![Thinking running task](assets/thinking-running.gif)

Full spritesheet contact sheet:

![Contact sheet](assets/contact-sheet.png)

## Package Contents

```text
raven/
  pet.json
  spritesheet.webp
```

`pet.json` declares the Codex pet metadata. `spritesheet.webp` is the Codex v2 pet atlas.

## Notes

Raven was made from a user-provided pixel PNG and packaged as a Codex v2 desktop pet.

Version `1.1` updates the package metadata to `Self-Improving Agent Harness.`, refreshes the current Raven spritesheet, and keeps the latest status mapping/preview assets aligned with the local package.

Status mappings:

- Task failed or network disconnected: fallen X face
- Task complete: smile face with green music-note frames; the optional renderer patch holds this feedback when `running` or `review` returns to `idle` and prevents look-frame masking
- Thinking/running task: > face with red pixel decoration
- Approval needed: ? face
- Review/output feedback: # face with yellow headphones
- Hover/interaction: smooth eye-loop animation
