#!/usr/bin/env python

import numpy as np
import aqml.cheminfo.core as cc
import itertools as itl
import aqml.io2 as io2
import os, sys, re, time
#from ase import Atom, Atoms
import cml.distance as cmld
import cml.kernels as cmlk
import cml.representation.slatm as csl
from cml.representation.core import generate_slatm
#import cml.representation.slatm_x as sl

import cml.math.matrix as cmt

import aqml.cheminfo as co
from aqml.cheminfo.rw.xyz import *
import cml.sd as sd # structured data module
import multiprocessing as mt
import aqml.cheminfo.data.atoms as cda
import ase.io as aio

T, F = True, False

uc = io2.Units()

class atoms(object):
    def __init__(self, f, pns=None, unit='h'):
        #nas, zs, coords, nsheav, props = read_xyz_simple(f, opt='z', property_names=pns)
        mi = aio.read(f)
        zs = mi.numbers
        self.coords = mi.positions #np.array(coords)
        self.na = len(mi) #nas[0]
        self.nheav = (zs>1).sum() #nsheav[0]
        #print('pn=',pns, props.keys())
        #const = {'h': uc.h2kc, 'eV': uc.e2kc}[unit]
        props = mi.info
        self.y = props[pns[0]] #* const
        self.zs = zs #np.array(zs, dtype=int)
        self.cell = mi.cell


class molecules(object):
    def __init__(self, fs, pns=None, unit='h'):
        nas = []; zs = []; coords = []; nsheav = []; props = {}
        self.nm = len(fs)
        const = 1. 
        if unit in ['h']: const = io2.Units().h2kc
        for f in fs:
            _nas, _zs, _coords, _nsheav, _props = read_xyz_simple(f, opt='z', property_names=pns)
            #print('f,props=',f, _props)
            nas += list(_nas)
            zs += list(_zs)
            coords += list(_coords)
            nsheav += list(_nsheav)
            for k in _props:
                if k in props:
                    props[k] += [ _props[k] * const ]
                else:
                    props[k] = [ _props[k] * const ]
        self.nas = nas
        self.zs = zs
        self.coords = coords
        self.nsheav = nsheav
        self.props = props
        self.ias2 = np.cumsum(nas)
        self.ias1 = np.concatenate(([0],self.ias2[:-1]))

    @property
    def ys(self):
        if not hasattr(self, '_ys'):
            pns = list(self.props.keys())
            self._ys = np.array(self.props[pns[0]])
        return self._ys

    @property
    def zsu(self):
        if not hasattr(self, '_zsu'):
            self._zsu = np.unique(self.zs)
        return self._zsu

    @property
    def namax(self):
        """ maximal number of heavy atoms of molecules """
        return np.max(self.nsheav)

    @property
    def zmax(self):
        return np.max(self.zs)

    @property
    def nzs(self):
        if hasattr(self, '_nzs'):
            nzs = self._nzs
        else:
            nzs = self.get_nzs()
        return nzs

    def get_nzs(self):
        nzs = []
        nm = len(self.nas)
        for i in range(nm):
            ib, ie = self.ias1[i], self.ias2[i]
            zsi = self.zs[ib:ie]
            nzsi = []
            for zi in self.zsu:
                nzsi.append( (zsi==zi).sum() )
            nzs.append(nzsi)
        return np.array(nzs, dtype=int)


def get_reference_atomic_energy(ref, meth, zs=None):
    """ get reference atomic energy from a set of mols
    located under directory `ref
    """
    fs = io2.cmdout('ls %s/*.xyz'%ref)
    ms = molecules(fs, [meth])
    #print('fs=',fs,'ms=',ms.props)
    esb,_,rank,_ = np.linalg.lstsq(ms.nzs, ms.props[meth], rcond=None)
    dct = np.zeros((ms.zsu[-1]+1))
    for i,zi in enumerate(ms.zsu):
        dct[zi] = esb[i]
    if zs is None:
        return dct
    return dct[zs]


