import os, json
from audfprint import audfprint as fp

audiodir = 'audio/'
db_dir = "dbs/audfprint/"

default_config = ['--density', '70', '--fanout', '8', '--bucketsize', '500',
    '--search-depth', '2000', '--min-count', '5']
tiny_config = ['--density', '20', '--fanout', '3', '--bucketsize', '100',
    '--search-depth', '100', '--min-count', '5']

dirs = filter(os.path.isdir, [audiodir+f for f in os.listdir(audiodir)])
#dirs = [dirs[2]]

def create_dbs():
    #create dbs
    for d in dirs:
        fs = [d+'/'+f for f in os.listdir(d) if f.endswith('.flac') or f.endswith('.mp3') or f.endswith('.shn')]
        dbname = d.replace('audio/','')
        fp.main([None, 'new', '--dbase', db_dir+dbname+'_default.plkz']+default_config+fs)

def find_matches():
    matches = {}
    for d in dirs:
        fs = [d+'/'+f for f in os.listdir(d) if f.endswith('.flac') or f.endswith('.mp3') or f.endswith('.shn')]
        #fs = [fs[0]]
        for e in dirs:
            dbname = e.replace('audio/','')
            output = fp.main([None, 'match', '--dbase', db_dir+dbname+'_default.plkz',
                '--find-time-range']+default_config+fs)
            for i in range(len(output)):
                if fs[i] not in matches:
                    matches[fs[i]] = {}
                matches[fs[i]][e] = output[i]
    with open('matches/audfprint.json', 'w') as outfile:
        json.dump(matches, outfile)

#create_dbs()
find_matches()