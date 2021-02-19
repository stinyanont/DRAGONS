#
#                                                                        DRAGONS
#
#                                                                    cal_service
# ------------------------------------------------------------------------------
from os import path
from importlib import import_module

from ..config import globalConf

from . import transport_request
from .userdb import UserDB
from .localdb import LocalDB
from .remotedb import RemoteDB

# ------------------------------------------------------------------------------
# BEGIN Setting up the calibs section for config files
CONFIG_SECTION = 'calibs'

# END Setting up the calibs section for config files
# ------------------------------------------------------------------------------
def get_calconf():
    try:
        return globalConf[CONFIG_SECTION]
    except KeyError:
        # This will happen if CONFIG_SECTION has not been defined in any
        # config file, and no defaults have been set (shouldn't happen if
        # the user has called 'load_calconf' before.
        pass


def init_calibration_databases(inst_lookups=None, ucals=None, upload=None):
    """
    Initialize the calibration databases for a PrimitivesBASE object.

    Parameters
    ----------
    inst_lookups : str
        local of the instrument lookups package (for the MDF lookup table)
    ucals : dict
        user calibrations
    upload : list
        things to upload (we're concerned about "calibs" and "science")

    Returns
    -------
    A UserDB object, possibly linked to additional CalDB objects
    """
    try:
        masks = import_module('.maskdb', inst_lookups)
        mdf_dict = getattr(masks, 'mdf_dict')
    except (ImportError, TypeError, AttributeError):
        mdf_dict = None
    else:
        for k, v in mdf_dict.items():
            mdf_dict[k] = path.join(path.dirname(masks.__file__),
                                    'MDF', v)

    caldb = UserDB(name="the darn pickle", mdf_dict=mdf_dict,
                   user_cals=ucals)
    upload_calibs = upload is not None and "calibs" in upload
    for db in parse_databases():
        if isinstance(db, RemoteDB):
            # Actually storing to a remote DB requires that "store" is set in
            # the config *and* the appropriate type is in upload
            db.store_science = db.store_cal and ("science" in upload)
            db.store_cal &= upload_calibs
        caldb.add_database(db)
    return caldb


def parse_databases(default_dbname="cal_manager.db"):
    """
    Parse the databases listed in the global config file.

    Parameters
    ----------
    default_dbname : str
        default name of database file (if only a directory is listed in the
        config file)

    Returns
    -------
    list of CalDB objects with the relevant attributes set
    """
    db_list = []
    databases = get_calconf().databases.splitlines()
    for line in databases:
        if not line:  # handle blank lines
            continue
        db, *flags = line.split()
        # "get" is default if there are no flags, but if any flags are
        # specified, then "get" must be there explicitly
        kwargs = {"get_cal": not bool(flags),
                  "store_cal": False}
        for flag in flags:
            if flag in kwargs:
                kwargs[f"{flag}_cal"] = True
            else:
                raise ValueError("{}: Unknown flag {!r}".format(db, flag))

        if path.isdir(db):
            db = path.join(db, default_dbname)
            cls = LocalDB
        elif path.isfile(db):
            cls = LocalDB
        else:  # does not check
            cls = RemoteDB
        db_list.append(cls(db, name=db, **kwargs))
    pass
