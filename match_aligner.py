import os, json

class MatchAligner:

    matches = {}

    def __init__(self, matchfile):
        if os.path.isfile(matchfile):
            with open(matchfile) as f:
                self.matches = json.load(f)

    def get_alignment_points(self, file, reffile):
        if file in self.matches:
            if reffile in self.matches[file]:
                return self.matches[file][reffile]
        return None, 0
