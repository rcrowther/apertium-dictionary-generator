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
# TODO:
# add date to annotation
# reposition paradigm prefix defaulting
# check strips() for duplication (stripped in paradigm prefix, and...?)
# sets {} to lists []
# check fails gracefully to leave partial files?
# check saving fails... on lines, anyhow?
# check stemming
# clean notifications
# one way > or <?

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
    
def mkParadigm(paradigmPrefix, baseParadigm):
    return baseParadigm if not paradigmPrefix else paradigmPrefix.strip() + '__' + baseParadigm
                                
def monodixTemplate(fOut, pairs, baseParadigm):
    # <e lm="earn"><i>earn</i><par n="reg__vblex"/></e>   
    for pair in pairs:
        lemma, stem = lemmaStem(pair.mark)
        paradigm = mkParadigm(pair.paradigm, baseParadigm)
        fOut.write('<e lm="')
        fOut.write(lemma)
        fOut.write('"><i>')
        fOut.write(stem)
        fOut.write('</i><par n="')
        fOut.write(paradigm)
        fOut.write('"/></e>\n')

def bilingualTemplate(fOut, srcPair, dstPair, baseParadigm):
    # <e><p><l>snack<s n="n"/></l><r>baggin<s n="n"/></r></p></e>
    srcM = matcher(srcPair.mark)
    dstM = matcher(dstPair.mark)

    fOut.write('<e><p><l>')
    fOut.write(srcM)
    fOut.write('<s n="')
    fOut.write(baseParadigm)
    fOut.write('"/></l><r>')
    fOut.write(dstM)
    fOut.write('<s n="')
    fOut.write(baseParadigm)
    fOut.write('"/></r></p></e>\n')
    
def bilingualTemplateWithTranslationMarkRL(
    fOut,
     srcPairs,
     dstPair,
     baseParadigm
    ):
    # <e srl="snack D"><p><l>snack<s n="n"/></l><r>baggin<s n="n"/></r></p></e>
    first = True
    dstM = matcher(dstPair.mark)
    for srcPair in srcPairs:
        srcL, srcM = lemmaMatcher(srcPair.mark)
        fOut.write('<e srl="')
        fOut.write(srcL)
        if first: 
            fOut.write(' D')
            first = False
        fOut.write('"><p><l>')
        fOut.write(srcM)
        fOut.write('<s n="')
        fOut.write(baseParadigm)
        fOut.write('"/></l><r>')
        fOut.write(dstM)
        fOut.write('<s n="')
        fOut.write(baseParadigm)
        fOut.write('"/></r></p></e>\n')
    
def bilingualTemplateWithTranslationMarkLR(
    fOut,
     srcPair,
     dstPairs,
     baseParadigm
    ):
    # <e slr="baggin D"><p><l>snack<s n="n"/></l><r>baggin<s n="n"/></r></p></e>
    first = True
    srcM = matcher(srcPair.mark)
    for dstPair in dstPairs:
        dstL, dstM = lemmaMatcher(dstPair.mark)
        fOut.write('<e slr="')
        fOut.write(dstL)
        if first: 
            fOut.write(' D')
            first = False
        fOut.write('"><p><l>')
        fOut.write(srcM)
        fOut.write('<s n="')
        fOut.write(baseParadigm)
        fOut.write('"/></l><r>')
        fOut.write(dstM)
        fOut.write('<s n="')
        fOut.write(baseParadigm)
        fOut.write('"/></r></p></e>\n')
    
def stanzaAnnotateTemplate(fOut, stanzaName, inPath):
    fOut.write('\n<!-- ')
    fOut.write(stanzaName)
    fOut.write(' -->\n')
    
    idx = inPath.rfind('/')
    fName = inPath if idx == -1 else inPath[:idx]
    fOut.write('<!-- ')
    fOut.write(fName)
    fOut.write(' -->\n')


Stanza = namedtuple('Stanza', [
    'baseParadigm'
])



unknownStanza = Stanza('?')


stanzas = {
    'n': Stanza('n'),
    'pn': Stanza('pn'),
    'prn': Stanza('prn'),
    'adj': Stanza('adj'),
    'itg': Stanza('itg'),
    'num': Stanza('num'),
    'vblex': Stanza('vblex'),
    'vbmod': Stanza('vbmod'),
    'vaux': Stanza('vaux'),
    'vbser': Stanza('ToBeVerb'),
    'vbhaver': Stanza('ToHaveVerb'),
    'adv': Stanza('adv'),
    'pr': Stanza('pr'),
    'ij': Stanza('ij'),
    'cnjsub': Stanza('cnjsub'),
    'cnjcoo': Stanza('cnjcoo'),
    'cnjadv': Stanza('cnjadv'),
    'pers': Stanza('pers'),
    'ref': Stanza('ref'),
    'res': Stanza('res')
}

