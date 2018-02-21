from qfp.qfp import ReferenceFingerprint, QueryFingerprint
from qfp.qfp.db import QfpDB

db = QfpDB()

print "create ref"
#fp_r = ReferenceFingerprint("audio/gd1982-10-10.111039.nak300.hoey.flac16/d1t02.flac")
#fp_r.create()

print "store ref"
#db.store(fp_r, "hoey - d1t02")

print "create qry"
fp_q = QueryFingerprint("audio/gd1982-10-10.111039.nak300.hoey.flac16/d1t02.flac")
#"audio/gd1982-10-10.aud.keshavan.bertha.77325.sbeok.flac16/gd82-10-10d1t03.flac"
fp_q.create()

print "query"
db.query(fp_q, 0)
print(fp_q.match_candidates)