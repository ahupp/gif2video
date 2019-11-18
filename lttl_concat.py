from lttl import ffmpeg_concat
import argparse
import time
import logging
import os
import tempfile
import shutil

logging.basicConfig(level=logging.INFO)

start = time.time()

parser = argparse.ArgumentParser(help="concatate video files")
parser.add_argument("--dest", type=str,
                    help="destination file name")
parser.add_argument("input", type=str, nargs="+",
                    help="input files to append to dest")

args = parser.parse_args()

# ordering of filenames implies order by time
args.input = sorted(args.input)

# if dest doesn't exist yet, copy first file to it
if not os.path.exists(args.dest):
    logging.info("Output video not found, copying")
    shutil.copyfile(args.input.pop(0), args.dest)

if args.input:
    _, fname = tempfile.mkstemp(suffix=".mp4")
    try:
        input = [args.dest] + args.input
        ffmpeg_concat(input, fname, copy=True)
        logging.info("Replacing %s", args.dest)
        os.replace(fname, args.dest)
    except:
        os.unlink(fname)
        raise

logging.info("Completed in %d sec", time.time() - start)

