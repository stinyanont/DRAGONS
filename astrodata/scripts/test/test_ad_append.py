from nose.tools import *

import file_urls 
from astrodata import AstroData
from astrodata import Errors


def ad_append_test1():
    """ad_append_test1 -moredata=AD, with auto_number
    """
    ad1 = AstroData(file_urls.testdatafile_1) #sci 3
    ad3 = AstroData(file_urls.testdatafile_3) #mdf sci var dq
    print "\n             >>>>>>>     AD HOST    <<<<<<<<"
    ad1.info()
    print "\n             >>>>>>>    AD APPEND   <<<<<<<<"
    ad3.info()
    ad1.append(moredata=ad3, auto_number=True)
    print "\n             >>>>>>>  AD HOST (NEW) <<<<<<<<"
    ad1.info()
    print ad1[3].extname()
    eq_(ad1[3].extname(), "MDF")
    eq_(ad1[4].extname(), "SCI")
    eq_(ad1[5].extname(), "VAR")
    eq_(ad1[6].extname(), "DQ")
    eq_(ad1[4].extver(), 4)
    eq_(ad1[5].extver(), 4)
    eq_(ad1[6].extver(), 4)

def ad_append_test2():
    """ad_append_test2 -moredata=AD, with auto_number
    """
    ad1 = AstroData(file_urls.testdatafile_1) #sci 3
    ad3 = AstroData(file_urls.testdatafile_3) #mdf sci var dq
    print "\n             >>>>>>>     AD HOST    <<<<<<<<"
    ad3.info()
    print "\n             >>>>>>>    AD APPEND   <<<<<<<<"
    ad1.info()
    ad3.append(moredata=ad1, auto_number=True)
    print "\n             >>>>>>>  AD HOST (NEW) <<<<<<<<"
    ad3.info()
    eq_(ad3[4].extname(), "SCI")
    eq_(ad3[5].extname(), "SCI")
    eq_(ad3[6].extname(), "SCI")
    eq_(ad3[4].extver(), 2)
    eq_(ad3[5].extver(), 3)
    eq_(ad3[6].extver(), 4)

def ad_append_test3():
    """ad_append_test3 -moredata=AD, with auto_number
    """
    ad1 = AstroData(file_urls.testdatafile_1) #sci 3
    ad4 = AstroData(file_urls.testdatafile_4) #sci3 var3 dq3
    print "\n             >>>>>>>     AD HOST    <<<<<<<<"
    ad4.info()
    print "\n             >>>>>>>    AD APPEND   <<<<<<<<"
    ad1.info()
    ad4.append(moredata=ad1, auto_number=True)
    print "\n             >>>>>>>  AD HOST (NEW) <<<<<<<<"
    ad4.info()
    eq_(ad4[9].extname(), "SCI")
    eq_(ad4[10].extname(), "SCI")
    eq_(ad4[11].extname(), "SCI")
    eq_(ad4[9].extver(), 4)
    eq_(ad4[10].extver(), 5)
    eq_(ad4[11].extver(), 6)

def ad_append_test4():
    """ad_append_test4 -moredata=AD, with auto_number
    """
    ad1 = AstroData(file_urls.testdatafile_1) #sci 3
    ad4 = AstroData(file_urls.testdatafile_4) #sci3 var3 dq3
    print "\n             >>>>>>>     AD HOST    <<<<<<<<"
    ad1.info()
    print "\n             >>>>>>>    AD APPEND   <<<<<<<<"
    ad4.info()
    ad1.append(moredata=ad4, auto_number=True)
    print "\n             >>>>>>>  AD HOST (NEW) <<<<<<<<"
    ad1.info()
    eq_(ad1[3].extname(), "SCI")
    eq_(ad1[4].extname(), "SCI")
    eq_(ad1[5].extname(), "SCI")
    eq_(ad1[6].extname(), "DQ")
    eq_(ad1[7].extname(), "DQ")
    eq_(ad1[8].extname(), "DQ")
    eq_(ad1[9].extname(), "VAR")
    eq_(ad1[10].extname(), "VAR")
    eq_(ad1[11].extname(), "VAR")
    eq_(ad1[3].extver(), 4)
    eq_(ad1[4].extver(), 5)
    eq_(ad1[5].extver(), 6)
    eq_(ad1[6].extver(), 4)
    eq_(ad1[7].extver(), 5)
    eq_(ad1[8].extver(), 6)
    eq_(ad1[9].extver(), 4)
    eq_(ad1[10].extver(), 5)
    eq_(ad1[11].extver(), 6)

