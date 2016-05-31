r"""
Reed-Muller code

Given integers `m, r` and a finite field `F` 
corresponding Reed Muller Code is the set:

.. math::

    \{ (f(\alpha_1), f(\alpha_2), \ldots, f(\alpha_n)  \mid  f \in F[x_1,x_2,\ldots,x_m], \deg f < r \}

This file contains the following elements:

    - :class:`QAryReedMullerCode`, the class for Reed Muller codes over non-binary field of size q and `r<q`
    - :class:`BinaryReedMullerCode`, the class for Reed Muller codes over binary field and `r<=m` 
    - :class:`ReedMullerVectorEncoder`, an encoder with a vectorial message space (for both the two code classes)
    - :class:`ReedMullerPolynomialEncoder`, an encoder with a polynomial message space (for both the code classes)
"""
#*****************************************************************************
#       Copyright (C) 2016 Parthasarathi Panda <parthasarathipanda314@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#                  http://www.gnu.org/licenses/
#*****************************************************************************

from operator import mul
from sage.matrix.constructor import matrix
from sage.functions.other import binomial
from sage.calculus.var import var
from sage.misc.functional import symbolic_sum
from sage.coding.linear_code import AbstractLinearCode, LinearCodeSyndromeDecoder
from sage.coding.encoder import Encoder
from sage.combinat.subset import Subsets
from sage.combinat.tuple import Tuples
from sage.rings.finite_rings.finite_field_constructor import GF
from sage.rings.finite_rings.finite_field_base import FiniteField
from sage.rings.integer import Integer
from sage.modules.free_module_element import vector
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing

from sage.interfaces.gap import gfq_gap_to_sage

#to compute the sum of n chose i where i ranges from 0 to k
r"""
Given ``n`` and ``k``, computes the sum of first `k+1` terms of the binomial expansion of `n`. Used to compute dimension of binomial reed muller code.
EXAMPLES:
    
    sage:binomialSum(5,3)
    26

"""
def binomialSum(n,k):
    s=1
    nCi=1
    for i in range(k):
        nCi=((n-i)*nCi)/(i+1)
        s=nCi+s
    return s
r"""
Given the evaluation of a multivariate polynomial of certain number of variables and certain degree over `F` on every point, this function returns the polynomial. 
INPUT:

    - ``evaluation`` -- A vector or a list of evaluation of the polynomial at all the points.

    - ``numberOfVariable`` -- The number of variables used in polynomial (i.e. `m`).

    - ``order`` -- The degree of the polynomial in question.

    - ``q`` -- The size of the finite field 

    - ``finiteField`` -- The finite field over which the computations are done

    - ``_R`` -- The Polynomial Ring the polynomial in question is from 
EXAMPLES:
    
    sage: F=GF(3)
    sage: R.<x0,x1>=F[]
    sage: multivariatePolynomialInterpolation([1, 2, 0, 0, 2, 1, 1, 1, 1], 2, 2, 3, F, R)
    x0*x1+x1^2+x0+x1+1
"""
def multivariatePolynomialInterpolation(evaluation, numberOfVariable, order, q, finiteField, _R):
    if numberOfVariable==0 or order==0:
        return evaluation[0]
    xcordinate=finiteField.list()
    nq=q**(numberOfVariable-1)
    d=min(order+1,q)
    evaluation2=[]
    uniPolyRing=PolynomialRing(finiteField,'x')
    for k in range(nq):
        points=[(xcordinate[i], evaluation[k+i*nq]) for i in range(q)]
        polyVector=uniPolyRing.lagrange_polynomial(points).coefficients(sparse=False)
        if len(polyVector)<d:
            #adding zeros to represet a (d-1) degree polynomial
            polyVector=polyVector+[0 for i in range(d-len(polyVector))]
        evaluation2.append(polyVector)
    poly=0
    z=1
    x=_R.gen(numberOfVariable-1)
    for k in range(d):#computing the polynomial
        poly=poly+z*multivariatePolynomialInterpolation([evaluation2[i][k] for i in range(nq)], numberOfVariable-1, order-k, q, finiteField, _R)
        z=z*x
    return poly

