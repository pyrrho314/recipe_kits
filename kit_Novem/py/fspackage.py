import getpass
from astrodata import Lookups
import os
import re
import shutil
from copy import deepcopy, copy

from astrodata.adutils import ksutil as ks

def recursive_listdir(dirname = "."):
    rfilelist = []
    print "fs10:", dirname
    for root, dirs, files in os.walk(dirname):
        #print root, len(dirs), len(files)
        for fil in files:
            fpath = os.path.join(root, fil)
            rfilelist.append(fpath)
    return rfilelist

class FSPackage(object):
    """Used to move files between the working directory and
    some other file storage location. This is a base
    class for packagers that might retrieve files from other stores
    such as cloud storage services such as S3. 
    
    The base class uses another mounted drive, that is,
    it does regular system file copies.
    
    Attributes
    ----------
    
    setref (dict): the setref dictionary for the file being transferred.
    
    """
    setref = None
    storename = None
    elements = {}
   
    def __init__(self, setref = None, storename = None):
        self.elements["user"] = getpass.getuser()
        self.storename = storename
        info = Lookups.compose_multi_table( "*/warehouse_settings", 
                                            "warehouse_elements", 
                                            "shelf_addresses", 
                                            "type_shelf_names",
                                            "type_store_precedence")
        # basic elements like root
        self.warehouse_elements = info["warehouse_elements"]
        # named storage templates
        self.shelf_addresses    = info["shelf_addresses"]
        self._convert_shelf_addresses()
        # shelf_addresses/names to use for a given type
        self.type_shelf_names   = info["type_shelf_names"]
        # the order to check the types, so some types override others
        # e.g. SETREF has a default storage location, a sort of misc. file
        # that should be over written by other packages
        self.type_store_precedence    = info["type_store_precedence"]
        #print "fs20: ts_prec", self.type_store_precedence
        #print "fs21: sh_names", self.type_shelf_names
        if setref:
             self.elements_from_setref(setref)   
             #self.get_storename()
    
    def _convert_shelf_addresses(self):
        """The purpose is to change addresses that are strings into
            the dict version used by the class."""
        import re
        for key in self.shelf_addresses:
            addrobj = self.shelf_addresses[key]
            
            if isinstance(addrobj, basestring):
                addrdict = {"path_templ":addrobj}
            else:
                addrdict = addrobj
            if "requires" not in addrdict:
                stempl = addrdict["path_templ"]
                m = re.findall("\{(.*?)\}", stempl)
                addrdict["requires"] = m
            
            self.shelf_addresses[key] = addrdict
                     
             
    def elements_from_setref(self, setref):
        self.setref = setref
        year = setref.meta("year")
        month = setref.meta("month")
        day = setref.meta("day")
        if day and month and year:
            self.elements.update({"year":year, "day":day, "month":month})
        self.elements.update(self.warehouse_elements)
        if year and month and day:
            current_day = "%4d%02d%02d" % (year, month, day)
            self.elements["complete_day"] = current_day
        # type
        srtypes = setref.get_types()
        # note that it should only be ONE of these types
        # but we stop at the first
        settype = None
        for typ in self.type_store_precedence:
            #print "fs42: typ", typ
            if typ in srtypes:
                settype = typ
                break
                
        if not settype:
            settype = "&".join(srtypes)
        #print "fs48: settype",settype
        self.elements["type"] = settype
        self.elements["region"] = setref.meta("region")

    def format_storage_location(self, shelfname, elements = {}):
        fargs = self.elements
        fargs.update(elements)
        #print "dw65 FARGS",fargs
        wareobj = self.shelf_addresses[shelfname]
        if isinstance(wareobj, basestring):
            wareobj = {"path_templ": wareobj}
        
        requires = None
        if "requires" in wareobj:
            requires = wareobj["requires"]
            
        try:
            path = wareobj["path_templ"].format( **fargs )
        except KeyError:
            print "can't compose %s" % wareobj["path_templ"]
            print "using fargs   %s" % fargs
            raise
        fullpath = path
        return fullpath
    
    def get_store_dirname(self, setref = None, elements= None):
        if setref:
            self.elements_from_setref(setref)
        if elements:
            print ks.dict2pretty("fsp134:elements", self.elements)
            self.elements.update(elements)
            print ks.dict2pretty("fsp134:elements", self.elements)
            
        if "shelf_name" in self.elements:
            # presumably by override
            storepath = self.format_storage_location(
                                                    self.elements["shelf_name"]
                                                    )
        else:
            # find the shelf based on types
            settype = self.elements["type"]
            if settype in self.type_shelf_names:
                shelfname = self.type_shelf_names[settype]
                storepath = self.format_storage_location(shelfname)
            else:
                storepath = self.format_storage_location(shelfname)
        self.store_dirname = storepath
        return storepath
    
    def get_store_prefix(self, elements = None):
        if not elements:
            elements = self.elements
        whelem = deepcopy(self.warehouse_elements)
        whelem.update(elements)
        
        shelf_name = (  whelem["shelf_name"] 
                            if "shelf_name" in whelem 
                            else None
                     )
        
        if shelf_name == None:
            return None
        template_dsc = self.shelf_addresses[shelf_name]
        req = template_dsc["requires"]
        for elem in req:
            #print "fs143: elem", elem
            if elem not in whelem:
                whelem[elem] = "\n{%s}\n" % elem
        temp = template_dsc["path_templ"]
        #print "fs160:", temp
        #print "fs107:", whelem
        pfx_ml = temp.format(**whelem)
        pfx = pfx_ml.split()[0]
        if pfx[-1] == os.sep:
            pfx = pfx[:-1]
            
        return pfx
        
    def get_store_template(self, elements = None):
        whelem = deepcopy(self.warehouse_elements)
        whelem.update(elements)
        
        shelf_name = (  whelem["shelf_name"] 
                            if "shelf_name" in elements 
                            else "processed_data"
                     )
        
        template_dsc = self.shelf_addresses[shelf_name]
        temp = template_dsc["path_templ"]
        return temp 
        
    def get_store_sidecars(self, elements = None):
        template_dsc = self.get_ware_spec(elements = elements)
        if "sidecar_templates" in template_dsc:
            return template_dsc["sidecar_templates"]
        elif "sidecar_templ" in template_dsc:
            return template_dsc["sidecar_templ"]
        elif "sidecar_templs" in template_dsc:
            return template_dsc["sidecar_templs"]
        return None
        
        
    def get_store_path(self, setref = None, elements = None):
        storepath = self.get_store_dirname(setref, elements = elements)
        storename = os.path.join(storepath, setref.basename)
        self.storename = storename
        return storename
    
    def get_store_list(self, prefix = None, elements = None):
        if not prefix:
            prefix = self.get_store_prefix(elements)
        print "fs121: prefix = %s" % prefix
        
        lcurse = recursive_listdir( prefix )
        
        l = []
        for fnam in lcurse:
            if "phrase" in elements:
                phrase = elements["phrase"]
                if phrase in fnam:
                    l.append(fnam)
            else:
                l.append(fnam)
                
        scelems = self.get_store_sidecars(elements)
        if scelems:
            newl = []
            for item in l:
                for sc in scelems:
                    #if item.endswith(sc):
                    if re.match(sc, item):
                        newl.append(item)
                        break;
            l = newl
        return l
        
    def get_ware_spec(self, elements = None):
        if not elements:
            elements = self.elements
        whelem = deepcopy(self.warehouse_elements)
        whelem.update(elements)
        
        shelf_name = (  whelem["shelf_name"] 
                            if "shelf_name" in elements 
                            else "processed_data"
                     )      
        template_dsc = self.shelf_addresses[shelf_name]
        return template_dsc
        
    def transport_to_warehouse(self, remove_local=False):
        workpath = self.setref.filename
        storedir = self.get_store_dirname()
        storepath    = os.path.join(storedir, self.setref.basename)
        sr_storepath = os.path.join(storedir, os.path.basename(self.setref.setref_fname))
        print "dw111:",workpath, storepath
        # ensure target dir exists
        if not os.path.exists(storedir):
            os.makedirs(storedir)
        
        # COPY MAIN FILE
        # copy workfile to store    
        if os.path.exists(workpath):
            if remove_local:
                shutil.move(workpath, storepath)
            else:
                shutil.copyfile(workpath, storepath)
        sr_workpath = self.setref._make_setref_fname(type="input")
        # COPY SETREF SIDECAR FILE
        # copy setref to store
        if os.path.exists(sr_workpath):
            if remove_local:
                shutil.move(sr_workpath, sr_storepath)
            else:
                shutil.copyfile(sr_workpath, sr_storepath)
        return True 
        
    def deliver_from_warehouse(self):
        curdir = os.getcwd()
        print "bp52:", self.storename
        basename = os.path.basename(self.storename)
        localpath = os.path.join(curdir, basename)
        self.local_path = localpath
        
        shutil.copyfile(self.storename, self.local_path)
        
        return True
        
        
