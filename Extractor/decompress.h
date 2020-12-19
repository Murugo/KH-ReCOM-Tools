// Implements a variant of LZSS decompression used by KH Re:COM.
uint8_t* Decompress(const uint8_t* buffer, int compressed_size,
                    int uncompressed_size) {
  uint8_t* out_buffer = new uint8_t[uncompressed_size];
  const int block_count =
      (compressed_size / 0x1000) + (compressed_size % 0x1000 != 0);
  char dictionary[0x100];
  memset(dictionary, 0, 0x100);
  int src = 0;
  int dst = 0;
  for (int block = 0; block < block_count; ++block) {
    src = block * 0x1000;
    int dct = 1;
    int bit_index = 0;
    while (dst < uncompressed_size) {
      // Get next bit
      const bool write_byte = (buffer[src] & (0x80 >> bit_index)) > 0;
      if (++bit_index >= 8) {
        bit_index = 0;
        src++;
      }
      // Get next 8 bits
      uint8_t b = bit_index > 0 ? ((buffer[src] << bit_index) |
                                   (buffer[src + 1] >> (8 - bit_index)))
                                : buffer[src];
      src++;
      if (write_byte) {
        out_buffer[dst++] = b;
        dictionary[dct++] = b;
        dct &= 0xFF;
      } else {
        if (b == 0) {
          break;
        }
        // Get next 4 bits
        const int count =
            2 + (bit_index < 5 ? ((buffer[src] >> (4 - bit_index)) & 0xF)
                               : (((buffer[src] << (bit_index - 4)) & 0xF) |
                                  ((buffer[src + 1] >> (12 - bit_index)))));
        bit_index += 4;
        if (bit_index >= 8) {
          bit_index -= 8;
          src++;
        }
        for (int i = 0; i < count; ++i) {
          out_buffer[dst++] = dictionary[b];
          dictionary[dct++] = dictionary[b++];
          dct &= 0xFF;
          b &= 0xFF;
        }
      }
    }
  }
  return out_buffer;
}
