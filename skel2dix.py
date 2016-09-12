#!/usr/bin/env python

"""
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


Note
~~~~
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
If the main notation includes a slash, 
the XML is constructed with a stem::

    f/ind, trouv/er, findParadigm, trouveParadigm

generates::

    <e lm="find"><i>f</i><par n="findParadigm"/></e> 

Note that the script has removed the slash for the lemma name,
and used the preceding codepoints for the detected stem.

Note also the look of a line with `apertium` suggested paradigm-naming::

    f/ind, trouv/er, f/ind, trouv/er



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

    :copyright: 2016 Rob Crowther
    :license: GPL, see LICENSE for details.
"""
# ? not covered
# check stemming
# clean notification
# spaces again
# put all strip and block into lemma producers?
# output file implied
import sys, getopt, re
from collections import namedtuple


dictionaryNames = {
    's': 'source monodix',
    'd': 'destination monodix',
    'bi': 'bi-lingual dictionary'
}

lineNum = 0

def printWarning(message):
    global lineNum
    print('{0:2d}:[warning] {1}'.format(lineNum, message))
    
def printError(message):
    global lineNum
    print('{0:2d}:[error] {1}'.format(lineNum, message))
    
def suffix(line, limitStr):
    idx = line.rfind(limitStr)
    #print idx
    if idx == -1: return line
    else: return line[idx + 1:]

def prefix(line, limitStr):
    idx = line.find(limitStr)
    #print idx
    if idx == -1: return line
    else: return line[:idx]

def lemmaStem(lemmaMark):
    idx = lemmaMark.find('/')
    if idx == -1:
        return  lemmaMark, lemmaMark
    else:
        return lemmaMark.replace("/", ""),  lemmaMark[:idx]
    
def lemma(lemmaMark):
    return lemmaMark.replace("/", "")
    
def monodixTemplate(fOut, lemmas, dixParadigm):
    # <e lm="earn"><i>earn</i><par n="reg__vblex"/></e>   
    for lemmaMark in lemmas:
        lemma, stem = lemmaStem(lemmaMark)
        fOut.write('<e lm="')
        fOut.write(lemma)
        fOut.write('"><i>')
        # fill out multi-words
        fOut.write(stem.replace(" ", "<b/>"))
        fOut.write('</i><par n="')
        fOut.write(dixParadigm)
        fOut.write('"/></e>\n')

def bilingualTemplate(fOut, srcLemma, dstLemma, dixParadigm):
    # <e><p><l>snack<s n="n"/></l><r>baggin<s n="n"/></r></p></e>
    srcL = lemma(srcLemma)
    dstL = lemma(dstLemma)

    fOut.write('<e><p><l>')
    fOut.write(srcL)
    fOut.write('<s n="')
    fOut.write(dixParadigm)
    fOut.write('"/></l><r>')
    fOut.write(dstL)
    fOut.write('<s n="')
    fOut.write(dixParadigm)
    fOut.write('"/></r></p></e>\n')
    
def bilingualTemplateWithTranslationMarkRL(
    fOut,
     srcLemmas,
     dstLemma,
     dixParadigm
    ):
    # <e srl="snack D"><p><l>snack<s n="n"/></l><r>baggin<s n="n"/></r></p></e>
    first = True
    dstL = lemma(dstLemma)
    for srcLemma in srcLemmas:
        srcL = lemma(srcLemma)
        fOut.write('<e srl="')
        fOut.write(srcL)
        if first: 
            fOut.write(' D')
            first = False
        fOut.write('"><p><l>')
        fOut.write(srcL)
        fOut.write('<s n="')
        fOut.write(dixParadigm)
        fOut.write('"/></l><r>')
        fOut.write(dstL)
        fOut.write('<s n="')
        fOut.write(dixParadigm)
        fOut.write('"/></r></p></e>\n')
    
def bilingualTemplateWithTranslationMarkLR(
    fOut,
     srcLemma,
     dstLemmas,
     dixParadigm
    ):
    # <e slr="baggin D"><p><l>snack<s n="n"/></l><r>baggin<s n="n"/></r></p></e>
    first = True
    srcL = lemma(srcLemma)
    for dstLemma in dstLemmas:
        dstL = lemma(dstLemma)
        fOut.write('<e slr="')
        fOut.write(dstL)
        if first: 
            fOut.write(' D')
            first = False
        fOut.write('"><p><l>')
        fOut.write(srcL)
        fOut.write('<s n="')
        fOut.write(dixParadigm)
        fOut.write('"/></l><r>')
        fOut.write(dstL)
        fOut.write('<s n="')
        fOut.write(dixParadigm)
        fOut.write('"/></r></p></e>\n')
    
def stanzaAnnotateTemplate(fOut, stanzaName):
    fOut.write('\n<!-- ')
    fOut.write(stanzaName)
    fOut.write(' -->\n')
    
def timeTemplate(fOut, dixLemma, dixStem, dixParadigm):
    pass


Stanza = namedtuple('Stanza', [
    'baseParadigm'
])

unknownStanza = Stanza('?')

stanzas = {
    'thing': Stanza('t'),
    'thing-wide': Stanza('tw'),
    'thing-suchness': Stanza('tsuch'),
    'tell': Stanza('tell'),
    'join-mark': Stanza('join'),
    'time': Stanza('vblex'),
    'time-mood': Stanza('tmmood')
}



