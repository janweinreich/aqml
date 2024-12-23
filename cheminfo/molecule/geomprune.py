#!/usr/bin/env python

import io2, re, os, sys
import numpy as np
from io2.gaussian_reader import GaussianReader as GR0
import aqml.cheminfo.molecule.molecule as cmm
from aqml.cheminfo.core import *
import aqml.cheminfo.rdkit.core as crk
from aqml.cheminfo.rw.ctab import *
import scipy.spatial.distance as ssd

h2kc = io2.Units().h2kc
T, F = True, False
np.set_printoptions(formatter={'float': '{: 0.4f}'.format})


class _atoms(object):
    """ `atoms object from file formats other than xyz"""
    def __init__(self, f):
        import ase.io as aio
        m = aio.read(f)
        self.zs = m.numbers
        self.coords = m.positions
        self.na = len(self.zs)

uc = io2.Units() # unit converter

def get_val(dic, key):
    assert key in list(dic.keys()), '#ERROR: prop not found!'
    if key in ['HF','MP2','MP3','MP4','CCSD','CCSD(T)']:
        return '%.4f'%( dic[key]*uc.h2kc )
    elif key in ['dipole']:
        return '%.4f'%dic[key]
    else:
        raise '#ERROR: prop not found!'


class CM(object):
    """
    coulomb matrix object
    """
    def __init__(self, atoms, param={'M':'cml1','rp':1.,'wz':T,'sort':T}):
        self.param = param
        self.atoms = atoms
        self.cml1 = T if param['M'] in ['cml1'] else F

    def generate_coulomb_matrix(self):
        """ Coulomb matrix

        sorted CM has serious limitation when used to identify unique conformers.
        E.g., for CH3-CH3 molecule, as the L1 norm of all H-containing columns are
        the same, so shuffling such columns leads to different CM, though the molecule
        remains unchanged

        The limitation can be alleviated through the use of L1 norm of each column!!
        """
        atoms = self.atoms
        na = atoms.na
        mat = np.zeros((na,na))
        _ds = ssd.squareform( ssd.pdist(atoms.coords) )
        dsp = _ds**self.param['rp']
        np.fill_diagonal(dsp, 1.0)
        zs = atoms.zs
        _X, _Y = np.meshgrid(zs,zs)
        if self.param['wz']:
            mat = _X*_Y/dsp
            diag = -np.array(zs)**2.4
        else:
            mat = 1/dsp
            diag = np.zeros(na)
        np.fill_diagonal(mat,  diag)
        if self.param['sort']:
            L1s = np.array([ np.sum(np.abs(mat[i])) for i in range(na) ])
            ias = np.argsort(L1s)
            if self.cml1:
                x = L1s[ias]
            else:
                x = np.ravel(mat[ias,:][:,ias])
        else:
            x = np.ravel(mat)
        #print 'x = ', x
        return x


def cdist(objs, param={}):
    _param = {'M':'cml1','rp':1.0,'sort':T,'wz':F}
    for key in list(param.keys()):
        if key in list(_param.keys()):
            if param[key] != _param[key]:
                _param[key] = param[key]
    _xs = []
    nc = len(objs)
    for obj in objs:
        if _param['M'] in ['cm','cml1']:
            _xobj = CM(obj,_param)
            xi = _xobj.generate_coulomb_matrix()#; print '              xi = ', xi
            _xs.append( xi )
        else:
            raise '#ERROR: unknown `M'
    xs = np.array(_xs)
    return xs, ssd.squareform( ssd.pdist(xs,'cityblock') )


def get_alternative(s):
    """ c1cccc[n]1 --> c1ccccn1 """
    patt = '\[n\]'
    s = re.sub(patt,'n',s)
    return s


