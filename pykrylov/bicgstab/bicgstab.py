
__docformat__ = 'restructuredtext'

import numpy as np
from math import sqrt

from pykrylov.generic import KrylovMethod

class BiCGSTAB( KrylovMethod ):
    """
    A pure Python implementation of the bi-conjugate gradient stabilized
    (Bi-CGSTAB) algorithm. Bi-CGSTAB may be used to solve unsymmetric systems
    of linear equations, i.e., systems of the form

        A x = b

    where the matrix A is unsymmetric and nonsingular.

    Bi-CGSTAB requires 2 matrix-vector products, 6 dot products and 6 daxpys
    per iteration.

    In addition, if a preconditioner is supplied, it needs to solve 2
    preconditioning systems per iteration.

    This implementation is a preconditioned version of that given in [Kelley].


    .. [Kelley] C. T. Kelley, *Iterative Methods for Linear and Nonlinear
                Equations*, number 16 in *Frontiers in Applied Mathematics*,
                SIAM, Philadelphia, 1995.
    """

    def __init__(self, matvec, **kwargs):
        KrylovMethod.__init__(self, matvec, **kwargs)

        self.prefix = 'Bi-CGSTAB: '
        self.name = 'Bi-CGSTAB'

    def solve(self, rhs, **kwargs):
        """
        Solve a linear system with `rhs` as right-hand side by the Bi-CGSTAB
        method. The vector `rhs` should be a Numpy array. An optional argument
        `guess` may be supplied, with an initial guess as a Numpy array. By
        default, the initial guess is the vector of zeros.
        """
        n = rhs.shape[0]
        nMatvec = 0

        # Initial guess is zero unless one is supplied
        guess_supplied = 'guess' in kwargs.keys()
        x = kwargs.get('guess', np.zeros(n))

        # Initial residual is the fixed vector
        r0 = rhs
        if guess_supplied:
            r0 = rhs - self.matvec(x)
            nMatvec += 1

        rho = alpha = omega = 1.0
        rho_next = np.dot(r0,r0)
        residNorm = self.residNorm0 = sqrt(rho_next)
        threshold = max( self.abstol, self.reltol * self.residNorm0 )

        finished = (residNorm <= threshold or nMatvec >= self.matvec_max)

        if self.verbose:
            self._write('Initial residual = %8.2e\n' % self.residNorm0)
            self._write('Threshold = %8.2e\n' % threshold)
            hdr = '%6s  %8s' % ('Matvec', 'Residual')
            self._write(hdr + '\n')
            self._write('-' * len(hdr) + '\n')

        if not finished:
            r = r0.copy()
            p = np.zeros(n)
            v = np.zeros(n)

        while not finished:

            beta = rho_next/rho * alpha/omega
            rho = rho_next

            # Update p in-place
            p *= beta
            p -= beta * omega * v
            p += r

            # Compute preconditioned search direction
            if self.precon is not None:
                q = self.precon(p)
            else:
                q = p

            v = self.matvec(q) ; nMatvec += 1

            alpha = rho/np.dot(r0, v)
            s = r - alpha * v

            # Check for CGS termination
            residNorm = sqrt(np.dot(s,s))

            if self.verbose:
                self._write('%6d  %8.2e\n' % (nMatvec, residNorm))

            if residNorm <= threshold:
                x += alpha * q
                finished = True
                continue

            if nMatvec >= self.matvec_max:
                finished = True
                continue

            if self.precon is not None:
                z = self.precon(s)
            else:
                z = s

            t = self.matvec(z) ; nMatvec += 1
            omega = np.dot(t,s)/np.dot(t,t)
            rho_next = -omega * np.dot(r0,t)

            # Update residual
            r = s - omega * t
            
            # Update solution in-place-ish. Note that 'z *= omega' alters s if
            # precon = None. That's ok since s is no longer needed in this iter.
            # 'q *= alpha' would alter p.
            z *= omega
            x += z
            x += alpha * q

            residNorm = sqrt(np.dot(r,r))

            if self.verbose:
                self._write('%6d  %8.2e\n' % (nMatvec, residNorm))

            if residNorm <= threshold or nMatvec >= self.matvec_max:
                finished = True
                continue


        self.nMatvec = nMatvec
        self.bestSolution = x
        self.residNorm = residNorm
