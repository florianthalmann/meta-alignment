import os, json, itertools
import numpy as np
from matplotlib import pyplot as plt
import matplotlib.patches as patches
import seaborn as sns
import match_aligner
import hough_aligner
import fprint_aligner
import util

audiodir = 'audio/'
resultsdir = 'results_fprint/'
aligner = fprint_aligner

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
    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.set_facecolor('white')

    # Generate a custom diverging colormap
    cmap = sns.diverging_palette(220, 10, as_cmap=True)

    # Draw the heatmap with the mask and correct aspect ratio
    g = sns.heatmap(matrix, cmap=cmap, #vmax=matrix.max(),
                #square=True, xticklabels=5, yticklabels=5,#xticklabels=[-5,-4,-3,-2,-1,0,1,2,3,4,5,6,7], yticklabels=[0,1,2,3,4,5,6,7,8,9],
                #linewidths=.5, cbar_kws={"shrink": .5}, ax=ax,
                mask=np.isnan(matrix))
    #sns.set_style("dark")
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
                points, rsquared = aligner.get_alignment_points(otherfiles[i], reffiles[j])
                if rsquared > 0.99:
                    timeline.append([points[0]+reftimeline[j][0], points[1]+reftimeline[j][1]])
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
                points, rsquared = aligner.get_alignment_points(otherfiles[i], reffiles[j])
                results.append([rsquared, points, j])
                confidence_matrix[i][j] = rsquared
        results.sort()
        best_j = results[-1][-1]
        timeline.append([results[-1][1][0]+reftimeline[best_j][0], results[-1][1][1]+reftimeline[best_j][1]])
        associations.append([i,best_j])
    return timeline, associations, confidence_matrix

def best_match_symm(reffiles, otherfiles, search_deltas, reftimeline):
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
                points, rsquared = aligner.get_alignment_points(otherfiles[i], reffiles[j])
                points2, rsquared2 = aligner.get_alignment_points(reffiles[j], otherfiles[i])
                rating = rsquared*rsquared2
                results.append([rating, rsquared, points, rsquared2, points2, j])
                confidence_matrix[i][j] = rating
        results.sort()
        best_j = results[-1][-1]
        if results[-1][2] and results[-1][4]:
            avg_delta_start = (results[-1][2][0]-results[-1][4][0])/2
            avg_delta_end = (results[-1][2][1]-results[-1][4][1])/2
        if results[-1][0] > 0.000001:#0.999:
            timeline.append([avg_delta_end+reftimeline[best_j][0], avg_delta_end+reftimeline[best_j][1]])
            print "RESULTING TIMEPOINTS: ", timeline[-1], results[-1][0]
            associations.append([True, best_j, results[-1][0]])
        else:
            print "NO ASSOC GOOD ENOUGH", results[-1][0]
            associations.append([False, best_j, results[-1][0]])
    return timeline, associations, confidence_matrix

def meta_align(audiodir, outdir):
    dirs = filter(os.path.isdir, [audiodir+f for f in os.listdir(audiodir)])
    durations = map(util.get_total_audio_duration, dirs)
    ref_index = durations.index(max(durations))

    reffiles = util.get_flac_filepaths(dirs[ref_index])
    reftimeline = util.get_ref_timeline(reffiles)
    dirs.pop(ref_index)

    timelines = [reftimeline]
    results = {}
    results['associations'] = []

    search_deltas = [0,1,-1,2,-2]
    for dir in dirs:
        currentfiles = util.get_flac_filepaths(dir)
        timeline, associations, confidence_matrix = best_match_symm(reffiles, currentfiles, search_deltas, reftimeline)
        timelines.append(timeline)
        results['associations'].append(associations)
        plot_heatmap(confidence_matrix, resultsdir+'confidence_'+dir.replace('/','_')+'_best_symm.png')

    plot_timelines(timelines, resultsdir+'timelines_best_symm.png')
    #results['timelines'] = timelines
    with open(resultsdir+'results_best_symm.json', 'w') as resultsfile:
        json.dump(results, resultsfile)

    #pyplot some alignments

    #first find show with most audio -> becomes reference
    #then align first of each show

    #OUTPUT IS A NEW TIMELINE WITH REFERENCES TO EACH OF THE RECORDINGS, e.g.
    #[
        #{time:0, refs:[{rec:'dirname', file:'filename', time:0.1}, {rec:'dirname2', file:'filename2', time:0.5}]},
        #{time:1, refs:[{rec:'dirname', file:'filename', time:1.2}, {rec:'dirname2', file:'filename2', time:1.4}]},
        #...
    #]

