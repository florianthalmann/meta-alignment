from essentia.standard import *
import sox, os, shutil
from random import random, randint, choice, getrandbits
from subprocess import Popen, DEVNULL, STDOUT
from progressbar import ProgressBar
import multiprocessing as mp
from itertools import repeat
from uuid import uuid4


REFS = ['gd1982-10-10.sbd.fixed.miller.110784.flac16', 'gd1995-03-18.sbd.miller.97659.flac16']
#REFS = ['gd1982-10-10.sbd.fixed.miller.110784.flac16']

THREADS = int(mp.cpu_count()/2)
manager = mp.Manager()
count = manager.Value('i', 0)
bar = None

CROSSFADE = 0.1
TRIM = 60           # tracks 1 and 10 must be > ADD * 2 (ADD reserved for adding to start/end)
ADD = 10
DATASETSIZE = 10


class Parameters(object):
    def __init__(self, ref):
        self.ref_dir = os.path.join('source', ref[0])
        self.ref_length = ref[1]
        self.ref_trackmarkers = sorted(ref[2])
        self.dir = os.path.join('data', ref[0], str(uuid4()).replace('-', ''))
        # generate random parameters
        self.speed = choice([1] + 2 * [randint(90, 110) * 0.01])
        self.equaliser = bool(choice(4 * [1] + [0]))                    # chance no EQ 1:4
        self.crowd = round(choice([0] + 2 * [randint(2, 8) * 0.1]), 1)  # chance no crowd 1:3
        self.bleed = round(random() * 0.5, 1)
        self.reverb = bool(getrandbits(1))
        self.add = choice([None, 'start', 'end', 'both'])
        if self.reverb == True:
            reverberance = randint(50, 75)
            pre_delay = randint(5, 10)
            wet_gain = randint(-10, 10) * 0.1
            self.reverb = (reverberance, pre_delay, wet_gain)
        
    def segments():
        pass




def refFiles():
    ref_files = []
    for e in REFS:
        sdir = os.path.join('source', e)
        [os.remove(os.path.join(sdir, f)) for f in os.listdir(sdir) if f.endswith('_snippet.wav')]
        if os.path.isfile(os.path.join(sdir, 'concatenated.wav')): os.remove(os.path.join(sdir, 'concatenated.wav'))
        if os.path.isfile(os.path.join(sdir, 'add_start.wav')): os.remove(os.path.join(sdir, 'add_start.wav'))
        if os.path.isfile(os.path.join(sdir, 'add_end.wav')): os.remove(os.path.join(sdir, 'add_end.wav'))
        if os.path.exists('data'): shutil.rmtree('data') 
        os.mkdir('data')
        p = os.path.join(sdir, 'original')
        ref_files += [(i, os.path.join(p, f)) for i, f in enumerate(os.listdir(p)) if f.endswith('.mp3')]
    return ref_files


def beatPostions(f):
    audio = MonoLoader(filename=f[1])()
    beat_tracker = BeatTrackerMultiFeature()
    beats, confidence = beat_tracker(audio)
    return { 'file':f[1], 'length':len(audio)/44100, 'beats':list(beats)[::4], 'track':f[0] }


def makeSnippet(f):
    if f['track'] in (1, 10) and f['length'] < ADD * 2:
        print('ERROR: track {0} shorter than {1}s', format(f['track'], ADD * 2))
        sys.exit()
    fbeats = f['beats']
    if f['track'] == 1: fbeats = [b for b in fbeats if b > ADD]
    elif f['track'] == 10: fbeats = [b for b in fbeats if b < f['length'] - ADD]
    snipfile = f['file'].replace('/original/', '/')[:-4] + '_snippet.wav'
    if f['length'] <= TRIM:
        tfm = sox.Transformer()
        tfm.build(f['file'], snipfile)
        return
    random_start = choice([b for b in fbeats if b < f['length'] - TRIM])
    random_choice = [f['length'] - TRIM] + 2 * [random_start]
    start_beat = choice(random_choice)
    end_beat = findNearest(fbeats, start_beat + TRIM)
    tfm = sox.Transformer()
    tfm.trim(start_beat, end_beat)
    tfm.build(f['file'], snipfile)
    if f['track'] == 1:
        end_beat = start_beat
        start_beat = findNearest(fbeats, start_beat - ADD)
        sfile = 'add_start.wav'
    elif f['track'] == 10:
        start_beat = end_beat
        end_beat = findNearest(fbeats, end_beat + ADD)
        sfile = 'add_end.wav'
    if f['track'] in (1, 10):
        snipfile = os.path.join('/'.join(f['file'].split('/')[:-2]), sfile)
        print(snipfile)
        tfm = sox.Transformer()
        tfm.trim(start_beat, end_beat)
        tfm.build(f['file'], snipfile)



  
