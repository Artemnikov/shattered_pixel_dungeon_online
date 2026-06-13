# Quickslot Bar — SPD Source Reference

Source: `shattered-pixel-dungeon/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/`
(`QuickSlot.java`, `ui/QuickSlotButton.java`, `ui/Toolbar.java`, `ui/Button.java`, `ui/RightClickMenu.java`, `SPDAction.java`)

## Data model (`QuickSlot.java`)
- Fixed array `slots[6]` (`QuickSlot.SIZE=6`), stored on `Dungeon.quickslot`.
- Each slot holds an `Item` reference that's *also* in the hero's inventory (not a copy).
- **Placeholder**: when a stackable item's quantity hits 0 (e.g. last potion thrown), `convertToPlaceholder()` replaces it with `item.virtual()` — a quantity-0 clone — so the slot stays visually occupied (dimmed icon) instead of going empty. `replacePlaceholder()` swaps a placeholder back for a real item when one is acquired again (matched via `isSimilar`).
- `isPlaceholder(slot)` = item exists but qty==0; `isNonePlaceholder` = item exists and qty>0 (this is what's actually usable).
- Bundling: placeholders are saved/restored separately (`storePlaceholders`/`restorePlaceholders`) using a parallel boolean "placements" array, since order is preserved but index isn't guaranteed.

## Assigning items to slots
Two paths, both end at `QuickSlotButton.set(...)`:

1. **From inventory** (`InventoryPane`/`WndBag`): **long-press** (0.5s, `Button.longClick`) on an item with a `defaultAction()` → `QuickSlotButton.set(item)` (no slot arg). This auto-picks: first slot that's empty OR already contains that same item; falls back to slot 0 if all full.
2. **From the toolbar itself**: clicking an empty/occupied quickslot button (`QuickSlotButton.onClick`) opens `WndBag.ItemSelector` ("Quickslot an item" prompt) → selecting an item calls `set(slotNum, item)` for that specific slot.
   - Right-click / middle-click / long-click on a quickslot button all just call `onClick()` too (same picker).

`set()` always calls `Dungeon.quickslot.setSlot()` (which first clears the item from any other slot — no duplicates) then `refresh()` (updates all 6 button visuals + the swap-tool icons).

## Using a quickslot item (`QuickSlotButton.slot.onClick`)
- Requires `hero.isAlive() && hero.ready`.
- If item `usesTargeting` and we're mid-targeting on this slot with a remembered target (`lastTarget`), it auto-aims (`autoAim`) instead of re-prompting — i.e. tapping the same wand quickslot again re-throws at the last target.
- Otherwise: `item.execute(hero)` (the item's default action — drink/zap/read/etc.), and if `item.usesTargeting`, enters targeting mode (`useTargeting()`).
- **Targeting mode**: shows a crosshair (`crossB`/`crossM` Icons.TARGET) over `lastTarget`'s sprite; `targetingSlot` tracks which slot is "armed". `QuickSlotButton.target(char)` is called elsewhere (on attack/cast) to set `lastTarget`. Cancelled via `cancel()` (clears crosshairs) when hero dies, target dies/leaves FOV, or becomes an ally.
- `autoAim`: tries direct targeting at the target's cell; if blocked, builds a 2-tile distance map around the target and finds any nearby cell where `item.targetingPos()` resolves back to the target (auto-angling throws around corners/obstacles).

## Toolbar layout (`Toolbar.java`)
- Buttons left→right (or mirrored if `flipToolbar`): Wait, Search/Examine, 4-6 quickslots, Inventory (+ optional Swap tool).
- **Responsive slot count**: `quickslotsToShow` starts at 4, +1 if `uiCamera.width>152`, +1 more if `>170` → so up to 6 on wide screens, as few as 4 on narrow/portrait.
- **Quickslot Swapper** (`SPDSettings.quickSwapper()`, default true, only when <6 fit): shows only 3 slots + a `SlotSwapTool` button. Clicking it toggles `swappedQuickslots` between slot range 0-2 and 3-5. The swap button itself renders a 2×2 mini-grid of the *other* 3 slots' item icons (dimmed if placeholder) as a preview, plus a "changes" icon.
- `QuickSlotButton.lastVisible` = 6 if swapper active (all 6 exist, 3 hidden off-screen), else = `quickslotsToShow`. Hidden buttons get moved off-camera (`setPos(x, uiCamera.height)`).
- `Toolbar.Mode`: SPLIT / GROUP / CENTER — controls whether quickslots cluster against the inventory button vs. center of screen vs. split with wait/search on the opposite side. Frame border graphics (rounded end caps) adjust per visible-slot position.
- Border/frame tiles differ for the first/last visible slot vs middle ones (rounded end caps: `frame(106,0,19,24)` end, `frame(86,0,20,24)` start, `frame(88,0,18,24)` middle).

## Quickslot Selector (radial menu, hidden button bound to `QUICKSLOT_SELECTOR`)
- If currently mid-targeting, pressing it just fires the auto-aimed shot at `lastTarget` (shortcut to repeat last quickslot action without touching the toolbar).
- Otherwise opens a `RadialMenu` with all 6 slot icons/names:
  - Empty/placeholder/lost-inventory-blocked slots show as "Assign Quickslot" with a generic icon.
  - **`alt`-select** (the menu's secondary action — right-click/L2 on controller) on any slot → opens item picker to (re)assign that slot.
  - **Normal select** on a populated slot → executes the item directly (`item.execute`) and enters targeting if needed.
- Tooltip text differs for keyboard/mouse vs controller (`ControllerHandler.controllerActive`): shows LEFT_CLICK=Select, RIGHT_CLICK=Assign, BACK=Cancel, using the actual bound key names.

## Input bindings (`SPDAction.java`)
- Desktop default keys: `1`-`6` → `QUICKSLOT_1..6` (direct-use that slot, same as clicking it).
- Controller: `BUTTON_X` → `QUICKSLOT_SELECTOR` (opens radial menu / repeats last target).
- `QuickSlotButton.keyAction()` maps slot index 0-5 to these actions — hovering a quickslot button shows the bound key in its tooltip (`hoverText` appends `_(key)_`).

## Click semantics (`Button.java`, shared by all slots)
- Single input model for mouse+touch: `onPointerDown` → start timer; if held ≥0.5s before release → `onLongClick()` (and triggers vibration via `SPDSettings.vibration()` if enabled — mobile haptic feedback); otherwise on release → `onClick`/`onRightClick`/`onMiddleClick` based on `PointerEvent.button` (mouse) — touch only ever produces LEFT.
- So **on mobile, right-click variants are effectively unreachable**; long-press is the only secondary action. This is why both "assign to quickslot" (long-press in inventory) and the toolbar's own picker (tap empty/used quickslot) exist — two redundant touch-friendly paths to the same `set()`.
- Hovering shows tooltip with item name + bound key (desktop only, since hover doesn't really exist on touch).

## Misc behaviors
- `enableSlot()`: a quickslot button is only interactive if its item has qty>0 (not a placeholder) AND (hero doesn't have `lostInventory` curse OR item is `keptThroughLostInventory()`).
- First-10-seconds-of-run waterskin heuristic: `SPDSettings.quickslotWaterskin` flag is set/cleared based on whether a `Waterskin` is in any quickslot during the opening moments — used elsewhere to nudge new players.
- `QuickSlotButton.refresh()` is the central "redraw everything" call — re-binds each button's item, re-enables, and refreshes the swap-tool's mini icons.

## Strings (for reference)
- `ui.quickslotbutton.select_item` = "Quickslot an item"
- `ui.toolbar.quickslot_prompt/select/assign/cancel` = "Select a Quickslot" / "Select Quickslot" / "Assign Quickslot" / "Cancel"
- `windows.wndkeybindings.quickslot_1..6`, `quickslot_selector` — keybinding menu labels.
