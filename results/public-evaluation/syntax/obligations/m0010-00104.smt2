(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_6 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x1600 (bvsge i_6 (_ bv1 8))))
(not $x1600)))
(check-sat)