def ad_append_test5():
    """ad_append_test5 -moredata=AD, with auto_number
    """
    ad3 = AstroData(file_urls.testdatafile_3) #mdf sci var dq
    ad4 = AstroData(file_urls.testdatafile_4) #sci3 var3 dq3
    print "\n             >>>>>>>     AD HOST    <<<<<<<<"
    ad3.info()
    print "\n             >>>>>>>    AD APPEND   <<<<<<<<"
    ad4.info()
    ad3.append(moredata=ad4, auto_number=True)
    print "\n             >>>>>>>  AD HOST (NEW) <<<<<<<<"
    ad3.info()
    eq_(ad3[4].extname(), "SCI")
    eq_(ad3[5].extname(), "SCI")
    eq_(ad3[6].extname(), "SCI")
    eq_(ad3[7].extname(), "DQ")
    eq_(ad3[8].extname(), "DQ")
    eq_(ad3[9].extname(), "DQ")
    eq_(ad3[10].extname(), "VAR")
    eq_(ad3[11].extname(), "VAR")
    eq_(ad3[12].extname(), "VAR")
    eq_(ad3[4].extver(), 2)
    eq_(ad3[5].extver(), 3)
    eq_(ad3[6].extver(), 4)
    eq_(ad3[7].extver(), 2)
    eq_(ad3[8].extver(), 3)
    eq_(ad3[9].extver(), 4)
    eq_(ad3[10].extver(), 2)
    eq_(ad3[11].extver(), 3)
    eq_(ad3[12].extver(), 4)

def ad_append_test6():
    """ad_append_test6 -moredata=AD, with auto_number
    """
    ad3 = AstroData(file_urls.testdatafile_3) #mdf sci var dq
    ad4 = AstroData(file_urls.testdatafile_4) #sci3 var3 dq3
    print "\n             >>>>>>>     AD HOST    <<<<<<<<"
    ad4.info()
    print "\n             >>>>>>>    AD APPEND   <<<<<<<<"
    ad3.info()
    ad4.append(moredata=ad3, auto_number=True)
    print "\n             >>>>>>>  AD HOST (NEW) <<<<<<<<"
    ad4.info()
    eq_(ad4[9].extname(), "MDF")
    eq_(ad4[10].extname(), "SCI")
    eq_(ad4[11].extname(), "VAR")
    eq_(ad4[12].extname(), "DQ")
    eq_(ad4[10].extver(), 4)
    eq_(ad4[11].extver(), 4)
    eq_(ad4[12].extver(), 4)

def ad_append_test7():
    """ad_append_test7 -auto_number, add sci1 to existing sci1
    """
    ad1 = AstroData(file_urls.testdatafile_1) #sci 3
    ad4 = AstroData(file_urls.testdatafile_4) #sci3 var3 dq3
    print "\n             >>>>>>>     AD HOST    <<<<<<<<"
    ad1.info()
    print "\n             >>>>>>>    AD APPEND   <<<<<<<<"
    adsci = ad4['SCI', 1]
    print("adsci = ad4['SCI', 1]")
    ad1.append(header=adsci.header, data=adsci.data, auto_number=True)
    print "ad1.append(header=adsci.header, data=adsci.data, auto_number=True)"
    print "\n             >>>>>>>  AD HOST (NEW) <<<<<<<<"
    ad1.info()
    eq_(ad1[3].hdulist[1].name, "SCI")
    eq_(ad1[3].extver(), 4)