#stanzas = {
    #'Noun': Stanza('n'),
    #'ProperNoun': Stanza('pn'),
    #'Pronoun': Stanza('prn'),
    #'Adjective': Stanza('adj'),
    #'Interrogative': Stanza('itg'),
    #'Numeral': Stanza('num'),
    #'Verb': Stanza('vblex'),
    #'ModalVerb': Stanza('vbmod'),
    #'AuxiliaryVerb': Stanza('vaux'),
    #'ToBeVerb': Stanza('vbser'),
    #'ToHaveVerb': Stanza('vbhaver'),
    #'Adverb': Stanza('adv'),
    #'Preposition': Stanza('pr'),
    #'Interjection': Stanza('ij'),
    #'SubordinatingConjunction': Stanza('cnjsub'),
    #'Co-ordinatingConjunction': Stanza('cnjcoo'),
    #'AdverbConjunction': Stanza('cnjadv'),
    #'PersonalPronoun': Stanza('pers'),
    #'ReflexivePronoun': Stanza('ref'),
    #'ReciprocalPronoun': Stanza('res')
#}

#stanzas = {
    #'thing': Stanza('t'),
    #'thing-wide': Stanza('tw'),
    #'thing-suchness': Stanza('tsuch'),
    #'tell': Stanza('tell'),
    #'stead-way': Stanza('steadw'),
    #'time': Stanza('vblex'),
    #'time-mood': Stanza('tmmood')
#}

MarkParadigmPair = namedtuple('MarkParadigmPair', [
    'mark',
    'paradigm'
])

ParsedData = namedtuple('ParsedData', [
    'src',
    'dst',
    'defaultParadigms'
])

def processLine(fOut, targetDictionary, stanza, parseResult):
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
    if targetDictionary == 's':
        monodixTemplate(
                        fOut, 
                        parseResult.src, 
                        baseParadigm
                        )
    elif targetDictionary == 'd':
        monodixTemplate(
                        fOut, 
                        parseResult.dst, 
                        baseParadigm
                        )
    elif targetDictionary == 'bi':
        if(len(parseResult.src) > 1):
            bilingualTemplateWithTranslationMarkRL(
            fOut,
            parseResult.src, 
            parseResult.dst[0], 
            baseParadigm
            )
        elif (len(parseResult.dst) > 1):
            bilingualTemplateWithTranslationMarkLR(
            fOut,
            parseResult.src[0], 
            parseResult.dst, 
            baseParadigm
            )
        else:
            # no alternative translations. Easy...
            bilingualTemplate(
            fOut, 
            parseResult.src[0], 
            parseResult.dst[0],  
            baseParadigm
            )    
  


# Anyone who likes Python because it is clean should stop long before
# this.
#...and it should be a function, but Python scoping can't handle it
class Parser():
    """
    Parses a line.
    """
    EOL = '\f'

    def __init__(self):
        self.b = [[],[]]
        self.defaultParadigms = ['', '']
        self.line = ''
        self.prev = 0
        self.i = 0
        self.curr = ''
        self.mark = ''
        self.paradigm = ''
        self.side = 0

    def __printOut(self):
        print("mark:" + self.mark)
        print("curr:" + self.curr)
        print("i: {0}".format(self.i))
        
    def skip(self):
        self.i = self.i + 1
    
    def findAny(self, chars):
        self.prev = self.i
        for x in range(self.i, len(self.line)):
            #print("x: {0}".format(x))
            self.curr = self.line[x] 
            if self.curr in chars:
                self.i = x
                return
        # EOL
        self.i = len(self.line)
        self.curr = self.EOL
        return
    
    def loadPair(self):
        self.b[self.side].append(MarkParadigmPair(self.mark, self.paradigm))
        self.mark = ''
        self.paradigm = ''

    def paradigmR(self):
        self.findAny('.}{:#')
        self.paradigm = self.line[self.prev:self.i]
    
    def markR(self):
        self.findAny('.}{:#')
        self.mark = self.line[self.prev:self.i]
    
    def pair(self):
        self.markR()
        #self.__printOut()
        if self.curr == ':':
            self.skip()
            self.paradigmR()
        self.loadPair()
    
    def pairList(self):
        #self.__printOut()
        while self.curr == '.':
            self.skip()
            self.pair()
        #self.skip()
        
    def set(self):
        self.findAny('.}{:#')

    def parseDefaultParadigmOption(self, target):
        if self.curr ==  ':':
            self.skip()
            self.findAny('.}{:#')
            self.defaultParadigms[target] = self.line[self.prev:self.i]
        
    def parseSide(self, target):
        self.side = target
        self.findAny('.}{:#')
        #self.__printOut()

        if self.curr == '.':
            self.skip()
            self.pair()
        elif self.curr ==  '{':
            self.skip()
            self.findAny('.}{:#')
            if self.curr == '.':
                self.pairList()
                if self.curr == '}':
                    self.skip()
                    self.findAny('.}{:#')
                    self.parseDefaultParadigmOption(target)
                else:
                    printWarning("set not closed?: '" + self.line + "'")
                    # kill with fake EOL
                    self.curr = self.EOL
            else:
                printWarning("set open not followed by mark?: '" + self.line + "'")
                # kill with fake EOL
                self.curr = self.EOL

        elif self.curr ==  ':':
            printWarning("paradigm not preceeded by mark: '" + self.line + "'")
            # kill with fake EOL
            self.curr = self.EOL
        elif self.curr ==  '#':
            # kill with fake EOL
            self.curr = self.EOL
        elif self.curr ==  '}':
            printWarning("bracket not matched: '" + self.line + "'")
            # kill with fake EOL
            self.curr = self.EOL
        elif self.curr == self.EOL:
            printWarning("data expected, but End Of Line: '" + self.line + "'")


    def parse(self, targetLine):
        """
        Parse a line.
        Output is not stripped.
        Reusable (oh, crimes, crimes).
        @return a list of two lists of MarkParadigmPairs. If the parse 
        fails, None, while emitting error messages.
        """
        self.b = [[],[]]
        self.defaultParadigms = ['', '']
        self.line = targetLine
        self.prev = 0
        self.i = 0
        self.curr = ''
        self.mark = ''
        self.paradigm = ''
        self.side = 0
        
        # root term for parse
        #print('to parse: "' + self.line + '"')
        self.parseSide(0)
        if  self.curr == '.' or self.curr == '{':
            self.parseSide(1)
            return ParsedData(self.b[0], self.b[1], self.defaultParadigms)
        else:
            printWarning("Unable to find second element: '" + self.line + "'")
            return None
            
