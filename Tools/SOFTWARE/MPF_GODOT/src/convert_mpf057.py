#!/usr/bin/env python3
"""First-pass MPF 0.57 to 0.80/GMC migration. Requires PyYAML.

Run with just MACHINE for an inventory, or add --output NEW --template GMC
to build a draft using an installed, configured Godot/GMC template project.
Review migration-report.json before running the draft.
"""

import argparse
import json
import math
from pathlib import Path
import re
import shutil
import sys
import tempfile

import yaml


class Loader(yaml.SafeLoader):
    """Match MPF's YAML 1.2 handling of strings such as 'on' and 'off'."""


Loader.yaml_implicit_resolvers = {
    char: [(tag, pattern) for tag, pattern in resolvers
           if tag != "tag:yaml.org,2002:bool"]
    for char, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}
Loader.add_implicit_resolver("tag:yaml.org,2002:bool",
                             re.compile(r"^(?:true|false)$", re.I), list("tTfF"))

LEGACY = set("""
animations assets bitmap_fonts displays effects image_pools image_templates
images images_frame_skips keyboard kivy_config mc_custom_code mpf-mc
playlist_player playlist_player_actions playlists slides sound_loop_player
sound_loop_player_actions sound_loop_sets sound_pools sound_system sounds
track_player transitions videos widget_styles widgets window
""".split())
FONT_TYPES = {".ttf", ".otf", ".fnt"}
CONFIG_DIRS = {"config", "modes", "shows"}
EXCLUDED = {".git", ".godot", ".venv", "venv", "venv39", ".venv39",
            "__pycache__", ".DS_Store", "logs"}


def read_yaml(path):
    original = path.read_text(encoding="utf-8-sig")
    return original, yaml.load(original, Loader=Loader)


def position(value, extent, low, high):
    if isinstance(value, (int, float)):
        return value
    match = re.fullmatch(
        rf"({low}|middle|center|{high}|-?[\d.]+%)(?:\s*([+-])\s*([\d.]+))?",
        str(value).strip(),
    )
    if not match:
        raise ValueError(f"unsupported position {value!r}")
    anchor, sign, offset = match.groups()
    if anchor.endswith("%"):
        base = extent * float(anchor[:-1]) / 100
    else:
        base = {low: 0, "middle": extent / 2, "center": extent / 2, high: extent}[anchor]
    return base + float(offset or 0) * (-1 if sign == "-" else 1)


def color(value, colors):
    value = str(colors.get(value, value) if isinstance(value, (str, int)) else value)
    basic = {"black": "000000", "white": "ffffff", "yellow": "ffff00",
             "red": "ff0000", "blue": "0000ff", "green": "008000"}
    value = basic.get(value.lower(), value).lstrip("#")
    if not re.fullmatch(r"[a-fA-F0-9]{6}(?:[a-fA-F0-9]{2})?", value):
        raise ValueError(f"unsupported color {value!r}")
    rgba = bytes.fromhex(value if len(value) == 8 else value + "ff")
    return "Color(" + ", ".join(f"{channel / 255:.6g}" for channel in rgba) + ")"