def get_offset_matrix(files):
    fr = range(len(files))
    results = [[0 for _ in fr] for _ in fr]
    confs = [[0 for _ in fr] for _ in fr]
    for i, j in itertools.product(fr, fr):
        results[i][j], confs[i][j] = aligner.get_alignment_points(files[i], files[j])
    return np.vectorize(lambda r: r[0] if r is not None else None)(results)

def add_to_histogram(value, histogram):
    if not np.isnan(value):
        if value not in histogram:
            histogram[value] = 1
        else:
            histogram[value] += 1

def validate_offsets(offsets):
    #algorithm from bano2015discovery, casanovas2015audio
    rounded = np.round(offsets)
    validated = np.zeros(offsets.shape)
    for i, j in itertools.product(range(len(offsets)), range(len(offsets))):
        histogram = {}
        for k in range(len(offsets)):
            add_to_histogram(rounded[i][k] + rounded[k][j], histogram)
            add_to_histogram(-1*(rounded[j][k] + rounded[k][i]), histogram)
        if len(histogram) > 0:
            validated[i][j] = max(histogram, key=histogram.get)
        else:
            validated[i][j] = np.nan
    return validated

def meta_align_construct_timeline_iterative(audiodir, outdir):
    dirs = filter(os.path.isdir, [audiodir+f for f in os.listdir(audiodir)])

    current_index = 0
    current_files = []

    for i in range(2):#while len(currentfiles) > 0:
        for d in dirs:
            current_files.append(util.get_flac_filepaths(d)[current_index])
        offset_matrix = get_offset_matrix(current_files)
        #set diagonal to 0!
        print np.matrix(offset_matrix)
        #offset_matrix = validate_offsets(offset_matrix)
        #print offset_matrix
        current_index += 1

def construct_timelines(offset_matrix, dirs, files):
    timelines = [[]]
    t = 0
    for f in util.get_flac_filepaths(dirs[0]):
        dur = util.get_duration(f)
        timelines[0].append([t, t+dur])
        t += dur
    for d in range(1, len(dirs)):
        fs = util.get_flac_filepaths(dirs[d])
        timeline = []
        for f in fs:
            i = files.index(f)
            offsets = offset_matrix[i]
            oe = enumerate(offsets)
            ref_index = next((j for j, o in oe if j != i and not np.isnan(o)), None)
            #TODO add way of dealing with ref_index not in first rec
            #TODO anyway, really construct timeline now!!
            if ref_index and ref_index < len(timelines[0]):
                #print i, ref_index, offsets[ref_index]
                ref = timelines[0][ref_index]
                offset = ref[0]+offsets[ref_index]
                timeline.append([offset, offset+util.get_duration(f)])
        timelines.append(timeline)
    return timelines

def meta_align_construct_timeline(audiodir, outdir):
    dirs = filter(os.path.isdir, [audiodir+f for f in os.listdir(audiodir)])
    files = [f for d in dirs for f in util.get_flac_filepaths(d)]

    offset_matrix = get_offset_matrix(files)
    plot_heatmap(offset_matrix, resultsdir+'offsets_raw.png')
    timelines = construct_timelines(offset_matrix, dirs, files)
    plot_timelines(timelines, resultsdir+'timelines_fprint_raw.png')

    offset_matrix = validate_offsets(offset_matrix)
    plot_heatmap(offset_matrix, resultsdir+'offsets_val.png')
    timelines = construct_timelines(offset_matrix, dirs, files)
    plot_timelines(timelines, resultsdir+'timelines_fprint_val.png')


meta_align_construct_timeline(audiodir, resultsdir)
