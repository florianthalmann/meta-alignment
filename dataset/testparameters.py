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
import pickle


REFS = [d for d in os.listdir('source') if os.path.isdir(os.path.join('source', d))]
#REFS = ['gd1982-10-10.sbd.fixed.miller.110784.flac16']

THREADS = int(mp.cpu_count()/2)
manager = mp.Manager()
count = manager.Value('i', 0)
bar = None

SR = 44100
FADE = int(0.1 * SR)
TRIM = 60           # tracks 1 and 10 must be >= TRIM+ADD, tracks 2-9 >= TRIM
ADD = 20            # up to 20s can be prepended/appended to test audio
DATASETSIZE = 100    # per etree
MARKER_DEVIATION = 10


class Parameters(object):
    def __init__(self, ref):
        self.etree = ref[0]
        self.ref_length = ref[1]
        self.ref_trackmarkers = ref[2]
        self.dir = os.path.join('data', ref[0], str(uuid4()).replace('-', ''))
        # generate random parameters
        self.speed = choice([1] + 2 * [randint(90, 110) * 0.01])
        self.equaliser = bool(choice(4 * [1] + [0]))                    # chance no EQ 1:4
        #self.crowd = round(choice([0] + 2 * [randint(2, 8) * 0.1]), 1)  # chance no crowd 1:3
        self.crowd = round(0.01 * choice(range(0, 30, 5)), 2)
        self.bleed = round(random() * 0.5, 1)
        self.reverb = bool(getrandbits(1))
        self.add = choice([None, 'start', 'end', 'both'])
        self.split_tracks = randint(0, 2)
        self.join_tracks = randint(0, 2)
        self.remove_tracks = randint(0, 2)
        self.reverberation()
        self.eq()
        self.segments()
        
    def reverberation(self):
        if self.reverb == True:
            reverberance = randint(50, 75)
            pre_delay = randint(5, 10)
            wet_gain = round(randint(-10, 10) * 0.1, 1)
            self.reverb = (reverberance, pre_delay, wet_gain)
        
    def eq(self):
        if self.equaliser == True:
            equaliser = []
            # low shelf
            gain = randint(-6, -1)
            f = randint(3, 10) * 10
            slope = randint(1,5) * 0.1
            equaliser.append((gain, f, slope))
            # EQ
            for m in range(4):
                centre = randint(1, 50) * 100
                bandwidth = round(0.1 * randint(2, 5), 1)
                gain = randint(-6, -1)
                equaliser.append((centre, bandwidth, gain))
                #print((centre, bandwidth, gain))
            # high shelf
            gain = randint(-6, -1)
            f = randint(100, 150) * 100
            slope = randint(1,5) * 0.1
            equaliser.append((gain, f, slope))
            self.equaliser = equaliser

    def segments(self):
        markers = []
        if self.add in ('start', 'both'): markers.append(0)   # if add audio at start set first start to 0
        else: markers.append(MARKER_DEVIATION * random())
        for i, m in enumerate(self.ref_trackmarkers[1:]): 
            markers.append(2 * MARKER_DEVIATION * (random() - 0.5) + m)
        if self.add in ('end', 'both'): markers.append(self.ref_length)  # if add audio at end set last marker end to ref_length 
        else: markers.append(self.ref_length - MARKER_DEVIATION * random())

        # join tracks
        join_indices = [i for i in range(10)]    # track indices valid for joining with next track
        split_indices = join_indices.copy()      # track indices valid for splitting
        _markers = markers[1:]
        remove_is = []
        for n in range(self.join_tracks):
            remove_i = choice(join_indices)
            join_indices.remove(remove_i)
            remove_is.append(remove_i)
            remove_m = _markers[remove_i]
            markers.remove(remove_m)
            if remove_i + 1 in join_indices: join_indices.remove(remove_i + 1)
            if remove_i - 1 in join_indices: join_indices.remove(remove_i - 1)
            if remove_i + 1 in split_indices: split_indices.remove(remove_i + 1)
            split_indices.remove(remove_i)

        # split tracks
        for r in sorted(remove_is):
            for i, v in enumerate(split_indices):
                if split_indices[i] > r: split_indices[i] -= 1
        split_is = []
        for n in range(self.split_tracks):
            split_i = choice(split_indices)
            split_is.append(split_i)
            split_indices.remove(split_i)
        _segments = []
        [_segments.append([markers[i], markers[i+1]]) for i in range(len(markers[:-1]))]
        segments = []
        for i, s in enumerate(_segments):
            if i in split_is:
                middle = s[0] + 0.5 * (s[1] - s[0])
                insert_segment = [s[0], middle]
                segments.append(insert_segment)
                s[0] = middle
            segments.append(s)

        # remove tracks:
        remove_indices = split_indices
        for s in sorted(split_is):
            for i, v in enumerate(remove_indices):
                if remove_indices[i] > s: remove_indices[i] += 1
        remove_is = []
        for n in range(self.remove_tracks):
            remove_i = choice(remove_indices)
            remove_is.append(remove_i)
            remove_indices.remove(remove_i)
        _segments = []
        for i, s in enumerate(segments):
            if i not in remove_is: _segments.append(s)

        self.segments = _segments
              

