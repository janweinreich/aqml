#!/usr/bin/env python

import numpy as np
import io2
import re,os,sys

from qml.math import cho_solve
import qml.distance as qd
import qml.kernels as qk

def get_line_number(f,s):
    return int( io2.cmdout2("grep -n '%s' %s | tail -1 | sed 's/:/ /g' | awk '{print $1}'"%(s,f) ) )

class wfns(object):

    def __init__(self, wds, ia1, ia2, coeff=1.0, llambda=1.e-4):

        """
        ia1, ia2 -- atomic index, starting from 0,
        """

        s1 = SLATM(wds, 'out', regexp='', properties='AE', M='slatm', \
                local=True, igroup=False, ow=False, nproc=1, istart=0, \
                slatm_params = { 'nbody':3, 'dgrids': [0.03,0.03],  'sigmas':[0.05,0.05],\
                                 'rcut':4.8, 'rpower2':6, 'ws':[1.,1.,1.], \
                                 'rpower3': 3, 'isf':0, 'kernel':'g', 'intc':3 }, \
                iY=False)
        fs = s1.fs
        coords = s1.coords
        iast2 = s1.nas.cumsum()
        iast1 = np.array([0,] + list(kas2[:-1]) )

        objs = []
        ds = []
        for i, f in enumerate(fs):
            obj = wfn(f)
            obj.get_dm()
            objs.append( obj )
            if i < self.nm - 1:
                ds.append( ssd.cdist( coords[i], coords[self.nm-1] ) )

        ## specify target atom pairs!!
        #ia1, ia2 = 0, 1
        #coeff = 1.0; llambda = 1e-6

        cia1 = coords[-1][ia1]
        cia2 = coords[-1][ia2]
        xs = []; ys = []; nhass = []
        for i, f in enumerate(fs):
            dsi = ds[i]
            jas = np.arange( dsi.shape[0] )
            filt1 = ( dsi[:, ia1] <= 0.01 )
            filt2 = ( dsi[:, ia2] <= 0.01 )
            if np.any(filt1) and np.any(filt2):
                nhass.append( s1.nhass[i] )
                obj = objs[i]
                ja1 = jas[filt1]; ja2 = jas[filt2]
                p,q,r,s = obj.ibs1[ja1],obj.ibs2[ja1], obj.ibs1[ja2],obj.ibs2[ja2]
                dmij = obj.dm[p:q,r:s].ravel()
                ys.append(dmij)

                iat1 = iast1[i] + ja1
                iat2 = iast1[i] + ja2
                x1 = s1.X[ iat1 ]; x2 = s1.X[iat2]
                xs.append( np.concatenate((x1,x2),axis=0) )

        nprop = len(dmij)

        nt = len(nhass)
        nhass = np.array(nhass)
        tidxs = np.arange(nt)
        nhass_u = np.unique( nhass ); nu = len(nhass_u)
        xs = np.array(xs)
        ys = np.array(ys)
        xs2 = np.array([ xs[-1] ])
        ys2 = np.array([ ys[-1] ])
        for j in range(nu):
            jdxs = tidxs[ nhass <= nhass_u[j] ]
            xs1 = xs[ jdxs, : ]
            ys1 = ys[ jdxs, : ]
            ds1 = qd.l2_distance(X1,X1) # ssd.pdist(x1, metric='euclidean')
            dmax = max(ds1.ravel())
            sigma = coeff*dmax/np.sqrt(2.0*np.log(2.0))
            K1 = qk.gaussian_kernel(xs1, xs1, sigma)
            assert np.allclose(K1, K1.T), "Error in local Gaussian kernel symmetry"

            K1[np.diag_indices_from(K1)] += llambda
            alpha = np.array([ cho_solve(K1,ys1) ]).T

            K2 = qk.gaussian_kernel(xs2, xs1, sigma)
            ys2_est = np.dot(K2, alpha)
            error = np.squeeze(ys2_est) - ys2
            mae = np.sum(np.abs(error))/nprop
            rmse = np.sqrt( np.sum( error**2 )/nprop )
            print '%4d %12.8f %12.8f'%(len(xs1), mae, rmse)