def calc_ae_dressed(obj, idx1, idx2, meth=None, ref=None):
    ims = np.arange(obj.nm)
    ns1 = obj.ngs[idx1]
    ns2 = obj.ngs[idx2]
    ns = np.concatenate((ns1,ns2), axis=0)
    nel = len(ns1[0]) # number of elements
    if meth is None:
        pns = obj.property_names
        assert len(pns)==1, '##ERROR: plz specify `meth'
        meth = pns[0]
    ys = obj.props[meth].ravel()
    ys1, ys2 = ys[idx1], ys[idx2]

    t1 = cmt.Matrix(ns1)
    t = cmt.Matrix(ns)

    istat = T
    esb = np.zeros(ns1.shape[1])
    if ref is None:
        if t1.rank < nel:
            #print('ys1=', ys1, 'len(ys1)=',len(ys1))
            #print('ns1=', ns1, 'ns=', ns)
            #print('t1.rank=', t1.rank, 't.rank=', t.rank)
            #print('t1.idx=', t1.idx, 't.idx=',t.idx)
            if (t1.rank != t.rank): istat = F
            if (t1.idx != t.idx): istat = F
            if istat:
                ns1 = ns1[:,t.idx]
                ns2 = ns2[:,t.idx]
                esb,_,rank,_ = np.linalg.lstsq(ns1,ys1,rcond=None)
            else:
                # simply use the energy of free atom as reference!
                prog = None
                c = uc.h2kc ######### aaaa
                if meth in ['pbe340', 'pbe450']:
                    prog = 'vasp'
                else:
                    prog = 'orca'
                try:
                    esb = [ c * cda.dct[prog][co.chemical_symbols[zl]][meth] for zl in obj.zsu ]
                    #print('esb=',esb)
                except:
                    print(' ** warning: atomic energy at level %s not available'%meth)
                istat = T
        else:
            esb,_,rank,_ = np.linalg.lstsq(ns1,ys1,rcond=None)
    else:
        esb = get_reference_atomic_energy(ref, meth, obj.zsu)
    ys1p = np.dot(ns1,esb)
    dys1 = ys1 - ys1p
    ys2_base = np.dot(ns2,esb)
    dys2 = ys2 - ys2_base
    return istat, dys1, dys2, esb


class fobj(object):

    """ function object """

    def __init__(self, kernel, local=T):

        self.kernel = kernel

        if self.kernel[0] == 'g':
            self.d = cmld.l2_distance
            self.k = cmlk.get_local_kernels_gaussian if local else cmlk.gaussian_kernels
            self._factor = 1./np.sqrt(2.0*np.log(2.0))
        elif self.kernel[0] == 'l':
            self.d = cmld.manhattan_distance
            self.k = cmlk.get_local_kernels_laplacian if local else cmlk.laplacian_kernels
            self._factor = 1./np.log(2.0)
        else:
            raise Exception('#ERROR: not supported!')


def get_kernel_width(nas, zs, x, cab=F, kernel='g', itarget=F, debug=F):
    zsu = np.unique(zs)
    ias2 = np.cumsum(nas); ias1 = np.concatenate(([0],ias2[:-1]))
    nat = sum(nas)
    iast = np.arange(nat)
    dct = iast.copy()
    dct2 = iast.copy()
    for i,nai in enumerate(nas):
        ib, ie = ias1[i], ias2[i]
        dct[ib:ie] = i
        dct2[ib:ie] = np.arange(nai)
    Nz = len(zsu)
    zmax = zsu[-1]
    #print('    +++++ nas =',nas)
    fun = fobj(kernel)
    if Nz == 1:
        ds = fun.d(x,x)
        dsmax = np.array([np.max(ds)]*Nz)
    else: # Nz == 2:
        if cab:
            filt1 = (zs == zsu[-2]); filt2 = (zs == zsu[-1])
            ds = fun.d(x[filt1,:],x[filt2,:])
            dsmax = np.array([np.max(ds)]*Nz)
        else:
            # one dmax per atom type
            dsmax = []
            for i in range(Nz):
                # `i starts from 1 instead of 0 (i.e., 'H' atom) due to that
                # d(H,X) << d(X,X'), where X stands for any heavy atom
                filt = (np.array(zs) == zsu[i])
                xi = x[filt] 
                ias = iast[filt]; 
                #print('xi.shape=', xi.shape)
                _ds = fun.d(xi,xi)
                dmax_i = np.max(_ds)
                loc = np.array(np.where(dmax_i==np.triu(_ds)), dtype=int).T
                if debug:
                    print('  i,zi = ', i, zsu[i])
                for rci in loc:
                    ir0,ic0 = rci; ir,ic = ias[ir0],ias[ic0]
                    if debug:
                        print('  dmin is associated with  ', 'atom 1: im,ia=', dct[ir]+1,dct2[ir]+1, ', atom 2: im,ia=', dct[ic]+1,dct2[ic]+1)
                #print('zi,dmax=',zsu[i],dmax_i)
                dsmax.append(dmax_i)
            dsmax = np.array(dsmax)
    dso = np.ones(zmax) * 1.e-9 # in Fortran, first entry: 1
    for i,zi in enumerate(zsu):
        dso[zi-1] = dsmax[i]
    if debug:
        print('    dsmax=', dict(zip(zsu,dsmax)))
    #print('dso=',dso)
    return dso


