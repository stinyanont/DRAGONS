# This parameter file contains the parameters related to the primitives located
# in the primitives_GSAOI.py file, in alphabetical order.
{"standardizeInstrumentHeaders":{
    "suffix":{
        "default"       : "_instrumentHeadersStandardized",
        "type"          : "str",
        "recipeOverride": True,
        "userOverride"  : True,
        "uiLevel"       : "UIBASIC",
        },
    },
 "standardizeStructure":{
    "suffix":{
        "default"       : "_structureStandardized",
        "type"          : "str",
        "recipeOverride": True,
        "userOverride"  : True,
        "uiLevel"       : "UIBASIC",
        },
    "attach_mdf":{
        "default"       : True,
        "type"          : "bool",
        "recipeOverride": True,
        "userOverride"  : True,
        "uiLevel"       : "UIBASIC",
        },
    "mdf":{
        "default"       : None,
        # No default type defined, since the mdf parameter could be a string or
        # an AstroData object
        "recipeOverride": True,
        "userOverride"  : True,
        "uiLevel"       : "UIBASIC",
        },
    },
 "tileArrays":{
    "suffix":{
        "default"       : "_tiled",
        "type"          : "str",
        "recipeOverride": True,
        "userOverride"  : True,
        "uiLevel"       : "UIBASIC",
        },
    "tile_all":{
        "default"       : True,
        "type"          : "bool",
        "recipeOverride": True,
        "userOverride"  : True,
        "uiLevel"       : "UIBASIC",
        },
    },
 "trimOverscan":{
    "suffix":{
        "default"       : "_overscanTrimmed",
        "type"          : "str",
        "recipeOverride": True,
        "userOverride"  : True,
        "uiLevel"       : "UIBASIC",
        },
    },
 "validateData":{
    "suffix":{
        "default"       : "_dataValidated",
        "type"          : "str",
        "recipeOverride": True,
        "userOverride"  : True,
        "uiLevel"       : "UIBASIC",
        },
    "repair":{
        "default"       : False,
        "type"          : "bool",
        "recipeOverride": True,
        "userOverride"  : True,
        "uiLevel"       : "UIBASIC",
        },
    },
 "measureBG":{
    "remove_bias":{
        "default"       : False,
        "type"          : "bool",
        "recipeOverride": True,
        "userOverride"  : True,
        "uiLevel"       : "UIBASIC",
        },
    },
 "measureIQ":{
    "suffix":{
        "default"       : "_iqMeasured",
        "type"          : "str",
        "recipeOverride": True,
        "userOverride"  : True,
        "uiLevel"       : "UIBASIC",
        },
    "display":{
        "default"       : False,
        "type"          : "bool",
        "recipeOverride": True,
        "userOverride"  : True,
        "uiLevel"       : "UIBASIC",
        },
    "remove_bias":{
        "default"       : False,
        "type"          : "bool",
        "recipeOverride": True,
        "userOverride"  : True,
        "uiLevel"       : "UIBASIC",
        },
    "separate_ext":{
        "default"       : False,
        "type"          : "bool",
        "recipeOverride": True,
        "userOverride"  : True,
        "uiLevel"       : "UIBASIC",
        },
    },
 "associateSky":{
    "time":{
        "default"       : 900.,
        "type"          : "float",
        "recipeOverride": True,
        "userOverride"  : True,
        "uiLevel"       : "UIBASIC",
        },
    "distance":{
        "default"       : 1.,
        "type"          : "float",
        "recipeOverride": True,
        "userOverride"  : True,
        "uiLevel"       : "UIBASIC",
        },
    },
 "addReferenceCatalog":{
    "suffix":{
        "default"       : "_refcatAdded",
        "type"          : "str",
        "recipeOverride": True,
        "userOverride"  : True,
        "uiLevel"       : "UIBASIC",
        },
    "radius":{
        # in degrees; default is 2 arcmin
        "default"       : 0.033,
        "type"          : "float",
        "recipeOverride": True,
        "userOverride"  : True,
        "uiLevel"       : "UIBASIC",
        },
    "source":{  
        "default"       : "2mass",
        "type"          : "str",
        "recipeOverride": True,
        "userOverride"  : True,
        "uiLevel"       : "UIBASIC",
        },
    },
"display":{ 
    "extname":{
        "default"       : "SCI",
        "type"          : "str",
        "recipeOverride": True,
        "userOverride"  : True,
        "uiLevel"       : "UIBASIC",
        },
    "frame":{
        "default"       : 1,
        "type"          : "int",
        "recipeOverride": True,
        "userOverride"  : True,
        "uiLevel"       : "UIBASIC",
        },
    "ignore":{
        "default"       : False,
        "type"          : "bool",
        "recipeOverride": True,
        "userOverride"  : True,
        "uiLevel"       :"UIBASIC"
        },
    "remove_bias":{
        "default"       : False,
        "type"          : "bool",
        "recipeOverride": True,
        "userOverride"  : True,
        "uiLevel"       : "UIBASIC",
        },
    "threshold":{
        "default"       : "auto",
        "type"          : "str",
        "recipeOverride": True,
        "userOverride"  : True,
        "uiLevel"       : "UIBASIC",
        },
    "tile":{
        "default"       : True,
        "type"          : "bool",
        "recipeOverride": True,
        "userOverride"  : True,
        "uiLevel"       : "UIBASIC",
        },
    "zscale":{
        "default"       : True,
        "type"          : "bool",
        "recipeOverride": True,
        "userOverride"  : True,
        "uiLevel"       : "UIBASIC",
        },
    },

}
