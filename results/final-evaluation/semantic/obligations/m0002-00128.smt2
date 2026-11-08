(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_117 () (_ BitVec 16))
(declare-fun i_4 () (_ BitVec 1))
(declare-fun s_5 () (_ BitVec 1))
(assert
 (let ((?x369 (ite (bvule s_117 ((_ zero_extend 15) (_ bv1 1))) (_ bv1 1) (_ bv0 1))))
 (let ((?x118 (bvxor i_4 ?x369)))
 (let ((?x6 (bvnot ?x118)))
 (let ((?x116 (bvor ?x6 ?x6)))
 (and (= (bvor s_5 (bvnot (bvnot s_5))) (_ bv1 1)) (= ?x116 (_ bv1 1))))))))
(assert
 (let ((?x369 (ite (bvule s_117 ((_ zero_extend 15) (_ bv1 1))) (_ bv1 1) (_ bv0 1))))
(let ((?x118 (bvxor i_4 ?x369)))
(let ((?x59 (bvnot s_5)))
(let (($x3248 (= ?x59 ?x118)))
(not $x3248))))))
(check-sat)
