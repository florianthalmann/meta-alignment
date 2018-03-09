import os, json, subprocess
import util

def make_dbs(audiodir, dbdir, maxdirs=None):
    dirs = util.get_subdirs(audiodir, maxdirs)
    for d in dirs:
        dbpath = dbdir+d.replace(audiodir,'')
        #only create if not there yet
        if not os.path.isfile(dbpath):
            audiofiles = " ".join(util.get_audiofiles(d))
            cmd = "panako store NFFT_MAPDB_DATABASE=" + dbpath \
                + " MAX_FILE_SIZE=200000000 " + audiofiles
            print dirs.index(d)+1, "/", len(dirs), "creating panako db"
            p = subprocess.Popen(cmd, shell=True)
            p.communicate()

def find_all_matches(audiodir, dbdir, outfile, maxdirs=None):
    matches = {}
    #load matches if some already exist
    if os.path.isfile(outfile):
        with open(outfile) as f:
            matches = json.load(f)
    dirs = util.get_subdirs(audiodir, maxdirs)
    for d in dirs:
        fs = util.get_audiofiles(d)
        for f in fs:
            if f not in matches:
                matches[f] = {}
            for e in dirs:
                if e not in matches[f]:
                    dbpath = dbdir+e.replace(audiodir,'')
                    #THIS DOESNT WORK, PROB DUE TO CROSSCOVARIANCE FAILING!!
                    #cmd = "panako sync "+dbdir+dbname+" "+f
                    cmd = "panako query NFFT_MAPDB_DATABASE=" + dbpath \
                        + " MAX_FILE_SIZE=200000000 " + f
                    p = subprocess.Popen(cmd.format(f), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    stdout, stderr = p.communicate()
                    print dirs.index(d)+1, "/", len(dirs), ",", fs.index(f)+1, "/", len(fs), dirs.index(e)+1, "/", len(dirs), "matching with panako"
                    matches[f][e] = stdout
                    #save state
                    with open(outfile, 'w') as fairu:
                        json.dump(matches, fairu)