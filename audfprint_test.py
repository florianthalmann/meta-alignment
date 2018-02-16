import os, json
from audfprint import audfprint as fp

audiodir = 'audio/'

dirs = filter(os.path.isdir, [audiodir+f for f in os.listdir(audiodir)])

def create_dbs():
    #create dbs
    for d in dirs:
        fs = [d+'/'+f for f in os.listdir(d) if f.endswith('.flac')]
        fp.main([None, 'new', '--dbase', d+'.plkz']+fs)

def find_matches():
    matches = []
    for d in dirs:
        fs = [d+'/'+f for f in os.listdir(d) if f.endswith('.flac')]
        for e in dirs:
            matches.append(fp.main([None, 'match', '--dbase', e+'.plkz', '--find-time-range']+fs))
    return matches

matches = find_matches()
with open('results/fp_matches.json', 'w') as outfile:
    json.dump(matches, outfile)