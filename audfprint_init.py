import os, json
from itertools import product
from audfprint import audfprint as fp
import util

default_config = ['--density', '70', '--fanout', '8', '--bucketsize', '500',
    '--search-depth', '2000', '--min-count', '5']
tiny_config = ['--density', '20', '--fanout', '3', '--bucketsize', '100',
    '--search-depth', '100', '--min-count', '5']

def make_dbs(audiodir, dbdir, maxdirs=None):
    for d in util.get_subdirs(audiodir, maxdirs):
        dbpath = dbdir+d.replace(audiodir,'')+'_default.plkz'
        audiofiles = util.get_audiofiles(d)
        fp.main([None, 'new', '--dbase', dbpath] + default_config + audiofiles)

def find_all_matches(audiodir, dbdir, outfile, maxdirs=None):
    matches = {}
    dirs = util.get_subdirs(audiodir, maxdirs)
    for d, e in product(dirs, dirs):
        audiofiles = util.get_audiofiles(d)
        dbpath = dbdir+d.replace(audiodir,'')+'_default.plkz'
        output = fp.main([None, 'match', '--dbase', dbpath,
            '--find-time-range'] + default_config + audiofiles)
        for i in range(len(output)):
            if audiofiles[i] not in matches:
                matches[audiofiles[i]] = {}
            matches[audiofiles[i]][e] = output[i]
    with open(outfile, 'w') as outfile:
        json.dump(matches, outfile)

#create_dbs()
#find_matches()