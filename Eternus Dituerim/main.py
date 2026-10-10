import cmd
import json
import re
from pathlib import Path
import html
import webbrowser
import shutil
import subprocess
from string import Template
import random
import os

BASE_DIR = Path(__file__).resolve().parent

JSON_DIR = BASE_DIR / "JSON"
CHARACTER_DIR = JSON_DIR / "characters"
NPC_DIR = JSON_DIR / "npcs"
ITEM_REGISTRY_PATH = JSON_DIR / "items.json"
SPELL_REGISTRY_PATH = JSON_DIR / "spells.json"
ATTACK_REGISTRY_PATH = JSON_DIR / "attacks.json"
COMBAT_ROSTER_PATH = JSON_DIR / "combat_roster.json"

HTML_DIR = BASE_DIR / "HTML"
TEMPLATE_PATH = HTML_DIR / "character_sheet_template.html"
CHARACTER_HTML_DIR = HTML_DIR / "characters"
NPC_HTML_DIR = HTML_DIR / "npcs"

STAT_NAMES = (
    "soak",
    "wound",
    "strain",
    "agility",
    "cunning",
    "dexterity",
    "presence",
)

CLASS_NAMES = (
    "Warrior",
    "Mage",
    "Rogue",
    "Cleric",
    "Ranger",
    "Bard",
    "Paladin",
    "Druid",
    "Monk",
    "Sorcerer",
    "Warlock",
    "Artificer"
    "Blood Hunter",
)

class Character:
    def __init__(self, name, description, stats, equipped_items, inventory, currency, role=""):
        self.name = name
        self.description = description
        self.role = str(role)
        self.stats = stats
        self.equipped_items = equipped_items
        self.inventory = inventory
        self.currency = currency

    def to_dict(self):
        return {
            "name": self.name,
            "description": self.description,
            "role": self.role,
            "stats": self.stats,
            "equipped_items": self.equipped_items,
            "inventory": self.inventory,
            "currency": self.currency,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            name=data["name"],
            description=data["description"],
            role=data.get("role", ""),
            stats=data["stats"],
            equipped_items=data["equipped_items"],
            inventory=data["inventory"],
            currency=data["currency"],
        )


def safe_filename(name):
    """Turn a character name into a safe filename."""
    filename = re.sub(r"[^A-Za-z0-9_-]+", "_", name).strip("_")
    return filename or "character"


def save_character(character):
    """Save a character to a new JSON file without overwriting another."""
    CHARACTER_DIR.mkdir(parents=True, exist_ok=True)

    base_name = safe_filename(character.name)
    path = CHARACTER_DIR / f"{base_name}.json"
    number = 2

    while path.exists():
        path = CHARACTER_DIR / f"{base_name}_{number}.json"
        number += 1

    with path.open("w", encoding="utf-8") as file:
        json.dump(character.to_dict(), file, indent=4)

    return path

def read_json_list(path, label):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, list):
        raise ValueError(f"{label} must contain a JSON list.")
    return data


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    with temporary_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)
    temporary_path.replace(path)


def normalize_item(item):
    if not isinstance(item, dict):
        return {}

    modifier = item.get("modifier")
    if isinstance(modifier, dict):
        try:
            modifier_value = int(modifier.get("value", 0))
        except (TypeError, ValueError):
            modifier_value = 0
        modifier = {
            "stat": str(modifier.get("stat", "")).strip().lower(),
            "value": modifier_value,
        }
        if not modifier["stat"]:
            modifier = None
    else:
        modifier = None

    item_type = str(item.get("type") or item.get("item_type") or "trinket").strip()
    if not item_type:
        item_type = "trinket"
    item_type = item_type.lower().replace("_", " ")

    rarity = str(item.get("rarity") or item.get("quality") or "common").strip() or "common"
    rarity = rarity.lower().replace("_", " ")

    value = item.get("value", item.get("price", 0))
    if value is None:
        value = 0
    try:
        value = float(value)
    except (TypeError, ValueError):
        value = 0.0

    strain = item.get("strain", 0)
    try:
        strain = int(strain)
    except (TypeError, ValueError):
        strain = 0

    return {
        "name": str(item.get("name", "")).strip(),
        "description": str(item.get("description") or item.get("effect") or ""),
        "type": item_type,
        "rarity": rarity,
        "value": value,
        "strain": strain,
        "modifier": modifier,
        "effect": str(item.get("effect") or item.get("effects") or ""),
    }


def load_item_registry():
    if not ITEM_REGISTRY_PATH.exists():
        return []

    with ITEM_REGISTRY_PATH.open("r", encoding="utf-8") as file:
        items = json.load(file)

    if not isinstance(items, list):
        raise ValueError("The item registry must contain a JSON list.")

    normalized = []
    for item in items:
        normalized_item = normalize_item(item)
        if normalized_item.get("name"):
            normalized.append(normalized_item)
    return normalized


def load_spell_registry():
    return read_json_list(SPELL_REGISTRY_PATH, "Spell registry")


def load_attack_registry():
    return read_json_list(ATTACK_REGISTRY_PATH, "Attack registry")


def save_item_registry(items):
    normalized = []
    for item in items:
        normalized_item = normalize_item(item)
        if normalized_item.get("name"):
            normalized.append(normalized_item)
    write_json(ITEM_REGISTRY_PATH, normalized)


