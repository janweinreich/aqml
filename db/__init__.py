
from ase.data import g2_1,g2_2
from db.nist import hlai, xprmt, xprmt_2

from ase import *
from ase.units import Bohr
from ase.parallel import paropen

from stropr import *

import numpy as np
import os,sys

def merge_dicts(*dict_args):
    '''
    Given any number of dicts, shallow copy and merge into a new dict,
    precedence goes to key value pairs in latter dicts.
    '''
    result = {}
    for dictionary in dict_args:
        result.update(dictionary)
    return result

def get_molecule_db(formula, dbn=None):

    if dbn is None:
        data = merge_dicts(g2_1.data, g2_2.data, hlai.data, xprmt.data, xprmt_2.data)
    elif dbn == 'g2':
        data = merge_dicts(g2_1.data, g2_2.data)
    elif dbn == 'exp':
        data = merge_dicts(xprmt.data, xprmt_2.data)
    elif dbn == 'hlai':
        data = hlai.data
    else:
        raise Exception('#ERROR: no such db')

    try:
        db = data[formula]
    except:
        raise Exception('#ERROR: inquired molecule not in db')

    return db

def db2atoms(formula, dbn=None, rdb=False):

    db0 = get_molecule_db(formula, dbn=dbn)

    m0 = Atoms([],cell=[10,10,10])
    ss0 = get_symbols(db0['symbols'])
    na = len(ss0)

    moms = db0['magmoms']
    if moms is None:
        moms = [0,]*na

    ps_raw = db0['positions']
    if type(ps_raw) is str:
        ps = read_data(ps_raw)
    else:
        ps = ps_raw

    for i in range(na):
        m0.append(Atom(ss0[i], position=ps[i], magmom=moms[i]))

    if rdb: # return db info
        m0 = [m0, db0]

    return m0

def write_gcube(obj, filename=None, dbn=None, etyp=None):
    """
    write general cube file, being either trivial gaussian cube
    or extended gaussian cube file (where the second line is energy
    in unit kJ/mol)
    """

    if isinstance(obj, str):
        print(' use string to gen geometry from db, then write cube')
        atoms, db0 = db2atoms(obj, dbn=dbn, rdb=True)
        filename = obj
        try:
            energy = db0[etyp] # e.g., etyp = 'De' or 'D0'
        except:
            print('#ERROR: no such keyword `%s in db0'%etyp)
            sys.exit(2)
    elif isinstance(obj, Atoms):
        print(' directly use input Atoms obj to write cube')
        atoms = obj
        if filename is None:
            filename = concatenate([ aj.symbol for aj in atoms ])
        energy = 1.0E+20
    else:
        print('#ERROR: invalid input obj for writing cube file')

    try:
        De = db0['De']
    except:
        print('#ERROR: no `De keyword')
        sys.exit(2)

# codes following are extracted from cube.py in ase/io/ directory
# with minor modifications.
    fileobj = formula + '.cube'
    fileobj = paropen(fileobj, 'w')

    data = np.ones((2, 2, 2))
    data = np.asarray(data)

    fileobj.write('%s\n'%formula)
    fileobj.write('%.5E\n'%energy)

    cell = atoms.get_cell()
    shape = np.array(data.shape)

    corner = np.zeros(3)
    for i in range(3):
        if shape[i] % 2 == 1:
            shape[i] += 1
            corner += cell[i] / shape[i] / Bohr

    fileobj.write('%5d%12.6f%12.6f%12.6f\n' % (len(atoms), corner[0],
                                               corner[1], corner[2]))

    for i in range(3):
        n = data.shape[i]
        d = cell[i] / shape[i] / Bohr
        fileobj.write('%5d%12.6f%12.6f%12.6f\n' % (n, d[0], d[1], d[2]))

    positions = atoms.get_positions() / Bohr
    numbers = atoms.get_atomic_numbers()
    for Z, (x, y, z) in zip(numbers, positions):
        fileobj.write('%5d%12.6f%12.6f%12.6f%12.6f\n' % (Z, 0.0, x, y, z))

    data.tofile(fileobj, sep='\n', format='%e')


