import os, json
from audfprint import audfprint as fp

audiodir = 'audio/'
default_config = ['--density', '70', '--fanout', '8', '--bucketsize', '500',
    '--search-depth', '2000', '--min-count', '5']
tiny_config = ['--density', '20', '--fanout', '3', '--bucketsize', '100',
    '--search-depth', '100', '--min-count', '5']

dirs = filter(os.path.isdir, [audiodir+f for f in os.listdir(audiodir)])

def create_dbs():
    #create dbs
    for d in dirs:
        fs = [d+'/'+f for f in os.listdir(d) if f.endswith('.flac')]
        fp.main([None, 'new', '--dbase', d+'_default.plkz']+default_config+fs)

def find_matches():
    matches = []
    for d in dirs:
        fs = [d+'/'+f for f in os.listdir(d) if f.endswith('.flac')]
        for e in dirs:
            matches.append(fp.main([None, 'match', '--dbase', e+'_default.plkz',
                '--find-time-range']+default_config+fs))
    with open('results/fp_matches_default.json', 'w') as outfile:
        json.dump(matches, outfile)

#create_dbs()
find_matches()