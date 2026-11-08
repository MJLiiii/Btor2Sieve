(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_7 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x212 (bvsle i_7 (_ bv255 8))))
(not $x212)))
(check-sat)
