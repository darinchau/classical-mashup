# The module responsible for displaying scores and stuff
from ..score import M21Score, M21Object
from ..analysis.representation import NoteRepresentation
from ..analysis.voices import get_offset_to_site
from ..util import is_ipython
from music21 import expressions, style, stream
import music21 as m21
from music21.ipython21 import converters as ip21_converters
from music21.converter.subConverters import ConverterMusicXML
from music21 import defaults
from music21.converter import museScore
import pathlib
import matplotlib.image as mpimg
import numpy as np
import tempfile

class TextAnnotation(m21.note.Lyric):
    def __init__(self, text: str):
        self._annotations = [text]
        super().__init__(text)

    def add_text(self, text: str):
        self._annotations.append(text)
        self.text = "\n".join(self._annotations)

    def remove_text(self, text: str):
        self._annotations.remove(text)
        self.text = "\n".join(self._annotations)

    def clear(self):
        self._annotations = []
        self.text = ""

def add_border_and_annotation_to_note(s: M21Score, note: NoteRepresentation, annotation: str):
    """Add a border and an annotation to a note in a score."""
    # TODO find better ways to do this? Also any way to
    # - change the color of the border
    # - change the color of the annotation
    # - make border thicker
    # - add spanner type annotations
    def get_note_or_chord_by_representation(rep: NoteRepresentation, s: M21Score):
        for note in s._data.recurse().notes:
            if get_offset_to_site(note, s) == rep.onset_quarter and rep.pitch in [n.ps for n in note.pitches]:
                return note
        return None

    note_ = get_note_or_chord_by_representation(note, s)
    if note_ is None:
        return False

    if note_.activeSite is None:
        return False

    rm = expressions.RehearsalMark("  ")
    assert isinstance(rm.style, style.TextStylePlacement)
    rm.style.alignHorizontal = None
    rm.style.enclosure = "rectangle"
    rm.style.absoluteY = -40
    rm.style.fontSize = 40
    note_.activeSite.insert(note_.offset, rm)

    for lyric in note_.lyrics:
        if isinstance(lyric, TextAnnotation):
            lyric.add_text(annotation)
            return True
    note_.lyrics.append(TextAnnotation(annotation))
    return True

def display_score(obj: M21Object, invert_color: bool = True, skip_display: bool = False):
    """Displays the score. Returns a dictionary where keys are the page numbers and values are the images of the page in np arrays"""
    savedDefaultTitle = defaults.title
    savedDefaultAuthor = defaults.author
    defaults.title = ''
    defaults.author = ''

    if isinstance(obj, stream.Opus):
        raise NotImplementedError("Perform a recursive call to show here when we support Opuses. Ref: music21.ipython21.converters.showImageThroughMuseScore")

    fp = ConverterMusicXML().write(
        obj,
        fmt="musicxml",
        subformats=["png"],
        trimEdges=True,
    )

    last_png = museScore.findLastPNGPath(fp)
    last_number, num_digits = museScore.findPNGRange(fp, last_png)

    pages: dict[int, np.ndarray] = {}
    stem = str(fp)[:str(fp).rfind('-')]
    for pg in range(1, last_number + 1):
        page_str = stem + '-' + str(pg).zfill(num_digits) + '.png'
        page = np.array(mpimg.imread(page_str) * 255, dtype = np.uint8)

        # Invert the color because dark mode
        if invert_color:
            page[:, :, :3] = 255 - page[:, :, :3]
        pages[pg] = page

    if is_ipython() and not skip_display:
        from IPython.display import Image, display, HTML

        for pg in range(1, last_number + 1):
            with tempfile.NamedTemporaryFile(suffix=".png") as f:
                mpimg.imsave(f.name, pages[pg])
                display(Image(data=f.read(), retina=True))
            if pg < last_number:
                display(HTML('<p style="padding-top: 20px">&nbsp;</p>'))

    defaults.title = savedDefaultTitle
    defaults.author = savedDefaultAuthor
    return pages
