(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_7 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x6730 (bvsle i_7 (_ bv1 8))))
(not $x6730)))
(check-sat)