r"""
Returns of a Reed Muller code. If the given field is binary it returns a binary Reed Muller code, otherwise it returns a q-ary Reed MUller Code.

INPUT:

- ``baseField`` -- The finite field `F` over which code is built.

- ``order`` -- The order of the Reed Muller Code, i.e., the maximum degree of the polynomial to be used in the code.

- ``numberOfVariable`` -- The number of variables used in polynomial (i.e. `m`).

EXAMPLES:

A Reed-Muller code can be constructed by using a predefined field or using the value of q::

    sage: F = GF(3)
    sage: C = codes.ReedMullerCode(F, 2, 2)
    sage: C
    3-ary Reed Muller Code of order 2 and number of variables 2

Simmilarly, using the finite field `F` of size 2 we can generate a binary reed muller code 

    sage: F = GF(2)
    sage: C = codes.ReedMullerCode(F, 2, 2)
    sage: C
    Binary Reed Muller Code of order 2 and number of variables 2

"""
def ReedMullerCode(baseField, order, numberOfVariable):
    if not(isinstance(baseField,FiniteField)):
        raise ValueError("Incorrect data-type of input: The parameter `baseField` must be a finite")
    q=baseField.cardinality()
    if q == 2:
        return BinaryReedMullerCode(order, numberOfVariable)
    else:
        return QAryReedMullerCode(baseField, order, numberOfVariable)

class QAryReedMullerCode(AbstractLinearCode):
    r"""
    Representation of a q-ary Reed Muller code with `r<q`.

    INPUT:

    - ``baseField`` -- The finite field `F` or the size of finite field `F` over which code is built.

    - ``order`` -- The order of the Reed Muller Code, i.e., the maximum degree of the polynomial to be used in the code.

    - ``numberOfVariable`` -- The number of variables used in polynomial (i.e. `m`).

    EXAMPLES:

    A Reed-Muller code can be constructed by using a predefined field or using the value of q::

        sage: F = GF(3)
        sage: C = codes.QAryReedMullerCode(F, 2, 2)
        sage: C
        3-ary Reed Muller Code of order 2 and number of variables 2
    """

    _registered_encoders={}
    _registered_decoders={}

    def __init__(self, baseField, order, numberOfVariable):
        r"""
        TESTS:

        If the order given is greater than (q-1) an error is raised

            sage: C = codes.QAryReedMullerCode(GF(3), 4, 4)
            Traceback (most recent call last):
            ...
            ValueError: The order must be less than 3

        The order and the number of variable must be integers

            sage: C = codes.QAryReedMullerCode(GF(3),1.1,4)
            Traceback (most recent call last):
            ...
            ValueError: Incorrect data-type of input: The order of the code must be an integer

        The baseField parameter must be a finite field
            sage: C = codes.QAryReedMullerCode(QQ,1,4)
            Traceback (most recent call last):
            ...
            Incorrect data-type of input: Incorrect data-type of input: the input `baseField` must be a finiteField
        """
        #input sanitization
        if not(isinstance(baseField,FiniteField)):
            raise ValueError("Incorrect data-type of input: the input `baseField` must be a finiteField")
        if not(isinstance(order,Integer)):
            raise ValueError("Incorrect data-type of input: The order of the code must be an integer")
        if not(isinstance(numberOfVariable, Integer)):
            raise ValueError("Incorrect data-type of input: The number of variables must be an integer")
        q=baseField.cardinality()
        if (order>=q):
            raise ValueError("The order must be less than %s" % q)

        super(QAryReedMullerCode, self).__init__(baseField,q**numberOfVariable,"EvaluationVector","Syndrome")
        self.order=order
        self.numberOfVariable=numberOfVariable
        self.q=q
        self._dimension=binomial(numberOfVariable+order, order)

    def _repr_(self):
        r"""
        Returns a string representation of ``self``.

        EXAMPLES::

            sage: F = GF(59)
            sage: C = codes.QAryReedMullerCode(F, 2, 4)
            sage: C
            59-ary Reed Muller Code of order 2 and number of variables 4
        """
        return "%s-ary Reed Muller Code of order %s and number of variables %s" % (self.q, self.order, self.numberOfVariable)

    def _latex_(self):
        r"""
        Returns a latex representation of ``self``.

        EXAMPLES::

            sage: F = GF(59)
            sage: C = codes.QAryReedMullerCode(F, 2, 4)
            sage: latex(C)
            59\textnormal{-ary Reed Muller Code of order} 2 \textnormal{and number of variables} 4
        """
        return "%s\textnormal{-ary Reed Muller Code of order} %s \textnormal{and number of variables} %s" % (self.q, self.order, self.numberOfVariable)

    def __eq__(self,other):
        r"""
        Tests equality between Reed-Muller Code objects.

        EXAMPLES::

            sage: F = GF(59)
            sage: C1 = codes.QAryReedMullerCode(F, 2, 4)
            sage: C2 = codes.QAryReedMullerCode(GF(59), 2, 4)
            sage: C1.__eq__(C2)
            True
        """
        return (isinstance(other, QAryReedMullerCode)) and self.q==other.q and self.order==other.order and self.numberOfVariable==other.numberOfVariable

