(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_120 () (_ BitVec 16))
(declare-fun i_4 () (_ BitVec 1))
(declare-fun s_5 () (_ BitVec 1))
(assert
 (let ((?x1724 (ite (bvule s_120 ((_ zero_extend 15) (_ bv1 1))) (_ bv1 1) (_ bv0 1))))
(let ((?x1172 (bvxor i_4 ?x1724)))
(let ((?x973 (bvnot ?x1172)))
(let ((?x89 (bvor ?x973 ?x973)))
(and (= (bvor s_5 (bvnot (bvnot s_5))) (_ bv1 1)) (= ?x89 (_ bv1 1))))))))
(check-sat)
