import os, json
from itertools import product
import numpy as np
from scipy import stats
from scipy.sparse.csgraph import minimum_spanning_tree, floyd_warshall
from matplotlib import pyplot as plt
import matplotlib.patches as patches
import seaborn as sns
import match_aligner
import hough_aligner
import fprint_aligner
import panako_aligner
import util

audiodir = 'audio/'
aligner = match_aligner
aligner_name = 'match'
resultsdir = 'results_'+aligner_name+'/'

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
                mask=np.isnan(matrix), center=0)
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
    dirs = util.get_subdirs(audiodir)
    durations = map(util.get_total_audio_duration, dirs)
    ref_index = durations.index(max(durations))

    reffiles = util.get_audiofiles(dirs[ref_index])
    reftimeline = util.get_ref_timeline(reffiles)
    dirs.pop(ref_index)

    timelines = [reftimeline]
    results = {}
    results['associations'] = []

    search_deltas = [0,1,-1,2,-2]
    for dir in dirs:
        currentfiles = util.get_audiofiles(dir)
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

#pass in list of recordings, which in turn are lists of segments
#and rrange the range in which segments are compared, e.g. 2 = [-2,-1,0,1,2]
def get_offset_matrix(recordings, rrange, aligner):
    segments = [seg for rec in recordings for seg in rec]
    offsets = np.full((len(segments), len(segments)), np.nan)
    confidences = np.full((len(segments), len(segments)), np.nan)
    #go through all unequal pairs of recordings
    for r, s in product(recordings, recordings):
        if r != s:
            #go through all adjacent recordings
            for i, j in product(range(len(r)), range(len(s))):
                if abs(i-j) <= rrange:
                    ii, jj = segments.index(r[i]), segments.index(s[j])
                    rs, confidences[ii,jj] = aligner.get_alignment_points(r[i], s[j])
                    if rs is not None:
                        offsets[ii,jj] = rs[0]
    return offsets

def add_to_histogram(value, histogram):
    if not np.isnan(value):
        if value not in histogram:
            histogram[value] = 1
        else:
            histogram[value] += 1

def validate_offsets_histo(offsets):
    #algorithm from bano2015discovery, casanovas2015audio
    rounded = np.round(offsets)
    validated = np.zeros(offsets.shape)
    for i, j in product(range(len(offsets)), range(len(offsets))):
        if i != j:
            histogram = {}
            for k in range(len(offsets)):
                add_to_histogram(rounded[i][k] + rounded[k][j], histogram)
                add_to_histogram(-1*(rounded[j][k] + rounded[k][i]), histogram)
            if len(histogram) > 0:
                validated[i][j] = max(histogram, key=histogram.get)
            else:
                validated[i][j] = np.nan
    return validated

def validate_offsets_mst(offsets):
    #algorithm from kammerl2014temporal
    penalty = lambda i,j,k: abs(offsets[i][j]+offsets[j][k]+offsets[k][i])
    #calculate edge consistencies
    consistencies = np.zeros(offsets.shape)
    for i, j in product(range(len(offsets)), range(len(offsets))):
        penalties = [penalty(i,j,k) for k in range(len(offsets))]
        penalties = [p for p in penalties if not np.isnan(p)]
        if len(penalties) > 0:
            consistencies[i,j] = sum(penalties)
    #calculate minimum spanning tree
    mst = minimum_spanning_tree(consistencies)#.toarray()
    trans_closure = floyd_warshall(mst)
    #TODO this can be lowered to get rid of misalignments! e.g. > 200 works well
    trans_closure[trans_closure >= np.inf] = np.nan
    #this issues a warning due to np.nan, but it works well!
    trans_closure = np.fmin(trans_closure, -1*np.transpose(trans_closure))
    return trans_closure

def meta_align_construct_timeline_iterative(audiodir, outdir):
    dirs = util.get_subdirs(audiodir)

    current_index = 0
    current_files = []

    for i in range(2):#while len(currentfiles) > 0:
        for d in dirs:
            current_files.append(util.get_audiofiles(d)[current_index])
        offset_matrix = get_offset_matrix(current_files)
        #set diagonal to 0!
        print np.matrix(offset_matrix)
        #offset_matrix = validate_offsets(offset_matrix)
        #print offset_matrix
        current_index += 1

def construct_timelines(offset_matrix, dirs, recordings):
    segments = [seg for rec in recordings for seg in rec]
    timelines = [[]]
    t = 0
    #take first as ref timeline
    for f in util.get_audiofiles(dirs[0]):
        dur = util.get_duration(f)
        timelines[0].append([t, t+dur])
        t += dur
    #go through all others and compare to first TODO GENERALIZE
    for d in range(1, len(dirs)):
        timeline = []
        for f in recordings[d]:
            i = segments.index(f)
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
            else:
                timeline.append(None)
        timelines.append(timeline)
    return timelines

