#!/usr/bin/env python

"""
    skel2dix
    ========
    Preprocessor for 'apertium' .dix files.
    
    If you are compiling from corpus, you need power tools. If you are 
    editing existing fles, you need a text editor with XML support.
    This script is for a limited use case, where you have organised
    dictionary infofmation, and need to generate XML.
    
    The text file input data is in this form,::
    
        wordToTranslate, translationWord, Optional(firstParadigmName, second paradigmName)
    
    single lines, one per translation,
    
        head, noggin
        ...
        
    
    
    What it can not do
    ------------------
    The script is an automated input helper. There are many Apertiumn 
    features it can not create, but major items are,
    
    No full output
        The results in the output files will need to be pasted into 
        dictionaries. The script does the grunt work.
    
    Dictionaries only
        no transfer files etc.
         
    Cross-category hints can not be added to bi-lingual dictionaries
        No shifting to femine or male end-marks/inflexions, unknown
        gender marks etc.
        
    To add other features the generated code will need to be
    hand-edited.
    
    Usage
    ~~~~~
    From the commandline,::
    
        ./skel2dix.py -i /.../inputFile
    
    -i : input file path
    -o : output filepath (optional, taken from input)
    -t : 's' for mono dict source, 'd' for mondict destination. 'bi' for bilingual
    -s : add stanza annotation
    
    Many of the following examples are for mono-dictionaries, to keep 
    the examples cleaner.
    
    
    Stanzas
    ~~~~~~~
    Marks groups of word type.
    
    Are introduced with  OneOrMore('='),::
    
        == verb
        
    Stanza marks affect output. They are mapped in this structure,::
    
        stanzas = {
        'verb': Stanza('vblex'),
        ...
        }
        
    Stanza marks are case-insensitive (can be titled in source, but lower in the ''stanza'' array).
    
    If text data do not include optional paradigm marks, the mark defaults to the 
    value mapped in ''stanza''. So,::
    
        buy, acheter
         
    generates,::
    
        <e lm="buy"><i>buy</i><par n="vblex"/></e> 

    but,::

    
        buy, acheter, irregularbuy, regularverb
         
    generates,::
    
        <e lm="buy"><i>buy</i><par n="irregularbuy__vblex"/></e>
        
        
    Unrecognised stanza names
    -------------------------
    If a stanza is not mapped in the ''stanza'' structure, following 
    data is not parsed.
    
    Can be useful for commenting out big blocks of data.
    
    
 
    
    Other Features
    ~~~~~~~~~~~~~~
    
    Comments
    --------
    Comments are introduced with '#',::
    
        # a comment
        
    Comments can follow data lines,::
    
    
    Stemming-paradigm notation
    --------------------------
    If optional dialogue notation includes the slash, 
    the XML is constructed with a stem,::
    
        find, trouver, f/ind, trouv/er
    
        <e lm="find"><i>f</i><par n="f/ind__vblex"/></e> 
    
    
    Alternate/ambiguous translation
    -------------------------------
    Data lines can include sets of items,::
    
        {wierd, bizzare, strange}, bizzare
    
    In all dictionaries, these will be expanded into individual entries.
    In bilingual dictionaries, entries will be marked with the appropriate 'slr'/'srl'
    marks. The first item in the set is the default,::
    
        <e srl="wierd D"><p><l>wierd<s n="vblex"/></l><r>bizzare<s n="vblex"/></r></p></e>    
        ...
        
    Multi-word usage
    ----------------
    
    Whitespace in word definitions (apart from head and tail whitespace)
    will be treated as multi-word definitions,::
    
        a lot, beaucoup
    
    generates,::
        
        <e lm="a lot"><i>a<b/>lot</i><par n="adj"/></e>   
    
    :copyright: 2016 Rob Crowther
    :license: GPL, see LICENSE for details.
"""
# ? not covereed
# or <b/>
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


def monodixTemplate(fOut, dixLemma, dixStem, dixParadigm):
    # <e lm="earn"><i>earn</i><par n="reg__vblex"/></e>   
    fOut.write('<e lm="')
    fOut.write(dixLemma)
    fOut.write('"><i>')
    fOut.write(dixStem)
    fOut.write('</i><par n="')
    fOut.write(dixParadigm)
    fOut.write('"/></e>\n')

def bilingualTemplate(fOut, dixLemma1, dixLemma2, dixParadigmMark):
#       <e><p><l>snack<s n="n"/></l><r>baggin<s n="n"/></r></p></e>
    fOut.write('<e><p><l>')
    fOut.write(dixLemma1)
    fOut.write('<s n="')
    fOut.write(dixParadigmMark)
    fOut.write('"/></l><r>')
    fOut.write(dixLemma2)
    fOut.write('<s n="')
    fOut.write(dixParadigmMark)
    fOut.write('"/></r></p></e>\n')
    
def bilingualTemplateWithTranslationMarkRL(
    fOut,
     srcLemmas,
     dstLemma,
     dixParadigmMark
    ):
    #  <e srl="snack D"><p><l>snack<s n="n"/></l><r>baggin<s n="n"/></r></p></e>
    # <e slr="baggin D"><p><l>snack<s n="n"/></l><r>baggin<s n="n"/></r></p></e>
    first = True
    dst= dstLemma[0]

    for src in srcLemmas:
        fOut.write('<e srl="')
        fOut.write(src)
        if first: 
            fOut.write(' D')
            first = False
        fOut.write('"><p><l>')
        fOut.write(src)
        fOut.write('<s n="')
        fOut.write(dixParadigmMark)
        fOut.write('"/></l><r>')
        fOut.write(dst)
        fOut.write('<s n="')
        fOut.write(dixParadigmMark)
        fOut.write('"/></r></p></e>\n')
    
