def parse_bitmap_stream(stream):
    # BMP Header offsets
    FILE_HEADER_SIZE = 14
    DIB_HEADER_SIZE = 40
    HEADER_SIZE = FILE_HEADER_SIZE + DIB_HEADER_SIZE

    def read_little_endian(data, offset, size):
        return int.from_bytes(data[offset:offset + size], 'little')

    # Read the full header (file + DIB header)
    header = stream.read(HEADER_SIZE)
    if len(header) < HEADER_SIZE:
        raise ValueError("Stream does not contain enough data for a valid BMP header.")

    # Parse the header
    pixel_data_offset = read_little_endian(header, 10, 4)
    width = read_little_endian(header, 18, 4)
    height = read_little_endian(header, 22, 4)
    bits_per_pixel = read_little_endian(header, 28, 2)

    print(f"Width: {width}, Height: {height}, Bits per pixel: {bits_per_pixel}")

    if bits_per_pixel != 24:
        raise ValueError("Only 24-bit BMP files are supported in this example.")

    # Calculate row size (with padding)
    row_size = (width * 3 + 3) & ~3  # Each row is padded to a 4-byte boundary

    # Skip to the pixel data
    remaining_header_bytes = pixel_data_offset - HEADER_SIZE
    if remaining_header_bytes > 0:
        stream.read(remaining_header_bytes)  # Read and discard any remaining header bytes

    # Read the pixel data row by row
    pixel_data = []
    for y in range(height):
        row_data = stream.read(row_size)  # Read the full row, including padding
        if len(row_data) < row_size:
            raise ValueError("Stream ended prematurely while reading pixel data.")
        for x in range(width):
            # Each pixel is 3 bytes: Blue, Green, Red
            pixel_offset = x * 3
            red = row_data[pixel_offset]
            green = row_data[pixel_offset + 1]
            blue = row_data[pixel_offset + 2]
            #pixel_data.append((red, green, blue))  # Store pixel as (R, G, B)
            pixel_data.append((red & 0xf8) << 8 | (green & 0xfc) << 3 | blue >> 3)

    return width, height, pixel_data


class BMPStreamReader:
    def __init__(self, stream):
        self.stream = stream
        
        self.buffer = b""  # Buffer to hold row data
        self.buffer_pos = 0  # Position in the buffer
        self.stream_pos = 0  # Current read position in the stream
        
        self.pixel_data_offset, self.row_size, self.width, self.height = self._parse_header()

        # Initialize state variables
        self.current_row = self.height - 1  # BMP rows are stored bottom to top
        self.current_col = 0
        
        # Skip to the pixel data offset
        bytes_to_skip = self.pixel_data_offset - self.stream_pos
        self._consume_stream(bytes_to_skip)

    def _parse_header(self):
        FILE_HEADER_SIZE = 14
        DIB_HEADER_SIZE = 40
        HEADER_SIZE = FILE_HEADER_SIZE + DIB_HEADER_SIZE

        def read_little_endian(data, offset, size):
            return int.from_bytes(data[offset:offset + size], 'little')

        # Read the full header
        header = self.stream.read(HEADER_SIZE)
        self.stream_pos += len(header)

        if len(header) < HEADER_SIZE:
            raise ValueError("Stream does not contain enough data for a valid BMP header.")

        # Extract metadata
        pixel_data_offset = read_little_endian(header, 10, 4)
        width = read_little_endian(header, 18, 4)
        height = read_little_endian(header, 22, 4)
        bits_per_pixel = read_little_endian(header, 28, 2)

        if bits_per_pixel != 24:
            raise ValueError("Only 24-bit BMP files are supported.")

        row_size = (width * 3 + 3) & ~3  # Each row is padded to a 4-byte boundary
        return pixel_data_offset, row_size, width, height

    def _consume_stream(self, n):
        """Consume `n` bytes from the stream."""
        while n > 0:
            chunk = self.stream.read(min(n, 1024))  # Read in chunks
            if not chunk:
                raise ValueError("Stream ended prematurely.")
            n -= len(chunk)
            self.stream_pos += len(chunk)

    def _load_next_row(self):
        """Load the next row into the buffer."""
        if self.current_row < 0:
            return None  # No more rows to load

        self.buffer = self.stream.read(self.row_size)
        if len(self.buffer) < self.row_size:
            raise ValueError("Stream ended prematurely while reading a row.")

        self.buffer_pos = 0
        self.current_row -= 1
        return self.buffer

    def read_pixels(self, n):
        """Read `n` pixels from the stream."""
        #print(f"reading {n} pixels")
        pixels = []
        while n > 0:
            # Load the row if the buffer is empty
            if self.buffer_pos >= len(self.buffer):
                #print("getting new row")
                if not self._load_next_row():
                    break  # No more rows to load

            # Read pixels from the buffer
            while n > 0 and self.buffer_pos + 3 <= len(self.buffer):
                #print(f"get pixel nr {n}")
                red = self.buffer[self.buffer_pos]
                green = self.buffer[self.buffer_pos + 1]
                blue = self.buffer[self.buffer_pos + 2]
                # Append the pixel in RGB565 format
                pixels.append((red & 0xf8) << 8 | (green & 0xfc) << 3 | blue >> 3)
                self.buffer_pos += 3
                n -= 1

            # Handle row padding (skip remaining bytes in the row if needed)
            if self.buffer_pos+3 > len(self.buffer):
                #print("Padding, discarting buffer")
                self.buffer = b""

        return pixels
    
    def empty_stream(self):
        while self._load_next_row():
            pass
    