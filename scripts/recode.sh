#!/bin/bash

FIN=output_huffy.avi
FOUT=enc

# mpeg4
ffmpeg -i $FIN -c:v mpeg4 -vtag xvid -qscale:v 1 -c:a libmp3lame -qscale:a 1 -y ${FOUT}_1.avi

ffmpeg -i $FIN -c:v mpeg4 -vtag xvid -qscale:v 2 -c:a libmp3lame -qscale:a 2 -y ${FOUT}_2.avi

ffmpeg -i $FIN -c:v mpeg4 -vtag xvid -qscale:v 3 -c:a libmp3lame -qscale:a 3 -y ${FOUT}_3.avi

# x264

ffmpeg -i $FIN -c:v libx264 -strict -2 -preset slow -pix_fmt yuv420p -y ${FOUT}_4.mp4
