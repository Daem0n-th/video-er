#!/usr/bin/env python3
from multiprocessing.dummy import Pool as ThreadPool
from hashlib import sha256
from math import ceil,sqrt
import subprocess as sp
import numpy as np
import argparse
import shutil
import binascii
import sys
import os
import cv2

def pad_hex(string):
	length=len(string)
	if(length%6==0):
		return string
	else:
		return '0'*(6-(length%6)) + string

def pad_image(tuple_list):
	return [(0,0,0)]*(res[0]*res[1]-len(tuple_list)) + tuple_list

def hex2tuple(hex_color):
	return tuple([int(hex_color[i:i+2],16) for i in [0,2,4]])

def tuple2hex(pixel):
	return ''.join([('0'*(2-len(i)))+i for i in [hex(i)[2:] for i in pixel]])

def render_frame(hex_stream):
	sha256_hash=sha256(hex_stream).hexdigest()
	hex_str=sha256_hash+binascii.hexlify(hex_stream).decode('utf-8')
	feed=[hex_str[i:i+6] for i in range(0,len(hex_str),6)]
	tempool=ThreadPool(10)
	hex_colors=tempool.map(hex2tuple,feed)
	return np.uint8(np.array(hex_colors).reshape((res[0],res[1],3)))

def render_last_frame(hex_stream):
	sha256_hash=sha256(hex_stream).hexdigest()
	signature=binascii.hexlify(b'DM').decode('utf-8')
	hex_str=pad_hex(signature+sha256_hash+binascii.hexlify(hex_stream).decode('utf-8'))
	feed=[hex_str[i:i+6] for i in range(0,len(hex_str),6)]
	tempool=ThreadPool(10)
	hex_colors=pad_image(tempool.map(hex2tuple,feed))
	return np.uint8(np.array(hex_colors).reshape((res[0],res[1],3)))

def encode(IN,OUT):
	try:
		src_fp=open(IN,'rb')
	except FileNotFoundError:
		print("File {} is not found.\nExiting...".format(args.input))
		return
	print("Reading from file...")
	file_data=src_fp.read()
	frame_size=res[0]*res[1]*3 - 32
	print("Creating Chunks...")
	chunk_list=[file_data[i:i+frame_size] for i in range(0,len(file_data),frame_size)]
	print("Rendering frames...")
	last_frame=render_last_frame(chunk_list[-1])
	pool = ThreadPool(60)
	frames=pool.map(render_frame,chunk_list[:-1])
	frames.append(last_frame)
	i=0
	for frame in frames:
		i=i+1
		fc='0'*(3-len(str(i))) + str(i)
		cv2.imwrite('temp_frames/frame{}.png'.format(fc),frame)	
	if (OUT[-4:]=='.avi'):
		pass
	else:
		OUT=OUT+'.avi'
	command=['ffmpeg','-y','-i','temp_frames/frame%03d.png','-c:v','ffvhuff','-framerate','25','-flags','bitexact','-fflags','bitexact',OUT,'-v','0']
	print("Stitching frames...")
	sp.run(command,stdout=sp.PIPE)
	print("Finished encoding.")
	
def deconstruct_frame(frame_data):
	color_list=frame_data.reshape((res[0]*res[1],3))
	hex_list=[tuple2hex(pixel) for pixel in color_list]
	hex_list=''.join(hex_list)
	found_hash=hex_list[:64]
	hex_list=hex_list[64:]
	file_data=binascii.unhexlify(hex_list)
	actual_hash=sha256(file_data).hexdigest()
	if (found_hash==actual_hash):
		#print("Hash check succeeded.")
		return file_data
	else:
		print("Data Corrupted.")
		sys.exit(1)

def de_last_frame(frame_data):
	i=0
	color_list=frame_data.reshape((res[0]*res[1],3))
	while(not any(color_list[i])):
		i=i+1
	color_list=color_list[i:]
	hex_list=[tuple2hex(pixel) for pixel in color_list]
	offset,rest=hex_list[0],hex_list[1:]
	hex_list=hex(int(offset,16))[2:]+''.join(rest)
	if (hex_list[:4]=='444d'):
		hex_list=hex_list[4:]
		found_hash=hex_list[:64]
		hex_list=hex_list[64:]
		file_data=binascii.unhexlify(hex_list)
		actual_hash=sha256(file_data).hexdigest()
		if (found_hash==actual_hash):
			#print("Hash check succeeded.")
			return file_data
		else:
			print("Data Corrupted.")
			sys.exit(1)
	else :
		print("Video was not encoded by this program or is corrupt.")

def decode(IN,OUT):
	print("Reading from video...")
	try:
		_=open(IN,'rb')
	except FileNotFoundError:
		print("No such file is found.\nExiting...")
		return
	print("Unstitching frames...")
	command=['ffmpeg','-i',IN,'-an','-f','image2','temp_frames/outframe_%03d.png','-v','0']
	sp.run(command,stdout=sp.PIPE)
	video_frames=list()
	f=0
	while True:
		f=f+1
		fc='0'*(3-len(str(f))) + str(f)
		try:
			_=open("temp_frames/outframe_{}.png".format(fc))
			frame=cv2.imread("temp_frames/outframe_{}.png".format(fc))
			video_frames.append(frame)
		except FileNotFoundError:
			break
	pool = ThreadPool(60)
	print("Found {} frames.".format(len(video_frames)))
	print("De-rendering frames...")
	try:
		last_frame=de_last_frame(video_frames[-1])
	except:
		print("Cannot decode the file. Some of the frames seem to be missing.")
		sys.exit(0)
	hex_data=pool.map(deconstruct_frame,video_frames[:-1])
	print("Data integrity of all frames is verified")
	hex_data.append(last_frame)
	file=b''.join(hex_data)
	print("Writing to file...")
	fp2=open(OUT,'wb')
	fp2.write(file)
	fp2.close()
	print("Finished decoding.")
	print("Details about the file:")
	sp.run(['file',OUT])

def main(args):
	if (args.encode and args.decode):
		print("Invalid arguments")	
		sys.exit(0)
	try:
		os.mkdir('temp_frames')
	except FileExistsError:
		shutil.rmtree('temp_frames',ignore_errors=True)
		os.mkdir('temp_frames')
	if (args.encode):
		encode(args.input,args.output)
	if (args.decode):
		decode(args.input,args.output)
	print("Cleaning up...")
	shutil.rmtree('temp_frames',ignore_errors=True)

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description="Encode any file as a playable video and decode")
	parser._action_groups.pop()
	required = parser.add_argument_group('required arguments')
	optional = parser.add_argument_group('optional arguments')
	required.add_argument('-i','--input',help="Input file for operation",required=True)
	required.add_argument('-o','--output',help="output filename to save As",required=True)
	required.add_argument('-e','--encode',help="encode the file",required=False,action='store_true')
	required.add_argument('-d','--decode',help="decode the file",required=False,action='store_true')   
	optional.add_argument('-l','--length',default=500,help="length and width of the video default is 500",type=int)
	args=parser.parse_args()
	res=(args.length,args.length)
	main(args)