def findNearest(a, v):
    return min(a, key=lambda x:abs(x-v))


def fixMp3Header(f):
    ftemp = f[:-4] +'_temp.mp3'
    os.rename(f, ftemp)
    cmd = 'ffmpeg -i {0} -c:a copy -c:v copy {1}'.format(ftemp, f)
    p = Popen(cmd, shell=True, stdout=DEVNULL, stderr=DEVNULL)
    p.wait()
    os.remove(ftemp)


def listener(q):
    global bar
    while 1:
        g = q.get()
        if g == 'kill': 
            break
        elif g == 1:
            count.value += 1
            bar.update(count.value)


def storeSnippets(args):
    return _storeSnippets(*args)
    
def _storeSnippets(f, args):
    #fixMp3Header(f)
    b = beatPostions(f)
    makeSnippet(b)
    q = args[-1]
    q.put(1)


def concatenateSnippets(args):
    return _concatenateSnippets(*args)

def _concatenateSnippets(e, args):
    sdir = os.path.join('source', e)
    snipfiles = [os.path.join(sdir, f) for f in os.listdir(sdir) if f.endswith('_snippet.wav')]
    out_file = os.path.join(sdir, 'out.wav')
    concat_file = os.path.join(sdir, 'concatenated.wav')
    shutil.copy(snipfiles[0], concat_file)
    _cmd = 'sox {0} {1} {2} gain -n -0.01 splice -q {3},{4}'
    concat_length = sox.file_info.duration(concat_file)
    track_markers = [0, concat_length - CROSSFADE]
    for i, file2 in enumerate(snipfiles[1:]):
        snip_length = sox.file_info.duration(file2)
        track_markers.append(track_markers[i+1] + snip_length - CROSSFADE )
        cmd = _cmd.format(concat_file, file2, out_file, concat_length, CROSSFADE)
        p = Popen(cmd, shell=True, stdout=DEVNULL, stderr=DEVNULL)
        p.wait()
        shutil.move(out_file, concat_file)
        concat_length = sox.file_info.duration(concat_file)
    [os.remove(s) for s in snipfiles]
    q = args[-1]
    q.put(1)
    return (e, concat_length, track_markers[:-1])



def makeParameters(etree_refs):
    for e in etree_refs:
        d = os.path.join('data', e[0])
        if not os.path.exists(d): os.mkdir(d)
    ps = []
    for n in range(DATASETSIZE):
        for e in etree_refs:
            p = Parameters(e)
            os.mkdir(p.dir)
            with open(os.path.join(p.dir, 'parameters.txt'), 'w') as pfile:
                [pfile.write(str(a) + '\n') for a in vars(p).items()] 
            ps.append(p)
    return ps


def mpStart(func, enum, threads=THREADS, args=()):
    global bar
    count.value = 0
    q = manager.Queue()
    args = args + tuple([q])  
    bar = ProgressBar(max_value=len(enum)).start()
    pool = mp.Pool(threads + 1)
    watcher = pool.apply_async(listener, (q,))
    p = pool.map(func, zip(enum, repeat(args)), chunksize=1)
    q.put('kill')
    pool.close()
    pool.join()
    bar.finish()
    return p


def main():
    ref_files = refFiles()
    print('making 1 min snippets')
    mpStart(storeSnippets, ref_files)
    print('concatenating snippets')
    etree_refs = mpStart(concatenateSnippets, REFS)
    #[print(sorted(e[2])) for e in etree_refs]
    parameters = makeParameters(etree_refs)



main()


