import os, subprocess, json
from shutil import move
import numpy as np
from scipy import stats
from matplotlib import pyplot as plt
import matplotlib.patches as patches
import seaborn as sns


matchfeature = 'vamp:match-vamp-plugin:match:a_b'
audiodir = 'audio/'
featuresdir = 'features/'
resultsdir = 'results/'


def create_folder(path):
    if not os.path.exists(path):
        os.makedirs(path)
    return path

def get_flac_filepaths(dir):
    return [dir+'/'+f for f in os.listdir(dir) if f.endswith('.flac')]

def get_duration(file):
    sox_out = subprocess.check_output('sox --i -D ' + file, shell=True)
    return float(sox_out.replace('\n', ''))

def get_total_audio_duration(dir):
    duration = 0
    for file in get_flac_filepaths(dir):
        duration += get_duration(file)
    return duration

def extract_match_feature(file, reffile):
    featurefile = (file.replace(audiodir, '') + '_' + reffile.replace(audiodir, '') + '.json')
    featurefile = featuresdir + featurefile.replace('/', '_')
    if not os.path.isfile(featurefile):
        print 'extracting match feature for ..' + file[file.rfind('/')-15:] + ' and ..'+reffile[reffile.rfind('/')-15:]
        with open(os.devnull, 'wb') as devnull:
            subprocess.check_output("sonic-annotator -d vamp:match-vamp-plugin:match:a_b -m " + reffile + " " + file + " -w jams", shell=True, stderr=subprocess.STDOUT)
            move(reffile[:reffile.rfind('.flac')]+'.json', featurefile)
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

def get_alignment_points(file, reffile):
    featurefile = extract_match_feature(file, reffile)
    with open(featurefile) as f:
        featurejson = json.load(f)
    timeline = loadABTimeline(featurejson)
    #plot_line(timeline, featurefile.replace('.json', '.png'))
    cutoff = int(len(timeline)/8)
    slope, intercept, r_value = stats.linregress(timeline[cutoff:-cutoff])[:3]
    rsquared = r_value**2
    #print str(slope)+'x + '+str(intercept), 'r^2: '+str(r_value**2)
    #plot_line_reg(timeline, slope, intercept, featurefile.replace('.json', '.png'))
    filedur = get_duration(file)
    refdur = get_duration(reffile)
    start = intercept
    end = filedur*slope+intercept
    print rsquared, [0, refdur], [start, end]
    return [start, end], rsquared

def get_ref_timeline(files):
    timeline = []
    current_time = 0
    for file in files:
        current_duration = get_duration(file)
        timeline.append([current_time, current_time+current_duration])
        current_time += current_duration
    return timeline

def plot_timelines(timelines, outfile):
    fig = plt.figure()
    ax = fig.add_subplot(111)
    max = timelines[0][-1][1]
    height = 1.0/(len(timelines))
    for i in range(len(timelines)):
        rects = [patches.Rectangle((point[0]/max, 1-((i+1)*height)), (point[1]/max)-(point[0]/max), height, alpha=0.3) for point in timelines[i]]
        for r in rects:
            ax.add_patch(r)
    fig.patch.set_facecolor('white')
    plt.savefig(outfile, facecolor='white', edgecolor='none')

def plot_heatmap(matrix, outfile):
    f, ax = plt.subplots(figsize=(11, 9))
    
    # Generate a custom diverging colormap
    cmap = sns.diverging_palette(220, 10, as_cmap=True)
    
    # Draw the heatmap with the mask and correct aspect ratio
    g = sns.heatmap(matrix, cmap=cmap, #vmax=matrix.max(),
                #square=True, xticklabels=5, yticklabels=5,#xticklabels=[-5,-4,-3,-2,-1,0,1,2,3,4,5,6,7], yticklabels=[0,1,2,3,4,5,6,7,8,9],
                #linewidths=.5, cbar_kws={"shrink": .5}, ax=ax,
                mask=np.isnan(matrix))
    sns.set_style("dark")
    #g.set(xlabel="segment duration "+r"$2^\sigma$", ylabel="number of segments "+r"$2^\rho$")
    plt.savefig(outfile)

def fast_match(reffiles, otherfiles, search_deltas, reftimeline, keep_bias=False):
    timeline = []
    associations = []
    confidence_matrix = np.empty((len(otherfiles), len(reffiles)))
    confidence_matrix[:] = np.nan
    if keep_bias:
        ref_index = 0
    for i in range(0, len(otherfiles)):
        for d in search_deltas:
            if keep_bias:
                j = ref_index+d
            else:
                j = i+d
            if 0 <= j and j < len(reffiles):
                print i, j, d
                points, rsquared = get_alignment_points(otherfiles[i], reffiles[j])
                if rsquared > 0.99:
                    timeline.append([points[0]+reftimeline[j][0], points[1]+reftimeline[j][0]])
                    associations.append([i,j])
                    confidence_matrix[i][j] = rsquared
                    ref_index = j+1
                    break
    return timeline, associations, confidence_matrix

def best_match(reffiles, otherfiles, search_deltas, reftimeline):
    timeline = []
    associations = []
    confidence_matrix = np.empty((len(otherfiles), len(reffiles)))
    confidence_matrix[:] = np.nan
    for i in range(0, len(otherfiles)):
        results = []
        for d in search_deltas:
            j = i+d
            if 0 <= j and j < len(reffiles):
                print i, j, d
                points, rsquared = get_alignment_points(otherfiles[i], reffiles[j])
                results.append([rsquared, points, j])
                confidence_matrix[i][j] = rsquared
        results.sort()
        best_j = results[-1][2]
        timeline.append([results[-1][1][0]+reftimeline[best_j][0], results[-1][1][1]+reftimeline[best_j][0]])
        associations.append([i,best_j])
    #NOW RESOLVE CONFLICTS!!!!
    return timeline, associations, confidence_matrix

def meta_align(audiodir, outdir):
    dirs = filter(os.path.isdir, [audiodir+f for f in os.listdir(audiodir)])
    durations = map(get_total_audio_duration, dirs)
    ref_index = durations.index(max(durations))
    
    reffiles = get_flac_filepaths(dirs[ref_index])
    reftimeline = get_ref_timeline(reffiles)
    dirs.pop(ref_index)
    
    timelines = [reftimeline]
    associations = []
    
    search_deltas = [0,1,-1,2,-2]
    for dir in dirs:
        currentfiles = get_flac_filepaths(dir)
        timeline, associations, confidence_matrix = best_match(reffiles, currentfiles, search_deltas, reftimeline)
        timelines.append(timeline)
        associations.append(associations)
        plot_heatmap(confidence_matrix, resultsdir+'confidence_'+dir.replace('/','_')+'_best.png')
    
    plot_timelines(timelines, resultsdir+'timelines_best.png')
    print associations
    
    #pyplot some alignments
    
    #first find show with most audio -> becomes reference
    #then align first of each show
    
    #OUTPUT IS A NEW TIMELINE WITH REFERENCES TO EACH OF THE RECORDINGS, e.g.
    #[
        #{time:0, refs:[{rec:'dirname', file:'filename', time:0.1}, {rec:'dirname2', file:'filename2', time:0.5}]},
        #{time:1, refs:[{rec:'dirname', file:'filename', time:1.2}, {rec:'dirname2', file:'filename2', time:1.4}]},
        #...
    #]

meta_align(audiodir, resultsdir)