def ad_append_test8():
    """ad_append_test8 -auto_number, append var
    """
    ad1 = AstroData(file_urls.testdatafile_1) #sci 3
    ad4 = AstroData(file_urls.testdatafile_4) #sci3 var3 dq3
    print "\n             >>>>>>>     AD HOST    <<<<<<<<"
    ad1.info()
    print "\n             >>>>>>>    AD APPEND   <<<<<<<<"
    adsci = ad4['VAR', 2]
    print("adsci = ad4['VAR', 2]")
    ad1.append(header=adsci.header, data=adsci.data, auto_number=True)
    print "ad1.append(header=adsci.header, data=adsci.data, auto_number=True)"
    print "\n             >>>>>>>  AD HOST (NEW) <<<<<<<<"
    ad1.info()
    eq_(ad1[3].extname(), "VAR")
    eq_(ad1[3].extver(), 4)


def ad_append_test9():
    """ad_append_test9 -auto_number, append high var
    """
    ad1 = AstroData(file_urls.testdatafile_1) #sci 3
    ad4 = AstroData(file_urls.testdatafile_4) #sci3 var3 dq3
    print "\n             >>>>>>>     AD HOST    <<<<<<<<"
    ad1.hdulist.__delitem__(3)
    print("ad1.hdulist.__delitem__(3)")
    ad1.info()
    print "\n             >>>>>>>    AD APPEND   <<<<<<<<"
    adsci = ad4['VAR', 3]
    print("adsci = ad4['VAR', 3]")
    print "ad1.append(header=adsci.header, data=adsci.data, auto_number=True)"
    ad1.append(header=adsci.header, data=adsci.data, auto_number=True)
    print "\n             >>>>>>>  AD HOST (NEW) <<<<<<<<"
    ad1.info()
    eq_(ad1[2].extname(), "VAR")
    eq_(ad1[2].extver(), 3)

@ raises(Errors.AstroDataError)
def ad_append_test10():
    """ad_append_test10 -auto_number, raise when no header
    """
    ad1 = AstroData(file_urls.testdatafile_1) #sci 3
    ad4 = AstroData(file_urls.testdatafile_4) #sci3 var3 dq3
    print "\n             >>>>>>>     AD HOST    <<<<<<<<"
    ad1.info()
    print "\n             >>>>>>>    AD APPEND   <<<<<<<<"
    adsci = ad4['SCI', 1]
    print("adsci = ad4['SCI', 1]")
    ad1.append(data=adsci.data, auto_number=True)
    print "ad1.append(data=adsci.data, auto_number=True)"
    print "\n             >>>>>>>  AD HOST (NEW) <<<<<<<<"
    ad1.info()
    eq_(ad1[3].extname(), "SCI")
    eq_(ad1[3].extver(), 4)

def ad_append_test11():
    """ad_append_test11 -auto_number, append with high sci extver
    """
    ad1 = AstroData(file_urls.testdatafile_1) #sci 3
    ad4 = AstroData(file_urls.testdatafile_4) #sci3 var3 dq3
    print "\n             >>>>>>>     AD HOST    <<<<<<<<"
    ad1.info()
    print "\n             >>>>>>>    AD APPEND   <<<<<<<<"
    adsci = ad4['SCI', 1]
    print("adsci = ad4['SCI', 1]")
    ad1.append(extver=10, header=adsci.header, data=adsci.data, auto_number=True)
    print("ad1.append(extver=10, header=adsci.header, data=adsci.data,\
          auto_number=True)")
    print "\n             >>>>>>>  AD HOST (NEW) <<<<<<<<"
    ad1.info()
    eq_(ad1[3].extname(), "SCI")
    eq_(ad1[3].extver(), 10)

@ raises(Errors.AstroDataError)
def ad_append_test12():
    """ad_append_test12 -no auto_number, moredata raise when conflict
    """
    ad1 = AstroData(file_urls.testdatafile_1) #sci 3
    ad4 = AstroData(file_urls.testdatafile_4) #sci3 var3 dq3
    print "\n             >>>>>>>     AD HOST    <<<<<<<<"
    ad1.info()
    print "\n             >>>>>>>    AD APPEND   <<<<<<<<"
    ad4.info()
    ad1.append(moredata=ad4)
    print "ad1.append(moredata=ad4)"
    print "\n             >>>>>>>  AD HOST (NEW) <<<<<<<<"
    ad1.info()

