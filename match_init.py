import os, json, subprocess
from itertools import product
from shutil import move
import numpy as np
from scipy import stats
from matplotlib import pyplot as plt
import util

matchfeature = 'vamp:match-vamp-plugin:match:a_b'

def extract_match_feature(file, reffile, featuresdir):
    common_path = util.get_common_path(file, reffile)
    featurefile = (file.replace(common_path, '') + '_' + reffile.replace(common_path, '') + '.json')
    featurefile = featuresdir + featurefile.replace('/', '_')
    if not os.path.isfile(featurefile):
        print 'extracting match feature for ..' + file[file.rfind('/')-15:] + ' and ..'+reffile[reffile.rfind('/')-15:]
        with open(os.devnull, 'wb') as devnull:
            subprocess.check_output("sonic-annotator -d vamp:match-vamp-plugin:match:a_b -m " + reffile + " " + file + " -w jams", shell=True, stderr=subprocess.STDOUT)
            move(os.path.splitext(reffile)[0]+'.json', featurefile)
    return featurefile

def loadABTimeline(featurejson):
    abTimes = []
    for row in featurejson["annotations"][0]["data"]:
        abTimes.append([float(row["time"]), float(row["value"])])
    return np.array(abTimes)

def plot_line(line, outfile):
    fig = plt.figure()
    plt.plot(line[:,0], line[:,1])
    fig.patch.set_facecolor('white')
    plt.savefig(outfile, facecolor='white', edgecolor='none')

def plot_line_reg(line, slope, intercept, outfile):
    fig = plt.figure()
    plt.plot(line[:,0], line[:,1])
    plt.plot(line[:,0], slope*line[:,0]+intercept)
    fig.patch.set_facecolor('white')
    plt.savefig(outfile, facecolor='white', edgecolor='none')

def calculate_alignment(file, reffile, featuresdir):
    featurefile = extract_match_feature(file, reffile, featuresdir)
    with open(featurefile) as f:
        featurejson = json.load(f)
    timeline = loadABTimeline(featurejson)
    #plot_line(timeline, featurefile.replace('.json', '.png'))
    cutoff = int(len(timeline)/8)
    slope, intercept, r_value = stats.linregress(timeline[cutoff:-cutoff])[:3]
    rsquared = r_value**2
    #print str(slope)+'x + '+str(intercept), 'r^2: '+str(r_value**2)
    #plot_line_reg(timeline, slope, intercept, featurefile.replace('.json', '.png'))
    filedur = util.get_duration(file)
    refdur = util.get_duration(reffile)
    delta_start = intercept
    delta_end = (filedur*slope+intercept)-refdur
    #print rsquared, [0, refdur], [delta_start, delta_end]
    return [delta_start, delta_end], rsquared

def find_all_matches(audiodir, featuresdir, outfile, maxdirs=None, rrange=2):
    matches = {}
    #load matches if some already exist
    if os.path.isfile(outfile):
        with open(outfile) as f:
            matches = json.load(f)
    dirs = util.get_subdirs(audiodir, maxdirs)
    for r, s in product(dirs, dirs):
        if r != s:
            f = util.get_audiofiles(r)
            g = util.get_audiofiles(s)
            shift = 0
            #go through all adjacent recordings
            for i, j in product(range(len(f)), range(len(g))):
                if abs(i-j-shift) <= rrange:
                    rs, conf = calculate_alignment(f[i], g[j], featuresdir)
                    if conf > 0.999:
                        if f[i] not in matches:
                            matches[f[i]] = {}
                        matches[f[i]][g[j]] = rs, conf
                        shift = i-j
                        #save state
                        with open(outfile, 'w') as fairu:
                            json.dump(matches, fairu)
                        break