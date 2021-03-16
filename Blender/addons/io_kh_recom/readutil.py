import os
import struct


class BinaryFileReader:
  def __init__(self, filepath):
    self.f = open(filepath, 'rb')
    self.filesize = os.path.getsize(filepath)
    self.base_offset = 0

  def seek(self, offs):
    self.f.seek(offs + self.base_offset)

  def tell(self):
    return self.f.tell()

  def set_base_offset(self, offs):
    self.base_offset = offs

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
    self.f.read(length)


# Returns a list of tuples of the form (filename, byte_offs, byte_size).
def read_rsrc_header(f):
  files = []

  index = 0
  f.seek(0)
  while True:
    base_offs = index * 0x20
    f.seek(base_offs + 0x1C)
    byte_size = f.read_int32()
    if not byte_size:
      break
    elif byte_size < 0:
      byte_size &= 0x7FFFFFFF
      f.seek(base_offs)
      byte_offs = f.read_uint32()
      filename = f.read_string(0x14)
    else:
      f.seek(base_offs)
      filename = f.read_string(0x10)
      byte_offs = f.read_uint32()
    files.append((filename, byte_offs, byte_size))
    index += 1
  
  return files


# Skip PS4 header if it exists.
def maybe_skip_ps4_header(f):
  f.seek(0)
  file_size_test = f.read_uint32()
  gnf_table_count = f.read_int32()
  f.skip(0x8)
  
  if gnf_table_count == 0 and file_size_test == f.filesize - 0x10:
    f.set_base_offset(f.tell())
  elif gnf_table_count > 0 and gnf_table_count < (f.filesize - 0x10) // 0x30:
    # Attempt to read the first GNF entry.
    try:
      gnf_filename = f.read_string(0x20)
    except UnicodeDecodeError:
      f.seek(0)
      return
    if gnf_filename[-4:].lower() == '.gnf':
      # Skip the remainder of the GNF table.
      f.skip((gnf_table_count - 1) * 0x30 + 0x10)
      f.set_base_offset(f.tell())
      return

  # Header likely does not exist.
  f.seek(0)