class BinaryReedMullerCode(AbstractLinearCode):
    r"""
    Representation of a binary Reed Muller code with `r<=m`.

    INPUT:

    - ``order`` -- The order of the Reed Muller Code, i.e., the maximum degree of the polynomial to be used in the code.

    - ``numberOfVariable`` -- The number of variables used in polynomial (i.e. `m`).

    EXAMPLES:

    A binary Reed-Muller code can be constructed by simply giving the order of the code and the number of variables::

        sage: C = codes.binaryReedMullerCode(2, 4)
        sage: C
        Binary Reed Muller Code of order 2 and number of variables 4
    """

    _registered_encoders={}
    _registered_decoders={}

    def __init__(self, order, numberOfVariable, old_input = False):
        r"""
        TESTS:

        If the order given is greater than the number of variables an error is raised

            sage: C = codes.BinaryReedMullerCode(5, 4)
            Traceback (most recent call last):
            ...
            ValueError: The order must be less than or equal to 4

        The order and the number of variable must be integers

            sage: C = codes.BinaryReedMullerCode(1.1,4)
            Traceback (most recent call last):
            ...
            ValueError: Incorrect data-type of input: The order of the code must be an integer
        """
        #if (old_input = False):
        #input sanitization
        if not(isinstance(order,Integer)):
            raise ValueError("Incorrect data-type of input: The order of the code must be an integer")
        if not(isinstance(numberOfVariable, Integer)):
            raise ValueError("Incorrect data-type of input: The number of variables must be an integer")
        if (numberOfVariable<order):
            raise ValueError("The order must be less than or equal to %s" % numberOfVariable)

        super(BinaryReedMullerCode, self).__init__(GF(2), 2**numberOfVariable,"EvaluationVector","Syndrome")
        self.order=order
        self.numberOfVariable=numberOfVariable
        self.q=2
        self._dimension=binomialSum(numberOfVariable,order)
        #else:
        #    F = GF(2)
        #    gap.load_package("guava")
        #    gap.eval("C:=ReedMullerCode("+str(r)+", "+str(k)+")")
        #    gap.eval("G:=GeneratorMat(C)")
        #    k = int(gap.eval("Length(G)"))
        #    n = int(gap.eval("Length(G[1])"))
        #    G = [[gfq_gap_to_sage(gap.eval("G["+str(i)+"]["+str(j)+"]"),F) for j in range(1,n+1)] for i in range(1,k+1)]
        #    MS = MatrixSpace(F,k,n)
        #    return LinearCode(MS(G))

    def _repr_(self):
        r"""
        Returns a string representation of ``self``.

        EXAMPLES::

            sage: C = codes.BinaryReedMullerCode(2, 4)
            sage: C
            Binary Reed Muller Code of order 2 and number of variables 4
        """
        return "Binary Reed Muller Code of order %s and number of variables %s" % (self.order, self.numberOfVariable)

    def _latex_(self):
        r"""
        Returns a latex representation of ``self``.

        EXAMPLES::

            sage: C = codes.BinaryReedMullerCode(2, 4)
            sage: latex(C)
            \textnormal{Binary Reed Muller Code of order} 2 \textnormal{and number of variables} 4
        """
        return "\textnormal{Binary Reed Muller Code of order} %s \textnormal{and number of variables} %s" % (self.q, self.order, self.numberOfVariable)

    def __eq__(self,other):
        r"""
        Tests equality between Reed-Muller Code objects.

        EXAMPLES::

            sage: C1 = codes.BinaryReedMullerCode(2, 4)
            sage: C2 = codes.BinaryReedMullerCode(2, 4)
            sage: C1.__eq__(C2)
            True
        """
        return (isinstance(other, BinaryReedMullerCode)) and self.order==other.order and self.numberOfVariable==other.numberOfVariable

