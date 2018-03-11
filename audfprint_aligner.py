import json
import numpy as np
import util

class AudfprintAligner:

    matches = {}

    def __init__(self, matchfile):
        with open(matchfile) as f:
            for x, ys in json.load(f).iteritems():
                for y, m in ys.iteritems():
                    m = m[0]
                    if "Matched" in m:
                        d = float(self.between(m, "Matched ", " s "))
                        t1 = float(self.between(m, " at ", " s "))
                        f1 = self.between(m, " in ", " to ")
                        t2 = float(self.between(m, " time ", " s "))
                        f2 = self.between(m, " in ", " with ", 1)
                        if f1 not in self.matches:
                            self.matches[f1] = {}
                        self.matches[f1][f2] = [t1, t2, d]

    def between(self, string, s1, s2, index=0):
        string = string.split(s1)[index+1]
        return string[:string.find(s2)]

    def get_alignment_points(self, file, reffile):
        if file in self.matches:
            if reffile in self.matches[file]:
                t1, t2, d = self.matches[file][reffile]
                filedur = util.get_duration(file)
                refdur = util.get_duration(reffile)
                delta_start = t2-t1
                delta_end = delta_start+filedur #assume slope 1
                return [delta_start, delta_end], 1
        return None, 0