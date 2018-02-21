import os, subprocess


def make_db():
    d = "/Volumes/gspeed1/florian/meta-alignment/audio/gd1982-10-10.sbd.fixed.miller.110784.flac16"
    cmd = "panako store {0}".format(os.path.join(d, "*.mp3"))#
    print(cmd)
    p = subprocess.Popen(cmd, shell=True)
    p.communicate()

def test_match():
    #cmd = "panako monitor {0}"
    cmd = "panako query {0}"
    d = "/Volumes/gspeed1/florian/meta-alignment/audio"
    fs = []
    for root, dirs, files in os.walk(os.path.abspath(d)):
        for f in files:
            if (f.endswith('.flac') or f.endswith('.mp3') or f.endswith('.shn')):
                fs.append(os.path.join(root, f))
    c = 0
    for f in fs:
        c += 1
        print("{0}/{1}".format(c, len(fs)))
        p = subprocess.Popen(cmd.format(f), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
        strng = stdout + "\n"
        #print(strng)
        with open("./panako_test.log", "a") as logfile:
            logfile.write(strng)

make_db()

test_match()