class ReedMullerVectorEncoder(Encoder):
    r"""
    Encoder for Reed-Muller codes which encodes vectors into codewords.

    INPUT:

    - ``code`` -- The associated code of this encoder.

    EXAMPLES::

        sage: C1=ReedMullerCode(GF(2), 2, 4)
        sage: E1=ReedMullerVectorEncoder(C1)
        sage: E1
        Evaluation vector-style encoder for Binary Reed Muller Code of order 2 and number of variables 4
        sage: C2=ReedMullerCode(GF(3), 2, 2)
        sage: E2=ReedMullerVectorEncoder(C2)
        sage: E2
        Evaluation vector-style encoder for 3-ary Reed Muller Code of order 2 and number of variables 2

    Actually, we can construct the encoder from ``C`` directly::

        sage: E = C1.encoder("EvaluationVector")
        sage: E
        Evaluation vector-style encoder for Binary Reed Muller Code of order 2 and number of variables 4
    """

    def __init__(self, code):
        r"""
        TESTS:

        If ``code`` is not a GRS code, an error is raised::

            sage: C  = codes.RandomLinearCode(10, 4, GF(11))
            sage: codes.encoders.ReedMullerVectorEncoder(C)
            Traceback (most recent call last):
            ...
            ValueError: code has to be a Reed Muller Code
        """
        if not (isinstance(code, QAryReedMullerCode) or isinstance(code, BinaryReedMullerCode)):
            raise ValueError("code has to be a Reed Muller code")
        super(ReedMullerVectorEncoder, self).__init__(code)
        baseField=code.base_field()
        order=code.order
        numberOfVariable=code.numberOfVariable
        q=code.q
        baseFieldTuple=Tuples(baseField.list(),numberOfVariable)
        exponents=Subsets(range(numberOfVariable)*(q-1), submultiset=True)[0:code.dimension()]
        self.generator = matrix(baseField, [[reduce(mul, [x[i] for i in exponent],1) for x in baseFieldTuple.list()] for exponent in exponents])

    def _repr_(self):
        r"""
        Returns a string representation of ``self``.

        EXAMPLES::

            sage: F = GF(59)
            sage: C = codes.ReedMullerCode(F, 2, 4)
            sage: E=codes.encoders.ReedMullerVectorEncoder(C)
            sage: E
            Evaluation vector-style encoder for 59-ary Reed Muller Code of order 2 and number of variables 4
        """
        return "Evaluation vector-style encoder for %s" % self.code()

    def _latex_(self):
        r"""
        Returns a string representation of ``self``.

        EXAMPLES::

            sage: F = GF(59)
            sage: C = codes.ReedMullerCode(F, 2, 4)
            sage: E=codes.encoders.ReedMullerVectorEncoder(C)
            sage: latex(E)
            \textnormal{Evaluation vector-style encoder for }59\textnormal{-ary Reed Muller Code of order} 2 \textnormal{and number of variables} 4
        """
        return "\textnormal{Evaluation vector-style encoder for }%s" % self.code()._latex_()

    def __eq__(self,other):
        r"""
        Tests equality between ReedMullerVectorEncoder objects.

        EXAMPLES::

            sage: F = GF(59)
            sage: C = codes.ReedMullerCode(F, 2, 4)
            sage: D1 = codes.encoders.ReedMullerVectorEncoder(C)
            sage: D2 = codes.encoders.ReedMullerVectorEncoder(C)
            sage: D1.__eq__(D2)
            True
            sage: D1 is D2
            False
        """
        return (isinstance(other, ReedMullerVectorEncoder)) and self.code==other.code

    def generator_matrix(self):
        r"""
        Returns a generator matrix of ``self``

        EXAMPLES::

            sage: F = GF(3)
            sage: C = codes.ReedMullerCode(F, 2, 2)
            sage: E = codes.encoders.GRSEvaluationVectorEncoder(C)
            sage: E.generator_matrix()
            [1 1 1 1 1 1 1 1 1]
            [0 1 2 0 1 2 0 1 2]
            [0 0 0 1 1 1 2 2 2]
            [0 1 1 0 1 1 0 1 1]
            [0 0 0 0 1 2 0 2 1]
            [0 0 0 1 1 1 1 1 1]
        """
        return self.generator

