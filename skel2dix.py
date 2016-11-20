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

    ./skel2dix.py <options> inputFiles

Options include,

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


Auto-handling of paradigm slash marks
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
In monolingual dictionaries, entry matches will be cropped by slashed paradigm marks::

    dandy :bab/y

generates,

    <e lm="dandy"><i>dand</i><par n="bab/y__n"/></e>
   
    ...

Note that the script used the supplied text for the lemma name, then cropped for the text match.



Alternate/ambiguous translation
-------------------------------
Data lines can include sets of items::

    {weird, bizarre, strange}, bizarre

In mono-dictionaries, these will be expanded into individual entries.
In bilingual dictionaries, entries will be marked with the appropriate `slr`/`srl`
marks. The first item in the set is the default::

    <e><p><l>weird<s n="adj"/></l><r>bizarre<s n="adj"/></r></p></e>    
    <e r="LR"><p><l>bizarre<s n="adj"/></l><r>bizarre<s n="adj"/></r></p></e>    
    <e r="LR"><p><l>strange<s n="adj"/></l><r>bizarre<s n="adj"/></r></p></e>    
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
#x set, not derive, target basenames
# lexical .lrx skeleton?
#x fix annotation to basenames
# default paradigms?

# add date to annotation
# when no paradigm prefix, offer, or even default, in mondicts 
# to <s n=""/> not <par n=""/>
# reposition paradigm prefix defaulting
# check strips() for duplication (stripped in paradigm prefix, and...?)
# sets {} to lists []
# check fails gracefully to leave partial files?
# check saving fails... on lines, anyhow?
# check stemming
# clean notifications
# one way > or <?

import sys, getopt, re
import os.path
import argparse
from collections import namedtuple


dictionaryNames = {
    's': 'source monodix',
    'd': 'destination monodix',
    'bi': 'bi-lingual dictionary'
}

lineNum = 0


Stanza = namedtuple('Stanza', [
    'baseParadigm'
])



unknownStanza = Stanza('?')


