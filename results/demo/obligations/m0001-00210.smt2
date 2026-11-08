(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_9 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x120 (bvuge i_9 (_ bv128 8))))
(not $x120)))
(check-sat)
