#!/usr/bin/env python3
"""Apply the reviewed companion overlay to the pinned upstream iOS checkout."""
import argparse
import hashlib
from pathlib import Path
import re
import shutil

HERE = Path(__file__).resolve().parent


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f"Upstream integration point changed: {old[:100]}")
    return text.replace(old, new, 1)


def object_pattern(identifier):
    return rf'(\t\t{identifier}(?: /\* [^\n]+ \*/)? = \{{\n)(.*?)(\n\t\t\}};)'


def register_sources(project):
    source = project.read_text()
    names = ("OAJunctionCompanion.h", "OAJunctionCompanion.m")
    def identifier(name):
        return hashlib.sha256(("junction-ios:" + name).encode()).hexdigest()[:24].upper()
    refs = {name: identifier(name) for name in names}
    group = identifier("group")
    build = identifier("build")
    for value in [*refs.values(), group, build]:
        if value in source:
            raise ValueError("Companion is already registered; refusing a duplicate build entry")
    source = replace_once(source, "/* End PBXBuildFile section */",
        f'\t\t{build} /* OAJunctionCompanion.m in Sources */ = {{isa = PBXBuildFile; fileRef = {refs[names[1]]} /* OAJunctionCompanion.m */; }};\n/* End PBXBuildFile section */')
    additions = ""
    for name in names:
        kind = "sourcecode.c.h" if name.endswith(".h") else "sourcecode.c.objc"
        additions += f'\t\t{refs[name]} /* {name} */ = {{isa = PBXFileReference; lastKnownFileType = {kind}; path = {name}; sourceTree = "<group>"; }};\n'
    source = replace_once(source, "/* End PBXFileReference section */", additions + "/* End PBXFileReference section */")
    members = "".join(f'\t\t\t\t{refs[name]} /* {name} */,\n' for name in names)
    addition = f'\t\t{group} /* Junction Companion */ = {{\n\t\t\tisa = PBXGroup;\n\t\t\tchildren = (\n{members}\t\t\t);\n\t\t\tpath = Sources/Junction;\n\t\t\tsourceTree = "<group>";\n\t\t}};\n'
    source = replace_once(source, "/* End PBXGroup section */", addition + "/* End PBXGroup section */")
    root_id = re.search(r"mainGroup = ([A-F0-9]+);", source)[1]
    match = re.search(object_pattern(root_id), source, re.DOTALL)
    body = replace_once(match[2], "children = (", f"children = (\n\t\t\t\t{group} /* Junction Companion */,")
    source = source[:match.start()] + match[1] + body + match[3] + source[match.end():]
    target = re.search(object_pattern("BBA3AF30197FC4BB0039D991"), source, re.DOTALL)
    phase_id = re.search(r"([A-F0-9]+) /\* Sources \*/", target[2])[1]
    phase = re.search(object_pattern(phase_id), source, re.DOTALL)
    body = replace_once(phase[2], "files = (", f"files = (\n\t\t\t\t{build} /* OAJunctionCompanion.m in Sources */,")
    source = source[:phase.start()] + phase[1] + body + phase[3] + source[phase.end():]
    project.write_text(source)


def install(ios):
    target = ios / "Sources/Junction"
    if target.exists():
        raise ValueError("Existing Junction source directory left untouched")
    route_header = ios / "Sources/Router/OARouteCalculationResult.h"
    route_impl = ios / "Sources/Router/OARouteCalculationResult.mm"
    signature = "- (NSArray<OASRouteSegmentResult *> *)getJunctionSegmentsFrom:(int)start count:(int)count"
    header = route_header.read_text()
    position = header.rfind("\n@end")
    if position < 0: raise ValueError("Route declaration missing")
    header = header[:position] + "\n/** Read-only, bounded point-aligned segment window for the companion exporter. */\n" + signature + ";\n" + header[position:]
    implementation = route_impl.read_text()
    position = implementation.rfind("\n@end")
    if position < 0: raise ValueError("Route implementation missing")
    method = '\n' + signature + '\n{\n    if (start < 0 || count < 0 || (NSUInteger)start > _segments.count ||\n        (NSUInteger)count > _segments.count - (NSUInteger)start) return @[];\n    return [_segments subarrayWithRange:NSMakeRange(start, count)];\n}\n'
    implementation = implementation[:position] + method + implementation[position:]
    app = ios / "Sources/AppHost/OAAppDelegate.mm"
    app_text = app.read_text()
    app_text = '#import "OAJunctionCompanion.h"\n' + app_text
    app_text = replace_once(app_text, '_appInitDone = YES;',
        '_appInitDone = YES;\n            dispatch_async(dispatch_get_main_queue(), ^{ [[OAJunctionCompanion shared] start]; });')
    settings = ios / "Sources/Controllers/Settings/OAMainSettingsViewController.m"
    settings_text = '#import "OAJunctionCompanion.h"\n' + settings.read_text()
    marker = '    [data addObject:@[\n        @{\n            @"name" : @"osmand_settings",'
    row = '    [data addObject:@[\n        @{\n            @"name" : @"junction_companion",\n            @"title" : NSLocalizedString(@"junction_title", nil),\n            @"description" : NSLocalizedString(@"junction_source_explanation", nil),\n            @"img" : ACImageNameLeftMenuIconSettings,\n            @"type" : [OAValueTableViewCell getCellIdentifier]\n        },\n        @{\n            @"name" : @"osmand_settings",'
    settings_text = replace_once(settings_text, marker, row)
    marker = 'if ([name isEqualToString:@"osmand_settings"])'
    settings_text = replace_once(settings_text, marker,
        'if ([name isEqualToString:@"junction_companion"])\n    {\n        [[OAJunctionCompanion shared] presentSetupFrom:self];\n    }\n    else ' + marker)
    localization = ios / "Resources/Localizations/en.lproj/Localizable.strings"
    if not localization.is_file(): raise ValueError("Expected English iOS string catalog missing")
    strings = (HERE / "source/Junction.strings").read_text()
    # Validate every integration point before writing any existing source file.
    register_sources(ios / "OsmAnd.xcodeproj/project.pbxproj")
    target.mkdir()
    for name in ("OAJunctionCompanion.h", "OAJunctionCompanion.m"):
        shutil.copyfile(HERE / "source" / name, target / name)
    route_header.write_text(header)
    route_impl.write_text(implementation)
    app.write_text(app_text)
    settings.write_text(settings_text)
    localization.write_text(strings + "\n" + localization.read_text())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ios", required=True, type=Path)
    install(parser.parse_args().ios.resolve())