class Migration:
    def __init__(self, source):
        self.source = source
        self.configs = {}
        self.issues = []
        self.sections = {}
        self.slides = {}
        self.assets = {}
        self.aliases = {}
        self.alias_sources = {}
        self.buses = {}
        self.styles = {}
        self.colors = {}
        self.displays = {}
        self.rendered = {}

    def issue(self, path, key, message):
        self.issues.append({"file": str(path), "key": key, "message": message})

    def collect(self, relative, parents=()):
        if relative in parents:
            raise ValueError(f"cyclic config include: {relative}")
        if relative in self.configs:
            return
        original, config = read_yaml(self.source / relative)
        if config is None:
            config = {}
        if not isinstance(config, dict):
            raise ValueError(f"expected a config mapping: {relative}")
        includes = config.get("config") or []
        if isinstance(includes, str):
            includes = re.split(r"[,\s]+", includes.strip())
        for name in includes:
            path = (self.source / relative.parent / name).resolve()
            if not path.is_relative_to(self.source):
                raise ValueError(f"config include is outside the game: {path}")
            self.collect(path.relative_to(self.source), (*parents, relative))
        self.configs[relative] = (original, config)

    def inspect(self):
        self.collect(Path("config/config.yaml"))
        modes = ["attract"]
        for _, config in self.configs.values():
            names = config.get("modes") or []
            modes.extend(re.split(r"[,\s]+", names.strip()) if isinstance(names, str) else names)
        for name in dict.fromkeys(modes):
            path = Path("modes", name, "config", f"{name}.yaml")
            if (self.source / path).is_file():
                self.collect(path)

        for folder in ("fonts", "bitmap_fonts", "images", "sounds", "videos"):
            for path in sorted((self.source / folder).rglob("*")):
                if path.is_file() and not path.is_symlink():
                    for name in {path.name, path.stem}:
                        self.assets.setdefault((folder, name), []).append(path.relative_to(self.source))

        for path, (_, config) in self.configs.items():
            for key in sorted(LEGACY.intersection(config)):
                self.sections.setdefault(key, []).append(str(path))
            self.styles.update(config.get("widget_styles") or {})
            self.colors.update(config.get("named_colors") or {})
            self.displays.update(config.get("displays") or {})
            self.buses.update((config.get("sound_system") or {}).get("tracks") or {})
            for name, definition in (config.get("sounds") or {}).items():
                if isinstance(definition, dict):
                    self.aliases[name] = definition
                    self.alias_sources[name] = path
            for name, slide in (config.get("slides") or {}).items():
                if name in self.slides:
                    self.issue(path, f"slides.{name}", "Duplicate slide name. Review include order.")
                self.slides[name] = (path, slide)
            if path.parts[:2] in (("modes", "bonus"), ("modes", "high_score")):
                self.issue(path, "mode", "Review MPF 0.80 built-in mode events and payloads.")

        if self.displays:
            self.issue("project.godot", "displays",
                       "Configure the template's named MPFDisplay targets and cabinet layout.")
        for name, sound in sorted(self.aliases.items()):
            if sound.get("file"):
                self.asset("sounds", sound["file"], self.alias_sources[name], f"sounds.{name}.file")
        for name, (path, slide) in self.slides.items():
            scene = self.scene(name, path, slide)
            if scene:
                self.rendered[name] = scene

    def asset(self, folder, name, path, key):
        candidates = self.assets.get((folder, str(name)), [])
        if folder == "fonts":
            bitmap = self.assets.get(("bitmap_fonts", str(name)), [])
            candidates = [item for item in candidates + bitmap if item.suffix.lower() in FONT_TYPES]
        if len(candidates) == 1:
            return candidates[0].as_posix()
        self.issue(path, key, f"{'Missing' if not candidates else 'Ambiguous'} {folder} asset {name!r}.")
        return None

    def scene(self, name, path, slide):
        key = f"slides.{name}"
        if not isinstance(name, str) or not re.fullmatch(r"[\w-]+", name):
            self.issue(path, key, "Unsupported Godot scene filename.")
            return None
        settings = slide if isinstance(slide, dict) else {"widgets": slide}
        target = settings.get("target", "window")
        size = self.displays.get(target, {})
        width = int(size.get("width", 1920))
        height = int(size.get("height", 1080))
        nodes = []
        resources = {}

        def resource(path, kind):
            if path not in resources:
                resources[path] = (kind, str(len(resources) + 3))
            return 'ExtResource("' + resources[path][1] + '")'

        if "background_color" in settings:
            try:
                fill = color(settings["background_color"], self.colors)
                nodes.append(f'[node name="Background" type="ColorRect" parent="."]\n'
                             f'offset_right = {width}\noffset_bottom = {height}\n'
                             f'mouse_filter = 2\ncolor = {fill}')
            except ValueError as exc:
                self.issue(path, key, str(exc))

        widgets = settings.get("widgets") or []
        if not isinstance(widgets, list):
            self.issue(path, key, "Expected a list of widgets.")
            return None
        for index, widget in enumerate(widgets):
            location = f"{key}.widgets[{index}]"
            if not isinstance(widget, dict):
                self.issue(path, location, "Expected a widget mapping.")
                continue
            kind = widget.get("type")
            if kind != "text":
                if kind in {"image", "video"} and widget.get(kind):
                    self.asset(kind + "s", widget[kind], path, location)
                self.issue(path, location, f"Widget type {kind!r} needs a Godot implementation.")
                continue
            options = dict(self.styles.get(widget.get("style"), {}))
            options.update(widget)
            extra = options.keys() - {
                "type", "text", "x", "y", "z", "color", "style", "font_name",
                "font_size", "anchor_x", "anchor_y",
            }
            if extra:
                self.issue(path, location, "Review widget properties: " + ", ".join(sorted(extra)))
            content = str(options.get("text", ""))
            if re.search(r"\([^)]+\)", content):
                self.issue(path, location, "Bind legacy text tokens to GMC variables.")
            try:
                x = position(options.get("x", "middle"), width, "left", "right")
                y = height - position(options.get("y", "middle"), height, "bottom", "top")
                z = int(options.get("z", 0))
                font_size = int(options.get("font_size", 16))
                tint = color(options.get("color", "white"), self.colors)
            except (ValueError, TypeError) as exc:
                self.issue(path, location, str(exc))
                continue
            ax = {"left": 0, "middle": 0.5, "center": 0.5, "right": 1}
            ay = {"top": 0, "middle": 0.5, "center": 0.5, "bottom": 1}
            horizontal = ax.get(options.get("anchor_x", "center"), 0.5)
            vertical = ay.get(options.get("anchor_y", "middle"), 0.5)
            # A script can position the label after Godot resolves its font metrics.
            node = [f'[node name="Text{index}" type="Label" parent="."]',
                    'script = ExtResource("2")',
                    f'point = Vector2({x:g}, {y:g})',
                    f'alignment = Vector2({horizontal:g}, {vertical:g})',
                    f'z_index = {max(-4096, min(4096, z))}',
                    f'text = {json.dumps(content, ensure_ascii=False)}',
                    f'theme_override_font_sizes/font_size = {font_size}',
                    f'theme_override_colors/font_color = {tint}']
            if options.get("font_name"):
                font = self.asset("fonts", options["font_name"], path, location)
                if font:
                    node.append("theme_override_fonts/font = " + resource(font, "Font"))
            nodes.append("\n".join(node))

        if not nodes:
            return None
        headers = ['[gd_scene format=3]',
                   '[ext_resource type="Script" path="__SLIDE_SCRIPT__" id="1"]',
                   '[ext_resource type="Script" path="res://migration_label.gd" id="2"]']
        for asset, (kind, index) in resources.items():
            headers.append(f'[ext_resource type="{kind}" path={json.dumps("res://" + asset)} id="{index}"]')
        return "\n\n".join(headers + [f'[node name="{name}" type="Control"]\n'
                                          f'script = ExtResource("1")\n'
                                          f'offset_right = {width}\noffset_bottom = {height}'] + nodes) + "\n"

    def rewrite_sounds(self, path, entries):
        if not isinstance(entries, dict):
            self.issue(path, "sound_player", "Review non-mapping sound player syntax.")
            return entries
        for event, sounds in entries.items():
            if isinstance(sounds, str):
                sounds = {sounds: {}}
            if not isinstance(sounds, dict):
                self.issue(path, f"sound_player.{event}", "Review sound player syntax.")
                continue
            converted = {}
            for name, options in sounds.items():
                alias = self.aliases.get(name, {})
                if isinstance(options, dict):
                    options = dict(options)
                    track = options.pop("track", alias.get("track"))
                    if track is not None:
                        options.setdefault("bus", track)
                    if "volume" in alias:
                        options.setdefault("volume", alias["volume"])
                else:
                    self.issue(path, f"sound_player.{event}.{name}", "Review shorthand settings.")
                key = Path(alias["file"]).stem if alias.get("file") else name
                if key in converted:
                    self.issue(path, f"sound_player.{event}.{name}", "Sound aliases collide.")
                    key = name
                converted[key] = options
            entries[event] = converted
        return entries

    def rewrite(self, path, original, data):
        if not isinstance(data, dict):
            return original
        deprecated = LEGACY.intersection(data)
        for key in sorted(deprecated):
            if key not in {"slides", "widget_styles"}:
                self.issue(path, key, "Legacy definition omitted from the draft. Review its GMC equivalent.")
            del data[key]
        changed = bool(deprecated)
        if data.get("sound_player"):
            data["sound_player"] = self.rewrite_sounds(path, data["sound_player"])
            changed = True
        for key in ("slide_player", "widget_player"):
            if key in data:
                self.issue(path, key, "Verify triggers, display targets and widget/slide references.")
        if not changed:
            return original
        header = original.splitlines()[0] if original.startswith(("#config_version=", "#show_version=")) else ""
        return (header + "\n" if header else "") + yaml.safe_dump(data, sort_keys=False, allow_unicode=True)

    def report(self):
        return {
            "source": str(self.source),
            "target_mpf": "0.80.1",
            "status": "draft_requires_review",
            "active_config_files": [str(path) for path in self.configs],
            "legacy_sections": self.sections,
            "display_definitions": self.displays,
            "sound_alias_count": len(self.aliases),
            "sound_buses": list(self.buses),
            "generated_slides": sorted(self.rendered),
            "issues": sorted(self.issues, key=lambda issue: (issue["file"], issue["key"])),
        }

    def build(self, output, template):
        scripts = [path for path in (template / "addons").rglob("*.gd")
                   if re.search(r"^class_name\s+MPFSlide\b", path.read_text(encoding="utf-8"), re.M)]
        if not (template / "project.godot").is_file() or len(scripts) != 1:
            raise ValueError("template needs project.godot and an MPF-GMC add-on with one MPFSlide class")
        slide_script = "res://" + scripts[0].relative_to(template).as_posix()
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".mpf-migration-", dir=output.parent) as temp:
            draft = Path(temp) / "draft"
            ignore = shutil.ignore_patterns(*EXCLUDED)
            shutil.copytree(template, draft, ignore=ignore)
            shutil.copytree(self.source, draft, ignore=ignore, dirs_exist_ok=True)
            (draft / "migration_label.gd").write_text(LABEL_SCRIPT, encoding="utf-8")
            for name, scene in self.rendered.items():
                destination = draft / "slides" / f"{name}.tscn"
                destination.parent.mkdir(parents=True, exist_ok=True)
                if destination.exists():
                    raise ValueError(f"generated slide collides with template: {destination.name}")
                destination.write_text(scene.replace("__SLIDE_SCRIPT__", slide_script), encoding="utf-8")
            for path, original, data in self.documents():
                revised = self.rewrite(path, original, data)
                if revised != original:
                    (draft / path).write_text(revised, encoding="utf-8")
            self.write_buses(draft)
            (draft / "migration-report.json").write_text(
                json.dumps(self.report(), indent=2, default=str) + "\n", encoding="utf-8")
            if output.exists():
                raise FileExistsError(output)
            draft.rename(output)

    def documents(self):
        for relative, (original, data) in self.configs.items():
            yield relative, original, data
        for directory in CONFIG_DIRS:
            for path in sorted((self.source / directory).rglob("*.yaml")):
                relative = path.relative_to(self.source)
                if "shows" not in relative.parts[:-1]:
                    continue
                original, data = read_yaml(path)
                if not original.startswith("#show_version=") or not isinstance(data, list):
                    continue
                for index, step in enumerate(data):
                    if isinstance(step, dict):
                        for key in step.keys() & {"slides", "widgets", "sounds", "playlists"}:
                            self.issue(relative, f"step[{index}].{key}", "Verify show media action in GMC.")

    def write_buses(self, draft):
        if not self.buses:
            return
        location = draft / "default_bus_layout.tres"
        if location.exists():
            self.issue(location.name, "audio", "Template has a bus layout. Add legacy buses to it.")
            return
        lines = ['[gd_resource type="AudioBusLayout" format=3]', "", "[resource]"]
        for index, (name, options) in enumerate(self.buses.items(), start=1):
            gain = float(options.get("volume", 1))
            decibels = 20 * math.log10(gain) if gain > 0 else -80
            lines.extend([f'bus/{index}/name = &{json.dumps(name)}',
                          f'bus/{index}/volume_db = {decibels:g}',
                          f'bus/{index}/send = &"Master"'])
        location.write_text("\n".join(lines) + "\n", encoding="utf-8")


