(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_4 () (_ BitVec 1))
(declare-fun s_3 () (_ BitVec 1))
(declare-fun s_11 () (_ BitVec 1))
(assert
 (let ((?x1089 (bvnot s_11)))
 (let ((?x53 (bvor ?x1089 (bvnot (ite (= s_3 s_4) (_ bv1 1) (_ bv0 1))))))
 (and (= ?x53 (_ bv1 1))))))
(assert
 (let (($x85 (= s_3 s_4)))
(not $x85)))
(check-sat)
