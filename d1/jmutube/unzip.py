""" unzip.py
    Version: 1.1

    Extract a zipfile to the directory provided
    It first creates the directory structure to house the files
    then it extracts the files to it.

    Sample usage:
    command line
    unzip.py -p 10 -z c:\testfile.zip -o c:\testoutput

    python class
    import unzip
    un = unzip.unzip()
    un.extract(r'c:\testfile.zip', 'c:\testoutput')
    

    By Doug Tolton
"""

import sys
import zipfile
import zlib
import os
import os.path
import getopt


zlib.MAX_WBITS = 31

class unzip:
    def __init__(self, verbose = False, percent = 10):
        self.verbose = verbose
        self.percent = percent
        
    def extract(self, file, dir):
        if not dir.endswith(':') and not os.path.exists(dir):
            os.mkdir(dir)

        src = open(file, 'rb')
        zf = zipfile.ZipFile(src)

        # create directory structure to house files
        self._createstructure(file, dir)

        num_files = len(zf.namelist())
        percent = self.percent
        divisions = 100 / percent
        perc = int(num_files / divisions)

        # extract files to directory structure
        for i, m in enumerate(zf.infolist()):
            name = m.filename

            if self.verbose == True:
                print "Extracting %s" % name
            elif perc > 0 and (i % perc) == 0 and i > 0:
                complete = int (i / perc) * percent
                print "%s%% complete" % complete

            if not name.endswith('/'):
                src.seek(m.header_offset)
                src.read(30) # Good to use struct to unpack this.
                nm = src.read(len(m.filename))
                if len(m.extra) > 0:
                    ex = src.read(len(m.extra))
                if len(m.comment) > 0:
                    cm = src.read(len(m.comment))
                # Build a decompression object
                decomp = zlib.decompressobj(-15)
                out = open(os.path.join(dir, m.filename), "wb")


                remain = m.compress_size
                while remain:
                    bytes = src.read(min(remain, 1024 * 1024))
                    if m.compress_type == zipfile.ZIP_DEFLATED:
                        result = decomp.decompress(bytes)
                    else:
                        result = bytes
                    remain -= len(bytes)
                    out.write(result)
                result = decomp.decompress('Z') + decomp.flush()
                if result:
                    out.write(result)
                
                
                #out.write(zf.read(name))
                out.close()

        zf.close()
        src.close()
        

    def _createstructure(self, file, dir):
        self._makedirs(self._listdirs(file), dir)


    def _makedirs(self, directories, basedir):
        """ Create any directories that don't currently exist """
        for dir in directories:
            curdir = os.path.join(basedir, dir)
            if not os.path.exists(curdir):
                os.mkdir(curdir)

    def _listdirs(self, file):
        """ Grabs all the directories in the zip structure
        This is necessary to create the structure before trying
        to extract the file to it. """
        zf = zipfile.ZipFile(file)

        dirs = []

        for name in zf.namelist():
            if name.endswith('/'):
                dirs.append(name)
            elif not os.path.dirname(name) in dirs:
                dirs.append(os.path.dirname(name))

        dirs.sort()
        return dirs

def usage():
    print """usage: unzip.py -z <zipfile> -o <targetdir>
    <zipfile> is the source zipfile to extract
    <targetdir> is the target destination

    -z zipfile to extract
    -o target location
    -p sets the percentage notification
    -v sets the extraction to verbose (overrides -p)

    long options also work:
    --verbose
    --percent=10
    --zipfile=<zipfile>
    --outdir=<targetdir>"""
    

def main():
    shortargs = 'vhp:z:o:'
    longargs = ['verbose', 'help', 'percent=', 'zipfile=', 'outdir=']

    unzipper = unzip()

    try:
        opts, args = getopt.getopt(sys.argv[1:], shortargs, longargs)
    except getopt.GetoptError:
        usage()
        sys.exit(2)

    zipsource = ""
    zipdest = ""

    for o, a in opts:
        if o in ("-v", "--verbose"):
            unzipper.verbose = True
        if o in ("-p", "--percent"):
            if not unzipper.verbose == True:
                unzipper.percent = int(a)
        if o in ("-z", "--zipfile"):
            zipsource = a
        if o in ("-o", "--outdir"):
            zipdest = a
        if o in ("-h", "--help"):
            usage()
            sys.exit()

    if zipsource == "" or zipdest == "":
        usage()
        sys.exit()
            
    unzipper.extract(zipsource, zipdest)

if __name__ == '__main__': main()
