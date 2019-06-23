from essentia.standard import *
import sox, os, shutil
from random import random, randint, choice, getrandbits
from subprocess import Popen, DEVNULL, STDOUT
from progressbar import ProgressBar
import multiprocessing as mp
from itertools import repeat
from uuid import uuid4
import soundfile as sf
import numpy as np


REFS = ['gd1982-10-10.sbd.fixed.miller.110784.flac16', 'gd1995-03-18.sbd.miller.97659.flac16']
#REFS = ['gd1982-10-10.sbd.fixed.miller.110784.flac16']

THREADS = int(mp.cpu_count()/2)
manager = mp.Manager()
count = manager.Value('i', 0)
bar = None

SR = 44100
FADE = int(0.1 * SR)
TRIM = 60          # tracks 1 and 10 must be >= TRIM+ADD, tracks 2-9 >= TRIM
ADD = 10
DATASETSIZE = 10


class Parameters(object):
    def __init__(self, ref):
        self.etree = ref[0]
        self.ref_length = ref[1]
        self.ref_trackmarkers = ref[2]
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
        [os.remove(os.path.join(sdir, f)) for f in os.listdir(sdir) if f.endswith('.wav')]
        if os.path.exists('data'): shutil.rmtree('data') 
        os.mkdir('data')
        p = os.path.join(sdir, 'original')
        ref_files += [(i, os.path.join(p, f)) for i, f in enumerate(os.listdir(p)) if f.endswith('.mp3')]
    return ref_files



def mp3toWav(mp3, wav):
    tfm = sox.Transformer()
    tfm.build(mp3, wav)


def inputAudio(es):
    b = mpStart(beatPositions, es)
    edict = {}
    for f in sorted(b):
        if f[0] not in edict: edict[f[0]] = []
        edict[f[0]].append(f[2:])
    elist = []
    [elist.append(edict[e]) for e in edict]
    return elist


def sourceAudio(args):
    return _sourceAudio(*args)

def _sourceAudio(e, args):
    q = args[-1]
    concat = None
    track_markers = None
    for i, f in enumerate(e):
        #fixMp3Header(f[0])
        sdir = '/'.join(f[0].split('/')[:-2])
        fname = f[0].replace('/original/', '/')[:-3] + 'wav'
        flength = f[1]
        fbeats = f[2]
        mp3toWav(f[0], fname)
        audio, sr = sf.read(fname)
        os.remove(fname)
        if i == 0: fbeats = [b for b in fbeats if b > ADD]
        elif i == 9: fbeats = [b for b in fbeats if b < flength - ADD]
        random_start = choice([b for b in fbeats if b < flength - TRIM])
        random_choice = [flength - TRIM] + 2 * [random_start]
        start_beat = choice(random_choice)
        end_beat = findNearest(fbeats, start_beat + TRIM)
        if i == 0:
            addstart = audio[int((start_beat - ADD) * SR):int(start_beat * SR)]
            for pos in range(FADE): addstart[pos] *= np.square(np.sin(pos * 0.5 * np.pi/FADE))
            sf.write(os.path.join(sdir, 'addstart.wav'), addstart, SR)
            concat = audio[int(start_beat * SR):int(end_beat * SR)]
            for pos in range(FADE): concat[pos+len(concat)-FADE] *= np.square(np.cos(pos * 0.5 * np.pi/FADE)) 
            track_markers = [0, (len(concat) - 0.5 * FADE) / SR]
            q.put(1)
            continue
        elif i == 9:
            addend = audio[int(end_beat * SR):int((end_beat + ADD) * SR)]
            for pos in range(FADE): addend[pos+len(addend)-FADE] *= np.square(np.cos(pos * 0.5 * np.pi/FADE)) 
            sf.write(os.path.join(sdir, 'addend.wav'), addend, SR)
            snipaudio = audio[int(start_beat * SR):int(end_beat * SR)]
            for pos in range(FADE): snipaudio[pos] *= np.square(np.sin(pos * 0.5 * np.pi/FADE))
        else:
            snipaudio = audio[int(start_beat * SR):int(end_beat * SR)]
            for pos in range(FADE): snipaudio[pos] *= np.square(np.sin(pos * 0.5 * np.pi/FADE))
            for pos in range(FADE): snipaudio[pos+len(snipaudio)-FADE] *= np.square(np.cos(pos * 0.5 * np.pi/FADE)) 
        for pos in range(FADE):
            concat_pos = pos + len(concat) - FADE
            concat[concat_pos] += snipaudio[pos]
        concat = np.concatenate((concat, snipaudio[FADE:]), axis=0)
        track_markers.append((len(concat) - 0.5 * FADE) / SR)
        q.put(1)
    sf.write(os.path.join(sdir, 'concat.wav'), concat, SR)
    return (sdir.split('/')[1], len(concat) / SR, track_markers[:-1])


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
  

def beatPositions(args):
    return _beatPositions(*args)

def _beatPositions(f, args):
    q = args[-1]
    audio = MonoLoader(filename=f[1])()
    beat_tracker = BeatTrackerMultiFeature()
    beats, confidence = beat_tracker(audio)
    etree = f[1].split('/')[-3]
    q.put(1)
    return (etree, f[0], f[1], len(audio)/44100, list(beats)[::4]) 


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


def mpStart(func, enum, threads=THREADS, args=(), pbar=None):
    global bar
    if not pbar: pbar = len(enum)
    count.value = 0
    q = manager.Queue()
    args = args + tuple([q])  
    bar = ProgressBar(max_value=pbar).start()
    pool = mp.Pool(threads + 1)
    watcher = pool.apply_async(listener, (q,))
    p = pool.map(func, zip(enum, repeat(args)), chunksize=1)
    q.put('kill')
    pool.close()
    pool.join()
    bar.finish()
    return p


def main():
    print('analysing input audio')
    ref_files = refFiles()
    input_audio = inputAudio(ref_files)
    print('creating source audio')
    source_audio = mpStart(sourceAudio, input_audio, pbar=len(input_audio * 10))
    print('creating test audio')
    parameters = makeParameters(source_audio)



main()