@ raises(Errors.AstroDataError)
def ad_append_test13():
    """ad_append_test13 -no auto_number, raise when conflict
    """
    ad1 = AstroData(file_urls.testdatafile_1) #sci 3
    ad4 = AstroData(file_urls.testdatafile_4) #sci3 var3 dq3
    print "\n             >>>>>>>     AD HOST    <<<<<<<<"
    ad1.info()
    print "\n             >>>>>>>    AD APPEND   <<<<<<<<"
    adsci = ad4['SCI', 1]
    print("adsci = ad4['SCI', 1]")
    ad1.append(header=adsci.header, data=adsci.data)
    print("ad1.append(extver=10, header=adsci.header, data=adsci.data,\
          auto_number=True)")
    print "\n             >>>>>>>  AD HOST (NEW) <<<<<<<<"
    ad1.info()


def ad_append_test14():
    """ad_append_test14 -auto_number, build mef from phu instantiation
    """
    ad1 = AstroData(file_urls.testdatafile_1) #sci 3
    ad4 = AstroData(file_urls.testdatafile_4) #sci3 var3 dq3
    print "\n             >>>>>>>     AD NEW    <<<<<<<<"
    ad_new = AstroData(phu=ad1.phu)
    ad_new.info()
    print "\n             >>>>>>>    AD APPEND   <<<<<<<<"
    for i in range(1,4):
        adsci = ad1['SCI', i]
        print("adsci = ad1['SCI', %d]" % i)
        ad_new.append(header=adsci.header, data=adsci.data, auto_number=True)
        mystr = "ad_new.append(header=adsci.header, data=adsci.data,"
        mystr += " auto_number=True)"
        print mystr
    print "\n             >>>>>>>  AD NEW <<<<<<<<"
    ad_new.info()
    eq_(ad_new[0].extname(), "SCI")
    eq_(ad_new[0].extver(), 1)
    eq_(ad_new[1].extname(), "SCI")
    eq_(ad_new[1].extver(), 2)
    eq_(ad_new[2].extname(), "SCI")
    eq_(ad_new[2].extver(), 3)

def ad_append_test15():
    """ad_append_test15 -auto_number, extver override
    """
    ad4 = AstroData(file_urls.testdatafile_4) #sci3 var3 dq3
    print "\n             >>>>>>>     AD NEW    <<<<<<<<"
    ad_new = AstroData(phu=ad4.phu)
    ad_new.info()
    print "\n             >>>>>>>    AD APPEND   <<<<<<<<"
    ad_new.append(header=ad4[1].header, data=ad4[1].data,  extver=1, \
        auto_number=True) 
    ad_new.append(header=ad4[4].header, data=ad4[4].data,  extver=1, \
        auto_number=True) 
    mystr = "ad_new.append(header=ad4[1].header, data=ad4[1].data,  extver=1,"
    mystr += " auto_number=True)" 
    mystr += "\nad_new.append(header=ad4[4].header, data=ad4[4].data,  extver=1,"
    mystr += " auto_number=True)"
    print mystr
    print "\n             >>>>>>>  AD NEW <<<<<<<<"
    ad_new.info()
    
    eq_(ad_new[0].extname(), "SCI")
    eq_(ad_new[0].extver(), 1)
    eq_(ad_new[1].extname(), "DQ")
    eq_(ad_new[1].extver(), 1)


def ad_append_test16():
    """ad_append_test16 -auto_number, mdf
    """
    ad3 = AstroData(file_urls.testdatafile_3) #mdf sci var dq
    print "\n             >>>>>>>     AD NEW    <<<<<<<<"
    ad_new = AstroData(phu=ad3.phu)
    ad_new.info()
    print "\n             >>>>>>>    AD APPEND   <<<<<<<<"
    print ad3[0].data.__class__
    ad_new.append(header=ad3[0].header, data=ad3[0].data,\
        auto_number=True) 
    mystr = "ad_new.append(header=ad4[1].header, data=ad4[1].data,"
    mystr += " auto_number=True)" 
    print mystr
    print "\n             >>>>>>>  AD NEW <<<<<<<<"
    ad_new.info()
    eq_(ad_new[0].extname(), "MDF")
    eq_(ad_new[0].extver(), None)