stanzas = {
    'n': Stanza('n'),
    'pn': Stanza('pn'),
    'prn': Stanza('prn'),
    'adj': Stanza('adj'),
    'det': Stanza('det'),
    'itg': Stanza('itg'),
    'num': Stanza('num'),
    'vblex': Stanza('vblex'),
    'vbmod': Stanza('vbmod'),
    'vaux': Stanza('vaux'),
    'vbser': Stanza('vbser'),
    'vbhaver': Stanza('vbhaver'),
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

def parseWarning(message):
    global lineNum
    print('{0:2d}:[warning] {1}'.format(lineNum, message))
    
def parseError(message):
    global lineNum
    print('{0:2d}:[error] {1}'.format(lineNum, message))
    
def printWarning(message):
    print('[warning] {0}'.format(message))
    
def printError(message):
    print('[error] {0}'.format(message))
    
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


def lemmaStem(entryData):
    """
    creates a lemma and stem matcher.
    remove slash, on stem insert blank-tags.
    """
    p = entryData.paradigm.strip()
    markStripped = entryData.mark.strip()
    stemWithBlanks = markStripped.replace(" ", "<b/>")
    idx = p.find('/')
    if idx == -1:
        return markStripped, stemWithBlanks
    else:
        try:
            stemSliceIdx = len(stemWithBlanks) - (len(p) - idx - 1)
        except:
            return None
        return markStripped, stemWithBlanks[:stemSliceIdx]


def matcher(lemmaMark):
    """
    creates a string matcher.
    remove slash, insert blank-tags.
    used for late matches in bi-lingual dictionaries.
    """
    return lemmaMark.strip().replace(" ", "<b/>")
    
def lemmaMatcher(lemmaMark):
    l = lemmaMark.strip()
    return l, l.replace(" ", "<b/>")
    
def mkParadigm(paradigmPrefix, baseParadigm):
    return baseParadigm if not paradigmPrefix else paradigmPrefix.strip() + '__' + baseParadigm
                                
def monodixTemplate(fOut, pairs, baseParadigm):
    # <e lm="tatty"><i>tatt</i><par n="bab/y__n"/></e>
    for pair in pairs:
        ls = lemmaStem(pair)
        if not ls:
            printError("building lemma and stem mark:{0} paradigm:{1}".format(pair.mark, pair.paradigm))
        else:
            lemma, stem = ls
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
        #fOut.write('<e srl="')
        fOut.write('<e')
        if first: 
            first = False
        else:
            fOut.write(' r="LR"')

        #fOut.write(srcL)
        #if first: 
            #fOut.write(' D')
            #first = False
        fOut.write('><p><l>')
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
        #fOut.write('<e slr="')
        fOut.write('<e')
        if first: 
            first = False
        else: 
            fOut.write(' r="RL"')
        
        #fOut.write(dstL)
        #if first: 
            #fOut.write(' D')
            #first = False
        fOut.write('><p><l>')
        fOut.write(srcM)
        fOut.write('<s n="')
        fOut.write(baseParadigm)
        fOut.write('"/></l><r>')
        fOut.write(dstM)
        fOut.write('<s n="')
        fOut.write(baseParadigm)
        fOut.write('"/></r></p></e>\n')


def lemmaPrintTemplate(fOut, entryDatas):
    for entryData in entryDatas:
        lemma = entryData.mark.strip()
        fOut.write(lemma)
        fOut.write('\n')
        
        
def stanzaAnnotateTemplate(fOut, stanzaName, inPath):
    fOut.write('\n<!-- ')
    fOut.write(stanzaName)
    fOut.write(' -->\n')
    
    # initial tests guarantee a basename exists 
    fName = os.path.basename(inPath)
    fOut.write('<!-- ')
    fOut.write(fName)
    fOut.write(' -->\n')




########################
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
  

        
def processLineForLemma(fOut, dictionaryType, parseResult):
    # <e lm="tatty"><i>tatt</i><par n="bab/y__n"/></e>
    if dictionaryType == 's':
        lemmaPrintTemplate(fOut, parseResult.src)
    elif dictionaryType == 'd':
        lemmaPrintTemplate(fOut, parseResult.dst)
    else:
        # bi and a do the same thing, print all lemmas
        lemmaPrintTemplate(fOut, parseResult.src)
        lemmaPrintTemplate(fOut, parseResult.dst)

            
# Anyone who likes Python because it is clean should stop long before
# classes.
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

    def _printOut(self):
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
        #self._printOut()
        if self.curr == ':':
            self.skip()
            self.paradigmR()
        self.loadPair()
    
    def pairList(self):
        #self._printOut()
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
        #self._printOut()

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
                    parseError("set not closed?: '" + self.line + "'")
                    # kill with fake EOL
                    self.curr = self.EOL
            else:
                parseError("set open not followed by mark?: '" + self.line + "'")
                # kill with fake EOL
                self.curr = self.EOL

        elif self.curr ==  ':':
            parseError("paradigm not preceeded by mark: '" + self.line + "'")
            # kill with fake EOL
            self.curr = self.EOL
        elif self.curr ==  '#':
            # kill with fake EOL
            self.curr = self.EOL
        elif self.curr ==  '}':
            parseError("bracket not matched: '" + self.line + "'")
            # kill with fake EOL
            self.curr = self.EOL
        elif self.curr == self.EOL:
            parseError("data expected, but End Of Line: '" + self.line + "'")


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
            parseWarning("Unable to find second element: '" + self.line + "'")
            return None
            
################

def processLemmas(inPath, outPath, dictionaryType, annotate):
    """
    Process a file, stepping by line.
    """
    global lineNum
    
    print(outPath)
    fIn = open(inPath, 'r')
    fOut = open(outPath, 'a')
    
    stanza = unknownStanza
    
    p = Parser()

    lineNum = 0
    
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
                parseWarning("unknown stanza name: '" + sStr + "'")
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
                printWarning('parse fail?')
            else:
                # verify this
                if len(r.src)> 1 and len(r.dst) > 1:
                    parseError("source and destination are both sets: '" + line + "'")
                else:
                    # gather entryData, no paradigm needed
                    srcNew = [MarkParadigmPair(e.mark, '') for e in r.src]
                    dstNew = [MarkParadigmPair(e.mark, '') for e in r.dst]
                    # defaults now processed, abandon
                    newR = ParsedData(srcNew, dstNew, [])
                    # no stanza?
                    processLineForLemma(fOut, dictionaryType, newR)

    fIn.close()
    fOut.close()



def process(inPath, outPath, dictionaryType, annotate):
    """
    Process a file, stepping by line.
    """
    global lineNum
    
    fIn = open(inPath, 'r')
    fOut = open(outPath, 'a')
    
    stanza = unknownStanza
    
    p = Parser()

    lineNum = 0
    
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
                parseWarning("unknown stanza name: '" + sStr + "'")
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
                printWarning('parse fail?')
            else:
                #print("parse:")
                #print(r.src)
                #print(r.dst) 
               # print(r.defaultParadigms)
                #print("--")

                # verify this
                if len(r.src)> 1 and len(r.dst) > 1:
                    parseError("source and destination are both sets: '" + line + "'")
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
                    processLine(fOut, dictionaryType, stanza, newR)

    fIn.close()
    fOut.close()
    
def _silentRemove(entryPath):
    try:
        os.remove(entryPath)
    except OSError:
        pass
    
def outputEntryPath(outputBasenamePath, basename, tpe):
    return os.path.join(outputBasenamePath, basename + '-' + tpe + '.parDix')

def processOpts(opts):
    if (opts.lemmaFile):
        o = os.path.join(opts.outputBasenamePath,  opts.outputBasename + '-lemmas')
        # delete existing output file
        _silentRemove(o) 
        for inPath in opts.infiles:
            processLemmas(inPath, o, opts.type, opts.annotate)

    else:
        if(opts.type == 'a'):
            oS = outputEntryPath(opts.outputBasenamePath, opts.outputBasename, 's')
            oD = outputEntryPath(opts.outputBasenamePath, opts.outputBasename, 'd')
            oBi = outputEntryPath(opts.outputBasenamePath, opts.outputBasename, 'bi')
            # delete existing output files
            _silentRemove(oS) 
            _silentRemove(oD) 
            _silentRemove(oBi) 
    
            for inPath in opts.infiles:
                process(inPath, oS, 's', opts.annotate)
                process(inPath, oD, 'd', opts.annotate)
                process(inPath, oBi, 'bi', opts.annotate)
                
        else:
            oPath = outputEntryPath(opts.outputBasenamePath, opts.outputBasename, opts.type)
            # trunc the output files
            _silentRemove(oPath) 
    
            for inPath in opts.infiles:
                process(inPath, oPath, opts.type, opts.annotate)

        
def stripExtension(path):
    #os.path.basename(path)
    i = path.rfind('.')
    return path[:i] if (i != -1) else path
    

# main

def main(argv):
    annotate = False
    inPath = 'in'
    outPath = ''
    targetDictionary = 's'
    
    parser = argparse.ArgumentParser(
        epilog= "NB: keynames in the internal 'stanza' variable must be adjusted to match input files"
        )
        
    parser.add_argument("-a", "--annotate", 
        default=False,
        help="annotate the output with stanza information",
        action="store_true"
        )
        
    parser.add_argument("-l", "--lemmaFile",
        default=False,
        help="output lemmas to a file, one per line. Parses like the main parser (ignoring unknown stanza names etc.) Responds to -t, printing src/dst/all dictionary entries. Also responds to -a.",
        action="store_true"
        )
        
    parser.add_argument("-t", "--type",
        choices=['s', 'd', 'bi', 'a'],
        default='bi',
        help="output dictionary type ('s': source monodix, 'd': destination monodix, or 'bi': bilingualdix. Default: 'bi')",
        )
        
    parser.add_argument("-o", "--outputBasename",
        default='output',
        help="output file name. Must not be a path (default: 'output')"
        )

    parser.add_argument("infiles", 
        nargs='*',
        help="files for input"
        )
        
    args = parser.parse_args()

    # assert infiles as absolute paths
    args.infiles = [os.path.abspath(f) for f in args.infiles]
    # test infiles exist
    success = True
    for f in args.infiles:
        if (not os.path.exists(f)):
            printError('Path not exists path: {0}'.format(f))
            success = False
            break
        if (os.path.isdir(f)):
            printError('Path is dir path: {0}'.format(f))
            success = False
            break
    if (not success):
        return 1
        
    # test basename is not a path
    if (args.outputBasename.find(os.pathsep) != -1):
        printError('-o outputBasename option appears to be a path: {0}'.format(args.outputBasename))
        return 1
        
    # set output directory to first inFile arg
    args.outputBasenamePath = os.path.dirname(args.infiles[0]) 

    print ('Input files:' + str(args.infiles))
    print ('OutputBasename:' + str(args.outputBasename))
    print ('OutputBasenamePath:' + str(args.outputBasenamePath))
    print ('Type:' + str(args.type))
    print ('Annotate:' + str(args.annotate))
    print ('LemmaFile:' + str(args.lemmaFile))

    
    
    try:
        processOpts(args)
    except IOError:
        printError('file would not open: %s' % inPath)


if __name__ == "__main__":
    main(sys.argv[1:])
