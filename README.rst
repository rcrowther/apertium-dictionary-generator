skel2dix
========
Preprocessor for `apertium` .dix files.

If you are compiling from corpus, you need power tools. If you are 
editing existing files, you need a text editor with XML support.
This script is for a limited use case; self-organised
dictionary information needs to generate XML.

The text file input data is in this form::

    .wordToTranslate :firstParadigmPrefix .translationWord :second paradigmPrefix
    ...

single lines, one per translation::

    .head :regularNoun .noggin :regularNoun
    ...


Notes
~~~~~
What it can not do
------------------
The script is an automated input helper. There are many Apertium 
features it can not create, major items are,

No full output
    the results in the output files must be pasted into 
    dictionaries.

Dictionaries only
    no transfer files etc.
 
Cross-category hints can not be added to bi-lingual dictionaries
    no shifting feminine/masculine end-marks/inflexions, asymmetric
    left right analysis etc.

Clean up letter case
    in Apertium, letter case is significant. The intentions
    of letter case are too hard to guess.

To add other features the generated code will need to be
hand-edited. But the script can do the bulk work.


What it has
-----------

Extensive error reporting
    Not always accurate, but gives line numbers.

Robust
    Now uses a mini-parser, and skips unparsable lines

Usage
~~~~~
From the commandline::

    ./skel2dix.py <options> -i /.../inputFile

Current options are,

-a : annotate the output with XML comments 
-i : input file path
-o : output filepath (optional, default taken from input)
-t : `s` for mono-dictionary source, `d` for mono-dictionary destination. `bi` for bilingual

Output filepaths are tagged with dictionary extensions, so the script can be run repeatedly on a source file without adapting filepath names (change -t instead).

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

    == verb
    ...
    .buy .acheter
 
generates::

    <e lm="buy"><i>buy</i><par n="vblex"/></e> 

but::

    == verb
    ...
    buy, acheter, irregularbuy, regularverb
 
generates::

    <e lm="buy"><i>buy</i><par n="irregularbuy__vblex"/></e>


Unrecognised stanza names
-------------------------
If a stanza is not mapped in the `stanza` structure, following 
data is not parsed.

Can be useful for commenting out big blocks of data.


Alternate/ambiguous translation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Data lines can include lists of items::

    {.weird .bizarre .strange} .bizarre

Note there is no need for the period/full stop mark if a list is supplied.

In mono-dictionaries, lists will be expanded into individual entries.
In bilingual dictionaries, entries will be marked with the appropriate `slr`/`srl`
marks::

    <e srl="strange"><p><l>weird<s n="vblex"/></l><r>strange<s n="vblex"/></r></p></e>    
    ...

The first item in the list is the default::

    <e srl="weird D"><p><l>weird<s n="vblex"/></l><r>bizarre<s n="vblex"/></r></p></e>    
    ...


Paradigm prefixes near sets
---------------------------

Lists can have prefixes defined on each element::

    {.weird :regular .bizarre :regular .strange :regular}  .bizarre :regular

...but also overall. This is useful while making a dictionary; you can define a prefix for a paradigm to make the dictionary work, then refine later. The words in this list are not regular, but the dictionary will work::

    {.throw .chuck} :regular  .jeter :regular

As you build up paradigms, under-ride,

    {.throw :thr/ow .chuck} :regular  .jeter :regular


Other Features
~~~~~~~~~~~~~~

Comments
--------
Comments are introduced with `#`::

    # a comment

Comments can follow data lines::

    .find .trouver # expand this definition?


Stemming-paradigm notation
--------------------------
If the main notation includes a slash, 
the XML is constructed with a stem::

    .f/ind :findParadigm .trouv/er :trouverParadigm

generates::

    <e lm="find"><i>f</i><par n="findParadigm"/></e> 

Note that the script has removed the slash for the lemma name,
and used the preceding codepoints for the detected stem.

Note also the look of a line with `apertium` suggested paradigm-naming::

    .f/ind :f/ind .trouv/er :trouv/er





Multi-word usage
----------------

Whitespace in word definitions (apart from head and tail whitespace)
will be treated as multi-word definitions::

    .a lot .beaucoup

generates::

    <e lm="a lot"><i>a<b/>lot</i><par n="adj"/></e>   


Last Note
~~~~~~~~~
'.' and ':' are easy to type, but hard to read. If you would like the files to be more readable, the files and the script could be refactored. To me, this reads better::

    {|throw |chuck}#regular  |jeter#regular

but is horrible to type.