def save_spell_registry(spells):
    write_json(SPELL_REGISTRY_PATH, spells)


def save_attack_registry(attacks):
    write_json(ATTACK_REGISTRY_PATH, attacks)


def item_summary(item):
    modifier = item.get("modifier")
    modifier_text = (
        f"{modifier['stat']} {modifier['value']:+}"
        if modifier and modifier.get("stat")
        else "none"
    )
    effect_text = item.get("effect") or item.get("description") or "none"
    return (
        f"{item.get('name', '')}: type {item.get('type', 'trinket')}, "
        f"rarity {item.get('rarity', 'common')}, value {item.get('value', 0)}, "
        f"strain {item.get('strain', 0)}, modifier {modifier_text}, effect {effect_text}"
    )


def find_registered_item(items, name):
    return next(
        (item for item in items if item["name"].casefold() == name.casefold()),
        None,
    )


def find_registered_spell(spells, name):
    return next(
        (
            spell for spell in spells
            if str(spell.get("name", "")).casefold() == str(name).casefold()
        ),
        None,
    )


def normalize_spell(spell):
    if not isinstance(spell, dict):
        return {}

    cost = spell.get("cost", spell.get("resource_cost", 0))
    if cost is None:
        cost = 0
    try:
        cost = int(cost)
    except (TypeError, ValueError):
        cost = 0

    return {
        "name": str(spell.get("name", "")),
        "description": str(spell.get("description", spell.get("effect", ""))),
        "school": str(spell.get("school") or "Unknown"),
        "rank": str(spell.get("rank") or "1"),
        "target_type": str(spell.get("target_type") or spell.get("target") or "single").lower(),
        "range": str(spell.get("range") or "touch"),
        "cost": cost,
        "resource_name": str(spell.get("resource_name") or spell.get("resource_type") or "mana"),
        "required_item": str(spell.get("required_item") or ""),
        "consume_item": bool(spell.get("consume_item", False)),
        "effects": str(spell.get("effects") or spell.get("effect") or ""),
    }


def get_effective_stats(entity):
    stats = dict(entity.stats)
    items = load_item_registry()

    for equipped_name in entity.equipped_items:
        item = find_registered_item(items, equipped_name)
        modifier = item.get("modifier") if item else None

        if modifier and modifier["stat"] in stats:
            stat = modifier["stat"]
            stats[stat] += modifier["value"]

    return stats

def get_status(entity):
    soak = get_effective_stats(entity).get("soak", 0)

    if soak >= 1:
        condition = "Conscious and alive"
    elif soak == 0:
        condition = "Unconscious and alive"
    elif soak > -20:
        condition = "Alive, but not conscious"
    else:
        condition = "Dead"

    return condition, soak


def write_character(character, path):
    write_json(path, character.to_dict())

