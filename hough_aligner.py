import os, subprocess
import util


resultsdir = 'features/'

def hough_align(file, reffile):
    common_path = util.get_common_path(file, reffile)
    resultsfile = (file.replace(common_path, '') + '_' + reffile.replace(common_path, '') + '.txt')
    resultsfile = resultsdir + resultsfile.replace('/', '_')
    if not os.path.isfile(resultsfile):
        print 'performing hough align for ..' + file[file.rfind('/')-15:] + ' and ..'+reffile[reffile.rfind('/')-15:]
        #convert to wav
        wavref = '.wav'.join(reffile.rsplit('.flac', 1))
        wavfile = '.wav'.join(file.rsplit('.flac', 1))
        os.system("sox " + reffile + " "+ wavref)
        os.system("sox " + file + " "+ wavfile)
        reffile = wavref
        file = wavfile
        #align
        with open(os.devnull, 'wb') as devnull:
            subprocess.check_output("~/anaconda/bin/python3 ../recalign/recalign.py -oi " + resultsfile + " " + reffile + " " + file, shell=True, stderr=subprocess.STDOUT)
            #subprocess.check_output("python ../recalign/recalign.py -oi " + resultsfile + " " + reffile + " " + file, shell=True, stderr=subprocess.STDOUT)
        os.remove(reffile)
        os.remove(file)
    return resultsfile

def get_alignment_points(file, reffile):
    resultsfile = hough_align(file, reffile)
    with open(resultsfile) as f:
        lines = f.readlines()
        slope = float(lines[0])
        intercept = float(lines[1])
        confidence = float(lines[2])
    filedur = util.get_duration(file)
    refdur = util.get_duration(reffile)
    delta_start = intercept
    delta_end = (filedur*slope+intercept)-refdur
    return [delta_start, delta_end], confidence
