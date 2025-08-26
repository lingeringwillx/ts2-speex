import ctypes
import io
import struct
import sys
import os
import wave

libspeex = ctypes.cdll.LoadLibrary(os.path.join(os.path.dirname(__file__),'libspeex.dll'))

#struct definitions
#--------------------
class SpeexMode(ctypes.Structure):
    _fields_ = [('mode', ctypes.c_void_p),
               ('query', ctypes.CFUNCTYPE(ctypes.c_int)),
               ('mode_name', ctypes.c_char_p),
               ('mode_id', ctypes.c_int),
               ('bitstream_version', ctypes.c_int),
               ('enc_init', ctypes.CFUNCTYPE(ctypes.c_void_p)),
               ('enc_destory', ctypes.CFUNCTYPE(ctypes.c_int)),
               ('enc', ctypes.CFUNCTYPE(ctypes.c_int)),
               ('dec_init', ctypes.CFUNCTYPE(ctypes.c_void_p)),
               ('dec_destroy', ctypes.CFUNCTYPE(ctypes.c_int)),
               ('dec', ctypes.CFUNCTYPE(ctypes.c_int)),
               ('enc_ctl', ctypes.CFUNCTYPE(ctypes.c_int)),
               ('dec_ctl', ctypes.CFUNCTYPE(ctypes.c_int))]

class SpeexBits(ctypes.Structure):
    _fields_ = [('chars', ctypes.c_char_p),
                ('n_bits', ctypes.c_int),
                ('char_ptr', ctypes.c_int),
                ('bit_ptr', ctypes.c_int),
                ('owner', ctypes.c_int),
                ('overflow', ctypes.c_int),
                ('buf_size', ctypes.c_int),
                ('reserved1', ctypes.c_int),
                ('reserved2', ctypes.c_void_p)]

#function definitions
#--------------------
#get mode data stuct
libspeex.speex_lib_get_mode.argtypes = [ctypes.c_int]
libspeex.speex_lib_get_mode.restype = ctypes.POINTER(SpeexMode)

#get decoder state struct
libspeex.speex_decoder_init.argtypes = [ctypes.POINTER(SpeexMode)]
libspeex.speex_decoder_init.restype = ctypes.c_void_p

#get bitstream struct
libspeex.speex_bits_init.argtypes = [ctypes.POINTER(SpeexBits)]
libspeex.speex_bits_init.restype = ctypes.c_int

#put frame in bitstream
libspeex.speex_bits_read_from.argtypes = [ctypes.POINTER(SpeexBits), ctypes.c_char_p, ctypes.c_int]
libspeex.speex_bits_read_from.restype = ctypes.c_int

#decode the bytes to shorts
libspeex.speex_decode_int.argtypes = [ctypes.c_void_p, ctypes.POINTER(SpeexBits), ctypes.POINTER(ctypes.c_short)]
libspeex.speex_decode_int.restype = ctypes.c_int

#free state struct
libspeex.speex_decoder_destroy.argtypes = [ctypes.c_void_p]
libspeex.speex_decoder_destroy.restypes = ctypes.c_int

#decode the speex file
#--------------------
src = sys.argv[1]
dst = sys.argv[2]

r_stream = io.BytesIO()
w_stream = io.BytesIO()

with open(src, 'rb') as file:
    r_stream = io.BytesIO(file.read())
    
file_len = len(r_stream.getvalue())

r_stream.seek(5)
decoded_size = struct.unpack('<I', r_stream.read(4))[0]

#usually mode 2 (ultra-wide band, sampling rate 32k hz)
speex_mode = struct.unpack('<i', r_stream.read(4))[0]

#usually 640 samples/frame
samples_per_frame = struct.unpack('<H', r_stream.read(2))[0]

mode = libspeex.speex_lib_get_mode(speex_mode)
state = libspeex.speex_decoder_init(mode)

speex_bits = SpeexBits()
libspeex.speex_bits_init(ctypes.byref(speex_bits))

while r_stream.tell() < file_len:
    frame_size = r_stream.read(1)[0] #slicing casts to int
    frame = r_stream.read(frame_size)
    
    #char array to be treated as a short array
    short_arr = (ctypes.c_char * (samples_per_frame * ctypes.sizeof(ctypes.c_short)))()
    
    libspeex.speex_bits_read_from(ctypes.byref(speex_bits), frame, frame_size)
    libspeex.speex_decode_int(state, ctypes.byref(speex_bits), ctypes.cast(short_arr, ctypes.POINTER(ctypes.c_short)))
    
    w_stream.write(short_arr)
    
libspeex.speex_decoder_destroy(state)
    
#the final stream's size comes out to be a little different from the size written in the original file
#there could a small mistake that's causing this...
#print(len(w_stream.getvalue()) - decoded_size)

#convert from short integer pcm to wav
with wave.open(dst, 'wb') as wav_file:
    wav_file.setnchannels(1)
    wav_file.setsampwidth(2)
    wav_file.setframerate(32000)
    wav_file.writeframes(w_stream.getvalue())
    
print('Done...\n')