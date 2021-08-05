#!/bin/bash
# Play two video files side-by-side

mpv --lavfi-complex="[vid1][vid2]hstack[vo];[aid1][aid2]amix[ao]" $1 --external-file=$2
