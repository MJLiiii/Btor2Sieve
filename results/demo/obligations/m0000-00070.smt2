(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_5 () (_ BitVec 8))
(assert
 (not (= (ite (bvuge s_5 (_ bv20 8)) (_ bv1 1) (_ bv0 1)) (_ bv1 1))))
(assert
 (let (($x69 (bvsge s_5 (_ bv1 8))))
(not $x69)))
(check-sat)
