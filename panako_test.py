import os, json, subprocess

panako_db_dir = "dbs/panako/"
audiodir = "audio/"

dirs = filter(os.path.isdir, [audiodir+f for f in os.listdir(audiodir)])
#dirs = [dirs[0]]


def make_db():
    for d in dirs:
        fs = [d+'/'+f for f in os.listdir(d) if f.endswith('.flac') or f.endswith('.mp3') or f.endswith('.shn')]
        db = d.replace('audio/','')
        cmd = "panako store NFFT_MAPDB_DATABASE="+panako_db_dir+db+" MAX_FILE_SIZE=200000000 "+(" ".join(fs))
        print(cmd)
        p = subprocess.Popen(cmd, shell=True)
        p.communicate()

def test_match():
    matches = {}
    for d in dirs:
        fs = [d+'/'+f for f in os.listdir(d) if f.endswith('.flac') or f.endswith('.mp3') or f.endswith('.shn')]
        #fs = [fs[0]]
        for f in fs:
            matches[f] = {}
            for e in dirs:
                dbname = e.replace('audio/','')
                cmd = "panako query NFFT_MAPDB_DATABASE="+panako_db_dir+dbname+" MAX_FILE_SIZE=200000000 "+f
                p = subprocess.Popen(cmd.format(f), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdout, stderr = p.communicate()
                print f, e, stdout
                matches[f][e] = stdout
    with open('matches/panako.json', 'w') as outfile:
        json.dump(matches, outfile)

#make_db()

#test_match()