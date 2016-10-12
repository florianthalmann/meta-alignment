import os, subprocess, json
from shutil import move
import numpy as np
from scipy import stats
from matplotlib import pyplot as plt
import matplotlib.patches as patches


matchfeature = 'vamp:match-vamp-plugin:match:a_b'
audiodir = 'audio-light/'
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
        print 'extracting match feature for ' + file.replace(audiodir, '')
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
    cutoff = int(len(timeline)/4)
    slope, intercept, r_value = stats.linregress(timeline[cutoff:-cutoff])[:3]
    rsquared = r_value**2
    #print str(slope)+'x + '+str(intercept), 'r^2: '+str(r_value**2)
    plot_line_reg(timeline, slope, intercept, featurefile.replace('.json', '.png'))
    if rsquared > 0.98:
        filedur = get_duration(file)
        refdur = get_duration(reffile)
        start = intercept
        end = filedur*slope+intercept
        print rsquared, [0, refdur], [start, end]
        return [start, end]
    else:
        print rsquared

def get_ref_timeline(files):
    timeline = []
    current_time = 0
    for file in files:
        current_duration = get_duration(file)
        timeline.append([current_time, current_time+current_duration])
        current_time += current_duration
    return timeline

def plot_timelines(timelines):
    fig = plt.figure()
    ax = fig.add_subplot(111)
    max = timelines[0][-1][1]
    height = 1.0/(len(timelines)+1)
    for i in range(len(timelines)):
        rects = [patches.Rectangle((point[0]/max, 1-((i+1)*height)), point[1]/max, height, alpha=0.3) for point in timelines[i]]
        for r in rects:
            ax.add_patch(r)
    fig.patch.set_facecolor('white')
    plt.savefig(resultsdir+'timelines.png', facecolor='white', edgecolor='none')

def meta_align(audiodir, outdir):
    dirs = filter(os.path.isdir, [audiodir+f for f in os.listdir(audiodir)])
    durations = map(get_total_audio_duration, dirs)
    ref_index = durations.index(max(durations))
    
    reffiles = get_flac_filepaths(dirs[ref_index])
    reftimeline = get_ref_timeline(reffiles)
    
    dirs.pop(ref_index)
    
    #get_alignment_points(get_flac_filepaths(dirs[0])[0], reffiles[0])
    
    timelines = [reftimeline]
    
    for dir in dirs:
        currentfiles = get_flac_filepaths(dir)
        current_timeline = []
        ref_index = 0
        for i in range(0, len(currentfiles)):
            if ref_index < len(reffiles):
                points = get_alignment_points(currentfiles[i], reffiles[ref_index])
                if points is not None:
                    current_ref = reftimeline[ref_index]
                    current_timeline.append([points[0]+current_ref[0], points[1]+current_ref[0]])
                ref_index += 1
        print current_timeline
        timelines.append(current_timeline)
    
    plot_timelines(timelines)
    
    #get_alignment_points(files[0], reffiles[0])
    #get_alignment_points(reffiles[0], files[0])
    #get_alignment_points(files[1], reffiles[1])
    #get_alignment_points(reffiles[1], files[1])
    
    #plot_example_alignments(files[0], reffiles[0], resultsdir+'match00.json', resultsdir+'match00.png')
    #plot_example_alignments(files[1], reffiles[0], resultsdir+'match10.json', resultsdir+'match10.png')
    #plot_example_alignments(files[0], reffiles[1], resultsdir+'match01.json', resultsdir+'match01.png')
    #plot_example_alignments(files[1], reffiles[1], resultsdir+'match11.json', resultsdir+'match11.png')
    
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

#create alignment features and tune wavs
def align_and_tune(self):
    extract_features(self.original_audio_folder, self.original_features_folder, [features[0]], "jams")
    tune_wavs(self.original_audio_folder, self.tuned_audio_folder, self.original_features_folder)
    #normalize_audio(self.tuned_audio_folder)

#recreate alignment features for tuned wavs, separate channels and extract features for separate channels
def realign_and_separate_and_analyze(self):
    extract_features(self.tuned_audio_folder, self.tuned_features_folder, [features[0]], "jams")
    separate_channels(self.tuned_audio_folder, self.channels_audio_folder)
    copy_features_of_separated_channels(self.tuned_features_folder, self.channels_features_folder)
    extract_features(self.channels_audio_folder, self.channels_features_folder, features[1:], "jams")

def create_clustering_and_plots(self):
    ClusterPlotter().saveSegmentAnalysisAndPlots("mfcc", self.channels_features_folder, self.results_folder)
    ClusterPlotter().saveSegmentAnalysisAndPlots("chroma", self.channels_features_folder, self.results_folder)

def recursively_analyze_the_shit_out_of_this(self, basefolder, subfolder, outfolder):
    files = os.listdir(basefolder+subfolder)
    
    if any(f.endswith('.wav') for f in files):
        #analyze current folder
        self.create_current_folders(basefolder, subfolder, outfolder)
        #if len(os.listdir(self.channels_audio_folder)) <= 1:
            #self.align_and_tune()
        #self.realign_and_separate_and_analyze()
        self.create_clustering_and_plots()
    
    #recursively go through all subfolders
    for file in files:
        if os.path.isdir(basefolder+subfolder+file):
            print "\n WORKING ON ", basefolder+subfolder+file, "\n"
            self.recursively_analyze_the_shit_out_of_this(basefolder, subfolder+file+"/", outfolder)
