#!/usr/bin/env python3

import os
import stat
from os import mkdir, listdir, path
from string import hexdigits
from pathlib import Path
import re
import subprocess
import json
from collections import OrderedDict


class ProcessCheats:
    def __init__(self, in_path, out_path):
        self.out_path = Path(out_path)
        self.in_path = Path(in_path)
        self.parseCheats()

    def isHexAnd16Char(self, file_name):
        return (len(file_name) == 16) and (all(c in hexdigits for c in file_name[0:15]))

    def getCheatsPath(self, tid):
        for folder in tid.iterdir():
            if folder.name.lower() == "cheats":
                return folder
        return None

    def getAttribution(self, tid):
        attribution = OrderedDict()
        for f in tid.iterdir():
            if f.suffix.lower() == ".txt":
                with open(f, "r", encoding="utf-8", errors="ignore") as attribution_file:
                    attribution[f.name] = attribution_file.read()
        return attribution

    def constructBidDict(self, sheet_path):
        out = OrderedDict()
        pos = []
        with open(sheet_path, 'r', encoding="utf-8", errors="ignore") as cheatSheet:
            lines = cheatSheet.readlines()

        for i in range(len(lines)):
            titles = re.search(r"(\[.+\]|\{.+\})", lines[i])
            if titles:
                pos.append(i)

        for i in range(len(pos)):
            try:
                codeLines = lines[pos[i]:pos[i + 1]]
            except IndexError:
                codeLines = lines[pos[i]:]
            if len(codeLines) > 1:
                code = "".join(codeLines)
                if re.search("[0-9a-fA-F]{8}", code):
                    out[lines[pos[i]].strip()] = code.strip("\n ") + "\n\n"
        return out

    def update_dict(self, new, old):
        for key, value in new.items():
            if key in old:
                old[key] |= value
            else:
                old[key] = value
        return old

    def createJson(self, tid):
        out = OrderedDict()
        cheats_dir = self.getCheatsPath(tid)
        if cheats_dir:
            try:
                for sheet in cheats_dir.iterdir():
                    if self.isHexAnd16Char(sheet.stem):
                        out[sheet.stem.upper()] = self.constructBidDict(sheet)
            except FileNotFoundError as e:
                print(f"error: FileNotFoundError {e}")
            attribution = self.getAttribution(tid)
            if attribution:
                out = self.update_dict(out, {"attribution": attribution})

            cheats_file = self.out_path.joinpath(f"{tid.name.upper()}.json")
            try:
                with open(cheats_file, 'r', encoding="utf-8", errors="ignore") as json_file:
                    out = self.update_dict(out, json.load(json_file))
            except FileNotFoundError:
                pass

            out = OrderedDict(sorted(out.items()))

            with open(cheats_file, 'w', encoding="utf-8") as json_file:
                json.dump(out, json_file, indent=4, ensure_ascii=False)

    def parseCheats(self):
        # Make files writable (cross-platform)
        try:
            for root, dirs, files in os.walk(self.in_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        os.chmod(file_path, stat.S_IWRITE | stat.S_IREAD)
                    except (OSError, PermissionError):
                        pass  # Ignore permission errors
        except Exception:
            pass  # If chmod fails, continue anyway
            
        if not(self.out_path.exists()):
            self.out_path.mkdir(parents=True)
        for tid in self.in_path.iterdir():
            if self.isHexAnd16Char(tid.name):
                self.createJson(tid)
