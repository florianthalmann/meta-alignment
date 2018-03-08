import panako_init, audfprint_init

audiodir = "ISMIR18/dataset/data/gd1982-10-10.sbd.fixed.miller.110784.flac16/"

panako_db = "ISMIR18/dbs/panako/"
panako_matches = "ISMIR18/matches/panako.json"

fprint_db = "ISMIR18/dbs/audfprint/"
fprint_matches = "ISMIR18/matches/audfprint.json"

panako_init.make_dbs(audiodir, panako_db, 2)
panako_init.find_all_matches(audiodir, panako_db, panako_matches, 2)

audfprint_init.make_dbs(audiodir, fprint_db, 2)
audfprint_init.find_all_matches(audiodir, fprint_db, fprint_matches, 2)