class ReedMullerPolynomialEncoder(Encoder):
    r"""
    Encoder for Reed-Muller codes which encodes appropiate multivariate polynomials into codewords.

    INPUT:

    - ``code`` -- The associated code of this encoder.

    EXAMPLES::

        sage: C1=ReedMullerCode(GF(2), 2, 4)
        sage: E1=ReedMullerPolynomialEncoder(C1)
        sage: E1
        Evaluation polynomial-style encoder for Binary Reed Muller Code of order 2 and number of variables 4
        sage: C2=ReedMullerCode(GF(3), 2, 2)
        sage: E2=ReedMullerPolynomialEncoder(C2)
        sage: E2
        Evaluation polynomial-style encoder for 3-ary Reed Muller Code of order 2 and number of variables 2

    We can also pass a predefined polynomial ring

        sage: R=PolynomialRing(GF(3), 2, 'y')
        sage: C=ReedMullerCode(GF(3), 2, 2)
        sage: E=ReedMullerPolynomialEncoder(C, R)
        sage: E 
        Evaluation polynomial-style encoder for 3-ary Reed Muller Code of order 2 and number of variables 2

    Actually, we can construct the encoder from ``C`` directly::

        sage: E = C1.encoder("EvaluationPolynomial")
        sage: E
        Evaluation polynomial-style encoder for encoder for Binary Reed Muller Code of order 2 and number of variables 4
    """

    def __init__(self, code, _R='default'):
        r"""
        TESTS:

        If ``code`` is not a GRS code, an error is raised::

            sage: C  = codes.RandomLinearCode(10, 4, GF(11))
            sage: codes.encoders.ReedMullerPolynomialEncoder(C)
            Traceback (most recent call last):
            ...
            ValueError: code has to be a Reed Muller Code
        
        If the polynomial ring passed is not according to the requirement (over a different field or different number of variables) then an error is raise::

            sage: F=GF(59)
            sage: R.<x,y,z,w>=F[]
            sage: C=codes.ReedMullerCode(F, 2, 3)
            sage: E=codes.encoders.ReedMullerPolynomialEncoder(C, R)
            Traceback (most recent call last):
            ...
            The Polynomial ring should be on Finite Field of size 59 and should have 3 variables
        """
        if not (isinstance(code, QAryReedMullerCode) or isinstance(code, BinaryReedMullerCode)):
            raise ValueError("code has to be a Reed Muller code")
        super(ReedMullerPolynomialEncoder, self).__init__(code)
        if (_R=='default'):
            self._R=PolynomialRing(code.base_field(), code.numberOfVariable, 'x')
        else:
            if (_R.base_ring()==code.base_field()) and (len(_R.variable_names())==code.numberOfVariable):
                self._R=_R
            else:
                raise ValueError("The Polynomial ring should be on %s and should have %s variables" % (code.base_field(), code.numberOfVariable))

    def _repr_(self):
        r"""
        Returns a string representation of ``self``.

        EXAMPLES::

            sage: F = GF(59)
            sage: C = codes.ReedMullerCode(F, 2, 4)
            sage: E=codes.encoders.ReedMullerPolynomialEncoder(C)
            sage: E
            Evaluation polynomial-style encoder for 59-ary Reed Muller Code of order 2 and number of variables 4
        """
        return "Evaluation polynomial-style encoder for %s" % self.code()

    def _latex_(self):
        r"""
        Returns a string representation of ``self``.

        EXAMPLES::

            sage: F = GF(59)
            sage: C = codes.ReedMullerCode(F, 2, 4)
            sage: E=codes.encoders.ReedMullerPolynomialEncoder(C)
            sage: latex(E)
            \textnormal{Evaluation polynomial-style encoder for }59\textnormal{-ary Reed Muller Code of order} 2 \textnormal{and number of variables} 4
        """
        return "\textnormal{Evaluation polynomial-style encoder for }%s" % self.code()._latex_()

    def __eq__(self,other):
        r"""
        Tests equality between ReedMullerVectorEncoder objects.

        EXAMPLES::

            sage: F = GF(59)
            sage: C = codes.ReedMullerCode(F, 2, 4)
            sage: D1 = codes.encoders.ReedMullerPolynomialEncoder(C)
            sage: D2 = codes.encoders.ReedMullerPolynomialEncoder(C)
            sage: D1.__eq__(D2)
            True
            sage: D1 is D2
            False
        """
        return (isinstance(other, ReedMullerPolynomialEncoder)) and self.code==other.code

    def encode(self, p):
        r"""
        Transforms the polynomial ``p`` into a codeword of :meth:`code`.

        INPUT:

        - ``p`` -- A polynomial from the message space of ``self`` of degree
          less than ``self.code().order``.

        OUTPUT:

        - A codeword in associated code of ``self``

        EXAMPLES::

            sage: F = GF(3)
            sage: m = 4
            sage: Fx.<x0,x1> = F[]
            sage: C = codes.ReedMullerCode(F, 2, 2)
            sage: E = C.encoder("EvaluationPolynomial")
            sage: p = 1+x0+x1+x1^2+x1*x0
            sage: c = E.encode(p); c
            (1, 2, 0, 0, 2, 1, 1, 1, 1)
            sage: c in C
            True

        If a polynomial of too high degree is given, an error is raised::

            sage: p = x1^10
            sage: E.encode(p)
            Traceback (most recent call last):
            ...
            ValueError: The polynomial to encode must have degree at most 2

        If ``p`` is not an element of the proper polynomial ring, an error is raised::

            sage: Qy.<y1,y2> = QQ[]
            sage: p = y1^2 + 1
            sage: E.encode(p)
            Traceback (most recent call last):
            ...
            ValueError: The value to encode must be in Multivariate Polynomial Ring in x0, x1 over Finite Field of size 3
        """
        M = self.message_space()
        if p not in M:
            raise ValueError("The value to encode must be in %s" % M)
        C=self.code()
        if p.degree() > C.order:
            raise ValueError("The polynomial to encode must have degree at most %s" % C.order)
        baseFieldTuple = Tuples(C.base_field().list(), C.numberOfVariable)
        return vector(C.base_ring(), [p(x) for x in baseFieldTuple])
    
    def unencode_nocheck(self, c):
        r"""
        Returns the message corresponding to the codeword ``c``.

        Use this method with caution: it does not check if ``c``
        belongs to the code, and if this is not the case, the output is
        unspecified. Instead, use :meth:`unencode`.

        INPUT:

        - ``c`` -- A codeword of :meth:`code`.

        OUTPUT:

        - An polynomial of degree less than ``self.code().order``.

        EXAMPLES::

            sage: F = GF(3)
            sage: C = codes.ReedMullerCode(F, 2, 2)
            sage: E = C.encoder("EvaluationPolynomial")
            sage: c = vector(F, (1, 2, 0, 0, 2, 1, 1, 1, 1))
            sage: c in C
            True
            sage: p = E.unencode_nocheck(c); p
            x0*x1 + x1^2 + x0 + x1 + 1
            sage: E.encode(p) == c
            True

        Note that no error is thrown if ``c`` is not a codeword, and that the
        result is undefined::

            sage: c = vector(F, (1, 2, 0, 0, 2, 1, 1, 1, 0))
            sage: c in C
            False
            sage: p = E.unencode_nocheck(c); p
            x1^2 + x0 + x1 + 1
            sage: E.encode(p) == c
            False

        """
        return multivariatePolynomialInterpolation(c, self.code().numberOfVariable, self.code().order, self.code().q, self.code().base_field(), self._R)


    def message_space(self):
        r"""
        Returns the message space of ``self``

        EXAMPLES::

            sage: F = GF(11)
            sage: C = codes.ReedMullerCode(F, 2, 4)
            sage: E = C.encoder("EvaluationPolynomial")
            sage: E.message_space()
            Multivariate Polynomial Ring in x0, x1, x2, x3 over Finite Field of size 11
        """
        return self._R

QAryReedMullerCode._registered_encoders["EvaluationVector"] = ReedMullerVectorEncoder
QAryReedMullerCode._registered_encoders["EvaluationPolynomial"] = ReedMullerPolynomialEncoder

QAryReedMullerCode._registered_decoders["Syndrome"] = LinearCodeSyndromeDecoder

BinaryReedMullerCode._registered_encoders["EvaluationVector"] = ReedMullerVectorEncoder
BinaryReedMullerCode._registered_encoders["EvaluationPolynomial"] = ReedMullerPolynomialEncoder

BinaryReedMullerCode._registered_decoders["Syndrome"] = LinearCodeSyndromeDecoder