class OptedMols(object):

    """
    postprocess optimized goemetries (by G09)
    so as to retrieve only the unqiue conformers
    and then convert to sdf format with properties
    embedded at the end of the file
    """

    def __init__(self, fs, rsmi, props=['HF'], istart=0):
        self.nc0 = len(fs)
        fsc = []
        cso = [] # mol objects
        ms = [] # ase mols
        ys = []
        #assert '_c' in fs[0]
        #self.filename = '_'.join( fs[0].split('/')[-1].split('_')[:-1] )
        self.fs_diss = []
        self.fs_redundant = []
        cids = []
        for i,f in enumerate(fs):
            fmt = f[-3:]
            if fmt in ['log','out']: #G09 output file
                dic = GR0(f, istart=istart)[-1]
                zs = np.array(dic['Atomic_numbers'],np.int)
                coords = np.array( dic['Positions'] )
                m = atoms(zs, coords)
                try:
                    co = cmm.Mol(zs, coords, ican=True)
                    can2 = get_alternative(co.can)
                    if rsmi not in [co.can,can2]:
                        print("#ERROR: %s has a SMILES %s, differs from %s"%(f,co.can,rsmi))
                        self.fs_diss.append(f)
                        continue
                    else:
                        _ys = {}
                        for key in props:
                            _ys[key] = get_val(dic,key)
                        ys.append(_ys)
                        ms.append(m); cso.append(co); fsc.append(f)
                except:
                    print("#ERROR: this is a radical!")
                    self.fs_diss.append(f)
                    continue
            elif fmt in ['mol','sdf']:
                oo = crk.RDMol(f)
                m = atoms(oo.zs, oo.coords)
                ms.append(m)
                cso.append( oo.prop['smiles_indigo'] )
                fsc.append(f)
                ys.append( [ oo.prop[k] for k in props ] )
        self.cso = cso
        self.ms = ms
        self.fsc = fsc
        self.nc = len(cso)
        self.ys = ys

    def prune_conformers(self, param={'M':'cml1','wz':F,'thresh':0.01}, KeepPat=None):
        """ get unique conformers """
        ccidsr = [0,] # always keep the first conformer!!
        if self.nc > 1:
            xs, ds = cdist(self.ms, param=param)
            #self.ds = ds
            #seq = np.argsort(self.ys[:,0])
            for i in range(1,self.nc):
                #ic = seq[i]
                if (not np.all(ds[i,ccidsr]>param['thresh'])):
                    self.fs_redundant.append( self.fsc[i] )
                    continue
                ccidsr.append(i)
        self.ccidsr = ccidsr
        nc2 = len(ccidsr)
        if nc2 < self.nc:
            print('   %d out of %d conformers survived'%(nc2, self.nc))

    def write_conformers(self):
        """ write conformers to sdf files """
        #print self.ccidsr
        #print self.fsc
        for ic in self.ccidsr:
            fo = self.fsc[ic][:-4] + '.sdf'
            ci = self.cso[ic]
            #zs = [ chemical_symbols[zi] for zi in mi.zs ]
            #si = '%.4f #HF '%(self.ys[cid]*h2kc)
            #write_xyz(fo, (zs, mi.coords), comments=si)
            prop = self.ys[ic]
            prop['smiles_indigo'] = ci.can
            zs, coords, chgs, bom = ci.blk
            write_ctab(zs, chgs, bom, coords, sdf=fo, prop=prop)


if __name__ == "__main__":
    """
    generate conformers for a input molecule

    Attention: most frequently, the input are sdf files of AMONs !!!!!!!!!!
    """
    import stropr as so

    _args = sys.argv[1:]
    if ('-h' in _args) or (len(_args) < 3):
        print("Usage: ")
        print("   geomprune [-r amons.can] [-thresh 0.01] [-M cml1] [folder]")
        sys.exit()

    print(' \n Now executing ')
    print('         geomprune ' + ' '.join(sys.argv[1:]) + '\n')

    idx = 0
    keys = ['-r','-ref']; hask,fsmi,idx = so.parser(_args,keys,'',idx,F)
    assert hask, '#ERROR: a reference smi/can file must be provided'
    assert fsmi[-3:] in ['smi','can'], '#ERROR: ref smiles file format not allowed'

    keys = ['-fmt','-format']; ifmt,ffmt,idx = so.parser(_args,keys,'sdf',idx,F)
    assert ifmt, '#ERROR: plz specify [-ffmt sdf/out]'

    keys = ['-d','-digits']; has_sl,sl,idx = so.parser(_args,keys,'6',idx,F) # frag_000001.sdf ...

    keys = ['-w','-write']; write,idx = so.haskey(_args,keys,idx) # rename & write unique conformers

    thresh = 0.01
    rep = 'cml1'

    fd = _args[idx]
    refs = [ si.strip() for si in file(fsmi).readlines() ]
    ng = len(refs) # number of (unique molecular) graphs

    if has_sl:
        sfmt = '%%0%dd'%( int(sl) )
    else:
        sfmt = '%%0%dd'%( len(str(ng)) )

    for _ in ['diss','redundant']:
        if not os.path.exists(fd+'/'+_):
            os.system('mkdir -p %s/%s'%(fd,_))

    for mid in range(1,ng+1):
        lb = sfmt%mid
        fs = io2.cmdout('ls %s/frag_'%fd + lb + '_*%s'%ffmt)
        print(' ** now processing mid %s'%lb)
        obj = OptedMols(fs,refs[mid-1])
        obj.prune_conformers(param={'M':rep,'wz':False,'thresh':thresh})
        if write:
            obj.write_conformers()
        for f in obj.fs_diss:
            os.system('mv %s.* %s/diss'%(f[:-4],fd))
        for f in obj.fs_redundant:
            cmd = 'mv %s.* %s/redundant'%(f[:-4],fd)
            os.system(cmd)