def show_asymmetry(matrix):
    return np.add(matrix, np.transpose(matrix))

def construct_and_plot(offset_matrix, name, dirs, recordings):
    plot_heatmap(offset_matrix, resultsdir+'offsets_'+aligner_name+'_'+name+'.png')
    #plot_heatmap(show_asymmetry(offset_matrix), resultsdir+'offsets_raw2as.png')
    timelines = construct_timelines(offset_matrix, dirs, recordings)
    plot_timelines(timelines, resultsdir+'timelines_'+aligner_name+'_'+name+'.png')
    return timelines

def meta_align_construct_timeline(audiodir, outdir, aligner):
    dirs = util.get_subdirs(audiodir)
    recordings = [util.get_audiofiles(d) for d in dirs]

    offset_matrix = get_offset_matrix(recordings, 2, aligner)
    construct_and_plot(offset_matrix, 'raw', dirs, recordings)

    mst_matrix = validate_offsets_mst(offset_matrix)
    construct_and_plot(mst_matrix, 'mst', dirs, recordings)

    histo_matrix = validate_offsets_histo(offset_matrix)
    construct_and_plot(histo_matrix, 'histo', dirs, recordings)

def get_validated_timelines(audiodir, aligner, maxdirs=None):
    dirs = util.get_subdirs(audiodir, maxdirs)
    recordings = [util.get_audiofiles(d) for d in dirs]
    offset_matrix = get_offset_matrix(recordings, 2, aligner)
    #mst_matrix = validate_offsets_mst(offset_matrix)
    #print offset_matrix, mst_matrix
    return construct_timelines(offset_matrix, dirs, recordings)

def get_deviations(alignment, groundtruth):
    deviations = []
    for a, g in zip(alignment, groundtruth):
        for s1, s2 in zip(a, g):
            if s1 and s2:
                deviations.append(abs(s1[0]-s2[0]))
            else:
                deviations.append(None)
    return deviations

#returns the total deviation for each element of the given alignment list
def get_deviation_sums(alignment, groundtruth):
    deviations = []
    for a, g in zip(alignment, groundtruth):
        dev = 0
        for s1, s2 in zip(a, g):
            if s1 and s2:
                dev += abs(s1[0]-s2[0])
        deviations.append(dev)
    return deviations

#tolerance in secs, for now just beginnings TODO also evaluate segment ends
#TODO ALSO EVAL MISSING SEGMENTS (PENALTY?)
def evaluate_alignment(alignment, groundtruth, tolerance=0.5):
    aligned = float(sum([len(rec) for rec in alignment]))
    total = float(sum([len(rec) for rec in groundtruth]))
    deviations = get_deviations(alignment, groundtruth)
    total_deviation = sum([d for d in deviations if d]) #ignore None
    correct = sum(1 for d in deviations if d < tolerance)
    print "aligned:", aligned / total, "correct:", correct / total, "deviation:",  total_deviation
    return aligned / total, correct / total, total_deviation

def plot_evaluation_graph(alignment, groundtruth, outfile):
    deviations = get_deviation_sums(alignment, groundtruth)
    fig = plt.figure()
    plt.plot(deviations)
    plt.savefig(outfile, facecolor='white', edgecolor='none')

def plot_linreg(param_name, param_values, alignment, groundtruth, outfile):
    x = np.array(param_values)
    deviations = get_deviation_sums(alignment, groundtruth)
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, deviations)
    fig = plt.figure()
    plt.xlabel(param_name)
    plt.ylabel('total deviation')
    plt.plot(x, deviations, 'o')
    plt.plot(x, intercept + slope*x, 'r', label='fitted line')
    plt.savefig(outfile, facecolor='white', edgecolor='none')

def test_eval():
    dirs = util.get_subdirs(audiodir)
    recordings = [util.get_audiofiles(d) for d in dirs]

    #mock groundtruth for now
    print "groundtruth"
    match = get_offset_matrix(recordings, 2, fprint_aligner)
    groundtruth = construct_timelines(match, dirs, recordings)
    print "aligning"
    fprint = get_offset_matrix(recordings, 2, panako_aligner)
    print "constructing"
    alignment = construct_timelines(fprint, dirs, recordings)

    evaluate_alignment(alignment, groundtruth)

#meta_align_construct_timeline(audiodir, resultsdir, audfprint_aligner)
#test_eval()
