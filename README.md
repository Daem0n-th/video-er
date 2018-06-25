# video-er
This tool converts any file to sequence of frames and then uses ffmpeg to stitch them togrther. uses ffvhuff lossless encoding.
```
usage: videor.py [-h] -i INPUT -o OUTPUT [-e] [-d] [-l LENGTH]

Encode any file as a playable video and decode

required arguments:
  -i INPUT, --input INPUT    Input file for operation
  -o OUTPUT, --output OUTPUT  output filename to save As
  -e, --encode          encode the file
  -d, --decode          decode the file

optional arguments:
  -l LENGTH, --length LENGTH  length and width of the video default is 500
```
