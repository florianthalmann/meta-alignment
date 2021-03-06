import json, logging
import panako_init, audfprint_init, match_init, util
from audfprint_aligner import AudfprintAligner
from panako_aligner import PanakoAligner
from match_aligner import MatchAligner
from meta_alignment import get_timelines, evaluate_alignment, plot_evaluation_graph, plot_linreg

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s',
                    filename='dataset_main.log',
                    filemode='a')

audiodir = "ISMIR18/dataset/data5/gd1982-10-10.sbd.fixed.miller.110784.flac16/"

panako_db = "ISMIR18/dbs/data5/panako/"
panako_matches = "ISMIR18/matches/data5/panako.json"

fprint_db = "ISMIR18/dbs/data5/audfprint/"
fprint_matches = "ISMIR18/matches/data5/audfprint.json"

match_dir = "ISMIR18/dbs/data5/match/"
match_matches = "ISMIR18/matches/data5/match.json"

results = "ISMIR18/results/data5/"

params = ["crowd", "speed", "deviation", "gaps", "quantity"]

numdirs = 10

#main info: adjust every time the script is run
logging.info('WORKING ON DATA5, NUMDIRS AT 10')

def setup_panako():
    logging.info('panako setup started')
    panako_init.make_dbs(audiodir, panako_db, numdirs)
    logging.info('panako dbs done')
    panako_init.find_all_matches(audiodir, panako_db, panako_matches, numdirs)
    logging.info('panako matches done')

def setup_audfprint():
    logging.info('audfprint setup started')
    audfprint_init.make_dbs(audiodir, fprint_db, numdirs)
    logging.info('audfprint dbs done')
    audfprint_init.find_all_matches(audiodir, fprint_db, fprint_matches, numdirs)
    logging.info('audfprint matches done')

def setup_match():
    logging.info('match setup started')
    match_init.find_all_matches(audiodir, match_dir, match_matches, numdirs)
    logging.info('match matches done')

def load_value(file, key):
    with open(file) as f:
        value = [l for l in f.readlines() if key in l][0]
        return json.loads(value.replace(key+" = ", ""))

def load_param(key):
    return [load_value(d+"/args.log", key) for d in util.get_subdirs(audiodir, numdirs)]

def evaluate(aligner, outfile, validated):
    alignment = get_timelines(audiodir, aligner, numdirs, validated)
    groundtruth = load_param("reference_times")
    logging.info(evaluate_alignment(alignment, groundtruth))
    for p in params:
        param = load_param(p)
        #sort by param value
        combined = zip(param, alignment, groundtruth)
        combined.sort(key = lambda l: l[0])
        param, sorted_align, sorted_ground = zip(*combined)
        plot_linreg(p, param, sorted_align, sorted_ground, results+outfile+"_"+p+"_"+str(validated)+".pdf")

def evaluate_all(validated):
    logging.info('audfprint evaluation started')
    evaluate(AudfprintAligner(fprint_matches), "fprint", validated)
    logging.info('audfprint evaluation done')
    logging.info('panako evaluation started')
    evaluate(PanakoAligner(panako_matches), "panako", validated)
    logging.info('panako evaluation done')
    logging.info('match evaluation started')
    evaluate(MatchAligner(match_matches), "match", validated)
    logging.info('match evaluation done')


setup_panako()
setup_audfprint()
setup_match()

evaluate_all(False)
#evaluate_all(True)
