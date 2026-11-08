(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_4 () (_ BitVec 1))
(declare-fun s_3 () (_ BitVec 1))
(assert
 (not (= (ite (= s_3 s_4) (_ bv1 1) (_ bv0 1)) (_ bv1 1))))
(assert
 (let (($x1617 (and (distinct s_4 (_ bv0 1)) true)))
(not $x1617)))
(check-sat)
