import os, json, subprocess
import util

def make_dbs(audiodir, dbdir, maxdirs=None):
    for d in util.get_subdirs(audiodir, maxdirs):
        dbpath = dbdir+d.replace(audiodir,'')
        audiofiles = " ".join(util.get_audiofiles(d))
        cmd = "panako store NFFT_MAPDB_DATABASE=" + dbpath \
            + " MAX_FILE_SIZE=200000000 " + audiofiles
        print(cmd)
        p = subprocess.Popen(cmd, shell=True)
        p.communicate()

def find_all_matches(audiodir, dbdir, outfile, maxdirs=None):
    dirs = util.get_subdirs(audiodir, maxdirs)
    matches = {}
    for d in dirs:
        for f in util.get_audiofiles(d):
            matches[f] = {}
            for e in dirs:
                dbpath = dbdir+e.replace(audiodir,'')
                #THIS DOESNT WORK, PROB DUE TO CROSSCOVARIANCE FAILING!!
                #cmd = "panako sync "+dbdir+dbname+" "+f
                cmd = "panako query NFFT_MAPDB_DATABASE=" + dbpath \
                    + " MAX_FILE_SIZE=200000000 " + f
                p = subprocess.Popen(cmd.format(f), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdout, stderr = p.communicate()
                print f, e, stdout
                matches[f][e] = stdout
    with open(outfile, 'w') as outfile:
        json.dump(matches, outfile)