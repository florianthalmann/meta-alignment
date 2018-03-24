import json
import panako_init, audfprint_init, util
from audfprint_aligner import AudfprintAligner
from panako_aligner import PanakoAligner
from match_aligner import MatchAligner
from meta_alignment import get_validated_timelines, evaluate_alignment, plot_evaluation_graph

audiodir = "ISMIR18/dataset/data/gd1982-10-10.sbd.fixed.miller.110784.flac16/"

panako_db = "ISMIR18/dbs/panako/"
panako_matches = "ISMIR18/matches/panako.json"

fprint_db = "ISMIR18/dbs/audfprint/"
fprint_matches = "ISMIR18/matches/audfprint.json"

match_dir = "ISMIR18/dbs/match/"

results = "ISMIR18/results/"

def setup_panako():
    panako_init.make_dbs(audiodir, panako_db)
    panako_init.find_all_matches(audiodir, panako_db, panako_matches, 10)

def setup_audfprint():
    audfprint_init.make_dbs(audiodir, fprint_db)
    audfprint_init.find_all_matches(audiodir, fprint_db, fprint_matches, 10)

def load_times(file):
    times_key = "reference_times = "
    with open(file) as f:
        times = [l for l in f.readlines() if times_key in l][0]
        return json.loads(times.replace(times_key, ""))

def construct_groundtruth():
    return [load_times(d+"/args.log") for d in util.get_subdirs(audiodir)]

def evaluate():
    aligner = AudfprintAligner(fprint_matches)
    #aligner = MatchAligner(match_dir)
    #aligner = PanakoAligner(panako_matches)
    alignment = get_validated_timelines(audiodir, aligner)
    groundtruth = construct_groundtruth()
    #print alignment, groundtruth
    #evaluate_alignment(alignment, groundtruth)
    plot_evaluation_graph(alignment, groundtruth, results+"fprint.pdf")

#setup_panako()
#setup_audfprint()
evaluate()
