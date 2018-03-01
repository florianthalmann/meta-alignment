import json
import numpy as np
import util

matches = {}

def init():
    with open('matches/audfprint.json') as f:
        for x, ys in json.load(f).iteritems():
            for y, m in ys.iteritems():
                m = m[0]
                if "Matched" in m:
                    d = float(between(m, "Matched ", " s "))
                    t1 = float(between(m, " at ", " s "))
                    f1 = between(m, " in ", " to ")
                    t2 = float(between(m, " time ", " s "))
                    f2 = between(m, " in ", " with ", 1)
                    if f1 not in matches:
                        matches[f1] = {}
                    matches[f1][f2] = [t1, t2, d]

def between(string, s1, s2, index=0):
    string = string.split(s1)[index+1]
    return string[:string.find(s2)]

def get_alignment_points(file, reffile):
    if file in matches:
        if reffile in matches[file]:
            t1, t2, d = matches[file][reffile]
            filedur = util.get_duration(file)
            refdur = util.get_duration(reffile)
            delta_start = t2-t1
            delta_end = delta_start+filedur #assume slope 1
            return [delta_start, delta_end], 1
    return None, 0

init()