class wfn(object):

    def __init__(self, f):

        self.f = f

        # total number of basis set
        nt = int( io2.cmdout2("grep 'cartesian basis functions$' %s | head -1 | awk '{print $1}'"%f) )
        self.nt = nt

        n1 = get_line_number(f, '     Density Matrix:') + 1
        n2 = get_line_number(f, '    Full Mulliken population analysis')
        cs = file(f).readlines()[n1-1:n2]
        self.cs = cs

        n0 = 5 # number of columns for DM in Gaussian output file
        nl = n2-n1
        i5 = 0
        ns = [0,]

        # Num_BlocKs
        nbk = nt/5 if nt%5 == 0 else nt/5 + 1
        self.nbk = nbk
        for i in range(nbk):
            nli = nt - i5*5 + 1; ns.append(nli); i5 += 1
        #print 'nl, ns = ', nt,ns
        assert nl == sum(ns), '#ERROR: Shit happens?'
        ins = np.cumsum(ns)
        self.ins = ins


    def get_dm(self):

        dm = np.zeros((self.nt,self.nt))

        nbk = self.nbk
        ins = self.ins
        cs = self.cs

        for i in range(nbk):
            i1 = ins[i]
            i2 = ins[i+1]
            ics = np.array(cs[i1].split()).astype(np.int) - 1 # indices of columns
            csi = cs[i1+1:i2]; ni = len(csi)
            if i == 0:
                ibs = []; bst = []; symbs = []
                # get basis --> atom Idx
                for j in range(ni):
                    sj = csi[j]
                    sj1 = sj[:22].strip().split(); sj2 = sj[22:].strip().split()
                    nj1 = len(sj1); nj2 = len(sj2)
                    if len(sj1) == 4:
                        #print ' ++ sj1 = ', sj1
                        ibs.append(j); symbs.append(sj1[2]); bst.append(sj1[3])
                    else:
                        bst.append(sj1[1])
                    ir = int(sj1[0])
                    dm[ir-1,ics[:nj2]] = np.array(sj2).astype(np.float)
            else:
                for j in range(ni):
                    sj = csi[j]
                    sj1 = sj[:22].strip().split(); sj2 = sj[22:].strip().split()
                    nj2 = len(sj2)
                    ir = int(sj1[0])
                    dm[ir-1,ics[:nj2]] = np.array(sj2).astype(np.float)

        self.bst = bst

        noccs = dm.diagonal()
        dm_u = dm + dm.T
        np.fill_diagonal(dm_u, noccs)
        dm = dm_u

        ibs_u = np.array( ibs + [self.nt,] ).astype(np.int)
        na = len(ibs)

        # get number of basis function for each atom
        nbsts = [ ibs_u[k+1]-ibs_u[k] for k in range(na) ]
        self.nbsts = nbsts

        # get beginning and ending indices of basis function for all atoms
        ibs1 = ibs_u[:na]; ibs2 = ibs_u[1:na+1]
        self.ibs1 = ibs1
        self.ibs2 = ibs2

        for ia in range(na):
            # get beginning and ending indices of basis function for atom `ia1 and `ia2
            p,q,r,s = ibs1[ia-1],ibs2[ia-1], ibs1[ia-1],ibs2[ia-1]
            dmij = dm[p:q,r:s]

            # if `ia1 and `ia2 correspond to the same atom, then sum up P_ij and P_ji
            # since \psi_i * \psi_j == \psi_j * psi_i (\psi is basis function)
            diag = dmij.diagonal()
            dmij_u = dmij + dmij.T
            np.fill_diagonal(dmij_u, diag)
            # return only the lower trainagular part of density matrix
            dmij = np.tril(dmij_u)
            dm[p:q,r:s] = dmij

        self.dm = dm


    def get_overlap_matrix(self):

        ins = self.ins
        S = np.zeros((self.nt,self.nt))

        # get overlap matrix
        cmd = "grep ' *** Overlap ***' %s"%f
        assert os.popen(cmd)
        n1 = get_line_number(f, ' *** Overlap ***') + 1

        cmd = "grep ' *** Kinetic Energy ***' %s"%f
        n2 = get_line_number(f, ' *** Kinetic Energy ***')

        cs = file(f).readlines()[n1-1:n2]

        for i in range(nbk):
            i1 = ins[i]
            i2 = ins[i+1]
            ics = np.array(cs[i1].split()).astype(np.int) - 1 # indices of columns
            csi = cs[i1+1:i2]; ni = len(csi)
            for j in range(ni):
                sj = csi[j]
                sj1 = sj[:7].strip().split(); sj2 = re.sub('D', 'E', sj[7:]).strip().split()
                nj2 = len(sj2)
                ir = int(sj1[0])
                S[ir-1,ics[:nj2]] = np.array(sj2).astype(np.float)

        diag = S.diagonal()
        S_u = S + S.T
        np.fill_diagonal(S_u, diag)
        self.S = S_u


