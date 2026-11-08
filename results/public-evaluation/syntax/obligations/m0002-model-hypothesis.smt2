(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_117 () (_ BitVec 16))
(declare-fun i_4 () (_ BitVec 1))
(declare-fun s_5 () (_ BitVec 1))
(assert
 (let ((?x122 (ite (bvule s_117 ((_ zero_extend 15) (_ bv1 1))) (_ bv1 1) (_ bv0 1))))
(let ((?x84 (bvxor i_4 ?x122)))
(let ((?x138 (bvnot ?x84)))
(let ((?x131 (bvor ?x138 ?x138)))
(and (= (bvor s_5 (bvnot (bvnot s_5))) (_ bv1 1)) (= ?x131 (_ bv1 1))))))))
(check-sat)
