(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_120 () (_ BitVec 16))
(declare-fun i_4 () (_ BitVec 1))
(declare-fun s_5 () (_ BitVec 1))
(assert
 (let ((?x2776 (ite (bvule s_120 ((_ zero_extend 15) (_ bv1 1))) (_ bv1 1) (_ bv0 1))))
(let ((?x496 (bvxor i_4 ?x2776)))
(let ((?x545 (bvnot ?x496)))
(let ((?x353 (bvor ?x545 ?x545)))
(and (= (bvor s_5 (bvnot (bvnot s_5))) (_ bv1 1)) (= ?x353 (_ bv1 1))))))))
(check-sat)