if __name__ == '__main__':

    import os,sys
    import stropr as so
    from termcolor import colored

    args = sys.argv[1:]; idx = 0

    if '-h' in args:
        print 'retrieve_density_matrix -idiff F -icomb F -ioverlap F [file,ia1,ia2] [file,ia1,ia2]'
        sys.exit(2)

    dic = {'T':True, 'F':False}
    keys = ['-idiff',]; hask,sidiff,idx = so.parser(args,keys,'F',idx); idiff = dic[sidiff]
    keys = ['-iratio',]; hask,siratio,idx = so.parser(args,keys,'T',idx); iratio = dic[siratio]
    keys = ['-icomb',]; hask,sicomb,idx = so.parser(args,keys,'F',idx); icomb = dic[sicomb]
    keys = ['-ioverlap',]; hask,sioverlap,idx = so.parser(args,keys,'F',idx); ioverlap = dic[sioverlap]

    s = args[idx:]
    n = len(s)
    Ss = []; dmijs = []; bstsi = []; bstsj = []

    ns1 = set([])
    ns2 = set([])
    fs = []
    for sk in s:
        f,sia1,sia2 = sk.split(',')
        fs.append(f)
        ia1,ia2 = int(sia1),int(sia2)
        bsti,bstj,dmij,Sij = get_dm(f, ia1, ia2, icomb, ioverlap)
        bstsi.append(bsti); bstsj.append(bstj); dmijs.append(dmij); Ss.append(Sij)
        nb1, nb2 = dmij.shape
        ns1.update([nb1])
        ns2.update([nb2])

    if len(ns1) > 1 or len(ns2) > 1 or (not idiff):
        for k,f in enumerate(fs):
            so = ''
            dmij = dmijs[k] if not ioverlap else Ss[k]
            bsti = bstsi[k]; bstj = bstsj[k]
            nb1, nb2 = dmij.shape
            print ' -- file = ', f
            print ' '*9 + ''.join( ['%9s'%bsj for bsj in bstj ] )
            vs = np.abs(dmij)
            for p in range(nb1):
                so += '%9s'%bsti[p]
                for q in range(nb2):
                    spq = '%9.5f'%dmij[p,q]
                    if vs[p,q] > 0.005: spq = colored(spq,'red')
                    so += spq
                so += '\n'
            print so
    else:
        so = ''
        assert len(ns1) == 1 and len(ns2) == 1 and n == 2
        if iratio:
            denom = dmijs[0]
            thresh = 0.1
        else:
            denom = 1.0
            thresh = 0.005
        dmij = (dmijs[1] - dmijs[0])/denom
        bsti = bstsi[0]; bstj = bstsj[0]
        vs = np.abs(dmij)
        nb1, nb2 = dmij.shape
        print ' '*9 + ''.join( ['%9s'%bsj for bsj in bstj ] )
        for p in range(nb1):
            so += '%9s'%bsti[p]
            for q in range(nb2):
                spq = '%9.5f'%dmij[p,q]
                if vs[p,q] > thresh: spq = colored(spq,'red')
                so += spq
            so += '\n'
        print so

