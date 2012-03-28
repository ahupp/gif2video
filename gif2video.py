#!/usr/bin/env python

# Convert an animated gif into a ~60s looping mp4 file.  This would be
# trivial except that some gifs have heterogenous frame durations (e.g
# most frames .07s, some .10s and one at 3.0s).  To solve this, set
# the framerate to the shortest frame and then replicate any frames
# with a longer duration.  This is not generally correct but works
# well enough in practice.  Also handles optimized gifs (via gifsicle
# --unoptimize).
#
# Author: adam@hupp.org
#
# depends on gifsicle and ffmpeg

import sys
import re
import subprocess
import tempfile
import os.path
import shutil

def invariant(condition, msg=None):
  if not condition:
    if msg is None:
      msg = 'oops!'
    raise Exception(msg)

def re_map(pattern, lines):
  ret = []
  for i in lines:
    m = re.search(pattern, i)
    if m:
      ret.append(m.group(1))
  return ret

def parse_framelen(info_lines):
  return map(float, re_map('disposal asis delay (.*)s', info_lines))

def repeat_frames(framerate, frame_len, src_format, dst_format):
  framecounter = 0
  # At least one minute of video
  while framecounter/framerate < 60:
    for idx, duration in enumerate(frame_len):
      repetitions = int(round(framerate*duration))
      invariant(repetitions >= 1)

      src = src_format % idx
      invariant(os.path.exists(src), 'expected file not found: ' + src)

      for _ in range(repetitions):
        shutil.copyfile(src, dst_format % framecounter)
        framecounter += 1

def convert_gif_to_video(input_gif, final_dir):

  explode_dir = tempfile.mkdtemp()
  expanded_dir = tempfile.mkdtemp()
  
  gif_name = os.path.basename(input_gif)

  try:
    gifinfo = subprocess.check_output(["gifsicle", "--info", input_gif])
    
    subprocess.check_call(
      # fix "background color not in colormap", not sure of the
      # consequence
      ["gifsicle", "--background", "000000", 
       "--unoptimize", "--explode", input_gif], 
      cwd=explode_dir)

    frame_len_sec = parse_framelen(gifinfo.split("\n"))
    invariant(len(frame_len_sec) > 0, 'no frames found')

    src_format = os.path.join(explode_dir, gif_name) + '.%03d'
    dst_format = os.path.join(expanded_dir, gif_name) + '.%03d.gif'
    
    framerate = int(round(1/min(frame_len_sec)))
    if framerate == 16:
      # for some reason 16fps can produce garbage encodings
      framerate -= 1

    repeat_frames(framerate, frame_len_sec, src_format, dst_format)

    subprocess.check_call(
      ["ffmpeg", "-b", "512k", 
       "-r", str(framerate), "-y", "-i", dst_format, 
       "-an", os.path.join(final_dir, gif_name + ".mp4")]
      )
    
  finally:
    shutil.rmtree(explode_dir)
    shutil.rmtree(expanded_dir)


if len(sys.argv) != 3:
  sys.exit('usage: %s gif output_dir' % sys.argv[0])

input_gif = os.path.abspath(sys.argv[1])
final_dir = sys.argv[2]

convert_gif_to_video(input_gif, final_dir)
