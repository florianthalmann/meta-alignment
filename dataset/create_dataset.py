
import multiprocessing as mp
import sox, os, shutil
from progressbar import ProgressBar
from itertools import repeat
import soundfile as sf
import numpy as np
from testparameters import test_parameters, test_parameters_pickle

THREADS = int(mp.cpu_count()/2)
manager = mp.Manager()
count = manager.Value('i', 0)
SR = 44100


class gl():
    bar = None
    concat= None
    addstart = None
    addend = None
    crowd = None


def makeData(args):
    _makeData(*args)

def _makeData(p, args):
    os.mkdir(p.dir)
    with open(os.path.join(p.dir, 'parameters.txt'), 'w') as pfile:
        [pfile.write(str(a) + '\n') for a in vars(p).items()]
    unsplit = np.copy(gl.concat)
    unsplit, segments, length = addAudio(unsplit, p)
    unsplit = addCrowd(unsplit, p, length)
    unsplit = bleedAudio(unsplit, p)
    unsplit = reverbSpeedEq(unsplit, p)
    segments = segmentAudio(unsplit, p)
    writeAudio(segments, p)
    args[-1].put(1)


def addAudio(a, p):
    if not p.add: return a, p.segments, p.ref_length
    length = p.ref_length
    if p.add in ('start', 'both'):
        p.segments[0][1] += 20
        length += 20
        for i in range(len(p.segments[1:])):
            i += 1 
            for j in range(2): p.segments[i][j] += 20
        a = np.concatenate((gl.addstart, a), axis=0)
    if p.add in ('end', 'both'):
        p.segments[-1][1] += 20
        length += 20
        a = np.concatenate((a, gl.addend), axis=0)
    return a, p.segments, length


def addCrowd(a, p, l):
    if p.crowd == 0: return a
    l = int(round(l * SR))
    a = p.crowd * gl.crowd[:l] + (1 - p.crowd) * a
    return a


def bleedAudio(a, p):
    if p.bleed == 0: return a
    l = p.bleed * a[:,1] + a[:,0]
    r = p.bleed * a[:,0] + a[:,1]
    return np.column_stack((l, r)) / (1 + p.bleed)


def reverbSpeedEq(a, p):
    if not p.reverb and p.speed == 1 and not p.equaliser: return a
    tfm = sox.Transformer()
    if p.reverb:
        tfm.gain(gain_db=-1)
        tfm.reverb(reverberance=p.reverb[0], pre_delay=p.reverb[1], wet_gain=p.reverb[2])
    if p.speed != 1:
        tfm.speed(p.speed)
        tfm.rate(44100, quality= "v")
    if p.equaliser:
        for s in p.equaliser[1:-1]:
            tfm.equalizer(s[0], s[1], s[2])
        tfm.bass(p.equaliser[0][0], p.equaliser[0][1], p.equaliser[0][2])
        tfm.treble(p.equaliser[-1][0], p.equaliser[-1][1], p.equaliser[-1][2])
    temp_in = os.path.join(p.dir, 'temp_in.wav')
    temp_out = os.path.join(p.dir, 'temp_out.wav')
    sf.write(temp_in, a, SR)
    tfm.build(temp_in, temp_out)
    a, sr = sf.read(temp_out)
    os.remove(temp_in)
    os.remove(temp_out)
    return a


def segmentAudio(a, p):
    markers = np.array(p.segments)
    if p.speed != 1: markers /= p.speed
    markers = np.round(markers * SR).astype(int)
    segments = []
    for m in markers: 
        segments.append(a[m[0]:m[1]])
    return segments


def writeAudio(segments, p):
    for i, s in enumerate(segments):
        sf.write('{0}/{1}.wav'.format(p.dir, i+1), s, SR)


def makeDataStart(params):
    total = len(params)
    c = 0
    gl.crowd, sr = sf.read('crowd_10m40s.flac')
    for e, ps in params.items():
        c += 1
        print('{0}/{1}'.format(c, total), e)
        d = os.path.join('data', e)
        if not os.path.exists(d): os.mkdir(d)
        gl.concat, sr = sf.read(os.path.join('source', e, 'concat.wav'))
        gl.addstart, sr = sf.read(os.path.join('source', e, 'addstart.wav'))
        gl.addend, sr = sf.read(os.path.join('source', e, 'addend.wav'))
        mpStart(makeData, ps)


def listener(q):
    while 1:
        g = q.get()
        if g == 'kill': break
        elif g == 1:
            count.value += 1
            gl.bar.update(count.value)


def mpStart(func, enum, threads=THREADS, args=(), pbar=None):
    if not pbar: pbar = len(enum)
    count.value = 0
    q = manager.Queue()
    args = args + (q,)
    gl.bar = ProgressBar(max_value=pbar).start()
    pool = mp.Pool(threads + 1)
    watcher = pool.apply_async(listener, (q,))
    p = pool.map(func, zip(enum, repeat(args)), chunksize=1)
    q.put('kill')
    pool.close()
    pool.join()
    gl.bar.finish()
    return p


def main():
    if os.path.exists('data'): shutil.rmtree('data')
    os.mkdir('data')
    parameters = test_parameters()
    parameters = test_parameters_pickle()
    makeDataStart(parameters)
    


main()