def refFiles():
    if os.path.exists('data'): shutil.rmtree('data') 
    os.mkdir('data')
    ref_files = []
    for e in REFS:
        sdir = os.path.join('source', e)
        [os.remove(os.path.join(sdir, f)) for f in os.listdir(sdir) if f.endswith('.wav')]
        if os.path.isfile(os.path.join(sdir, 'markers.txt')): os.remove(os.path.join(sdir, 'markers.txt'))
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
        fixMp3Header(f[0])
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
            addstart = fadeIn(addstart)
            sf.write(os.path.join(sdir, 'addstart.wav'), addstart, SR)
            concat = audio[int(start_beat * SR):int(end_beat * SR)]
            concat = fadeOut(concat)
            track_markers = [0, (len(concat) - 0.5 * FADE) / SR]
            q.put(1)
            continue
        elif i == 9:
            addend = audio[int(end_beat * SR):int((end_beat + ADD) * SR)]
            addend = fadeOut(addend)
            sf.write(os.path.join(sdir, 'addend.wav'), addend, SR)
            snipaudio = audio[int(start_beat * SR):int(end_beat * SR)]
            snipaudio = fadeIn(snipaudio)
        else:
            snipaudio = audio[int(start_beat * SR):int(end_beat * SR)]
            snipaudio = fadeIn(snipaudio)
            snipaudio = fadeOut(snipaudio)
        for pos in range(FADE):
            concat_pos = pos + len(concat) - FADE
            concat[concat_pos] += snipaudio[pos]
        concat = np.concatenate((concat, snipaudio[FADE:]), axis=0)
        track_markers.append((len(concat) - 0.5 * FADE) / SR)
        q.put(1)
    sf.write(os.path.join(sdir, 'concat.wav'), concat, SR)
    etree = sdir.split('/')[1]
    with open(os.path.join(sdir, 'markers.txt'), 'w') as mfile:
        mfile.write(etree + '\n')
        mfile.write(str(track_markers) + '\n')
    return (etree, len(concat) / SR, track_markers[:-1])


def fadeIn(a):
    for pos in range(FADE): a[pos] *= np.square(np.sin(pos * 0.5 * np.pi/FADE))
    return a


def fadeOut(a):
    for pos in range(FADE): a[pos+len(a)-FADE] *= np.square(np.cos(pos * 0.5 * np.pi/FADE))
    return a


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
        if g == 'kill': break
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
    #for e in etree_refs:
        #d = os.path.join('data', e[0])
        #if not os.path.exists(d): os.mkdir(d)
    ps = { e[0]: [] for e in etree_refs}
    for n in range(DATASETSIZE):
        for e in etree_refs:
            p = Parameters(e)
            #os.mkdir(p.dir)
            #with open(os.path.join(p.dir, 'parameters.txt'), 'w') as pfile:
                #[pfile.write(str(a) + '\n') for a in vars(p).items()] 
            ps[e[0]].append(p)
    return ps


def mpStart(func, enum, threads=THREADS, args=(), pbar=None):
    global bar
    if not pbar: pbar = len(enum)
    count.value = 0
    q = manager.Queue()
    args = args + (q,)
    bar = ProgressBar(max_value=pbar).start()
    pool = mp.Pool(threads + 1)
    watcher = pool.apply_async(listener, (q,))
    p = pool.map(func, zip(enum, repeat(args)), chunksize=1)
    q.put('kill')
    pool.close()
    pool.join()
    bar.finish()
    return p


def test_parameters():
    print('analysing input audio')
    ref_files = refFiles()
    input_audio = inputAudio(ref_files)
    print('creating source audio')
    source_audio = mpStart(sourceAudio, input_audio, pbar=len(input_audio * 10))
    #pickle.dump(source_audio, open('source_audio.pickle', 'wb'))
    print('creating test audio')
    parameters = makeParameters(source_audio)
    return parameters


#-------------------

def test_parameters_pickle():
    if os.path.exists('data'): shutil.rmtree('data')
    os.mkdir('data')
    source_audio = pickle.load(open('source_audio.pickle', 'rb'))
    parameters = makeParameters(source_audio)
    return parameters

#test_parameters()
#test_parameters_pickle()


