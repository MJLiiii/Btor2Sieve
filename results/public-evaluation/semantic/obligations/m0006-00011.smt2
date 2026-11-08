(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_4 () (_ BitVec 4))
(assert
 (not (= (ite (= (_ bv15 4) s_4) (_ bv1 1) (_ bv0 1)) (_ bv1 1))))
(assert
 (let (($x283 (and (distinct s_4 (_ bv0 4)) true)))
(not $x283)))
(check-sat)
