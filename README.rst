skel2dix
========
Preprocessor for `apertium` .dix files.

If you are compiling from corpus, you need power tools. If you are 
editing existing files, you need a text editor with XML support.
This script is for a limited use case, where you have organised
dictionary information and need to generate XML.

The text file input data is in this form::

    wordToTranslate, translationWord, Optional(firstParadigmName, second paradigmName)
    ...

single lines, one per translation::

    head, noggin
    ...



What it can not do
------------------
The script is an automated input helper. There are many Apertium 
features it can not create, but major items are,

No full output
    the results in the output files must be pasted into 
    dictionaries. The script does the grunt work.

Dictionaries only
    no transfer files etc.
 
Cross-category hints can not be added to bi-lingual dictionaries
    no shifting to feminine/male end-marks/inflexions, unknown
    gender marks etc.

Clean up letter case
    in Apertium, letter case is significant. The intentions
    of letter case are too hard to guess.

To add other features the generated code will need to be
hand-edited.

Usage
~~~~~
From the commandline::

    ./skel2dix.py <options> -i /.../inputFile

Options include,

-a : annotate the output with XML comments 
-i : input file path
-o : output filepath (optional, taken from input)
-t : `s` for mono-dictionary source, `d` for mono-dictionary destination. `bi` for bilingual

Many of the following examples are for mono-dictionaries, to keep 
the examples cleaner.


Stanzas
~~~~~~~
Marks groups of word type.

Are introduced with OneOrMore(`=`)::

    == verb

Stanza marks affect output. They are mapped in this structure::

    stanzas = {
    'verb': Stanza('vblex'),
    ...
    }

Stanza marks are case-insensitive (can be titled in source, but lower in the `stanza` array).

If text data do not include optional paradigm marks, the mark defaults to the 
value mapped in `stanza`. So::

    buy, acheter
 
generates::

    <e lm="buy"><i>buy</i><par n="vblex"/></e> 

but::


    buy, acheter, irregularbuy, regularverb
 
generates::

    <e lm="buy"><i>buy</i><par n="irregularbuy__vblex"/></e>


Unrecognised stanza names
-------------------------
If a stanza is not mapped in the `stanza` structure, following 
data is not parsed.

Can be useful for commenting out big blocks of data.


 

Other Features
~~~~~~~~~~~~~~

Comments
--------
Comments are introduced with `#`::

    # a comment

Comments can follow data lines::

    find, trouver # expand this definition?


Stemming-paradigm notation
--------------------------
If optional dialogue notation includes the slash, 
the XML is constructed with a stem::

    find, trouver, f/ind, trouv/er

generates::

    <e lm="find"><i>f</i><par n="f/ind__vblex"/></e> 


Alternate/ambiguous translation
-------------------------------
Data lines can include sets of items::

    {weird, bizarre, strange}, bizarre

In mono-dictionaries, these will be expanded into individual entries.
In bilingual dictionaries, entries will be marked with the appropriate `slr`/`srl`
marks. The first item in the set is the default::

    <e srl="weird D"><p><l>weird<s n="vblex"/></l><r>bizarre<s n="vblex"/></r></p></e>    
    ...

Multi-word usage
----------------

Whitespace in word definitions (apart from head and tail whitespace)
will be treated as multi-word definitions::

    a lot, beaucoup

generates::

    <e lm="a lot"><i>a<b/>lot</i><par n="adj"/></e>   

