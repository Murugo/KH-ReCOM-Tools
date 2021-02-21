import os
import struct


class BinaryFileReader:
  def __init__(self, filepath):
    self.f = open(filepath, 'rb')
    self.filesize = os.path.getsize(filepath)

  def seek(self, offs):
    self.f.seek(offs)

  def tell(self):
    return self.f.tell()

  def read_nuint8(self, n):
    return list(self.f.read(n))

  def read_int16(self):
    return struct.unpack('<h', self.f.read(2))[0]

  def read_nint16(self, n):
    return struct.unpack('<' + 'h' * n, self.f.read(n * 2))

  def read_uint16(self):
    return struct.unpack('<H', self.f.read(2))[0]

  def read_nuint16(self, n):
    return struct.unpack('<' + 'H' * n, self.f.read(n * 2))

  def read_int32(self):
    return struct.unpack('<i', self.f.read(4))[0]

  def read_nint32(self, n):
    return struct.unpack('<' + 'i' * n, self.f.read(n * 4))

  def read_uint32(self):
    return struct.unpack('<I', self.f.read(4))[0]

  def read_nuint32(self, n):
    return struct.unpack('<' + 'I' * n, self.f.read(n * 4))

  def read_float32(self):
    return struct.unpack('<f', self.f.read(4))[0]

  def read_nfloat32(self, n):
    return struct.unpack('<' + 'f' * n, self.f.read(n * 4))

  # Reads max_len bytes and returns the first zero-terminated string.
  def read_string(self, max_len):
    buf = self.f.read(max_len)
    offs = 0
    while offs < len(buf) and buf[offs] != 0:
      offs += 1
    return buf[:offs].decode('ascii')

  def skip(self, length):
    self.seek(self.tell() + length)
