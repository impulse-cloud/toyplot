# Copyright 2014, Sandia Corporation. Under the terms of Contract
# DE-AC04-94AL85000 with Sandia Corporation, the U.S. Government retains certain
# rights in this software.

"""Generate PDF documents."""

from __future__ import absolute_import
from __future__ import division


import toyplot

try:
    import toyplot.reportlab.pdf as implementation
except:
    try:
        import toyplot.qt.pdf as implementation
        toyplot.log.warning("Couldn't load toyplot.reportlab.pdf (preferred), using toyplot.qt.pdf (deprecated).")
    except:
        try:
            import toyplot.cairo.pdf as implementation
            toyplot.log.warning("Couldn't load toyplot.reportlab.pdf (preferred), using toyplot.cairo.pdf (deprecated).")
        except:
            toyplot.log.error("Couldn't load a PDF backend.  Try installing reportlab (preferred), PyQt 5, or pango / cairo.")
            raise


def render(canvas, fobj=None, width=None, height=None, scale=None):
    """Render the PDF representation of a canvas.

    Because the canvas dimensions are specified explicitly at creation time, they
    map directly to real-world units in the output PDF image.  Use one of
    `width`, `height`, or `scale` to override this behavior.

    Parameters
    ----------
    canvas: :class:`toyplot.canvas.Canvas`
      Canvas to be rendered.
    fobj: file-like object, string, or None
      The file to write.  Use a string filepath to write data directly to disk.
      If `None` (the default), the PDF data will be returned to the caller
      instead.
    width: number, string, or (number, string) tuple, optional
      Specify the width of the output image with optional units.  If the units
      aren't specified, defaults to points.  See :ref:`units` for details on
      unit conversion in Toyplot.
    height: number or (number, string) tuple, optional
      Specify the height of the output image with optional units.  If the units
      aren't specified, defaults to points.  See :ref:`units` for details on
      unit conversion in Toyplot.
    scale: number, optional
      Scales the output `canvas` by the given ratio.

    Returns
    -------
    pdf: PDF data, or `None`
      PDF representation of `canvas`, or `None` if the caller specifies the
      `fobj` parameter.

    Examples
    --------

    >>> toyplot.pdf.render(canvas, "figure-1.pdf", width=(4, "inches"))

    Notes
    -----
    The output PDF is currently rendered using (in order of preference)
    :func:`toyplot.reportlab.pdf.render()`, :func:`toyplot.qt.pdf.render()`, or
    :func:`toyplot.cairo.pdf.render()`.
    """
    return implementation.render(canvas, fobj, width, height, scale)
