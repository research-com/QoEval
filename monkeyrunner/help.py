#!/usr/bin/env monkeyrunner

# Imports the monkeyrunner modules used by this program
from com.android.monkeyrunner import MonkeyRunner, MonkeyDevice

text = MonkeyRunner.help("html")

f = open('help.html', 'w')
f.write(text)
f.close()
