import zipfile
import argparse
import fitz
import time
import numpy
from pathlib import Path
from PIL import Image
from io import BytesIO

class CbzCreator:
    # Device specs
    DISPLAY_RES = (1072, 1448)
    DISPLAY_RATIO = DISPLAY_RES[0] / DISPLAY_RES[1]
    OUTPUT_FORMAT = 'JPEG'
    SUPPORTED_FORMAT = {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp'}
    # ITU-R BT.709 (HD, modern, sRGB)
    BT709 = (0.2126, 0.7152, 0.0722)
    
    def __init__(self, input_path, output_path, quality):
        self.input_path = Path(input_path)
        self.output_path = Path(output_path)
        self.doc_name = self.input_path.stem
        self.jpeg_quality = quality

# Loading
    def _get_images(self) -> list[Image.Image]:
        """Get all image files sorted by name from folder or CBZ."""
        if self.input_path.is_file() and self.input_path.suffix.lower() == '.cbz':
            return self._load_from_cbzv2()
        elif self.input_path.is_file() and self.input_path.suffix.lower() == '.pdf':
            return self._load_from_pdf()
        elif self.input_path.is_dir():
            return self._load_from_folder()
        else:
            raise ValueError(f"Input must be a folder or a .cbz file: {self.input_path}")
        
    def _load_from_folder(self) -> list[Image.Image]:
        """Get all image files sorted by name."""
        
        paths = [
            file_path for file_path in self.input_path.iterdir()
            if file_path.suffix.lower() in self.SUPPORTED_FORMAT
        ]
        paths = sorted(paths)

        images = []
        for path in paths:
            images.append(Image.open(path))
        return images

    def _load_from_cbzv2(self) -> list[Image.Image]:
        """
        Extract images from a CBZ file and keep ComicInfo.xml (if present) in memory.

        Returns
        -------
        images : list[Image.Image]
            Sorted Pillow Image objects representing the comic pages.
        comic_info_xml : bytes | None
            Raw contents of ComicInfo.xml; ``None`` when the file is absent.
        """
        images: list[Image.Image] = []

        try:
            with zipfile.ZipFile(self.input_path, "r") as cbz:
                # -------------------------------------------------
                # Extract image files in natural archive order
                # -------------------------------------------------
                for file_info in sorted(cbz.infolist(), key=lambda x: x.filename):
                    filename = file_info.filename

                    # Skip directories, macOS metadata, and the XML we already saved
                    if filename.endswith("/") or filename.startswith("__MACOSX"):
                        continue
                    if Path(filename).name.lower() == "comicinfo.xml":
                        with cbz.open(filename) as xml_fp:
                            self.comic_info_xml = xml_fp.read()

                    suffix = Path(filename).suffix.lower()
                    if suffix not in self.SUPPORTED_FORMAT:
                        continue

                    with cbz.open(file_info) as fp:
                        try:
                            img = Image.open(fp)
                            img.load()
                            images.append(img)
                        except (OSError, Image.UnidentifiedImageError):
                            # Unreadable file – just ignore it
                            continue

        except zipfile.BadZipFile:
            raise ValueError(f"Invalid CBZ file: {self.input_path}")

        return images

    def _load_from_pdf(self) -> list[Image.Image]:
        """Extract all images from PDF as PIL Image objects."""
        images = []
        with fitz.open(self.input_path) as doc:
            for page in doc:
                image_list = page.get_images()
                
                for img_ref in image_list:
                    xref = img_ref[0]
                    pix = fitz.Pixmap(doc, xref)
                    
                    # Convert to RGB if needed
                    if pix.n - pix.alpha < 4:  # RGB or grayscale
                        mode = "RGB" if pix.n == 3 else "L"
                    else:
                        pix = fitz.Pixmap(fitz.csRGB, pix)
                        mode = "RGB"
                    
                    # Create PIL Image directly from pixel buffer
                    img = Image.frombytes(mode, (pix.width, pix.height), pix.samples)
                    images.append(img)
        return images

# Processing
    def _normalize_numpy(self, image, threshold=10, coefficients=BT709) -> Image.Image:
        # Step 1: Normalize near-grays
        pixels = numpy.array(image, dtype=numpy.uint8)
        r, g, b = pixels[:,:,0], pixels[:,:,1], pixels[:,:,2]
        
        is_near_gray = (numpy.max(pixels, axis=2) - numpy.min(pixels, axis=2)) <= threshold
        gray_vals = (coefficients[0] * r + coefficients[1] * g + coefficients[2] * b).astype(numpy.uint8)
        pixels[is_near_gray] = gray_vals[is_near_gray, numpy.newaxis]
        
        return Image.fromarray(pixels)

    def _is_color_numpy(self, image, tolerance=10, downscale=4) -> bool:
        """
        Returns True if image is color, False if grayscale.
        Compares max - min of RGB channels.
        """

        if image.mode == "L":
            return False
        elif image.mode != "RGB":
            image = image.convert("RGB")

        width, height = image.size
        if downscale:
            width = max(1, int(round(width/downscale)))
            height = max(1, int(round(height/downscale)))
        
        arr = numpy.array(
            image if not downscale else image.resize((width, height), resample=Image.Resampling.BILINEAR),
            dtype=numpy.uint8
            )
        flat = arr.reshape(-1, 3)
        
        max_channel = numpy.max(flat, axis=1)
        min_channel = numpy.min(flat, axis=1)
        
        return bool(numpy.any((max_channel - min_channel) > tolerance))

    def _crop_borders(self, image, threshold=240, max_crop=15, downscale=0) -> Image.Image:
        # go from each edge until hit content or reach max crop size
        image_mask = image.convert('L') if image.mode != 'L' else image.copy()

        o_width, o_height = image.size
        if downscale > 1:
            width = max(1, int(round(o_width/downscale)))
            height = max(1, int(round(o_height/downscale)))
            image_mask = image_mask.resize((width, height))
        else:
            width, height = image_mask.size

        pixels = image_mask.load()

        max_crop_x = round(max_crop / 100 * width)
        max_crop_y = round(max_crop / 100 * height)

        left=0
        for x in range(width):
            if x>max_crop_x or any(pixels[x, y] < threshold for y in range(height)):
                # left=x-1
                left=x
                break
        
        right=width-1
        for x in range(width-1, 0, -1):
            if x<(width-max_crop_x) or any(pixels[x,y] < threshold for y in range(height)):
                # right=x+1
                right=x
                break
        
        top=0
        for y in range(height):
            if y>max_crop_y or any(pixels[x,y] < threshold for x in range(width)):
                # top=y-1
                top=y
                break
        
        bottom=height-1
        for y in range(height-1, 0, -1):
            if y<(height-max_crop_y) or any(pixels[x,y] < threshold for x in range(width)):
                # bottom=y+1
                bottom=y
                break
        crop_rect = (0,0,o_width, o_height)
        if downscale > 1:
            crop_rect = (int(round(left*downscale)) if downscale > 1 and left > 0 else 0,
                         int(round(top*downscale)) if downscale > 1 and top > 0 else 0,
                         int(round(right*downscale)) if downscale > 1 and right < width-1 else o_width,
                         int(round(bottom*downscale)) if downscale > 1 and bottom < height-1 else o_height)
        else:
            crop_rect = (left, top, right, bottom)
        
        return image.crop(crop_rect)

    def _resize_image_adaptative(
        self,
        image : Image.Image,
        is_color,
        deformation_factor: float = 50
    ) -> Image.Image:
        """
        Resize manga image to fit Kobo reader with controllable aspect ratio deformation.
        
        Args:
            image_path: Path to the image file
            target_width: Target display width in pixels
            target_height: Target display height in pixels
            deformation_factor: 0-100 scale controlling aspect ratio preservation
                            0 = preserve aspect ratio completely
                            100 = stretch to fill display entirely
                            50 = balanced blend
        
        Returns:
            PIL Image object with target dimensions
        """
        target_width = self.DISPLAY_RES[0] if not is_color else self.DISPLAY_RES[0] // 2
        target_height = self.DISPLAY_RES[1]  if not is_color else self.DISPLAY_RES[1] // 2

        # Load image
        original_width, original_height = image.size
        
        # Calculate aspect ratios
        original_aspect = original_width / original_height
        
        # Clamp deformation factor to valid range
        deformation_factor = max(0, min(100, deformation_factor))
        
        # Calculate two candidate sizes
        # Option 1: Preserve aspect ratio (fit within bounds)
        preserve_width = original_width
        preserve_height = original_height
        if original_aspect > self.DISPLAY_RATIO:
            # Image is wider than target
            preserve_width = target_width
            preserve_height = int(target_width / original_aspect)
        else:
            # Image is taller than target
            preserve_height = target_height
            preserve_width = int(target_height * original_aspect)
        
        # Option 2: Stretch to fill display (ignore aspect ratio)
        stretch_width = target_width
        stretch_height = target_height
        
        # Blend between the two approaches based on deformation factor
        blend = deformation_factor / 100.0
        
        final_width = int(preserve_width + (stretch_width - preserve_width) * blend)
        final_height = int(preserve_height + (stretch_height - preserve_height) * blend)
        
        # Resize image to calculated dimensions
        resized_img = image.resize((final_width, final_height), Image.Resampling.LANCZOS)
        
        # Create white canvas at target resolution
        canvas = Image.new('RGB' if is_color else 'L', (target_width, target_height), color='white')
        
        # Calculate position to center the resized image
        offset_x = (target_width - final_width) // 2
        offset_y = (target_height - final_height) // 2
        
        # Paste resized image onto canvas
        canvas.paste(resized_img, (offset_x, offset_y))
        
        return canvas

    def _optimize_image(self, image, is_color) -> Image.Image:
        """Optimize image for e-ink display."""
        
        if self.OUTPUT_FORMAT == 'JPEG':
            if is_color and image.mode != 'RGB':
                image = image.convert('RGB', dither=Image.Dither.FLOYDSTEINBERG)
            elif not is_color and image.mode != 'L':
                image = image.convert('L', dither=Image.Dither.FLOYDSTEINBERG)
            
            # Unsignificant
            # if image.mode == 'RGB':
            #     image = self._normalize_numpy(image)

            return image

        # if is_color:
        #     # Reduce to indexed color for better space efficiency
        #     image = image.convert('P',
        #                       palette = Image.Palette.ADAPTIVE,
        #                       colors = 256,
        #                       dither = Image.Dither.FLOYDSTEINBERG)
        # elif image.mode != 'L':
        #     image = image.convert('L')

        # if image.mode == 'L':
        #     image = image.quantize(16)
        
        return image
    
    def _process_image(self, image) -> Image.Image:
        
        try:
            # check aspect ratio, if double page, rotate sideways
            width, height = image.size
            image_ratio = width / height
            if image_ratio > 1:
                # Rotate 90 clockwise: -90
                image = image.rotate(-90, fillcolor="white", expand=1)

            is_color_start = time.perf_counter()
            # Optimize for e-ink
            # is_color = self._is_color(image)
            is_color = self._is_color_numpy(image)
            # is_color = True
            is_color_done = time.perf_counter()

            

            optimize_start = time.perf_counter()
            image = self._optimize_image(image, is_color)
            optimize_done = time.perf_counter()

            crop_start = time.perf_counter()
            image = self._crop_borders(image, downscale=0)
            crop_done = time.perf_counter()

            # Resize to device specs
            # img = self._resize_image(img, is_color)
            resize_start = time.perf_counter()
            image = self._resize_image_adaptative(image, is_color, deformation_factor=80)
            resize_done = time.perf_counter()

            print(f"Total processing time: {resize_done - is_color_start}\n" \
                    f"is_color: {is_color_done - is_color_start}\n" \
                    f"optimize: {optimize_done - optimize_start}\n" \
                    f"crop: {crop_done - crop_start}\n" \
                    f"resize: {resize_done - resize_start}")

        except Exception as e:
            print(f"  Error processing {image}: {e}")

        return image

# Main
    def create_cbz(self):
        """Create CBZ file from images."""
        images = self._get_images()

        if not images:
            raise ValueError(f"No image files found in {self.input_path}")
        print(f"Found {len(images)} images")
        
        with zipfile.ZipFile(self.output_path, 'w', zipfile.ZIP_STORED) as cbz:
            for idx, image in enumerate(images, 1):
                print(f"Processing {idx}/{len(images)}")
                
                try:
                    image = self._process_image(image)

                    # Save to CBZ
                    img_bytes = BytesIO()
                    if self.OUTPUT_FORMAT == 'JPEG':
                        image.save(img_bytes, format=self.OUTPUT_FORMAT, quality=self.jpeg_quality, optimize=True)
                    elif self.OUTPUT_FORMAT == 'PNG':
                        image.save(img_bytes, format=self.OUTPUT_FORMAT, optimize=True)
                    img_bytes.seek(0)
                    
                    # Add to archive with zero-padded name for proper ordering
                    image_name = f"{idx:03d}.{self.OUTPUT_FORMAT.lower()}"
                    cbz.writestr(image_name, img_bytes.getvalue())
                    image.close()
                
                except Exception as e:
                    print(f"  Error repacking {image}: {e}")

            # metadata = self._generate_metadata()
            cbz.writestr("ComicInfo.XML", self.comic_info_xml)

        print(f"✓ CBZ created: {self.output_path}")

def main():
    parser = argparse.ArgumentParser(
        description="Convert images from CBZ/PDF/Folder into a CBZ file optimized for e-readers like Kobo Clara Color"
    )
    
    parser.add_argument(
        "input_path",
        type=Path,
        help="Path to the file/folder containing images"
    )
    
    parser.add_argument(
        "-o", "--output",
        default="output.cbz",
        type=Path,
        help="Output CBZ file path (default: output.cbz)"
    )

    parser.add_argument(
        "-q", "--quality",
        default=60,
        type=int,
        help="Change the output jpeg quality"
    )

    try:
        args = parser.parse_args()

        # Validate input folder
        if not args.input_path.exists():
            print(f"Error: Input path '{args.input_path}' does not exist")
            exit(1)

        creator = CbzCreator(
            input_path=args.input_path,
            output_path=args.output,
            quality=args.quality
        )
        creator.create_cbz()

    except Exception as e:
        print(f" Parsing Error: {e}")
        exit(1)

if __name__ == "__main__":
    main()