################

        

def process(inPath, outPath, targetDictionary, annotate):
    """
    Process a file, stepping by line.
    """
    global lineNum
    
    fIn = open(inPath, 'r')
    fOut = open(outPath, 'w')
    
    stanza = unknownStanza
    
    p = Parser()

        
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
                if annotate: stanzaAnnotateTemplate(fOut, sStr, inPath)
        elif stanza == unknownStanza:
            # not found a stanza, now
            # skip line if unknownStanza
            pass
        else:
            # process a line
            r = p.parse(line)
            if r == None:
                print('parse fail?')
            else:
                #print("parse:")
                #print(r.src)
                #print(r.dst) 
               # print(r.defaultParadigms)
                #print("--")

                # verify this
                if len(r.src)> 1 and len(r.dst) > 1:
                    printError("source and destination are both sets: '" + line + "'")
                else:
                    # assert paradigms, fill empty from default
                    # TODO: This is placed wastefully early,
                    # as bi- template does not uses paradigm prefixs
                    def assertParadigm(pairs, defaultP):
                        b = []
                        for pair in pairs:
                            p = pair.paradigm.strip()
                            newP = defaultP if not p else p
                            b.append(MarkParadigmPair(pair.mark, newP))
                        return b
                    srcNew = assertParadigm(r.src, r.defaultParadigms[0])
                    dstNew = assertParadigm(r.dst, r.defaultParadigms[1])

                    # defaults now processed, abandon
                    newR = ParsedData(srcNew, dstNew, [])
                    processLine(fOut, targetDictionary, stanza, newR)

    fIn.close()
    fOut.close()

def printHelp():
    print ('Usage: skel2dix.py <options> -i <inputfile> -o <outputfile>\n'
        "Keynames in the 'stanza' variable must be adjusted to match input files\n\n"
        '  -a, --annotate       annotate the output with stanza information\n'
        '  -h, --help           print this help\n'
        "  -t, --type           output dictionary type ('s' source mono,\n"
        "                       'd' destination mono, or 'bi' bilingual)\n")
        
        
        
# main

def main(argv):
    annotate = False
    inPath = 'in'
    outPath = ''
    targetDictionary = 's'
    try:
        opts, args = getopt.getopt(argv,"ahi:o:t:", ['annotate', 'infile=','outfile=','type='])
    except getopt.GetoptError:
        printHelp()
        sys.exit(2)
    for opt, arg in opts:
        if opt in ("-a", "--annotate"):
            annotate = True
        elif opt == '-h':
            printHelp()
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
            targetDictionary = arg
 
        
    #  if not stated, default the output filepath
    if not outPath:
        i = inPath.rfind('.')
        if i != -1:
            outPath = inPath[:i] + '-' + targetDictionary + '.parDix'
        else:
            outPath = inPath + '-' + targetDictionary + '.parDix'
            
    print 'Input file:', inPath
    print 'Output file:', outPath

    print 'targetDictionary:', targetDictionary
    print 'Annotate:', annotate
    print 'targetDictionary:', dictionaryNames[targetDictionary]

    try:
        process(inPath, outPath, targetDictionary, annotate)
    except IOError:
        print('file would not open: %s' % inPath)
    #finally:

if __name__ == "__main__":
    main(sys.argv[1:])
