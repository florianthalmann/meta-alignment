import json
import numpy as np
import util

class PanakoAligner:

    matches = {}

    def __init__(self, matchfile):
        with open(matchfile) as f:
            for x, ys in json.load(f).iteritems():
                for y, m in ys.iteritems():
                    m = m.split('\n')[1].split(';')
                    _,_,_,_,name, start, score, time_factor, freq_factor = m
                    if name != "null":
                        if x not in self.matches:
                            self.matches[x] = {}
                        self.matches[x][y+'/'+name] = [int(start), int(score)]

    def get_alignment_points(self, file, reffile):
        if file in self.matches:
            if reffile in self.matches[file]:
                delta_start, score = self.matches[file][reffile]
                filedur = util.get_duration(file)
                refdur = util.get_duration(reffile)
                delta_end = delta_start+filedur #assume slope 1
                return [delta_start, delta_end], score
        return None, 0