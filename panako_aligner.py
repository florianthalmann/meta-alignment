import json
import numpy as np
import util

matches = {}

def init():
    with open('matches/panako.json') as f:
        for x, ys in json.load(f).iteritems():
            for y, m in ys.iteritems():
                m = m.split('\n')[1].split(';')
                _,_,_,_,name, start, score, time_factor, freq_factor = m
                if name != "null":
                    if x not in matches:
                        matches[x] = {}
                    matches[x][y+'/'+name] = [int(start), int(score)]

def between(string, s1, s2, index=0):
    string = string.split(s1)[index+1]
    return string[:string.find(s2)]

def get_alignment_points(file, reffile):
    if file in matches:
        if reffile in matches[file]:
            delta_start, score = matches[file][reffile]
            filedur = util.get_duration(file)
            refdur = util.get_duration(reffile)
            delta_end = delta_start+filedur #assume slope 1
            return [delta_start, delta_end], score
    return None, 0

init()