(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_8 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x75 (bvsge i_8 (_ bv1 4))))
(not $x75)))
(check-sat)