LABEL_SCRIPT = """extends Label

@export var point: Vector2
@export var alignment: Vector2

func _ready() -> void:
    mouse_filter = Control.MOUSE_FILTER_IGNORE
    resized.connect(_position_label)
    _position_label.call_deferred()

func _position_label() -> void:
    position = point - size * alignment
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("machine", type=Path, help="MPF machine folder containing config/config.yaml")
    parser.add_argument("--output", type=Path, help="new folder for the converted draft")
    parser.add_argument("--template", type=Path, help="configured Godot/GMC project to copy")
    options = parser.parse_args()
    source = options.machine.resolve()
    if (options.output is None) != (options.template is None):
        parser.error("--output and --template are used together")
    try:
        migration = Migration(source)
        migration.inspect()
        if options.output:
            output, template = options.output.resolve(), options.template.resolve()
            if output.exists() or output.is_relative_to(source) or output.is_relative_to(template):
                parser.error("--output must be a new folder outside the machine and template")
            if source.is_relative_to(template) or template.is_relative_to(source):
                parser.error("machine and template must be separate folders")
            migration.build(output, template)
            print(f"Draft created at {output}. Review migration-report.json before running it.")
        else:
            # Audit discovers media references in shows and config files without writing.
            for path, original, data in migration.documents():
                migration.rewrite(path, original, data)
            print(json.dumps(migration.report(), indent=2, default=str))
    except (OSError, ValueError, TypeError, yaml.YAMLError) as exc:
        print(f"Migration failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
