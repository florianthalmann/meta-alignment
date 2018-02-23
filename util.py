import os, subprocess


def get_common_path(pa, pb):
    """ returns the longest common subpath of sa and sb """
    def _iter():
        for a, b in zip(pa, pb):
            if a == b:
                yield a
            else:
                return
    result = ''.join(_iter())
    return result[:result.rfind('/')+1]

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

def get_ref_timeline(files):
    timeline = []
    current_time = 0
    for file in files:
        current_duration = get_duration(file)
        timeline.append([current_time, current_time+current_duration])
        current_time += current_duration
    return timeline