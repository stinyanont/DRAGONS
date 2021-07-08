.. 02_what_is_recipe.rst

.. _what_is_recipe:

****************
What is a recipe
****************

Here is a recipe::

    def makeProcessedFlat(p):

        p.prepare()
        p.addDQ()
        p.addVAR(read_noise=True)
        p.nonlinearityCorrect()
        p.ADUToElectrons()
        p.addVAR(poisson_noise=True)
        p.makeLampFlat()
        p.normalizeFlat()
        p.thresholdFlatfield()
        p.storeProcessedFlat()
        return

Can you tell from looking at this recipe what it is for and what more or less
will be done to your data?  You probably have a pretty good idea, not the
details but the coarse outline should be clear.  That's the idea!  One should
not need to know anything about Python to get an idea of what the pipeline
is asked to do.  Just maybe a little bit of familiarization with our
nomenclature is needed at the beginning.

The recipe named "makeProcessedFlat" will produce a master flat (aka a
"processed flat").  There will be some "preparation" setup to verify the data
and standardize a few things, then a bad pixel mask will be added to the
data quality (DQ) plane of the astrodata object.  When working on Gemini data, an astrodata object is just
a FITS file opened with `astrodata`.  Astrodata objects are the units passed
around from one step to the other.

A variance (VAR) is calculated and added to the data, first the read noise
portion, then the poisson noise portion.  There is a non-linearity correction being
applied.  The gain is applied through the `ADUToElectrons` step.

Then a lamp flat is made.  How it is made depends on the instrument and often
the band.  The `makeLampFlat` step takes care of the subtleties for you.  Most of
the time for Gemini near-IR instruments, for example, it is the standard
lamp-on/lamp-off scheme that is used.  You just pass everything and
`makeLampFlat` deals with it.

Finally, the flat field is normalized.  The "threshold" step is a bit less
descriptive but it flags any "out of range" pixels as bad and replaces them
with 1.0 to avoid issues like divisions by zero or ``inf`` values.  Those
pixels will not be used for anything scientific later, they are marked as
bad in the DQ plane and that flagging will be propagated when the flat is used
on the science frames.

The `p` variable in that recipe is what links the steps together.  It contains
the list of inputs and outputs being passed around.  The `p` stands for
"Primitive Set".  In fact, those "steps" are called "primitives".  Let's
next talk about "primitives".