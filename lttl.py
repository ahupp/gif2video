import shutil
import argparse
import os
import os.path
import sys
import tempfile
import subprocess
import logging
import time

"""
The goal of this script is to incrementally generate a timelapse video while
minimizing disk use.

The video is generated in two steps, first by encoding a batch of images (batch
size defined by --frames_per_block) into a new mp4 file, and then appending that
file using ffmpeg's lossless copy into the final video.

The new images could be directly appended to the video but (AFAICT) that will
use the MJPEG codec which makes the output quite a bit larger than necessary,
motivating the two-step process.  

There's probably a simpler solution available but this works well enough.
"""


def listdir(dirname):
    return sorted([os.path.join(dirname, i)
                   for i in os.listdir(dirname)])

def ffmpeg_concat(inputs, output, copy):
    with tempfile.NamedTemporaryFile() as f:
        for fname in inputs:
            fname = os.path.abspath(fname)
            f.write(b"file %s\n" % fname.encode("utf-8"),)
        f.flush()

        # copy does a direct copy (e.g a bunch of mp4 into a new mp4)
        # while without copy this does an encoding
        if copy:
            copyarg = ["-vcodec", "copy",
                       "-acodec", "copy"]
        else:
            copyarg = []
            
        cmd = ["ffmpeg",
               "-y", # overwrite dest file, because it's a tmpfile we created
               "-f", "concat", "-safe", "0", "-i", f.name] + \
               copyarg + \
               [output]
        logging.info("Exec: %s", " ".join(cmd))
        subprocess.run(cmd)


def main():
    logging.basicConfig(level=logging.INFO)

    start = time.time()

    parser = argparse.ArgumentParser()
    parser.add_argument("--frames_per_block", 
        type=int,
        help="the number of frames to accumulate before encoding a block",
        # assume 24fps, so 10s of video
        default=240)
    parser.add_argument("--loop", action="store_true",
                        help="loop forever watching for new images")
    parser.add_argument("indir",
                        help="directory of input images")
    parser.add_argument("outdir",
                        help="directory of output videos")
    args = parser.parse_args()                   

    while True:
        infiles = listdir(args.indir)
        # limit to the first N frames, to avoid OOMing my poor tiny machine
        infiles = infiles[:args.frames_per_block]

        if len(infiles) < args.frames_per_block:
            logging.info("Found %d, frames_per_block is %d.",
                    len(infiles), args.frames_per_block)
        else:
            logging.info("Found %d files, encoding", len(infiles))

            # output file name is the basename of the last input file
            oname = os.path.splitext(os.path.basename(infiles[-1]))[0]
            outpath = os.path.abspath(os.path.join(args.outdir, oname + ".mp4"))
            try:
                ffmpeg_concat(infiles, outpath, False)
            finally:
                for i in infiles:
                    os.unlink(i)

            logging.info("Completed in %d sec", time.time() - start)

        if args.loop:
            time.sleep(4)
        else:
            break

if __name__ == "__main__":
    main()

