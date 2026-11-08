(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_9 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x52 (bvsle i_9 (_ bv255 8))))
(not $x52)))
(check-sat)