def calc_ka(x2, x1, zs2, zs1, nas2, nas1, cab, zmax, sigmas, zaq=None, kernel='g'):
    """
    calculate atomic kernel matrix 

    vars
    ============
    zq: if set to None, then all pairwise atomic kernel elements are calc
        otherwise, only the kernel matrix elements corresponding to atoms
        with the specified `za are computed. 
    """
    nsg = len(sigmas)
    n1 = len(nas1); n2 = len(nas2)
    na1 = len(zs1); na2 = len(zs2)

    zs2 = np.array(zs2)
    zs1 = np.array(zs1)

    fun = fobj(kernel)

    if cab:
        raise Exception('??')
    else:
        iamap2 = np.cumsum(nas1)
        iamap1 = np.concatenate(([0], iamap2[:-1]))
        iast1 = np.arange(na1); iast2 = np.arange(na2)
        iac = T # calculate atomic contribution
        if zaq is None:
            ks = np.zeros((nsg,na2,n1))
            ksa = np.zeros((nsg,na2,na1))
            zsu = np.unique(zs2)
        else:
            iac = F
            ksa = np.zeros((nsg, (zaq==zs2).sum(), (zaq==zs1).sum()))
            zsu = [zaq]

        for zi in zsu:
            ias1 = iast1[zs1==zi]; ias2 = iast2[zs2==zi]
            ds = fun.d(x2[ias2], x1[ias1])
            ksi = np.array([ np.exp( -0.5 * (ds/sigmasi[zi-1])**2) for sigmasi in sigmas ])
            if iac:
                for i2,ia2 in enumerate(ias2):
                    for i1,ia1 in enumerate(ias1):
                        ksa[:, ia2, ia1] = ksi[:, i2, i1]
            else:
                ksa = ksi
        if iac:
            for i in range(n1):
                ib = iamap1[i]; ie = iamap2[i]
                ks[:,:,i] = np.sum(ksa[:,:,ib:ie], axis=2)
        else:
            ks = ksa
    return ks




