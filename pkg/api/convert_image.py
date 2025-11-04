# import time
from io import BytesIO
from PIL import Image

def pixel_toRGB565(r, g, b, a):
    """Convert 24-bit RGB8888 (r,g,b,a) to 16-bit RGB565"""
    # Truncate to 5/6 bits
    r5 = (r * 32) // 256
    g6 = (g * 64) // 256
    b5 = (b * 32) // 256

    # Pack in BGR565 order: [RRRR RGGG GGGB BBBB]
    value = (r5 << 11) | (g6 << 5) | b5

    # Return as two bytes (LSB first to reproduce same error as on FLAM)
    return value.to_bytes(2, byteorder='little')

def image_to_liff(image_data):
    image_bytesio = BytesIO(image_data)
    img = Image.open(image_bytesio)

    # reading image properties
    width, height = img.size

    # reading image format
    # img_format = img.format

    # print(f"Image format: {img_format}, size: {width}x{height} (total {len(image_data)} bytes)")

    # Resize the image to have a max width or height of 104 pixels
    max_size = 104
    img.thumbnail((max_size, max_size), Image.Resampling.BICUBIC)

    width, height = img.size
    # print(f"Updated image: {img_format}, size: {width}x{height} (total {len(img.tobytes())} bytes)")

    # write LIFF header as bytes
    liff_data = b"liff"  # LIFF magic number
    liff_data += width.to_bytes(4, byteorder='big')
    liff_data += height.to_bytes(4, byteorder='big')
    liff_data += b"\xA2" # channel info

    # writing image data, each pixel in BGR prefixed with FF
    for pixel in img.getdata():
        if img.mode == "RGB":
            r, g, b = pixel
            a = 255
        elif img.mode == "RGBA":
            r, g, b, a = pixel
        elif img.mode == "L":
            r = g = b = pixel
            a = 255
        else:
            raise ValueError(f"Unsupported image mode: {img.mode}")

        liff_data += b"\xFE"  # prefix byte
        # encode pixel from RGB888 to RGB565
        liff_data += pixel_toRGB565(r, g, b, a)

    # writing footer
    liff_data += b"\x00" * 7
    liff_data += b"\x01"

    # print(f"Converted LIFF size: {len(liff_data)} bytes")
    return liff_data

def image_to_bitmap_rle4(image_data):
    image_bytesio = BytesIO(image_data)
    img = Image.open(image_bytesio)

    # checking if conversion is not necessary
    if img.format == "BMP" and img.info["compression"] == img.RLE4 and img.size == (320, 240):
        return image_data

    if img.size != (320, 240):
        img = img.resize((320, 240))
    if img.format != "BMP":
        img = img.transpose(Image.FLIP_TOP_BOTTOM)

    # print(img.mode)
    if img.mode not in ["1", "L"]:
        img = img.convert("RGB")

    # Get pixel data
    pixel_data = list(img.getdata())

    # start = time.time()
    bmp_data = b""

    # Iterate through pixels
    rle_count = 0
    rle_value = 0

    width, height = img.size
    for y in range(height):
        for x in range(width):
            # Calculate the index in the flat pixel_data list
            index = y * width + x

            # GrayScaled source
            if img.mode in ['P', 'L', '1']:
                # Get gray values for the current pixel
                gray = pixel_data[index]
                grayscale_value = int(gray/16)
                # print(f"@{x:3}x{y:3}: GR={gray:02X} => GR={grayscale_value:02X}")
            # RGB source
            else:
                # Get RGB values for the current pixel
                r, g, b = pixel_data[index]

                grayscale_value = int(
                        (r * 0.299 +
                         g * 0.587 +
                         b * 0.114) / 16
                    )
                # print(f"@{x:3}x{y:3}: R={r:02X}, G={g:02X}, B={b:02X} => GR={grayscale_value:02X}")

            # checking for new line
            if not x:
                rle_count = 1
                rle_value = grayscale_value
                continue

            # same value as prev ?
            if grayscale_value == rle_value and rle_count < 255:
                rle_count += 1

            # rle limit reached or new value
            else:
                color8 = (rle_value << 4) | rle_value
                bmp_data += rle_count.to_bytes(1, 'little')
                bmp_data += color8.to_bytes(1, 'little')

                rle_count = 1
                rle_value = grayscale_value

        color8 = (rle_value << 4) | rle_value
        bmp_data += rle_count.to_bytes(1, 'little')
        bmp_data += color8.to_bytes(1, 'little')

        if y < height - 1:
            bmp_data += b"\x00\x00"

    bmp_data += b"\x00\x01"

    # end = time.time()
    # print(f"{end-start:2.3}s")

    header_size = 54
    data_size = len(bmp_data)
    palette_size = 16 * 4
    data_offset = header_size + palette_size
    file_size = data_offset + data_size

    bmp_buffer = bytearray([0] * file_size)

    # BMP Header
    bmp_buffer[:54] = [
        0x42, 0x4d,  # BM (bitmap signature)
        file_size & 0xff, (file_size >> 8) & 0xff, (file_size >> 16) & 0xff, (file_size >> 24) & 0xff,
        0x00, 0x00, 0x00, 0x00,  # Reserved
        data_offset & 0xff, (data_offset >> 8) & 0xff, (data_offset >> 16) & 0xff, (data_offset >> 24) & 0xff,
        0x28, 0x00, 0x00, 0x00,  # Header size (40 bytes)
        width & 0xff, (width >> 8) & 0xff, (width >> 16) & 0xff, (width >> 24) & 0xff,
        height & 0xff, (height >> 8) & 0xff, (height >> 16) & 0xff, (height >> 24) & 0xff,
        0x01, 0x00,  # Number of color planes (1)
        0x04, 0x00,  # 4 bits per pixel
        0x02, 0x00, 0x00, 0x00,  # Compression method
        data_size & 0xff, (data_size >> 8) & 0xff, (data_size >> 16) & 0xff, (data_size >> 24) & 0xff,
        0x00, 0x00, 0x00, 0x00,  # Horizontal resolution
        0x00, 0x00, 0x00, 0x00,  # Vertical resolution
        0x10, 0x00, 0x00, 0x00,  # Palette colors (16)
        0x00, 0x00, 0x00, 0x00,  # Important colors (0 = all)
    ]

    # BMP Palette (Grayscale)
    for i in range(16):
        index = header_size + i * 4
        gray = int((255 / 16) * i)

        bmp_buffer[index] = gray  # Blue
        bmp_buffer[index + 1] = gray  # Green
        bmp_buffer[index + 2] = gray  # Red
        bmp_buffer[index + 3] = 0  # Reserved

    # Add BMP data to buffer
    bmp_buffer[header_size + palette_size:] = bmp_data

    return bytes(bmp_buffer)
