DIST_NAME = 'manga-optimizer'
# alias don't need to be present, as choices will be matched against after parsing type
WRITING_MODES = ('horizontal-lr', 'horizontal-rl')
WRITING_MODE_ALIASES = {
    'lr': 'horizontal-lr',
    'rl': 'horizontal-rl',
}
SUPPORTED_IMAGES = {'.png', '.jpg', '.jpeg', '.webp'}
OUTPUT_FORMATS = ('cbz', 'epub', 'mobi', 'pdf')
