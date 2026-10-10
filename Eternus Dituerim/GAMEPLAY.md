# Gameplay Commands Reference

This file documents the commands currently exposed by the CLI in `main.py`. It is intentionally limited to the commands that are implemented and routed by the game itself.

## Command Categories

The CLI supports these category routers:

- `characters` — route character-management commands
- `npcs` — route NPC-management commands
- `items` — route item-registry commands
- `spells` — route spell-registry commands
- `attacks` — route attack-registry commands

Typical routed calls look like:

- `characters create`
- `characters list`
- `items newitem`
- `spells cast fireball`
- `attacks newattack`

## General System Commands

- `clear` — clear the terminal screen.
- `help` — display available commands and command help.
- `?` — shorthand for `help` in `cmd.Cmd`.
- `quit` — exit the CLI.
- `exit` — alias of `quit`.

## Character Commands

These are the direct commands for player characters, plus the corresponding `characters ...` routed forms.

- `create` — create a new character and save it to the character folder.
- `characters create` — routed version of `create`.
- `list` — list all saved character files.
- `characters list` — routed version of `list`.
- `load <name or filename>` — load a saved character.
- `characters load <name or filename>` — routed version.
- `unload` — unload the currently loaded character.
- `characters unload` — routed version.
- `give <item name>` — add a registered item to the loaded character's inventory.
- `characters give <item name>` — routed version.
- `remove <item name>` — remove an item from the loaded character's inventory.
- `characters remove <item name>` — routed version.
- `equip <item name>` — move an item from inventory to equipped items.
- `characters equip <item name>` — routed version.
- `unequip <item name>` — remove an equipped item back to inventory.
- `characters unequip <item name>` — routed version.
- `sheet` — open the loaded character's character sheet in a browser.
- `characters sheet` — routed version.

## NPC Commands

- `createnpc` — create and save a new NPC.
- `npcs createnpc` — routed version.
- `listnpcs` — list all saved NPC files.
- `npcs list` and `npcs listnpcs` — routed/listing forms.
- `loadnpc <name or filename>` — load a saved NPC.
- `npcs load <name or filename>` and `npcs loadnpc <name or filename>` — routed versions.
- `unloadnpc` — unload the currently loaded NPC.
- `npcs unloadnpc` — routed version.
- `npcgive <item name>` — give a registered item to the loaded NPC.
- `npcs npcgive <item name>` — routed version.
- `npcremove <item name>` — remove an item from the loaded NPC.
- `npcs npcremove <item name>` — routed version.
- `npc_equip <item name>` — equip an NPC inventory item.
- `npcs npc_equip <item name>` — routed version.
- `npc_unequip <item name>` — unequip an NPC item.
- `npcs npc_unequip <item name>` — routed version.
- `npcsheet` — open the loaded NPC's sheet in a browser.
- `npcs npcsheet` — routed version.

## Item Registry Commands

- `newitem` — create a new item entry in the item registry.
- `items newitem` — routed version.
- `items` — list all registered items and their stats.
- `items <command>` — category routing for item-registry actions.

Registered item entries can include:

- name
- description
- strain
- modifier (stat + value)

## Spell Registry Commands

- `newspell` — create a new spell entry in the spell registry.
- `spells newspell` — routed version.
- `spells` — list all registered spells.
- `cast <spell name>` — cast a registered spell using the active loaded character or NPC.
- `spells cast <spell name>` — routed version.

Spell entries can include:

- name
- required item
- whether that item is consumed when cast

## Attack Registry Commands

- `newattack` — create a new registered attack.
- `attacks newattack` — routed version.
- `attacks` — list all registered attacks.
- `useattack <attack name>` — use a registered attack after verifying requirements.
- `attacks useattack <attack name>` — routed version.

Attack entries can include:

- name
- requirement type (`item` or `spell`)
- required item or spell name

## Combat Commands

- `addcombatant character` — add the currently loaded character to the combat roster.
- `addcombatant npc` — add the currently loaded NPC to the combat roster.
- `roster` — display combatants in initiative order and show status.
- `removecombatant <name>` — remove a combatant from the roster by name.
- `clearroster` — clear the saved roster when combat is not active.
- `status` — print the current status of each roster member.
- `startcombat` — roll initiative and begin combat.
- `endcombat` — end combat without clearing the roster.
- `turn` — advance the turn and reduce negative soak values for combatants.

## Routing Notes

The CLI uses category routers, so these commands are valid in more than one form:

- `characters create`
- `characters list`
- `characters load <name>`
- `characters sheet`
- `npcs listnpcs`
- `npcs loadnpc <name>`
- `npcs npcgive <item>`
- `items newitem`
- `spells newspell`
- `attacks newattack`

If a command is invoked outside its proper category, the CLI will print a routing reminder indicating the correct usage.

## Examples

- `create`
- `load aria`
- `give sword`
- `equip sword`
- `createnpc`
- `loadnpc guard`
- `npcgive potion`
- `newitem`
- `newspell`
- `newattack`
- `cast fireball`
- `useattack slash`
- `startcombat`
- `roster`
- `turn`
- `quit`

## Important Clarification

This file documents only the commands that are actually implemented in `main.py`. It does not describe a generic fantasy action grammar. The command set here is the real CLI API for the project.
