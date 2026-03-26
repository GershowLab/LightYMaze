#install openblas on pi
#sudo apt-get install -y libopenblas-dev


import numpy as np

class AffineCalculator:
    def __init__(self, srcpts=None,dstpts=None):
        self._src = []
        self._dst = []
        self.fwdmat = np.eye(3)
        self.revmat = self.fwdmat.copy()
        if srcpts is not None and dstpts is not None:
            self.add_pair_list(srcpts, dstpts)
            self.calculate()

        #[x(:) y(:) <z(:)> 1]*F = dst

    def add_pair(self, src, dst):
        self._src.append(src)
        self._dst.append(dst)

    def add_pair_list(self, srclist, dstlist):
        for src, dst in zip(srclist, dstlist):
            self.add_pair(src, dst)

    @staticmethod
    def prep_vec(v):
        v = np.array(v).copy()
        sh = np.asarray(v.shape)
        sh[-1] = sh[-1] + 1
        vv = np.ones(sh)
        vv[:,:-1] = v
        return vv

    def calculate(self):
        if self._src == [] or self._dst == []:
            return
        s = self.prep_vec(self._src)
        d = self.prep_vec(self._dst)
        dim = s.shape[1] - 1
        if s.shape[0] < s.shape[1]:
            return #not enough pts
        self.fwdmat = (np.linalg.pinv(s)@d).astype(np.float32)
        self.revmat = (np.linalg.pinv(d)@s).astype(np.float32)
        #
        # self.fwdrot = self.fwdmat[:dim,:dim]
        # self.fwdoffset = self.fwdmat[-1,:dim]
        # self.revrot = self.revmat[:dim,:dim]
        # self.revoffset = self.revmat[-1,:dim]

#Specific NumPy/Hardware bug (macOS M4/M3 chips): There is a known issue where NumPy versions 2.0.0+ on M4 Macs (and potentially M3s) with certain BLAS (Basic Linear Algebra Subprograms) implementations (like Accelerate or OpenBLAS 0.3.30) incorrectly trigger this warning during matrix multiplication due to the use of SME (Scalable Matrix Extension).

    @staticmethod
    def transform(mat, x, y, z = None):
        xx = np.asarray(x, np.float32).flatten().reshape(-1,1)
        yy = np.asarray(y, np.float32).flatten().reshape(-1,1)
        o = np.ones_like(xx)
        if z is None:
            v = np.hstack((xx,yy,o))
        else:
            zz = np.asarray(z, np.float32).flatten().reshape(-1, 1)
            v = np.hstack((xx,yy,zz,o))
        dd = v@mat
        xx = np.reshape(dd[:,0],x.shape)
        yy = dd[:,1].reshape(y.shape)
        if z is None:
            return xx,yy
        else:
            return xx,yy, d[:,2].reshape(z.shape)

    def transform_fwd(self, x, y, z = None):
        return self.transform(self.fwdmat, x, y, z)
    def transform_rev(self, x, y, z = None):
        return self.transform(self.revmat, x, y, z)


    def transform_ptlist(self, srcx):
        v = self.prep_vec(srcx)
        dim = v.shape[1] - 1
        d = v@self.fwdmat
        return d[:,:dim]

    def itransform_ptlist(self, dstx):
        v = self.prep_vec(dstx)
        dim = v.shape[1] - 1
        s = v@self.revmat
        return s[:,:dim]


if __name__ == "__main__":
    F = np.array(((1,1,0),(1,1,0), (-2,3, 1)))
    srcpts = [(0,0), (1,0), (0,1), (1,1)]
    s = AffineCalculator.prep_vec(srcpts)
    print(s)
    d = s@F

    print(d)

    dstpts = d[:,:2]

    ac = AffineCalculator()
    for s,d in zip(srcpts,dstpts):
        ac.add_pair(s,d)

    ac.calculate()

    print(F)
    print(ac.fwdmat)

    print(dstpts)
    print(ac.transform(srcpts))

    print(srcpts)
    print(ac.itransform(dstpts))





