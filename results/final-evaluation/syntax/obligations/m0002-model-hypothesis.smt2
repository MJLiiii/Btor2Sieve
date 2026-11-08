(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_117 () (_ BitVec 16))
(declare-fun i_4 () (_ BitVec 1))
(declare-fun s_5 () (_ BitVec 1))
(assert
 (let ((?x267 (ite (bvule s_117 ((_ zero_extend 15) (_ bv1 1))) (_ bv1 1) (_ bv0 1))))
(let ((?x234 (bvxor i_4 ?x267)))
(let ((?x173 (bvnot ?x234)))
(let ((?x169 (bvor ?x173 ?x173)))
(and (= (bvor s_5 (bvnot (bvnot s_5))) (_ bv1 1)) (= ?x169 (_ bv1 1))))))))
(check-sat)
