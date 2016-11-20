skel2dix
========
Preprocessor for `apertium` .dix files.

If you are compiling from corpus, you need power tools. If you are 
editing existing files, you need a text editor with XML support.
This script is for a limited use case; self-organised
dictionary information needs to generate XML.

The text file input data is in this form::

    .wordToTranslate :firstParadigmPrefix .translationWord :secondParadigmPrefix
    ...

single lines, one per translation::

    .head :regularNoun .noggin :regularNoun
    ...

Prefixes are optional.


Notes
~~~~~
What it can not do
------------------
The script is an automated input helper. There are many Apertium 
features it can not create. Major items are,

No full output
    results in the output files must be pasted into 
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

Good error reporting
    Not always accurate, but gives line numbers.

Robust
    Uses a mini-parser, and skips unparsable lines

Concatenated output
    Multiple input files are concatenated to one output file

Annotated output
    Optionally, the resulting dictionaries can have
    annotated comments noting the source.


Usage
~~~~~
From the commandline::

    ./skel2dix.py <options> inputFiles

Current options are,

-a : annotate the output with XML comments
-o : output filebasename (optional, default is 'output')
-l : output lemmas to a file, one per line. This option responds to -a and -t
-t : `s` for mono-dictionary source, `d` for mono-dictionary destination. `bi` for bilingual 'a' for all

Output filepaths are tagged with dictionary extensions, so the script can be run repeatedly on source files without adapting filepath names (change -t instead).

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
    .buy :irregularbuy .acheter :regularverb
 
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

Note there is no need for an opening period/full-stop to the list itself.

In mono-dictionaries, lists will be expanded into individual entries. The first item in the list is the default. Subsequent entries generated from the list are marked with the 'r' attribute. From the example above::

    <e><p><l>weird<s n="adj"/></l><r>bizarre<s n="adj"/></r></p></e>    
    <e r="LR"><p><l>bizarre<s n="adj"/></l><r>bizarre<s n="adj"/></r></p></e>    
    <e r="LR"><p><l>strange<s n="adj"/></l><r>bizarre<s n="adj"/></r></p></e>    
    ...


Paradigm prefixes near sets
---------------------------

Lists can have paradigm prefixes defined on each element::

    {.weird :regular .bizarre :regular .strange :regular}  .bizarre :regular

...but also overall. This is useful while making a dictionary; you can define a prefix for a paradigm to make the dictionary work, then refine later. The words in this list are not regular, but the dictionary will work::

    {.throw .chuck} :regular  .jeter :regular

As you build up paradigms, under-ride individual elemts in the list,

    {.throw :thr/ow .chuck} :regular  .jeter :regular


Other Features
~~~~~~~~~~~~~~

Comments
--------
Comments are introduced with `#`::

    # a comment

Comments can follow data lines::

    .find .trouver # expand this definition?


Auto-handling of paradigm slash marks
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
In monolingual dictionaries, entry matches will be cropped by slashed paradigm marks::

    dandy :bab/y

generates,

    <e lm="dandy"><i>dand</i><par n="bab/y__n"/></e>
   
    ...

Note that the script used the supplied text for the lemma name, then cropped for the text match.



Multi-word usage
----------------

Whitespace in word definitions (apart from head and tail whitespace)
will be treated as multi-word definitions::

    .a lot .beaucoup

generates::

    <e lm="a lot"><i>a<b/>lot</i><par n="adj"/></e>   


Output lemmas
~~~~~~~~~~~~~
Minimal but useful option for producing files to test against frequency counts, for word existence, etc. Reuses the '-t' option, so can limit lemma output to only one mono dictionary. Can also annotate the output (in XML), which may have a use when handling very long dictionaries.

 
Last Note
~~~~~~~~~
'.' and ':' are easy to type, but hard to read. If you would like the files to be more readable, the files and the script could be refactored. To me, this reads better::

    {|throw |chuck} #regular  |jeter #regular

...but is horrible to type.

