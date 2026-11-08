(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_6 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x5 (bvsge i_6 (_ bv1 8))))
(not $x5)))
(check-sat)
