(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_9 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x174 (bvsge i_9 (_ bv0 8))))
(not $x174)))
(check-sat)
