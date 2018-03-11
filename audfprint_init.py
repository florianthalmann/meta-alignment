import os, json
from itertools import product
from audfprint import audfprint as fp
import util

default_config = ['--density', '70', '--fanout', '8', '--bucketsize', '500',
    '--search-depth', '2000', '--min-count', '5']
tiny_config = ['--density', '20', '--fanout', '3', '--bucketsize', '100',
    '--search-depth', '100', '--min-count', '5']

def make_dbs(audiodir, dbdir, maxdirs=None):
    dirs = util.get_subdirs(audiodir, maxdirs)
    for d in dirs:
        dbpath = dbdir+d.replace(audiodir,'')+'_default.plkz'
        #only create if not there yet
        if not os.path.isfile(dbpath):
            print dirs.index(d)+1, "/", len(dirs), "creating audfprint db"
            audiofiles = util.get_audiofiles(d)
            fp.main([None, 'new', '--dbase', dbpath] + default_config + audiofiles)

def find_all_matches(audiodir, dbdir, outfile, maxdirs=None):
    matches = {}
    #load matches if some already exist
    if os.path.isfile(outfile):
        with open(outfile) as f:
            matches = json.load(f)
    dirs = util.get_subdirs(audiodir, maxdirs)
    for d, e in product(dirs, dirs):
        audiofiles = util.get_audiofiles(d)
        #check if not already done
        if not (audiofiles[0] in matches and e in matches[audiofiles[0]]):
            print dirs.index(d)+1, "/", len(dirs), ",", dirs.index(e)+1, "/", len(dirs), "matching with audfprint"
            dbpath = dbdir+e.replace(audiodir,'')+'_default.plkz'

            output = fp.main([None, 'match', '--dbase', dbpath,
                '--find-time-range'] + default_config + audiofiles)
            print d, e, output
            for i in range(len(output)):
                if audiofiles[i] not in matches:
                    matches[audiofiles[i]] = {}
                matches[audiofiles[i]][e] = output[i]
            with open(outfile, 'w') as fairu:
                json.dump(matches, fairu)

#create_dbs()
#find_matches()