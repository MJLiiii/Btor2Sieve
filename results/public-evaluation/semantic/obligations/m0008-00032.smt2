(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_4 () (_ BitVec 1))
(declare-fun s_3 () (_ BitVec 1))
(declare-fun s_11 () (_ BitVec 1))
(assert
 (let ((?x1621 (bvnot s_11)))
 (let ((?x2342 (bvor ?x1621 (bvnot (ite (= s_3 s_4) (_ bv1 1) (_ bv0 1))))))
 (and (= ?x2342 (_ bv1 1))))))
(assert
 (let (($x159 (= s_11 s_3)))
(not $x159)))
(check-sat)
