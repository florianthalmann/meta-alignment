import json, logging
import panako_init, audfprint_init, util
from audfprint_aligner import AudfprintAligner
from panako_aligner import PanakoAligner
from match_aligner import MatchAligner
from meta_alignment import get_validated_timelines, evaluate_alignment, plot_evaluation_graph, plot_linreg

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s',
                    filename='dataset_main.log',
                    filemode='a')

audiodir = "ISMIR18/dataset/data4/gd1982-10-10.sbd.fixed.miller.110784.flac16/"

panako_db = "ISMIR18/dbs/panako/"
panako_matches = "ISMIR18/matches/panako.json"

fprint_db = "ISMIR18/dbs/audfprint/"
fprint_matches = "ISMIR18/matches/audfprint.json"

match_dir = "ISMIR18/dbs/match/"

results = "ISMIR18/results/"

numdirs = 13

params = ["crowd", "speed", "deviation", "gaps", "quantity"]

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
    alignment = get_validated_timelines(audiodir, MatchAligner(match_dir), numdirs)
    logging.info('match matches done')

def load_value(file, key):
    with open(file) as f:
        value = [l for l in f.readlines() if key in l][0]
        return json.loads(value.replace(key+" = ", ""))

def load_param(key):
    return [load_value(d+"/args.log", key) for d in util.get_subdirs(audiodir, numdirs)]

def evaluate(aligner, outfile):
    alignment = get_validated_timelines(audiodir, aligner, numdirs)
    groundtruth = load_param("reference_times")
    logging.info(evaluate_alignment(alignment, groundtruth))
    for p in params:
        param = load_param(p)
        #sort by param value
        combined = zip(param, alignment, groundtruth)
        combined.sort(key = lambda l: l[0])
        param, sorted_align, sorted_ground = zip(*combined)
        plot_linreg(p, param, sorted_align, sorted_ground, results+outfile+"_"+p+".pdf")

def evaluate_all():
    logging.info('audfprint evaluation started')
    evaluate(AudfprintAligner(fprint_matches), "fprint")
    logging.info('audfprint evaluation done')
    logging.info('panako evaluation started')
    evaluate(PanakoAligner(panako_matches), "panako")
    logging.info('panako evaluation done')
    logging.info('match evaluation started')
    evaluate(MatchAligner(match_dir), "match")
    logging.info('match evaluation done')


setup_panako()
setup_audfprint()
setup_match()

evaluate_all()