def processLine(fOut, target, stanza,  srcLemmaMarks, dstLemmaMarks, paradigms):
    """
    Processes line data by writing to the appropriate template.
    Assumes all input is correctly formed e.g. that one of srcLemma and dstLemma 
    is a list of length = 1.
    @param srcLemma a list
    @param dstLemma a list
    @param paradigms must be two elems, though the elems can be empty. 
    Must be pre-stripped.
    """
    baseParadigm = stanza.baseParadigm
    paradigm = 'error'


        
    # which target?
    if target == 's':
        p = paradigms[0]
        if p: paradigm = p + '__' + baseParadigm
        else: paradigm = baseParadigm
        monodixTemplate(fOut, 
                        lemmas = srcLemmaMarks, 
                        dixParadigm = paradigm
                        )
    elif target == 'd':
        p = paradigms[1]
        if p: paradigm = p + '__' + baseParadigm
        else: paradigm = baseParadigm
        monodixTemplate(fOut, 
                        lemmas = dstLemmaMarks,
                        dixParadigm = paradigm
                        )
    elif target == 'bi':
        if(len(srcLemmaMarks) > 1):
            bilingualTemplateWithTranslationMarkRL(
            fOut,
            srcLemmaMarks,
            dstLemmaMarks[0],
            baseParadigm
            )
        elif (len(dstLemmaMarks) > 1):
            bilingualTemplateWithTranslationMarkLR(
            fOut,
            srcLemmaMarks[0],
            dstLemmaMarks,
            baseParadigm
            )
        else:
            # no alternative translations. Easy...
            bilingualTemplate(
            fOut, 
            srcLemmaMarks[0], 
            dstLemmaMarks[0], 
            baseParadigm
            )
      


def parseSet(line):
    """
    Parses a string for an initial 'xxx', or '{xxx, yyy, zzz},'.
    Returns are whitespace-stripped (tail is left-stripped).
    @return: tuple of the parsed element and line tail. The element
    will be in a list, however parsed. If the parse fails, either
    element or tail can return None.
    """
    head = ''
    tail = ''
    if line[0] != '{':
        splitLine = line.split(',', 1)
        if len(splitLine) < 1:
            printWarning("data line has too few elements?: '" + line + "'")
        elif len(splitLine) < 2:
            head = [splitLine[0]]
        else:
            head, tail = splitLine
            head = [head]
            tail = tail.lstrip()
    else:
        splitLine = line[1:].split('}', 1)
        if len(splitLine) < 1:
            printWarning("bracket not matched: '" + line + "'")
        elif len(splitLine) < 2:
            head = [splitLine[0]]
        else:
            head, tail = splitLine
            # split bracketted contents
            head = map(lambda e: e.strip(), head.split(','))
            # trailing commas still present: '{},'
            tail = suffix(tail, ',').lstrip()
    return head, tail
                

def process(inPath, outPath, target, annotate):
    """
    Process a file, stepping by line.
    """
    global lineNum
    
    fIn = open(inPath, 'r')
    fOut = open(outPath, 'w')
    
    stanza = unknownStanza
    
    for l in fIn:
        lineNum += 1
        line = l.strip()
        
        if not line or line[0] == '#':
            # skip empty lines and comments
            pass
        elif line[0] == '=':
            # detect new stanza 
            sStr = suffix(line, '=').strip().lower()
            stanza = stanzas.get(sStr, unknownStanza)
            if stanza == unknownStanza:
                printWarning("unknown stanza name: '" + sStr + "'")
            else:
                if annotate: stanzaAnnotateTemplate(fOut, sStr)
        elif stanza == unknownStanza:
            # not found a stanza, now
            # skip line if unknownStanza
            pass
        else:
            # process a line
            # slice off tail comments with 'prefix'
            cleanLine = prefix(line, '#')
            srcLemmas, tail = parseSet(cleanLine)
            # print(' ,'.join(srcLemma) + ':' + tail)
            if (tail == False):
                printError("data line has one element: '" + cleanLine + "'")
                pass
            else:
                dstLemmas, tail = parseSet(tail)
                if (tail == False): paradigms = ['', '']
                else: paradigms = tail.split(',')
                if len(srcLemmas) > 1 and len(dstLemmas) > 1:
                    printError("source and destination are both sets: '" + cleanLine + "'")
                else:
                    if len(paradigms) > 2:
                        printWarning("data line has more than two paradigms?: '" + cleanLine + "'")
                    #print('srcLemma:' + ', '.join(srcLemma))
                    #print('dstLemma:' + ', '.join(dstLemma))
                    #print('paradigms:' + ', '.join(paradigms))
                    processLine(fOut, target, stanza, srcLemmas, dstLemmas, paradigms)

    fIn.close()
    fOut.close()

# Writefile



# main

def main(argv):
    annotate = False
    inPath = 'in'
    outPath = 'out'
    target = 's'
    try:
        opts, args = getopt.getopt(argv,"ahi:o:t:", ['annotate', 'infile=','outfile=','type='])
    except getopt.GetoptError:
        print 'skel2dix.py <options> -i <inputfile> -o <outputfile>'
        sys.exit(2)
    for opt, arg in opts:
        if opt in ("-a", "--annotate"):
            annotate = True
        elif opt == '-h':
            print 'skel2dix.py <options> -i <inputfile> -o <outputfile>'
            sys.exit()
        elif opt in ("-i", "--infile"):
            inPath = arg
        elif opt in ("-o", "--outfile"):
            outputfile = arg
        elif opt in ("-t", "--type"):
            # test enumeration
            if arg != 's' and arg != 'd' and arg != 'bi':
                print ('-type option must be from: {s, d, bi}')
                sys.exit()
            target = arg
    print 'Input file: ', inPath
    print 'Target: ', target
    print 'Annotate: ', annotate
    print 'Target: ', dictionaryNames[target]

    try:
        process(inPath, outPath, target, annotate)
    except IOError:
        print('file would not open: %s' % inPath)
    #finally:

if __name__ == "__main__":
    main(sys.argv[1:])