def bilingualTemplateWithTranslationMarkLR(
    fOut,
     srcLemma,
     dstLemmas,
     dixParadigmMark
    ):
    # <e slr="baggin D"><p><l>snack<s n="n"/></l><r>baggin<s n="n"/></r></p></e>
    first = True
    src = srcLemma[0]
    for dst in dstLemmas:
        fOut.write('<e slr="')
        fOut.write(dst)
        if first: 
            fOut.write(' D')
            first = False
        fOut.write('"><p><l>')
        fOut.write(src)
        fOut.write('<s n="')
        fOut.write(dixParadigmMark)
        fOut.write('"/></l><r>')
        fOut.write(dst)
        fOut.write('<s n="')
        fOut.write(dixParadigmMark)
        fOut.write('"/></r></p></e>\n')
    
    
def timeTemplate(fOut, dixLemma, dixStem, dixParadigm):
    pass


Stanza = namedtuple('Stanza', [
    'baseParadigm', 
    'templateCall', 
    'hasParadigms'
])

unknownStanza = Stanza('?', 'error', False)

stanzas = {
    'thing': Stanza('t', timeTemplate, False),
    'thing-wide': Stanza('tw', timeTemplate, False),
    'thing-suchness': Stanza('tsuch', timeTemplate, False),
    'tell': Stanza('tell', timeTemplate, False),
    'join-mark': Stanza('join', timeTemplate, False),
    'time': Stanza('vblex', timeTemplate, True),
    'time-mood': Stanza('tmmood', timeTemplate, True)
}

lineRE = re.compile('^([^,]+),([^,]+)(?:,?([^,#]+)){0,2}')

def processLine(fOut, target, stanza,  srcLemma, dstLemma, paradigms):
    """
    Processes line data by writing to the appropriate template.
    Assumes all input is correct;y formed e.g. that one of srcLemma and dstLemma 
    is a list of length = 1.
    @param srcLemma a list
    @param dstLemma a list
    @param paradigms must be two elems, though the elems can be empty. 
    Must be pre-stripped.
    """
    # get paradigms, based on stanza data
    # if stanza.hasParadigms:
    #    paradigm1 = elems[2].strip()
    #     paradigm2 = elems[3].strip()
    # else:
    #   paradigm1 = stanza.baseParadigm
    
    baseParadigm = stanza.baseParadigm
    paradigm = 'error'
    # which target?
    if target == 's':
        p = paradigms[0]
        if p: paradigm = p + '__' + baseParadigm
        else: paradigm = baseParadigm
        for lemma in srcLemma:
            monodixTemplate(fOut, 
                            dixLemma = lemma.strip(),
                            dixStem = prefix(lemma , '/'), 
                            dixParadigm = paradigm
                        )
    elif target == 'd':
        p = paradigms[1]
        if p: paradigm = p + '__' + baseParadigm
        else: paradigm = baseParadigm
        for lemma in dstLemma:
            monodixTemplate(fOut, 
                            dixLemma = lemma.strip(),
                            dixStem = prefix(lemma , '/'), 
                            dixParadigm = paradigm
                        )
    elif target == 'bi':
        if(len(srcLemma) > 1):
            bilingualTemplateWithTranslationMarkRL(
            fOut,
            srcLemma,
            dstLemma,
            baseParadigm
            )
        elif (len(dstLemma) > 1):
            bilingualTemplateWithTranslationMarkLR(
            fOut,
            srcLemma,
            dstLemma,
            baseParadigm
            )
        else:
            # no alternative translations. Easy...
            bilingualTemplate(
            fOut, 
            srcLemma[0], 
            dstLemma[0], 
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
                

def process(inPath, outPath, target):
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
        elif stanza == unknownStanza:
            # not found a stanza, now
            # skip line if unknownStanza
            pass
        else:
            # process a line
            # slice off tail comments with 'prefix'
            cleanLine = prefix(line, '#')
            srcLemma, tail = parseSet(cleanLine)
            # print(' ,'.join(srcLemma) + ':' + tail)
            if (tail == False):
                printError("data line has one element: '" + cleanLine + "'")
                pass
            else:
                dstLemma, tail = parseSet(tail)
                if (tail == False): paradigms = ['', '']
                else: paradigms = tail.split(',')
                if len(srcLemma) > 1 and len(dstLemma) > 1:
                    printError("source and destination are both sets: '" + cleanLine + "'")
                else:
                    if len(paradigms) > 2:
                        printWarning("data line has more than two paradigms?: '" + cleanLine + "'")
                    #print('srcLemma:' + ', '.join(srcLemma))
                    #print('dstLemma:' + ', '.join(dstLemma))
                    #print('paradigms:' + ', '.join(paradigms))
                    processLine(fOut, target, stanza, srcLemma, dstLemma, paradigms)

    fIn.close()
    fOut.close()

# Writefile



# main

def main(argv):
    inPath = 'in'
    outPath = 'out'
    target = 's'
    try:
        opts, args = getopt.getopt(argv,"hi:o:t:", ["infile=","outfile=",'type='])
    except getopt.GetoptError:
        print 'test.py -i <inputfile> -o <outputfile>'
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print 'test.py -i <inputfile> -o <outputfile>'
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

    print 'Target: ', dictionaryNames[target]

    try:
        process(inPath, outPath, target)
    except IOError:
        print('file would not open: %s' % inPath)
    #finally:

if __name__ == "__main__":
    main(sys.argv[1:])
