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
# clean notifications
# one way > or <

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
    """
    creates a lemma and stem matcher.
    remove slash, on stem insert blank-tags.
    """
    lm = lemmaMark.strip()
    idx = lm.find('/')
    if idx == -1:
        return  lm, lm.replace(" ", "<b/>")
    else:
        return lm.replace("/", ""),  lm[:idx].replace(" ", "<b/>")


def matcher(lemmaMark):
    """
    creates a string matcher.
    remove slash, insert blank-tags.
    used for late matches in bi-lingual dictionaries.
    """
    return lemmaMark.strip().replace("/", "").replace(" ", "<b/>")
    
def lemmaMatcher(lemmaMark):
    l = lemmaMark.strip().replace("/", "")
    return l, l.replace(" ", "<b/>")
    
    
def monodixTemplate(fOut, lemmas, dixParadigm):
    # <e lm="earn"><i>earn</i><par n="reg__vblex"/></e>   
    for lemmaMark in lemmas:
        lemma, stem = lemmaStem(lemmaMark)
        fOut.write('<e lm="')
        fOut.write(lemma)
        fOut.write('"><i>')
        fOut.write(stem)
        fOut.write('</i><par n="')
        fOut.write(dixParadigm)
        fOut.write('"/></e>\n')

def bilingualTemplate(fOut, srcLemma, dstLemma, dixParadigm):
    # <e><p><l>snack<s n="n"/></l><r>baggin<s n="n"/></r></p></e>
    srcM = matcher(srcLemma)
    dstM = matcher(dstLemma)

    fOut.write('<e><p><l>')
    fOut.write(srcM)
    fOut.write('<s n="')
    fOut.write(dixParadigm)
    fOut.write('"/></l><r>')
    fOut.write(dstM)
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
    dstM = matcher(dstLemma)
    for srcLemma in srcLemmas:
        srcL, srcM = lemmaMatcher(srcLemma)
        fOut.write('<e srl="')
        fOut.write(srcL)
        if first: 
            fOut.write(' D')
            first = False
        fOut.write('"><p><l>')
        fOut.write(srcM)
        fOut.write('<s n="')
        fOut.write(dixParadigm)
        fOut.write('"/></l><r>')
        fOut.write(dstM)
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
    srcM = matcher(srcLemma)
    for dstLemma in dstLemmas:
        dstL, dstM = lemmaMatcher(dstLemma)
        fOut.write('<e slr="')
        fOut.write(dstL)
        if first: 
            fOut.write(' D')
            first = False
        fOut.write('"><p><l>')
        fOut.write(srcM)
        fOut.write('<s n="')
        fOut.write(dixParadigm)
        fOut.write('"/></l><r>')
        fOut.write(dstM)
        fOut.write('<s n="')
        fOut.write(dixParadigm)
        fOut.write('"/></r></p></e>\n')
    
def stanzaAnnotateTemplate(fOut, stanzaName):
    fOut.write('\n<!-- ')
    fOut.write(stanzaName)
    fOut.write(' -->\n')



Stanza = namedtuple('Stanza', [
    'baseParadigm'
])

unknownStanza = Stanza('?')

stanzas = {
    'thing': Stanza('t'),
    'thing-wide': Stanza('tw'),
    'thing-suchness': Stanza('tsuch'),
    'tell': Stanza('tell'),
    'stead-way': Stanza('steadw'),
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
        if p: paradigm = p.strip() + '__' + baseParadigm
        else: paradigm = baseParadigm
        monodixTemplate(fOut, 
                        lemmas = srcLemmaMarks, 
                        dixParadigm = paradigm
                        )
    elif target == 'd':
        p = paradigms[1]
        if p: paradigm = p.strip() + '__' + baseParadigm
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
    @return: the parsed element, a list, and tail, a string. The element
    will be a list with at least one element, maybe empty.
    """
    head = ['']
    tail = ''
    if line[0] != '{':
        splitLine = line.split(',', 1)
        if len(splitLine) < 1:
            printWarning("data line has too few elements?: '" + line + "'")
        elif len(splitLine) < 2:
            head = [splitLine[0]]
        else:
            head = [splitLine[0]]
            tail = splitLine[1].lstrip()
    else:
        # drop the bracket
        splitLine = line[1:].split('}', 1)
        if len(splitLine) < 1:
            printWarning("bracket not matched: '" + line + "'")
        elif len(splitLine) < 2:
            head = [splitLine[0]]
        else:
            # split bracketed contents
            #head = map(lambda e: e.strip(), splitLine[0].split(','))
            head = splitLine[0].split(',')
            # trailing commas maybe still present e.g. '{},'
            tail = splitLine[1].lstrip()
            if len(tail) > 0 and tail[0] == ',':
                tail = tail[1:].lstrip()
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
            #print('srcLemmas:' + ' ,'.join(srcLemmas))
            if not tail:
                printError("data line has one element: '" + cleanLine + "'")
                pass
            else:
                dstLemmas, tail = parseSet(tail)
                #print('dstLemmas:' + ' ,'.join(dstLemmas))
                #print('tail: "' + tail + '"')

                if len(srcLemmas) > 1 and len(dstLemmas) > 1:
                    printError("source and destination are both sets: '" + cleanLine + "'")
                else:
                    paradigms = ['', ''] if not tail else tail.split(',')
                    #print('paradigms:' + ', '.join(paradigms))

                    if len(paradigms) < 2:
                        printWarning("data line has one paradigm?: '" + cleanLine + "'")
                        paradigms.append('')

                    if len(paradigms) > 2:
                        printWarning("data line has more than two paradigms?: '" + cleanLine + "'")
                    #print('srcLemmas:' + ', '.join(srcLemmas))
                    #print('dstLemmas:' + ', '.join(dstLemmas))
                    #print('paradigms len:{0}'.format(len(paradigms)))

                    processLine(fOut, target, stanza, srcLemmas, dstLemmas, paradigms)

    fIn.close()
    fOut.close()

# Writefile



# main

def main(argv):
    annotate = False
    inPath = 'in'
    outPath = ''
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
            outPath = arg
        elif opt in ("-t", "--type"):
            # test enumeration
            if arg != 's' and arg != 'd' and arg != 'bi':
                print ('-type option must be from: {s, d, bi}')
                sys.exit()
            target = arg
            
    #  if not stated, default the output filepath
    if not outPath:
        i = inPath.rfind('.')
        if i != -1:
            outPath = inPath[:i] + '-' + target + '.parDix'
        else:
            outPath = inPath + '-' + target + '.parDix'
            
    print 'Input file:', inPath
    print 'Output file:', outPath

    print 'Target:', target
    print 'Annotate:', annotate
    print 'Target:', dictionaryNames[target]

    try:
        process(inPath, outPath, target, annotate)
    except IOError:
        print('file would not open: %s' % inPath)
    #finally:

if __name__ == "__main__":
    main(sys.argv[1:])
