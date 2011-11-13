#!/usr/bin/env python

from PIL import Image
import os, sys, stat
import time
import zbar

#TODO sounds

try:
    cmd_folder = os.path.dirname(os.path.abspath(__file__))
except NameError:
    cmd_folder = os.path.dirname(os.path.abspath("."))

# look for modules in subfolders of the current path
if cmd_folder not in sys.path:
    sys.path.insert(0, cmd_folder)

from pages import Page

# create a Processor
proc = zbar.Processor()

# configure the Processor
proc.parse_config('enable')

# default video device
video_device = "/dev/video0"
# or whatever is on the command line
if len(sys.argv) > 1:
    video_device = sys.argv[1]

# populate video devices in list
video_list=[]
video_list.append("<none>")
for (root, dirs, files) in os.walk("/dev"):
    for dev in files:
        path = os.path.join(root, dev)
        if not os.access(path, os.F_OK):
            continue
        info = os.stat(path)
        if stat.S_ISCHR(info.st_mode) and os.major(info.st_rdev) == 81:
            # add the device unless it was the one on the command line
            if path != video_device:
                video_list.append(path)    

while 1:
    try:
        proc.init(video_device)
        break
    except SystemError:
        print "Video device {} could not be opened".format(video_device)
        if len(video_device)>0:
            video_device=video_list.pop()
        else:
            print "Count not find a video device to open"
            quit()
print "Barcode processor using video device {}".format(video_device)

# setup a callback
def my_handler(proc, image, closure):
    # print "handler invoked"
    global previous
    # meta={"symbols":[{"location":copy(s.location), "data":copy(s.data)} for s in image.symbols]}
    # if meta['symbols'][0]['data']==previous:
    #     return
    # previous=meta['symbols'][0]['data']
    
    global lastPage

    page=Page()
    lastPage=page
    # print "New page object"
    pilImage=Image.fromstring("RGB",image.size,image.data).convert('L')
    # print "make pilImage"
    page.pilImage=pilImage
    # print "set page.pilImage"
    # page.pilImage.show()
    page.symbols=image.symbols
    # print "page.symbols="

    page.read_grade_marks()
    # print "read grade marks on page"ipython 

    
    # pilImage=pilImage.convert("L")
    # temp="scan-{0.tm_year}{0.tm_mon:02}{0.tm_mday:02}-{0.tm_hour:02}{0.tm_min:02}{0.tm_sec:02}".format(time.localtime())
    # pilImage.save(temp+".png")
    # meta['filename']=temp
    # meta['time']=time.localtime()
    # pickle.dump(meta,file(temp + ".meta","wb") )
    # print pilImage.size, temp,meta['symbols'][0]['data']

    # page._marks.show()
    # print page.grades


proc.set_data_handler(my_handler)

# enable the preview window
proc.visible = True

global previous
previous  = None

global lastPage

# initiate scanning
proc.active = True

while 1:
    try:
        # proc.process_one()
        proc.process_one()
    except zbar.WindowClosed, KeyboardInterrupt:
       break
    page=lastPage
    status="{:10} {:30} {:10} = {}".format(page.data['B'],page.data['I'],page.data['N'],page.grade)
    file=open('log.txt','a')
    file.write(status+"\n")
    file.close()
    print status

proc.active = False
proc.visible = False

