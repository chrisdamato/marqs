#!/usr/bin/env python

#/home/chris/code/python/my-modules/pages.py

from StringIO import StringIO
import PythonMagick, pyglet, pyglet.window
import PIL.Image, PIL.ImageDraw
import zbar
import pyPdf
import math
import os

class MarksCol():
    """Information about one column on the OMR grading bitmap"""
    def __init__(self):
        self.__list=[]
        self.__boxes=[]
        
    @property
    def list(self):
        """List of pixel sums for this column"""
        return self.__list
    
    @list.setter
    def list(self,value):
        self.__list=value

    @property
    def boxes(self):
        return self.__boxes

    @property
    def min(self):
        return min(self.__list)
    
    @property
    def avg(self):
        return sum(self.__list)/len(self.__list)

    @property
    def choice(self):
        diff=[]
        for box in self.__list:
            others=list(self.__list)
            others.remove(box)
            others_avg=float(sum(others)/len(others))
            diff.append((others_avg-box)/others_avg)
        most_different=max(diff)
        if most_different < 0.1:
            return None
        else:
            return diff.index(most_different)


class Page(object):
    def __init__(self, filename="", page=0):
        self.filename = filename
        self.page = page
        self._pmBlob = None
        self._pmImage = None
        self.__pygImage = None
        self.__pilImage = None
        self._marks=None

    def pmImage(self):
        if self._pmImage != None:
            return self._pmImage
        if self.filename == None:
            print "No filename for pmImage to load"
            quit()
        try:
            print "render pmImage for {}".format(self.filename)
            self._pmImage=PythonMagick.Image()
        except:
            print "Unab"
            quit()
        self._pmImage.density('200')
        self._pmImage.read(self.filename)
        self._pmImage.magick("RGBA")
        return self._pmImage

    def pmBlob(self):
        if self._pmBlob != None:
            return self._pmBlob
        print "render ppBlob for {}".format(self.filename)
        self._pmBlob=PythonMagick.Blob()
        _pmImage=self.pmImage()
        # if you skip the next write, the pyglet image comes up as RGB
        _pmImage.write(self._pmBlob) # seems to need both of these writes!
        # print "_pmImage.write(blob)",len(blob.data),blob.data[:100].__repr__()
        _pmImage.write(self._pmBlob,"png") # seems to need both of these writes!
        # print "_pmImage.write(blob,png)",len(blob.data),blob.data[:100].__repr__()
        return self._pmBlob

    @property
    def pilImage(self):
        if self.__pilImage != None:
            return self.__pilImage
        
        #useful:  http://www.pythonware.com/library/pil/handbook/concepts.htm
        try:
            print "try: loading PIL image from {}".format(self.filename)
            self.__pilImage=PIL.Image.open(self.filename)
        except:
            try:
                print "try: use PythonMagick to render pilImage for {}".format(self.filename)
                self.__pilImage=PIL.Image.fromstring("L",(self.pmImage().size().width(),self.pmImage().size().height()),self.pmBlob().data)
            except:
                print "can't load or convert image, filename \"{}\"".format(self.filename)
        return self.__pilImage
    
    @pilImage.setter
    def pilImage(self, value):
        self.__pilImage=value
        return self

    @property
    def symbols(self):
        if self.__symbols != None:
            return self.__symbols
        
    
    @symbols.setter
    def symbols(self, zbarSymbolIterThing):
        """If the image has already been scanned by zbar, set the symbols directly"""
        self.__symbols=[s for s in zbarSymbolIterThing]
        self.data=dict([pair.split("=") for pair in self.symbols[0].data.lstrip("|").rstrip("|").split("|")])

    
    def pygImage(self):
        if self.__pygImage != None:
            return self.__pygImage
        if self.__pilImage != None:
            pass
        print "render pygImage for {}".format(self.filename)
        s=StringIO(self.pmBlob().data)
        self.__pygImage=pyglet.image.load("i.png",s) #works
        print "self.__pygImage.format=",self.__pygImage.format
        return self.__pygImage

    def draw(self, window_w, window_h):
        image=self.pygImage()
        # print "window_w,window_h"
        # print window_w,window_h
        # print "image.width,image.height"
        # print image.width,image.height
        # http://pyglet.org/doc/programming_guide/index.html
        image_ratio = float(image.width) / float(image.height)
        # print "image_ratio", image_ratio
        window_ratio = window_w / window_h
        image_w = window_w
        image_h = window_w / image_ratio
        image_x = 0
        image_y = window_h - image_h

        # print "window_w={},window_h={},image_w={},image_h={},image_x={},image_y={}".format(window_w,window_h,image_w,image_h,image_x,image_y)
        
        image.blit(
            x=image_x, y=image_y,
            # width=image_w, height=image_h,
            width=image_w, height=image_h,
            z=+1
        )

    def scanQR(self):
        """scan this page for symbols using zbar"""
        # create a reader
        scanner = zbar.ImageScanner()

        # configure the reader
        scanner.parse_config('enable')

        # obtain image data
        self.pmImage().depth(8)
        self.pmImage().write(self.pmBlob(),"GRAY")
        
        # wrap image data
        self.zbImage = zbar.Image(self.pmImage().size().width(), self.pmImage().size().height(), 'Y800', self.pmBlob().data)

        # scan the image for barcodes
        scanner.scan(self.zbImage)

        # extract results
        for symbol in self.zbImage.symbols:
            # do something useful with results
            print 'decoded', symbol.type, 'symbol', '"%s"' % symbol.data
        
        self.symbols = [s for s in self.zbImage.symbols]
        self.data=dict([pair.split("=") for pair in self.symbols[0].data.lstrip("|").rstrip("|").split("|")])

        return self.symbols

        # clean up
        # del(image)
    
    def read_grade_marks(self, refresh=False, x_offset=0.476, x_grid=0.423, y_offset=0.137, y_grid=0.178):
        if (self._marks != None) and (refresh == False):
            return self._marks
        for symbol in self.symbols:
            #vectors, size of qr code
            l=symbol.location
            self.qr_quad=( l[0][0],l[0][1], l[1][0],l[1][1], l[2][0],l[2][1], l[3][0],l[3][1] )

            vecW=(l[3][0]-l[0][0],l[3][1]-l[0][1])
            vecH=(l[1][0]-l[0][0],l[1][1]-l[0][1])
            self.vec=[vecW,vecH]
            self.qr_size=( int((vecW[0]**2+vecW[1]**2)**(0.5)), int((vecH[0]**2+vecH[1]**2)**(0.5)) )
            self.rotate=math.atan(float(vecW[1])/float(vecW[0])/math.pi)*180.0 * -1

            #location of grading grid in quad format for PIL.Image.transform

            q=[0,0,0,0,0,0,0,0]
            w=6 #grading area is this many times the width of the qr code
            q[0], q[1] = l[0][0]+vecW[0],   l[0][1]+vecW[1] #top left corner
            q[2], q[3] = l[1][0]+vecW[0],   l[1][1]+vecW[1]  #bottom left corner
            q[4], q[5] = q[2]+w*vecW[0], q[3]+w*vecW[1] #bottom right corner
            q[6], q[7] = q[0]+w*vecW[0], q[1]+w*vecW[1] #top right

            self.quad=q
            self.size=(self.qr_size[0]*w,self.qr_size[1])

            self._marks=self.pilImage.transform(self.size,PIL.Image.QUAD,self.quad)

            draw=PIL.ImageDraw.Draw(self._marks)

            #offset and grid are both factors of qr code width - to locate the grading columns

            col_w=int(self.qr_size[0]*x_grid )
            col_h=int(self.qr_size[1]*y_grid )
            col_x=range( int(self.qr_size[0]*x_offset) , self._marks.size[0], col_w )
            col_y=range( int(self.qr_size[1]*y_offset) , self._marks.size[1] - col_h , col_h )

            self.grades=[]
            self.grids=[]
            for x in col_x[:4]:
                g=MarksCol()
                for y in col_y:
                    rect=(x +1 ,y +1 ,x+col_w -1, y+col_h -1)
                    mark_image=self._marks.crop(rect)
                    g.boxes.append( mark_image )
                    g.list.append( sum(list(mark_image.getdata())) ) 
                    draw.rectangle( rect )
                self.grids.append(g)
                self.grades.append(g.choice)
            
            self.grade=""
            for g in self.grades:
                if g !=None:
                    if self.grade>"":
                        self.grade+=' -> '
                    self.grade+=['4','3','fix','R','RL'][g]

            return self._marks


    def submit(self, *args):
        print "len(args)={}\nargs={}".format(len(args),args)

if __name__ == "__main__":
    import helpers
    pages=[]
    for filename in filter(lambda f: f.startswith("qr") and f.endswith("pdf"), sorted(os.listdir( os.path.join(".",'burst') ) ) ):
        pages.append(Page(os.path.join("burst",filename)))
        pages[-1].read_grade_marks()
        print pages[-1].data,pages[-1].grades

    print "\nProcessed {} pages:".format(len(pages))
    for page in pages:
        print "\t{0:8} {1:30} = {2}".format(page.data['I'],page.data['N'],page.grades)

    
    # page.pmImage().display()
    # page.pmImage().rotate(-4.0)
    
    # read_grade_marks=page.read_grade_marks()
    # read_grade_marks.show()
    
    # i.transformOrigin(page.loc[0][0],page.loc[0][1])
    # i.rotate(page.rotate)
    # i.crop( "{}x{}+{}+{}".format(200,200,page.loc[0][0],page.loc[0][1]) )
    # page.pmImage().crop(page.geometry)
    # page.pmImage().rotate(page.rotate)
    # page.pmImage().display()