class calculator(object):

    def __init__(self, ag=None, prog=None, nprocs=1, bj=F, abc=F, pbc=F, 
                 rcut=4.8, p=None, z=None, fp=None, scu='atom', w0='./',
                 coeffs=[1.], kernel='g', cab=F, reusek=F, savek=F, 
                 savex=F, reusex=F, fk=None, fx1=None, fx2=None, 
                 train=None, exclude=None, keep=None, lambdas=[4.0], 
                 test=None, n2=None, i1by1=F, idx1=None, idx2=None, 
                 iaml=T, i2=None, add=[], dmxby='a', ref=None, iprta=F, 
                 i_disp_eaq=F, debug=F):
        """
        :param ag: None or a class object containing all input parameters to
                   run AQML
        :param prog: any of the 3 ab-initio programs: orca/g09/molpro. Used to
                     look up atomic energies
        :param nprocs: number of processes to be used for openmp
        :param bj: (logical) calculate 2-body dispersion energy in dft-d3? 
        :param abc: (logical) calculate 3-body dispersion energy in dft-d3? 
        :param pbc: (logical) the system is periodic? 
        :param rcut: cutoff radius, defaults to 4.8 Angstrom
        :param train: (string) a directory containing all training molecules
        :param test: (string) a directory containing all test molecules
        :param p: (string) property to be train/test for ML, must be present in the xyz files
                  under specified training/test folder
        :param z: (integer) if `p` is an atomic property, `z` must be specified, indicating \
                   `p` of all atoms having nuclear charge `z` is to be trained/test
        :param fp: (string) property file. If specified, properties would be read
                  from this file instead of from xyz files under training folder
        :param scu: (string) smallest constituting unit, being one of ['atom', 'group']
        :param w0: (string) current working folder, defaults to './' 
        :param coeffs: (list of floats) each entry corresponds to one scaling factor for
                       computation of kernel width, i.e., kernel_width = coeff * dmax, where
                        `dmax` is the largest distance between atoms (or molecules) for local
                        (or global) representation
        :param kernel: (string) 'g' or 'l', i.e., Gaussian or Laplacian kernel
        :param cab: (logical) coupling atomic kernel between dissimilar atoms? Defaults to False
        :param reusek: (logical) load kernel from file? Default: False
        :param savek: (logical) save kernel matrix once computed? Default: False
        :param pbc: (logical) Systems being periodic? Default: False
        :param savex: (logical) save representation once computed? default: False
        :param fk: (string) kernel file, default: None. 
        :param fx1: (string) representation file for training set, default: None
        :param fx2: (string) representation file for test set, default: None
        :param exclude: (list of integers) molecules to be excluded for training. Default: None
        :param keep: (list of integers) mols to be kept for training. Default: None
        :param lambdas: (list of floats) regularization parameters, Default: [4.,]
        :param n2: (integer) Number of test molecules; must be specified when no test folder 
                        is specified
        :param i1by1: (logical) Is training/test to be done 1 by 1, i.e., one test mol each time
        :param idx1: (list of integers) training set by idxs of mols under training directory
        :param idx2: (list of integers) test set by idxs of mols under test directory
        :param iaml: (logical) use amons as training set?
        :param i2: (integer) ID of test molecule, for debugging purpose.
        :param dmxby: (string) calc `dmax` using amons/target/all?
        :param i_disp_eaq: (logical) regress energy of atoms in query mol
        :param debug: (logical) debug the code by printing details
        """

        if ag is None:
            self.prog = prog 
            self.nprocs = nprocs
            self.bj = bj
            self.abc = abc 
            self.pbc = pbc 
            self.rcut=rcut
            self.p=p
            self.z=z
            self.fp=fp
            self.scu=scu
            self.w0=w0
            self.coeffs=coeffs
            self.kernel=kernel
            self.cab=cab
            self.reusek=reusek
            self.savek=savek
            self.savex=savex
            self.reusex=reusex
            self.fk=fk
            self.fx1=fx1
            self.fx2=fx2
            self.train=train
            self._exclude=_exclude
            self._keep=_keep
            self.lambdas=lambdas
            self.test=test
            self.n2=n2
            self.i1by1=i1by1
            self.idx1=idx1
            self.idx2=idx2
            self.iaml=iaml
            self.i2=i2
            self.add=add
            self.dmxby=dmxby
            self.ref=ref
            self.iprta=iprta
            self.i_disp_eaq=i_disp_eaq
            self.debug=debug
        else:
            #self = ag 
            self.__dict__ = ag.__dict__.copy()


    def run(self):
    
        ag = self 
        rcut = ag.rcut
        fs = []
        _fs1 = []; n2 = 0
        w0 = ag.w0
        if ag.w0 in ['.', './', '']:
            w0 = '' #ag.w0 + '/' 
        nfd = len(ag.train)
        for i,_wd in enumerate(ag.train):
            wd = _wd if _wd[-1] != '/' else _wd
            if ag.debug:
                print('_wd=',_wd)
            #if not os.path.exists(w0+wd):
            #    try:
            #        wd += '_extl/'
            #        assert os.path.exists(w0+wd)
            #    except:
            #        raise Exception('#ERROR: either %s or %s does not exist'%(w0+_wd, w0+wd))
            _fsi = io2.cmdout('ls %s%s/*.xyz'%(w0,wd))
            #print('fsi=',_fsi)
            if len(_fsi) == 0:
                if ag.debug:
                    print(' ** folder %s is empty'%wd)
                continue

            ii = i-nfd
            if ii in ag.dirsk: ### aaaa
                fsi = [ _fsi[ik] for ik in ag.idxsk[ii] ]
            else:
                fsi = _fsi

            _fs1 += fsi

        ## The 'copy()' below is essential! Otherwise, 
        ## we will end up with `_fs1 being equal to `fs!!
        fs = _fs1.copy() 

        n1t = len(_fs1)
        fmap = None 
        if ag.debug: print('test=',ag.test)
        if ag.test is not None:
            fs2 = []
            for wd in ag.test:
                fsj = io2.cmdout('ls %s%s/*.xyz'%(w0,wd))
                assert len(fsj) > 0
                fs2 += fsj
            n2 = len(fs2)
            assert n2>0, '#ERROR: no xyz files found in target folder'
            fs += fs2
            if n2>1: 
                fmap = ag.train[0]+'/map.pkl'
            fs1 = _fs1
        else:
            if ag.debug: print('n2 = ', ag.n2)
            if ag.n2 is not None: #len(ag._idx1)==0:
                fs1 = _fs1[:-ag.n2]
                fs = _fs1  
            else:
                idx1 = ag.idx1
                fs1 = [ _fs1[i1] for i1 in idx1 ]
                n1t = len(fs1)
                idx2 = ag.idx2
                fs2 = [ _fs1[i2] for i2 in idx2 ]
                fs = fs1 + fs2
                n2 = len(idx2) #n2



        if ag.p is None:
            # not explicitely given by user, then detect it from input file
            l2 = open(fs[0]).readlines()[1]
            ps = [ si.split('=')[0] for si in l2.split() ]
            if len(ps) > 1:
                print(' Property list: ', ps )
                raise Exception('#ERROR: pls specify one property!')
            if ag.debug: print('    set property to "%s"'% ps[0])
            ag.p = ps[0]

        unit = 'h'

        nm = len(fs)

        loops = 1
        maps = None 
        if ag.iaml:
            if n2==1:
                maps = np.array([np.arange(nm-1)], dtype=int)
            elif n2>1: # read map file
                if fmap and os.path.exists(fmap):
                    loops = n2
                    print('    ** found `fmap file: %s, use query-specific amons as training set'%fmap)
                    _dt = sd.io.load(fmap)
                    maps = _dt['maps']
                else:
                    print(' ** no `fmap file specified, use all mols with idx ranging from 0 to nm-n2 as a single training set')
                    if ag.i1by1:
                        loops = n2
                    else:
                        loops = 1
        else:
            if ag.i1by1:
                loops = n2

        res = {}


        iap = F
        if ag.p in ['nmr','chgs','cls','force']:
            iap = T
            assert ag.z is not None, '#ERROR: in case of atomic property, "-z [val]" must be specified'

        isimple = F
        if iap:
            isimple = T 

        os.environ['OMP_NUM_THREADS'] = "%d"%ag.nprocs



        for l in range(loops):

            if maps is None:
                n1 = n1t
                if ag.i1by1:
                    if ag.debug:
                        print('fs1=',fs1)
                        print('fs2=', fs2[l:l+1])
                    fsk = fs1 + fs2[l:l+1]
                    print('i=',n1+l+1) #, 'n1=',n1) #, 'idx1=[%s]'%(','.join(['%d'%(ix+1) for ix in idx])), ' idx2=',[n1t+l+1])
                else:
                    fsk = fs
            else:
                _idx = maps[l]
                idx1 = list( _idx[_idx>-1] )
                if ag.i2:
                    if l+1 != ag.i2:
                        continue
                    idx1 += [ ia-1 for ia in ag.add ]
                idx = list(set(idx1).difference(set(ag.exclude)))
                idx.sort() 
                n1 = len(idx)
                fsk = [ fs[_] for _ in idx + [n1t+l] ]
                if ag.debug: print('i=',l+1, 'n1=',n1)
                if ag.iprta:
                    print('idx1=[%s]'%(','.join(['%d'%(ix+1) for ix in idx])), ' idx2=',[n1t+l+1])

            if ag.debug: 
                if maps is not None:
                    comm = list( set(idx1).intersection(set(ag.exclude)) )
                    print('    deleted mols:', np.array(comm,dtype=int)+1)
                    print('    final training mols:', fs)


            ms = [ atoms(f,[ag.p],unit=unit) for f in fsk ]
            nml = len(fsk)
            ims = np.arange(nml)
            ims1 = ims[:n1]
            ims2 = ims[n1:]

            const = {'h': uc.h2kc}[unit]
            if ag.p not in ['nmr','alpha','chgs','cls']:
                const = 1.0

            if ag.fp is None:
                obj = cc.molecules(fsk, [ag.p], unit=unit, isimple=isimple)
                ys = obj.ys; #print('ys=',ys)
            else:
                obj = cc.molecules(fsk) #, [ag.p], unit=unit)
                p = ag.fp[:-4]
                ys = np.loadtxt(ag.fp) * const # use filename as property name

            #print('ngs=\n', obj.ngs)

            if ag.bj:
                ifd = F
                for xc in ['pbe','b3lyp',]:
                    if xc in ag.p:
                        if xc in ['b3lyp',]:
                            fun = {'b3lyp':'b3-lyp'}[xc]
                        else:
                            fun = xc
                        ifd = T
                        break
                assert ifd, '#ERROR: xc not identified!'
                print('    calc dftd3, xc=', fun)
                es_disp = obj.calc_dftd3_energy(xc=fun, iabc=ag.abc, nprocs=ag.nprocs) * const
                print('    disp shape:', np.array(es_disp).shape)
                ys += np.array([es_disp]).T
                print('    disp corr done')
            assert len(ys) == obj.nm
            obj.props[ag.p] = ys

            obj.set_scu(ag.scu) #'group')
            #print('scu=', ag.scu, 'scus=',obj.ngs)
            zsu = obj.zsu
            nzs = obj.nzs
            nas = obj.nas
            zs = obj.zs
            zmax = np.max(zs)
            ys = np.array(obj.props[ag.p])
     
            mb = csl.NBody(obj) #[ims2]) # determine many-body types by targets only
            mbtypes = mb.get_slatm_mbtypes()
            #print('mbtypes = ', mbtypes)
     
            cab=ag.cab
            dgrids = [0.04,0.04]; widths = [0.05,0.05]

            if ag.savex or ag.savek:
                if not os.path.exists('data/'):
                    os.mkdir('data/')

            # now x1 (training set)
            fn1 = ag.train[0]
            if fn1[-1] == '/': fn1 = fn1[:-1]
            fn1 = 'data/' + '-'.join(fn1.split('/'))
            if ag.rcut != 4.8:
                fn1 += '-rc%.1f'%ag.rcut

            if iap:
                fn1 += '-z%d'%ag.z
            fx1 = fn1 + '-x1.npz'
            #print('f1=', fn1)

            zs1=[]; nas1=[]; nhvs1=[]
            for i in ims1:
                zs1 += list(ms[i].zs)
                nas1 += [ms[i].na]
                nhvs1 += [ms[i].nheav]
            namax = np.max(nhvs1)
            fn2 = ag.test[0]
            if fn2[-1] == '/': fn2 = fn2[:-1]
            fn2 = 'data/' + '-'.join(fn2.split('/'))
            if ag.rcut != 4.8:
                fn2 += '-rc%.1f'%ag.rcut
            if iap:
                fn2 += '-z%d'%ag.z
            fx2 = fn2 + '-x2.npz'

            zs2=[]; nas2=[]; nhvs2=[]
            for i in ims2:
                mi = ms[i]
                zs2 += list(mi.zs)
                nas2 += [mi.na]
                nhvs2 += [mi.nheav]
            nas = nas1 + nas2
            fk = fn1 + '-kernels%s.npz'%( {'g':'', 'l':'-l'}[ag.kernel[0]] )
            #print('fk=',fk)

            debug = ag.debug

            coeffs = []
            i_atom_specific = F 
            try:
                sc = ag.coeffs[0] # ag.coeffs = ['1.0,2.0'], i.e., scale dmax by the same factor!
                coeffs = [ eval(ci) for ci in sc.split(',') ]
            except:
                i_atom_specific = T 
                zsc = []
                ysc = []
                for i, si in enumerate(ag.coeffs): # ag.coeffs = ['H,1.0', 'C,2.0',], i.e., different atom, different scaling of `dmax
                    s2 = si.split(',')
                    zsc.append( co.chemical_symbols_lowercase.index( s2[0] ) )
                    ysc.append( [ eval(vi) for vi in s2[1:] ] )
                tuples = list(itl.product(*ysc))
                nzc = len(zsc)
                #print(zsc)
                for t in tuples:
                    #print(t)
                    sigmas_i = dsmax.copy()
                    for j in range(nzc):
                        sigmas_i[zsc[j]-1] = t[j]
                    sigmas.append( sigmas_i )
                    coeffs.append( dict(zip(zsc, t)) )


            if ag.reusek:
                if ag.fk is not None:
                    fk = ag.fk
                assert os.path.exists(fk)
                print('       found kernel file: ', fk)
                dsk = np.load(fk)
                ks1 = dsk['ks1']; ks2 = dsk['ks2']
                print('       kernels read with success')
                print(' nm1=',len(ims1), 'shp1=',ks1[0].shape, 'shp2=',ks2[0].shape)
                if iap:
                    nz1 = (obj[ims1].zs==ag.z).sum(); nz2 = (obj[ims2].zs==ag.z).sum() 
                    print('nz1=', nz1, 'nz2=',nz2)
                    assert nz1 == ks1[0].shape[0]
                    assert nz2 == ks2[0].shape[0]
                else:
                    assert len(ims1) == ks1[0].shape[0] and len(ims2) == ks2[0].shape[0]
            else:
                if not ag.reusex:
                    _x = []
                    for i in ims1:
                        mi = ms[i]
                        xi = generate_slatm(mi.coords, mi.zs, mbtypes, local=T, sigmas=widths, dgrids=dgrids, rcut=rcut, pbc=ag.pbc, cell=mi.cell)
                        _x.append(xi)
                    x1 = np.concatenate(_x)
                    if ag.savex:
                        np.savez(fn1, x1=x1)
                else:
                    if ag.fx1 is not None:
                        fx1 = ag.fx1
                        assert os.path.exists(fx1)
                    d1 = np.load(fx1)
                    x1 = d1['x1']
      
                # now x2 (test set)
                if not ag.reusex:
                    _x = []
                    for i in ims2:
                        mi = ms[i]
                        xi = generate_slatm(mi.coords, mi.zs, mbtypes, local=T, sigmas=widths, dgrids=dgrids, rcut=rcut, pbc=ag.pbc, cell=mi.cell)
                        _x.append(xi)
                    x2 = np.concatenate(_x)
                    if ag.savex:
                        np.savez(fn2, x2=x2)
                else:
                    if ag.fx2 is not None:
                        fx2 = ag.fx2
                        assert os.path.exists(fx2)
                    d2 = np.load(fx2)
                    x2 = d2['x2']
     
                if ag.dmxby in ['target']:
                    dsmax = get_kernel_width(nas2, zs2, x2, kernel=ag.kernel, cab=cab, debug=debug)
                elif ag.dmxby in ['amons']:
                    dsmax = get_kernel_width(nas1, zs1, x1, kernel=ag.kernel, cab=cab, debug=debug)
                elif ag.dmxby in ['a', 'all']:
                    dsmax = get_kernel_width(nas, zs1+zs2, np.concatenate((x1,x2)), kernel=ag.kernel, cab=cab, debug=debug)
                else:
                    raise Exception('#ERROR: unknown ag.dmxby')
                #print('cab=',cab, 'dsmax=', dsmax)

                fun = fobj(ag.kernel)

                # for Gaussian kernel
                #if ag.kernel[0] == 'g':
                #    factor = 1./np.sqrt(2.0*np.log(2.0))
                #elif ag.kernel[0] == 'l':
                #    factor = 1./np.log(2.0)
                #else:
                #    raise Exception('not supported!')
                factor = fun._factor
     
                sigmas = []
                if i_atom_specific:
                    sigmas = []
                    for dcti in coeffs:
                        sigmas_i = []
                        for si in dcti:
                            zi = co.chemical_symbols_lowercase.index( s2[0] )
                            sigmas_i[zi-1] = dsmax[zi-1] * dcti[si]
                        sigmas.append( sigmas_i )
                else: 
                    sigmas = [ factor * dsmax * ci for ci in coeffs ]

                sigmas = np.array(sigmas)
                #print('sigmas = ', sigmas)
      


                # calculate kernel-matrix
                if iap:
                    ks1 = calc_ka(x1, x1, zs1, zs1, nas1, nas1, cab, zmax, sigmas, zaq=ag.z, kernel=ag.kernel)
                    ks2 = calc_ka(x2, x1, zs2, zs1, nas2, nas1, cab, zmax, sigmas, zaq=ag.z, kernel=ag.kernel) 
                    print('  size of k1: ', ks1[0].shape, ' size of k2: ', ks2[0].shape)
                else:
                    ks1 = fun.k(x1, x1, zs1, zs1, nas1, nas1, cab, zmax, sigmas)
                    ks2 = fun.k(x2, x1, zs2, zs1, nas2, nas1, cab, zmax, sigmas)

                if ag.i_disp_eaq:
                    ksa21 = calc_ka(x2, x1, zs2, zs1, nas2, nas1, cab, zmax, sigmas, zaq=None, kernel=ag.kernel)

                if ag.savek:
                    np.savez(fk, ks1=ks1, ks2=ks2)
                #print('    ks1.size=',ks1.shape)
                #print('    ks2.size=',ks2.shape)
     
            llambdas = [ 10**(-eval(l)) for l in ag.lambdas.split(',') ] #[1e-4]: # [1e-2, 1e-4, 1e-8]

            #nis = np.arange(1,1+namax)
            #if ag.i_disp_ae: # display atomic energies at the end
            #    nis = [namax]

            idx2 = ims2
            for ic,coeff in enumerate(coeffs):
              _k1 = ks1[ic]; _k2 = ks2[ic]
              for il, llambda in enumerate(llambdas):
                print('    coeff=', coeff, 'llambda=',llambda)
                for ni in range(1,1+namax):
                  if namax > 12 and (ni not in nhvs1): continue
                  idx1 = ims1[np.array(nhvs1) <= ni]
                  if len(idx1) == 0: continue 

                  if iap:
                    iasz1 = [] # relative idx within each subset of atoms associated with ag.z
                    for ii1 in idx1:
                        ib = obj.ias1[ii1]; ie = obj.ias2[ii1]
                        iasi = np.arange(ib,ie)
                        iasz1 += list(obj.iasz[iasi[obj.zs[ib:ie]==ag.z]])
                    assert len(iasz1)==len(np.unique(iasz1))
                    #print('iasz1=',iasz1)
                    k1c = _k1[iasz1][:,iasz1]
                    k2c = _k2[:,iasz1]

                  else:
                    k1c = _k1[idx1][:,idx1]; k2c = _k2[:,idx1]
                  #print('idx1=',idx1, ' idx2=',idx2, 'k2.shape=',k2.shape)

                  k1 = k1c.copy(); k2 = k2c.copy()

                  if iap: 
                    #print(' atomic property: shift `ys to center')
                    ysp = obj.props[ag.p]; #print('ysp=',ysp)
                    ys1 = []
                    for it in idx1:
                        ib = obj.ias1[it]; ie = obj.ias2[it]
                        ysi = ysp[it]
                        #print('ysi=', ysi)
                        ys1 += list( ysi[obj.zs[ib:ie]==ag.z] )
                    ys2 = []
                    for it in idx2:
                        ib = obj.ias1[it]; ie = obj.ias2[it]
                        ysi = ysp[it]
                        ys2 += list( ysi[obj.zs[ib:ie]==ag.z] )
                    #print('ys1=',ys1, 'mean=', np.mean(ys1))
                    ys1_base = np.mean(ys1)
                    ys1 = np.array(ys1) - ys1_base 
                    ys2 = np.array(ys2) - ys1_base
                    istat = T
                  else:
                    #print(' extensive property: dressed atom contrib')
                    istat, ys1, ys2, esb = calc_ae_dressed(obj, idx1, idx2, meth=ag.p, ref=ag.ref)

                  #irp = F
                  #if np.linalg.matrix_rank(obj.ngs[idx1]) < 

                  #print('ys1=', list(ys1))
                  #print('ys2=',ys2)
                  obsolete = """if not istat:
                      if np.all(np.array(esb)==0):
                          if len(ys2)==1:
                              print('  %2d %6d %12.4f %12.4f'%(ni,len(idx1),np.nan, np.nan))
                          else:
                              print('  %2d %6d %12.4f %12.4f %12.4f'%(ni,len(idx1),np.nan, np.nan, np.nan))
                      else:
                          if len(ys2)==1:
                              print('  %2d %6d %12.4f %12.4f'%(ni,len(idx1), abs(ys2[0]), ys2[0]))
                          else:
                              print('  %2d %6d %12.4f %12.4f %12.4f'%(ni,len(idx1),np.nan, np.nan, np.nan))
                      continue"""
     
                  #print('k1.shape = ', k1.shape, 'ys1.shape=',ys1.shape)
                  k1[np.diag_indices_from(k1)] += llambda
                  alphas = np.linalg.solve(k1,ys1)
                  ys2p = np.dot(k2,alphas)
                  #print('n2=',n2,'ys2p=',ys2p)
                  dys2 = ys2p - ys2
                  mae = np.sum(np.abs(dys2))/len(dys2)
                  rmse = np.sqrt(np.sum(dys2*dys2)/len(dys2))
                  errmax = np.max(np.abs(dys2))

                  #if len(dys2)==1:
                  #    print('dys2=',dys2, 'ys2=',ys2)
                  #    print('  %2d %6d %12.4f %12.4f  (DressedAtom mae=%12.4f)'%(ni,len(idx1),mae,dys2[0], -ys2[-1]))
                  #else:
                  if iap:
                    print('  %2d %6d %12.4f %12.4f %12.4f  (mean=%12.4f)'%(ni,len(idx1),mae,rmse,errmax, ys1_base))
                  else:
                    if len(dys2)==1:
                      yerr = dys2[-1]
                      #if np.abs(ys2p[-1]) > np.abs(obj.ys[idx2][-1]):
                      #   yerr = -obj.ys[idx2][-1]
                      print('  %2d %6d %12.4f %12.4f  (DressedAtom mae=%12.4f)'%(ni,len(idx1),mae, yerr, -ys2[-1]))
                    else:
                      yerr = np.mean(np.abs(dys2))
                      print('  %2d %6d %12.4f %12.4f %12.4f  (DressedAtom mae=%12.4f)'%(ni,len(idx1),mae,rmse,errmax, yerr)) #-ys2[-1]))
                  if ag.iprta and ni==namax:
                      print( '  detailed outcomes of prediction:')
                      #print( '      ', dict(zip(1+idx2, [eval('%.2f'%yi) for yi in dys2])) )
                      print( 'esb=',esb, 'ys2,ys2p,dys2=\n', np.concatenate(([ys2],[ys2p],[dys2]), axis=0).T)

                if ag.i_disp_eaq:
                    if not ag.iaml:
                        raise Exception(' ** Think twice: Is this meaningful??')
                    #print('ksa21=', ksa21)
                    #print('alpha.size=',alphas.size, ksa21[ic].shape)
                    easq = np.dot(ksa21[ic], alphas) #get_easq(idx=l) # `l is the idx of mol in test set!
                    assert len(dys2) == 1
                    assert np.abs(easq.sum() - ys2p[0]) <= 0.001
                    if ag.prog is None:
                        print(' *** for display of atomic contrib to AE, please specify -prog g09/orca/molpro')
                        sys.exit(2)
                    edct = dict(zip(obj.zsu, esb))
                    prefactor = {'h': uc.h2kc, }[unit]
                    eas0u = [ prefactor * cda.dct[ag.prog][co.chemical_symbols[zl]][ag.p] for zl in obj.zsu ]
                    eas0 = dict(zip(obj.zsu, eas0u))

                    zsq = []
                    for it in idx2: 
                        ib = obj.ias1[it]; ie = obj.ias2[it]
                        zsq += list(obj.zs[ib:ie])


                    sq = '\n'
                    for ja,eaj in enumerate(easq):
                        suffix = '\n'
                        zj = zsq[ja]
                        if eaj == easq[-1]:
                            suffix = ''
                        sq += '    %4d %3d %8.2f%s'%(ja+1, zj, eaj+edct[zj]-eas0[zj], suffix)
                    print('\natomic energies')
                    print('    #atm  #Z     #E_A', sq)
                    #print(' =====================')
                    #print('            sum: %.2f'%( sum(easq) ))

                if istat and len(dys2)==1:
                    _key = 'ic%dil%d'%(ic,il)
                    if _key in res:
                        res[_key] += list(dys2) 
                    else:
                        res[_key] = list(dys2)

        if ag.iprta:
            if len(dys2) == 1:
                print(' summary of predictions: ')
                for k1 in res:
                    print('icoeff, illambda = ', k1)
                    print( dict(zip(np.arange(1,loops+1), [ eval('%.2f'%dyi) for dyi in res[k1] ] )) )