def open_character_sheet(character, output_dir=CHARACTER_HTML_DIR):
    escape = lambda value: html.escape(str(value), quote=True)

    effective_stats = get_effective_stats(character)
    stats_html = "".join(
        f"<li><strong>{escape(stat.capitalize())}:</strong> {escape(value)}</li>"
        for stat, value in effective_stats.items()
    )
    stats_html = f"<li><strong>Class:</strong> {escape(character.role)}</li>" + stats_html
    equipped_html = "".join(
        f"<li>{escape(item)}</li>" for item in character.equipped_items
    ) or "<li>None</li>"
    inventory_html = "".join(
        f"<li>{escape(item)}</li>" for item in character.inventory
    ) or "<li>None</li>"

    condition, current_soak = get_status(character)
    template = Template(TEMPLATE_PATH.read_text(encoding="utf-8"))
    rendered_html = template.safe_substitute(
        name=escape(character.name),
        description=escape(character.description),
        stats_html=stats_html,
        equipped_html=equipped_html,
        inventory_html=inventory_html,
        currency=escape(character.currency),
        status=escape(f"{condition} (soak: {current_soak})"),
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{safe_filename(character.name)}_sheet.html"
    output_path.write_text(rendered_html, encoding="utf-8")
    url = output_path.resolve().as_uri()

    # Chromium's app mode opens the sheet in its own, non-fullscreen window
    # without browser tabs or toolbars.
    browser = shutil.which("msedge") or shutil.which("chrome") or shutil.which("chromium")
    if browser:
        subprocess.Popen([browser, f"--app={url}"])
    else:
        webbrowser.open_new(url)
    return output_path

def prompt_integer(prompt):
    while True:
        try:
            return int(input(prompt))
        except ValueError:
            print("Please enter a whole number.")


def prompt_currency():
    while True:
        try:
            return float(input("Currency: "))
        except ValueError:
            print("Please enter a number for currency.")


def prompt_class():
    print("Available classes: " + ", ".join(CLASS_NAMES))
    while True:
        answers = [role.strip() for role in input(
            "Character class(es) (separate up to 3 with commas): "
        ).split(",")]
        if not 1 <= len(answers) <= 3 or any(not role for role in answers):
            print("Enter one to three classes, separated by commas.")
            continue
# role is class
        selected_roles = []
        for answer in answers:
            selected_class = next(
                (class_name for class_name in CLASS_NAMES
                 if class_name.casefold() == answer.casefold()),
                None,
            )
            if selected_class is None:
                print("Please choose a class from the listed classes.")
                break
            selected_roles.append(selected_class)
        else:
            return ", ".join(selected_roles)


def prompt_item_list(prompt):
    answer = input(prompt)
    return [item.strip() for item in answer.split(",") if item.strip()]


def create_character():
    name = input("Character name: ").strip()
    description = input("Description: ").strip()
    role = prompt_class()

    stats = {
        stat: prompt_integer(f"{stat.capitalize()}: ")
        for stat in STAT_NAMES
    }

    equipped_items = prompt_item_list(
        "Equipped items (comma-separated, or leave blank): "
    )
    inventory = prompt_item_list(
        "Inventory items (comma-separated, or leave blank): "
    )
    currency = prompt_currency()

    return Character(
        name=name or "Unnamed Character",
        description=description,
        role=role,
        stats=stats,
        equipped_items=equipped_items,
        inventory=inventory,
        currency=currency,
    )

class NPC(Character):
    """An NPC with the same data fields as a player character."""
    pass


def save_npc(npc):
    NPC_DIR.mkdir(parents=True, exist_ok=True)

    base_name = safe_filename(npc.name)
    path = NPC_DIR / f"{base_name}.json"
    number = 2

    while path.exists():
        path = NPC_DIR / f"{base_name}_{number}.json"
        number += 1

    with path.open("w", encoding="utf-8") as file:
        json.dump(npc.to_dict(), file, indent=4)

    return path


def write_npc(npc, path):
    with path.open("w", encoding="utf-8") as file:
        json.dump(npc.to_dict(), file, indent=4)


class CharacterCLI(cmd.Cmd):
    intro = (
        "Categories: items, spells, attacks, characters, npcs. "
        "Combat: addcombatant character|npc, roster, removecombatant <name>, "
        "clearroster, status, startcombat, turn, endcombat. "
        "Use 'clear' to clear the terminal. "
        "Use '<category> <command>' for category commands."
    )
    prompt = "> "

    def __init__(self):
        super().__init__()
        self.combat_roster = []
        self.initiative = {}
        self.combat_active = False
        self.turn_index = 0
        self._load_combat_roster()

    def _sort_roster_by_initiative(self):
        """Keep the roster in initiative order for following rule 7."""
        self.combat_roster.sort(
            key=lambda entry: (
                self.initiative.get(str(entry[2].resolve()), -1),
                entry[1].name.casefold(),
            ),
            reverse=True,
        )

    def _current_turn(self):
        if not self.combat_active or not self.combat_roster:
            return None
        self._sort_roster_by_initiative()
        if self.turn_index >= len(self.combat_roster):
            self.turn_index = 0
        return self.combat_roster[self.turn_index]

    def onecmd(self, line):
        """Keep common file and malformed-data errors from stopping the CLI."""
        try:
            return super().onecmd(line)
        except (OSError, json.JSONDecodeError, ValueError, KeyError, TypeError) as error:
            print(f"Command failed: {error}")
            return False

    def _print_document_file(self, filename):
        """Print a markdown document as plain text in the terminal."""
        path = BASE_DIR / filename
        if not path.exists():
            print(f"{filename} was not found in {BASE_DIR}.")
            return

        with path.open("r", encoding="utf-8") as file:
            print(file.read())

    def do_info(self, arg):
        """Display documentation files as plain text: info 1|2|3|4."""
        choice = (arg or "").strip().lower()
        docs = {
            "1": "GAMEPLAY.md",
            "2": "README.md",
            "3": "RULES.md",
            "4": "Notes.txt"
        }

        filename = docs.get(choice)
        if filename is None:
            print("Usage: info 1|2|3")
            print("  1 = GAMEPLAY.md")
            print("  2 = README.md")
            print("  3 = RULES.md")
            print("  4 = Notes.txt")
            return

        self._print_document_file(filename)

    def do_clear(self, arg):
        """Clear the terminal screen."""
        subprocess.run(
            ["cmd", "/c", "cls"] if os.name == "nt" else ["clear"],
            check=False,
        )

    def _save_combat_roster(self):
        write_json(COMBAT_ROSTER_PATH, {
            "combatants": [
                {
                    "type": kind,
                    "path": str(path.resolve()),
                    "initiative": self.initiative.get(str(path.resolve())),
                }
                for kind, _, path in self.combat_roster
            ]
        })

    def _load_combat_roster(self):
        if not COMBAT_ROSTER_PATH.exists():
            return

        with COMBAT_ROSTER_PATH.open("r", encoding="utf-8") as file:
            data = json.load(file)

        for entry in data.get("combatants", []):
            kind = entry.get("type")
            if kind not in ("character", "npc"):
                continue

            path = Path(entry.get("path", "")).resolve()
            expected_dir = (CHARACTER_DIR if kind == "character" else NPC_DIR).resolve()
            if path.parent != expected_dir or not path.is_file():
                continue

            with path.open("r", encoding="utf-8") as file:
                entity_data = json.load(file)

            entity_class = Character if kind == "character" else NPC
            entity = entity_class.from_dict(entity_data)
            self.combat_roster.append((kind, entity, path))

            score = entry.get("initiative")
            if isinstance(score, int):
                self.initiative[str(path)] = score
    _category_commands = {
        "items": {"newitem", "items"},
        "spells": {"newspell", "spells", "cast"},
        "attacks": {"newattack", "attacks", "useattack"},
        "items": {"newitem", "items"},
        "characters": {
            "create", "list", "load", "unload", "give", "remove", "equip",
            "unequip", "sheet",
        },
        "npcs": {
            "createnpc", "list", "listnpcs", "load", "loadnpc", "unloadnpc", "npcgive", "npcremove",
            "npc_equip", "npc_unequip", "npcsheet",
        },
    }

    def precmd(self, line):
        command = line.strip().split(maxsplit=1)[0].lower() if line.strip() else ""

        # Category names are command routers, not commands that need a prefix.
        if command in self._category_commands:
            return line

        category = next(
            (
                name for name, commands in self._category_commands.items()
                if command in commands
            ),
            None,
        )
        if category and getattr(self, "_active_category", None) != category:
            print(f"Use '{category} {line.strip()}' for this command.")
            return ""

        return line
    def _run_category(self, category, arg, default_command):
        command, _, remainder = arg.strip().partition(" ")
        if not command:
            getattr(self, default_command)("")
            return

        command = command.lower()
        if command not in self._category_commands[category]:
            print(f"Unknown {category} command '{command}'.")
            return

        if category == "npcs":
            command = {"list": "listnpcs", "load": "loadnpc"}.get(command, command)

        previous = getattr(self, "_active_category", None)
        self._active_category = category
        try:
            self.onecmd(f"{command} {remainder}".rstrip())
        finally:
            self._active_category = previous

    def do_characters(self, arg):
        """List characters or run a character command."""
        self._run_category("characters", arg, "do_list")

    def do_npcs(self, arg):
        """List NPCs or run an NPC command."""
        self._run_category("npcs", arg, "do_listnpcs")

    def do_create(self, arg):
        """Create and save a character."""
        character = create_character()
        self.character_path = save_character(character)
        self.character = character
        print(f"Character saved to: {self.character_path}")

    def do_list(self, arg):
        """List saved character files."""
        if not CHARACTER_DIR.exists():
            print("No saved characters yet.")
            return

        files = sorted(CHARACTER_DIR.glob("*.json"))
        if not files:
            print("No saved characters yet.")
            return

        for path in files:
            print(path.stem)

    def do_load(self, arg):
        """Load a saved character: load <name or filename>."""
        name = arg.strip()
        if not name:
            print("Usage: load <name or filename>")
            return

        filename = safe_filename(name)
        path = CHARACTER_DIR / f"{filename}.json"

        try:
            with path.open("r", encoding="utf-8") as file:
                character = Character.from_dict(json.load(file))
            self.character = character
            self.character_path = path
            print(f"Loaded {self.character.name}.")
        except FileNotFoundError:
            print(f"No saved character found for '{name}'. Use 'list' to see files.")
        except (json.JSONDecodeError, KeyError, TypeError) as error:
            print(f"Could not read that character file: {error}")

    def do_unload(self, arg):
        """Unload the currently loaded character."""
        if not hasattr(self, "character"):
            print("No character is loaded.")
            return
        name = self.character.name
        del self.character
        del self.character_path
        print(f"Unloaded {name}.")

    def do_newitem(self, arg):
        """Create an item in the registry."""
        name = input("Item name: ").strip()
        if not name:
            print("Item name cannot be blank.")
            return

        valid_types = ("weapon", "armor", "consumable", "trinket", "key item")
        print(f"Item type ({', '.join(valid_types)}):")
        item_type = input("Type: ").strip().lower() or "trinket"
        if item_type not in {"weapon", "armor", "consumable", "trinket", "key item"}:
            print("Item type must be one of: weapon, armor, consumable, trinket, key item.")
            return

        rarity = input("Rarity (common, uncommon, rare, epic, legendary): ").strip().lower() or "common"
        if rarity not in {"common", "uncommon", "rare", "epic", "legendary"}:
            print("Rarity must be one of: common, uncommon, rare, epic, legendary.")
            return

        description = input("Item description: ").strip()
        try:
            value = float(input("Item value (currency): ").strip() or 0)
        except ValueError:
            print("Item value must be a number.")
            return

        strain = prompt_integer("Item strain: ")
        effect = input("Effect / bonus / restriction: ").strip()

        print(f"Modifier target ({', '.join(STAT_NAMES)}), or leave blank:")
        modifier_stat = input("Modifier stat: ").strip().lower()

        modifier = None
        if modifier_stat:
            if modifier_stat not in STAT_NAMES:
                print("That is not a recognized stat.")
                return
            modifier = {
                "stat": modifier_stat,
                "value": prompt_integer("Modifier amount (use - for a penalty): "),
            }

        try:
            items = load_item_registry()
            if find_registered_item(items, name):
                print(f"An item named '{name}' is already registered.")
                return

            items.append({
                "name": name,
                "description": description,
                "type": item_type,
                "rarity": rarity,
                "value": value,
                "strain": strain,
                "effect": effect,
                "modifier": modifier,
            })
            save_item_registry(items)
            print(f"Registered item: {name}")
        except (json.JSONDecodeError, ValueError) as error:
            print(f"Could not update the item registry: {error}")

    def do_items(self, arg):
        """List registered items, or run an item command."""
        if arg.strip():
            self._run_category("items", arg, "_list_items")
            return

        self._list_items()

    def _list_items(self):
        """List registered items and their stats."""
        try:
            items = load_item_registry()
        except (json.JSONDecodeError, ValueError) as error:
            print(f"Could not read the item registry: {error}")
            return

        if not items:
            print("No items registered yet.")
            return

        for item in items:
            modifier = item.get("modifier")
            modifier_text = (
                f"{modifier['stat']} {modifier['value']:+}"
                if modifier else "none"
            )
            effect_text = item.get("effect") or item.get("description") or "none"
            print(
                f"- {item['name']}: type {item.get('type', 'trinket')}, "
                f"rarity {item.get('rarity', 'common')}, value {item.get('value', 0)}, "
                f"strain {item.get('strain', 0)}, modifier {modifier_text}, effect {effect_text}"
            )

    def do_give(self, arg):
        """Add a registered item to the loaded character: give <item name>."""
        item_name = arg.strip()
        if not item_name:
            print("Usage: give <item name>")
            return
        if not hasattr(self, "character"):
            print("Load or create a character first.")
            return

        try:
            items = load_item_registry()
        except (json.JSONDecodeError, ValueError) as error:
            print(f"Could not read the item registry: {error}")
            return

        item = find_registered_item(items, item_name)
        if not item:
            print(f"'{item_name}' is not in the registry. Use 'items' to list items.")
            return

        self.character.inventory.append(item["name"])
        write_character(self.character, self.character_path)
        print(f"Added {item['name']} to {self.character.name}'s inventory.")

    def do_remove(self, arg):
        """Remove one item from the loaded character: remove <item name>."""
        item_name = arg.strip()
        if not item_name:
            print("Usage: remove <item name>")
            return
        if not hasattr(self, "character"):
            print("Load or create a character first.")
            return

        match = next(
            (
                item for item in self.character.inventory
                if item.casefold() == item_name.casefold()
            ),
            None,
        )
        if match is None:
            print(f"{self.character.name} does not have '{item_name}'.")
            return

        self.character.inventory.remove(match)
        write_character(self.character, self.character_path)
        print(f"Removed {match} from {self.character.name}'s inventory.")

    def do_createnpc(self, arg):
        """Create and save an NPC."""
        name = input("NPC name: ").strip() or "Unnamed NPC"
        description = input("Description: ").strip()
        role = input("NPC role/class: ").strip()

        stats = {
            stat: prompt_integer(f"{stat.capitalize()}: ")
            for stat in STAT_NAMES
        }

        equipped_items = prompt_item_list(
            "Equipped items (comma-separated, or leave blank): "
        )
        inventory = prompt_item_list(
            "Inventory items (comma-separated, or leave blank): "
        )
        currency = prompt_currency()

        self.npc = NPC(
            name, description, stats, equipped_items, inventory, currency, role
        )
        self.npc_path = save_npc(self.npc)
        print(f"NPC saved to: {self.npc_path}")

    def do_listnpcs(self, arg):
        """List saved NPCs."""
        files = sorted(NPC_DIR.glob("*.json")) if NPC_DIR.exists() else []
        if not files:
            print("No saved NPCs yet.")
            return

        for path in files:
            print(path.stem)

    def do_loadnpc(self, arg):
        """Load an NPC by name or filename: loadnpc <name or filename>."""
        name = arg.strip()
        if not name:
            print("Usage: loadnpc <name or filename>")
            return

        path = NPC_DIR / f"{safe_filename(name)}.json"
        if not path.is_file() and NPC_DIR.exists():
            matches = []
            for candidate in NPC_DIR.glob("*.json"):
                try:
                    with candidate.open("r", encoding="utf-8") as file:
                        data = json.load(file)
                except (OSError, json.JSONDecodeError):
                    continue
                if (isinstance(data, dict)
                        and str(data.get("name", "")).casefold() == name.casefold()):
                    matches.append(candidate)

            if len(matches) == 1:
                path = matches[0]
            elif len(matches) > 1:
                filenames = ", ".join(candidate.stem for candidate in matches)
                print(f"Multiple NPC files are named '{name}': {filenames}. "
                      "Load one by filename.")
                return

        try:
            with path.open("r", encoding="utf-8") as file:
                self.npc = NPC.from_dict(json.load(file))
            self.npc_path = path
            print(f"Loaded NPC {self.npc.name}.")
        except FileNotFoundError:
            print(f"NPC '{name}' not found. Use 'listnpcs' to see saved NPCs.")
        except (json.JSONDecodeError, KeyError, TypeError) as error:
            print(f"Could not read that NPC file: {error}")

    def do_unloadnpc(self, arg):
        """Unload the currently loaded NPC."""
        if not hasattr(self, "npc"):
            print("No NPC is loaded.")
            return
        name = self.npc.name
        del self.npc
        del self.npc_path
        print(f"Unloaded NPC {name}.")

    def do_npcsheet(self, arg):
        """Open the loaded NPC's sheet in a browser."""
        if not hasattr(self, "npc"):
            print("No NPC loaded. Use 'createnpc' or 'loadnpc' first.")
            return

        try:
            path = open_character_sheet(self.npc, output_dir=NPC_HTML_DIR)
            print(f"Opened NPC sheet: {path}")
        except FileNotFoundError:
            print(f"Could not find the HTML template: {TEMPLATE_PATH}")

    def do_npcgive(self, arg):
        """Give a registered item to the loaded NPC: npcgive <item name>."""
        if not hasattr(self, "npc"):
            print("Load or create an NPC first.")
            return

        try:
            item = find_registered_item(load_item_registry(), arg.strip())
        except (json.JSONDecodeError, ValueError) as error:
            print(f"Could not read the item registry: {error}")
            return

        if not item:
            print(f"'{arg.strip()}' is not in the item registry.")
            return

        self.npc.inventory.append(item["name"])
        write_npc(self.npc, self.npc_path)
        print(f"Added {item['name']} to {self.npc.name}'s inventory.")

    def do_npcremove(self, arg):
        """Remove an item from the loaded NPC: npcremove <item name>."""
        if not hasattr(self, "npc"):
            print("Load or create an NPC first.")
            return

        item_name = arg.strip()
        match = next(
            (item for item in self.npc.inventory
             if item.casefold() == item_name.casefold()),
            None,
        )
        if match is None:
            print(f"{self.npc.name} does not have '{item_name}'.")
            return

        self.npc.inventory.remove(match)
        write_npc(self.npc, self.npc_path)
        print(f"Removed {match} from {self.npc.name}'s inventory.")

    def _move_item(self, arg, is_npc, equip):
        entity_name = "npc" if is_npc else "character"
        entity = getattr(self, entity_name, None)
        path = getattr(self, f"{entity_name}_path", None)
        item_name = arg.strip()

        if entity is None or path is None:
            print(f"Load or create a {entity_name} first.")
            return
        if not item_name:
            action = "equip" if equip else "unequip"
            print(f"Usage: {action} <item name>")
            return

        source = entity.inventory if equip else entity.equipped_items
        destination = entity.equipped_items if equip else entity.inventory
        match = next(
            (item for item in source if item.casefold() == item_name.casefold()),
            None,
        )

        if match is None:
            location = "inventory" if equip else "equipped items"
            print(f"{entity.name} does not have '{item_name}' in {location}.")
            return

        source.remove(match)
        destination.append(match)

        if is_npc:
            write_npc(entity, path)
        else:
            write_character(entity, path)

        action = "Equipped" if equip else "Unequipped"
        print(f"{action} {match} for {entity.name}.")

    def do_equip(self, arg):
        """Equip an inventory item: equip <item name>."""
        self._move_item(arg, is_npc=False, equip=True)

    def do_unequip(self, arg):
        """Unequip an item: unequip <item name>."""
        self._move_item(arg, is_npc=False, equip=False)

    def do_npc_equip(self, arg):
        """Equip an NPC inventory item: npc_equip <item name>."""
        self._move_item(arg, is_npc=True, equip=True)

    def do_npc_unequip(self, arg):
        """Unequip an NPC item: npc_unequip <item name>."""
        self._move_item(arg, is_npc=True, equip=False)

    def _refresh_roster(self):
        """Reload roster entries so status reflects the latest saved JSON."""
        refreshed = []
        for kind, _, path in self.combat_roster:
            with path.open("r", encoding="utf-8") as file:
                data = json.load(file)
            entity_class = Character if kind == "character" else NPC
            refreshed.append((kind, entity_class.from_dict(data), path))
        self.combat_roster = refreshed

    def _add_to_roster(self, kind):
        entity = getattr(self, kind, None)
        path = getattr(self, f"{kind}_path", None)
        if entity is None or path is None:
            print(f"Load or create a {kind} first.")
            return
        if any(existing_path.resolve() == path.resolve()
               for _, _, existing_path in self.combat_roster):
            print(f"{entity.name} is already in the roster.")
            return

        self.combat_roster.append((kind, entity, path))
        self._save_combat_roster()
        print(f"Added {entity.name} to the combat roster.")

    def do_addcombatant(self, arg):
        """Add the currently loaded character or NPC to the roster."""
        kind = arg.strip().lower()
        if kind not in ("character", "npc"):
            print("Usage: addcombatant character|npc")
            return
        self._add_to_roster(kind)

    def do_roster(self, arg):
        """Show combatants in initiative order."""
        self._refresh_roster()
        if not self.combat_roster:
            print("The combat roster is empty.")
            return
        for _, entity, path in self.combat_roster:
            score = self.initiative.get(str(path.resolve()))
            initiative_text = f" | Initiative: {score}" if score is not None else ""
            condition, soak = get_status(entity)
            print(f"- {entity.name}{initiative_text} | {condition} (soak: {soak})")

    def do_removecombatant(self, arg):
        """Remove a roster member by name."""
        name = arg.strip().casefold()
        for index, (_, entity, _) in enumerate(self.combat_roster):
            if entity.name.casefold() == name:
                self.combat_roster.pop(index)
                self._save_combat_roster()
                print(f"Removed {entity.name} from the roster.")
                return
        print(f"No combatant named '{arg.strip()}' is in the roster.")

    def do_clearroster(self, arg):
        """Clear the saved roster when combat is inactive."""
        if self.combat_active:
            print("End combat before clearing the roster.")
            return
        self.combat_roster.clear()
        self.initiative.clear()
        self._save_combat_roster()
        print("Combat roster cleared.")

    def do_status(self, arg):
        """Report the status of every combatant in the roster."""
        self._refresh_roster()
        if not self.combat_roster:
            print("The combat roster is empty.")
            return
        for _, entity, _ in self.combat_roster:
            condition, soak = get_status(entity)
            print(f"{entity.name}: {condition} (soak: {soak})")

    def do_startcombat(self, arg):
        """Roll initiative alphabetically, then order highest to lowest."""
        if self.combat_active:
            print("Combat is already active.")
            return

        # Include currently loaded entities if they are not already listed.
        for kind in ("character", "npc"):
            entity = getattr(self, kind, None)
            path = getattr(self, f"{kind}_path", None)
            if entity is not None and path is not None:
                if not any(p.resolve() == path.resolve()
                           for _, _, p in self.combat_roster):
                    self.combat_roster.append((kind, entity, path))

        if not self.combat_roster:
            print("Add combatants before starting combat.")
            return

        self._refresh_roster()
        self.initiative.clear()

        # Roll alphabetically; stable sorting keeps alphabetical order on ties.
        self.combat_roster.sort(key=lambda entry: entry[1].name.casefold())
        for _, entity, path in self.combat_roster:
            self.initiative[str(path.resolve())] = random.randint(1, 20)

        self._sort_roster_by_initiative()
        self.turn_index = 0
        self.combat_active = True
        self._save_combat_roster()
        print("Combat started. Initiative:")
        self.do_roster("")
        current = self._current_turn()
        if current is not None:
            _, entity, _ = current
            print(f"Current turn: {entity.name}")

    def do_endcombat(self, arg):
        """End combat but preserve the roster."""
        self.combat_active = False
        self.turn_index = 0
        self._save_combat_roster()
        print("Combat ended; roster preserved.")

    def do_turn(self, arg):
        """Advance a turn in initiative order and tick down negative soak."""
        if not self.combat_active:
            print("Combat is not active. Use 'startcombat' first.")
            return

        self._refresh_roster()
        if not self.combat_roster:
            print("The combat roster is empty.")
            self.combat_active = False
            return

        current = self._current_turn()
        if current is None:
            print("No combatant is ready to act.")
            return

        kind, entity, path = current
        print(f"{entity.name}'s turn.")

        for _, foe, foe_path in self.combat_roster:
            effective_soak = get_effective_stats(foe).get("soak", 0)
            if -20 < effective_soak < 0:
                foe.stats["soak"] -= 1
                writer = write_npc if foe is not entity and isinstance(foe, NPC) else write_character
                if foe is entity:
                    writer = write_npc if kind == "npc" else write_character
                writer(foe, foe_path)
                print(f"{foe.name}'s soak is now {get_effective_stats(foe).get('soak', 0)}.")

        self.turn_index = (self.turn_index + 1) % len(self.combat_roster)
        next_kind, next_entity, _ = self.combat_roster[self.turn_index]
        print(f"Next up: {next_entity.name} ({next_kind}).")
    def do_sheet(self, arg):
        """Open the current character's sheet in a browser."""
        if not hasattr(self, "character"):
            print("No character loaded. Use 'create' or 'load' first.")
            return

        try:
            path = open_character_sheet(self.character)
            print(f"Opened character sheet: {path}")
        except FileNotFoundError:
            print(f"Could not find the HTML template: {TEMPLATE_PATH}")
    def do_spells(self, arg):
        """List spells or run a spell command."""
        if arg.strip():
            self._run_category("spells", arg, "_list_spells")
        else:
            self._list_spells()

    def _list_spells(self):
        spells = [normalize_spell(spell) for spell in load_spell_registry()]

        if not spells:
            print("No spells registered yet.")
            return

        for spell in spells:
            required_item = spell.get("required_item") or "none"
            resource_name = spell.get("resource_name", "mana")
            print(
                f"- {spell['name']}: school {spell['school']}, rank {spell['rank']}, "
                f"target {spell['target_type']}, range {spell['range']}, "
                f"cost {spell['cost']} {resource_name}, item {required_item}"
            )

    def do_newspell(self, arg):
        """Register a new spell in the spell registry."""
        name = input("Spell name: ").strip()
        if not name:
            print("Spell name is required.")
            return

        school = input("School: ").strip() or "Unknown"
        rank = input("Rank: ").strip() or "1"
        target_type = input("Target type (self/single/multiple/area): ").strip().lower() or "single"
        if target_type not in {"self", "single", "multiple", "area", "battlefield"}:
            print("Target type must be one of: self, single, multiple, area, battlefield.")
            return

        spell_range = input("Range: ").strip() or "touch"
        resource_type = input("Resource type (mana, focus, etc.): ").strip() or "mana"
        cost_text = input("Resource cost (leave blank for 0): ").strip()
        try:
            cost = int(cost_text) if cost_text else 0
        except ValueError:
            print("Spell cost must be a whole number.")
            return

        description = input("Description: ").strip()
        effects = input("Effects/notes: ").strip()
        required_item = input("Required item (leave blank if none): ").strip()
        consume = input("Consume the item when cast? (y/n): ").strip().lower()

        try:
            spells = load_spell_registry()
            if find_registered_spell(spells, name):
                print("A spell with that name already exists.")
                return

            spell = {
                "name": name,
                "description": description,
                "school": school,
                "rank": rank,
                "target_type": target_type,
                "range": spell_range,
                "cost": cost,
                "resource_name": resource_type,
                "resource_cost": cost,
                "resource_type": resource_type,
                "effects": effects,
                "required_item": required_item,
                "consume_item": bool(required_item and consume in ("y", "yes")),
            }
            spells.append(spell)
            save_spell_registry(spells)
            print(f"Registered spell: {name}")
        except (OSError, ValueError, KeyError, TypeError) as error:
            print(f"Could not update spell registry: {error}")

    def do_attacks(self, arg):
        """List attacks or run an attack command."""
        if arg.strip():
            self._run_category("attacks", arg, "_list_attacks")
        else:
            self._list_attacks()

    def _list_attacks(self):
        for attack in load_attack_registry():
            requirement = attack.get("required_name") or "none"
            print(f"- {attack['name']}: requires {attack['required_type']} "
                  f"{requirement}")

    def do_newattack(self, arg):
        """Register a new attack in the attack registry."""
        name = input("Attack name: ").strip()
        if not name:
            print("Attack name is required.")
            return

        attacks = load_attack_registry()
        if any(a["name"].casefold() == name.casefold() for a in attacks):
            print("An attack with that name already exists.")
            return

        if name.casefold() == "barehanded attack":
            requirement_type, required_name = "none", ""
        else:
            requirement_type = input("Requirement type (item/spell): ").strip().lower()
            required_name = input("Required item or spell name: ").strip()
            if requirement_type not in ("item", "spell") or not required_name:
                print("Every other attack must require an item or spell.")
                return

        attacks.append({
            "name": name,
            "required_type": requirement_type,
            "required_name": required_name,
        })
        save_attack_registry(attacks)
        print(f"Registered attack: {name}")

    def do_cast(self, arg):
        """Cast a spell using the currently loaded character or NPC."""
        entity, kind = self._active_entity()
        if entity is None:
            print("Load a character or NPC first.")
            return

        spell_name = arg.strip()
        spells = [normalize_spell(s) for s in load_spell_registry()]
        spell = next(
            (s for s in spells if s.get("name", "").casefold() == spell_name.casefold()),
            None,
        )
        if spell is None:
            print(f"Unknown spell: {spell_name}")
            return

        target_type = spell.get("target_type", "single")
        if target_type not in {"self", "single", "multiple", "area", "battlefield"}:
            print(f"Spell target type is invalid for {spell['name']}: {target_type}")
            return

        resource_name = spell.get("resource_name", "mana")
        resource_cost = int(spell.get("cost", 0) or 0)
        if resource_cost > 0:
            resource_key = resource_name.casefold()
            if resource_key not in entity.stats:
                print(f"{entity.name} does not have a {resource_name} stat to pay the cost.")
                return
            if entity.stats[resource_key] < resource_cost:
                print(f"{entity.name} does not have enough {resource_name} to cast {spell['name']}.")
                return
            entity.stats[resource_key] -= resource_cost

        item_name = spell.get("required_item")
        if item_name:
            owned = next(
                (item for item in entity.inventory + entity.equipped_items
                 if item.casefold() == item_name.casefold()),
                None,
            )
            if owned is None:
                print(f"{entity.name} needs {item_name} to cast that spell.")
                return

            if spell.get("consume_item"):
                if owned in entity.inventory:
                    entity.inventory.remove(owned)
                else:
                    entity.equipped_items.remove(owned)
                self._save_entity(entity, kind)

        self._save_entity(entity, kind)
        print(f"{entity.name} casts {spell['name']} ({spell['school']} {spell['rank']}, range {spell['range']}, target {target_type}).")

    def do_useattack(self, arg):
        """Use a registered attack after checking its requirement."""
        name = arg.strip()
        attack = next(
            (a for a in load_attack_registry()
             if a["name"].casefold() == name.casefold()),
            None,
        )
        if attack is None:
            print(f"Unknown attack: {name}")
            return

        if attack["required_type"] == "item":
            entity, _ = self._active_entity()
            if entity is None or not any(
                item.casefold() == attack["required_name"].casefold()
                for item in entity.inventory + entity.equipped_items
            ):
                print(f"The required item is not available: {attack['required_name']}")
                return
        elif attack["required_type"] == "spell":
            spell = next(
                (s for s in load_spell_registry()
                 if s["name"].casefold() == attack["required_name"].casefold()),
                None,
            )
            if spell is None:
                print(f"Required spell is not registered: {attack['required_name']}")
                return
            self.do_cast(spell["name"])
            return

        print(f"Used attack: {attack['name']}")

    def _active_entity(self):
        if getattr(self, "character", None) is not None:
            return self.character, "character"
        if getattr(self, "npc", None) is not None:
            return self.npc, "npc"
        return None, None

    def _save_entity(self, entity, kind):
        path = getattr(self, f"{kind}_path")
        (write_npc if kind == "npc" else write_character)(entity, path)
    def do_quit(self, arg):
        """Exit the character creator."""
        return True

    do_exit = do_quit

    def do_EOF(self, arg):
        """Exit on Ctrl-Z in the Windows terminal."""
        print()
        return True


if __name__ == "__main__":
    CharacterCLI().cmdloop()